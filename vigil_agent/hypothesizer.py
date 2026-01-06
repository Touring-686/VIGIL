"""假设推理器 (Hypothesizer)

这是VIGIL框架的Speculative Reasoner组件，负责生成多条可能的执行路径。

设计原则：
1. Multi-Branch Reasoning: 对于每个决策点，生成多个可能的分支
2. Symbolic Tagging: 为每个分支打上符号化标签（风险、冗余度、必要性）
3. Lazy Evaluation: 不直接执行，而是生成假设供验证器裁决

防御场景：
- Type II-A: Reasoning Distortion via Tool Description
- Type II-B: Over-Optimization via "More Powerful" Tools
"""

import logging
from typing import Any

from pydantic import BaseModel

from vigil_agent.config import VIGILConfig
from vigil_agent.token_stats_tracker import TokenStatsTracker, get_global_tracker
from vigil_agent.types import ToolCallInfo

logger = logging.getLogger(__name__)


# ==============================================================================
# OpenAI Function Calling Schema for VIGIL Framework
# ==============================================================================
# VIGIL_TOOL_SCHEMA = [
#     {
#         "type": "function",
#         "function": {
#             "name": "submit_candidate_strategies",
#             "description": "Submit execution strategies based on VIGIL framework logic.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "strategies": {
#                         "type": "array",
#                         "items": {
#                             "type": "object",
#                             "properties": {
#                                 "choice_id": {
#                                     "type": "string",
#                                     "description": "Identifier like 'choice1', 'choice2'"
#                                 },
#                                 "tool_name": {
#                                     "type": "string",
#                                     "description": "The specific tool to call (or virtual tools: __response__, __internal_reasoning__, __step_skip__)"
#                                 },
#                                 "execution_args": {
#                                     "type": "array",
#                                     "description": "List of argument sets. Contains 1 item for single execution, or N items for iterative execution of the SAME function.",
#                                     "items": {
#                                         "type": "object",
#                                         "properties": {
#                                             "args": {
#                                                 "type": "object",
#                                                 "description": "Key-value arguments for the function."
#                                             },
#                                             "verification_metadata": {
#                                                 "type": "object",
#                                                 "properties": {
#                                                     "operation_type": {
#                                                         "type": "string",
#                                                         "enum": ["READ", "WRITE", "SEARCH", "COMMUNICATE", "TRANSACT", "BOOK", "GRANT_ACCESS", "REASONING"]
#                                                     },
#                                                     "information_flow": {"type": "object"}
#                                                 },
#                                                 "required": ["operation_type", "information_flow"]
#                                             },
#                                             "reasoning": {"type": "string"}
#                                         },
#                                         "required": ["args", "verification_metadata", "reasoning"]
#                                     }
#                                 }
#                             },
#                             "required": ["choice_id", "tool_name", "execution_args"]
#                         }
#                     }
#                 },
#                 "required": ["strategies"]
#             }
#         }
#     }
# ]

VIGIL_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "submit_candidate_strategies",
            "description": "Submit execution strategies based on VIGIL framework logic.",
            "strict": True,  # 【关键点1】开启严格模式
            "parameters": {
                "type": "object",
                "properties": {
                    "strategies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "choice_id": {
                                    "type": "string",
                                    "description": "Identifier like 'choice1', 'choice2'"
                                },
                                "tool_name": {
                                    "type": "string",
                                    "description": "The specific tool to call (or virtual tools: __response__, __internal_reasoning__, __step_skip__)"
                                },
                                "operation_type": {
                                    "type": "string",
                                    "description": "Type of operation being performed",
                                    "enum": ["READ", "WRITE", "SEARCH", "COMMUNICATE", "TRANSACT", "BOOK", "GRANT_ACCESS", "REASONING"]
                                },
                                "execution_args": {
                                    "type": "array",
                                    "description": "List of argument sets. Contains 1 item for single execution, or N items for iterative execution of the SAME function.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "args": {
                                                "type": "object",
                                                "description": "Key-value arguments for the function.",
                                                "additionalProperties": True # args 内容动态变化，此处无法 strict，但外层结构已锁死
                                            },
                                            "information_flow": {
                                                "type": "object",
                                                "description": "Data flow mapping from source to argument, format: argument_name: 'Source -> Target'",
                                                "additionalProperties": {"type": "string"}
                                            },
                                            "reasoning": {"type": "string"}
                                        },
                                        "required": ["args", "information_flow", "reasoning"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["choice_id", "tool_name", "operation_type", "execution_args"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["strategies"], # 【关键点3】所有字段必填
                "additionalProperties": False
            }
        }
    }
]


# ==============================================================================
# Optimized System Prompt for _reason_tool_paths_v2 (Function Calling)
# ==============================================================================
OPTIMIZED_HYPOTHESIZER_PROMPT = """[ROLE]
You are the **Speculative Reasoner (Hypothesizer)** within the VIGIL framework.
Your task is to determine the best execution method for the **[Current Abstract Step]** based on available resources.

[INPUT CONTEXT]
1. **User Intent**: "{user_intent}"
2. **Current Abstract Step**:
   - Type: {current_step_type}
   - Description: {current_step_description}
   - Allowed Capabilities: {current_step_capabilities}
3. **Execution History (Observations)**:
{execution_history_text}
4. **Available Tools (Docstrings)**:
{tools_text}

[CRITICAL INSTRUCTIONS - EXECUTION HIERARCHY]

You MUST evaluate the following priorities in strict order (0 -> 1 -> 2 -> 3) and submit your decision by calling the function `submit_candidate_strategies`.

**PRIORITY 0: FINAL USER RESPONSE (Check First)**
- **Condition**: Does the [Current Abstract Step] type equal `GENERATE_FINAL_ANSWER` or `REPORT_RESULTS`?
- **Action**: Use `tool_name`: `"__response__"`.
- **Logic**: Synthesize final text based on History.

**PRIORITY 1: EXTERNAL TOOL EXECUTION**
- **Condition**: Does one or more tools exist that can retrieve the **Target Entity** or perform the **Core Action**?
- **Multi-Candidate Strategy**: If multiple distinct tools apply, return them as separate strategies (choice1, choice2).
- **Iterative Strategy (List -> Scalar Mismatch)**:
  - If the tool expects a **Single Value** but input data is a **List**:
  - Keep a SINGLE strategy (e.g., choice1).
  - Inside `execution_args`, generate **MULTIPLE** objects (one for each list item).

**PRIORITY 2: INTERNAL REASONING (Fallback)**
- **Condition**: Priority 0 and 1 failed. Step involves logic/extraction using ONLY History.
- **Action**: Use `tool_name`: `"__internal_reasoning__"`.

**PRIORITY 3: SKIP / NO-OP**
- **Condition**: Impossible to proceed.
- **Action**: Use `tool_name`: `"__step_skip__"`.

[METADATA RULES]
For every execution item, populate the metadata fields:
1. `operation_type`: Strictly choose from [`READ`, `WRITE`, `SEARCH`, `COMMUNICATE`, `TRANSACT`, `BOOK`, `GRANT_ACCESS`, `REASONING`].
2. `information_flow`: Format `argument_name: "Source -> Target"`.

[FEW-SHOT EXAMPLES - HOW TO CALL THE FUNCTION]

**Case A: Priority 0 - Final Response (The End of Task)**
{{
  "strategies": [
    {{
      "choice_id": "choice1",
      "tool_name": "__response__",
      "operation_type": "REASONING",
      "execution_args": [
        {{
          "args": {{
            "final_content": "The hotel 'Le Marais' has been booked. Rating: 4.8. Price: $180. Confirmation sent to your calendar."
          }},
          "information_flow": {{ "final_content": "History_All_Steps -> synthesis" }},
          "reasoning": "Step is 'GENERATE_FINAL_ANSWER'. Synthesizing all previous observations into a final response for the user."
        }}
      ]
    }}
  ]
}}

**Case B: Priority 1 - Tool Found**
{{
  "strategies": [
    {{
      "choice_id": "choice1",
      "tool_name": "get_most_recent_transactions",
      "operation_type": "SEARCH",
      "execution_args": [
        {{
          "args": {{ "n": 50 }},
          "information_flow": {{ "n": "Inferred_Default -> n" }},
          "reasoning": "Calling coarse-grained tool to fetch data for subsequent filtering."
        }}
      ]
    }}
  ]
}}

**Case C: Priority 2 - Internal Reasoning**
{{
  "strategies": [
    {{
      "choice_id": "choice1",
      "tool_name": "__internal_reasoning__",
      "operation_type": "REASONING",
      "execution_args": [
        {{
          "args": {{
            "task": "Filter transactions",
            "result": "List of March transactions",
            "source_data": "Output of get_transactions"
          }},
          "information_flow": {{ "source_data": "History_Step_1 -> content" }},
          "reasoning": "Filtering raw data internally."
        }}
      ]
    }}
  ]
}}

**Case D: Priority 3 - No Match (Skip)**
{{
  "strategies": [
    {{
      "choice_id": "choice1",
      "tool_name": "__step_skip__",
      "operation_type": "REASONING",
      "execution_args": [
        {{
          "args": {{ "reason": "No flight tools available." }},
          "information_flow": {{}},
          "reasoning": "No matching tools found to satisfy the request."
        }}
      ]
    }}
  ]
}}

Now, evaluate priorities 0->1->2->3 and call `submit_candidate_strategies` for the CURRENT step:
"""


class HypothesisBranch(BaseModel):
    """假设分支

    表示一个可能的工具调用方案。
    """

    branch_id: str
    """分支ID"""

    tool_call: ToolCallInfo
    """工具调用信息"""

    rationale: str
    """选择此工具的理由"""

    # Symbolic Tags
    risk_level: str  # "low", "medium", "high"
    """风险等级"""

    necessity_score: float  # 0.0 - 1.0
    """必要性得分（越高越必要）"""

    redundancy_level: str  # "minimal", "moderate", "high"
    """冗余度（功能是否过于强大）"""

    has_side_effects: bool
    """是否有副作用（WRITE/DELETE/SEND操作）"""

    requires_external_communication: bool
    """是否需要外部通信"""

    source: str = "hypothesis_generation"
    """分支来源：'hypothesis_generation' 或 'path_cache'

    - 'hypothesis_generation': 通过 Hypothesizer 生成的分支
    - 'path_cache': 从 Path Cache 中检索的已验证路径

    来自 path_cache 的分支可以跳过 verification 阶段直接执行
    """

    metadata: dict[str, Any] | None = None
    """额外元数据"""


class HypothesisTree(BaseModel):
    """假设树

    包含针对当前决策点的所有假设分支。
    """

    decision_point: str
    """决策点描述"""

    branches: list[HypothesisBranch]
    """假设分支列表"""

    recommended_branch_id: str | None = None
    """推荐的分支ID（根据最小必要性原则）"""


class Hypothesizer:
    """假设推理器

    为每个工具选择决策生成多个假设分支。
    使用 LLM 推理能力来生成合理的执行路径。
    """

    def __init__(self, config: VIGILConfig, openai_client=None, token_tracker: TokenStatsTracker | None = None, auditor=None):
        """初始化假设推理器

        Args:
            config: VIGIL配置
            openai_client: OpenAI客户端（用于LLM推理）
            token_tracker: Token 统计追踪器（可选，默认使用全局追踪器）
            auditor: EnhancedRuntimeAuditor实例（用于访问执行历史）
        """
        self.config = config
        self.openai_client = openai_client
        self.token_tracker = token_tracker or get_global_tracker()
        self.auditor = auditor  # 保存auditor引用

        # 如果没有提供 OpenAI client，尝试创建一个
        if self.openai_client is None and config.enable_hypothesis_generation:
            try:
                import openai
                from vigil_agent.client_utils import create_openai_client_for_model

                self.openai_client = create_openai_client_for_model(config.hypothesizer_model)
                logger.info("[Hypothesizer] Created default OpenAI client")
            except Exception as e:
                logger.warning(
                    f"[Hypothesizer] Failed to create OpenAI client: {e}. "
                    f"LLM-based hypothesis generation will be disabled."
                )
                self.openai_client = None

    def generate_hypotheses(
        self,
        available_tools: list[dict[str, Any]],
        current_state: dict[str, Any],
        user_intent: str,
        abstract_sketch: Any = None,  # AbstractSketch对象（可选）
        current_step_index: int = 0,  # 当前执行到的步骤索引
        rejected_tools: list[dict[str, str]] | None = None,  # 之前被拒绝的工具及理由
    ) -> HypothesisTree:
        """生成假设树

        遵循 VIGIL 的设计原则：
        - 如果有Abstract Sketch，基于当前步骤的tool_candidates生成假设
        - 如果没有Abstract Sketch，使用保守的启发式方法
        - 如果提供了 rejected_tools，在生成新假设时会避开这些工具并考虑拒绝理由

        Args:
            available_tools: 可用工具列表（包含名称、描述等）
            current_state: 当前状态
            user_intent: 用户意图描述
            abstract_sketch: 抽象草图（可选）
            current_step_index: 当前步骤索引
            rejected_tools: 之前被拒绝的工具列表，每个元素包含：
                - tool_name: 工具名称
                - rejection_reason: 拒绝理由

        Returns:
            假设树
        """
        if self.config.log_hypothesis_generation:
            logger.info(f"[Hypothesizer] Generating hypotheses for intent: {user_intent}...")
            if rejected_tools:
                logger.info(
                    f"[Hypothesizer] Considering {len(rejected_tools)} previously rejected tools "
                    f"to avoid similar mistakes"
                )

        # === 策略选择：基于Abstract Sketch或启发式 ===
        if abstract_sketch and hasattr(abstract_sketch, 'steps') and current_step_index < len(abstract_sketch.steps):
            # 有Abstract Sketch且步骤索引有效，使用基于意图的hypothesis生成
            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[Hypothesizer] Using Abstract Sketch-based hypothesis generation "
                    f"(Step {current_step_index + 1}/{len(abstract_sketch.steps)})"
                )
            return self._generate_from_sketch(
                abstract_sketch=abstract_sketch,
                current_step_index=current_step_index,
                available_tools=available_tools,
                user_intent=user_intent,
                rejected_tools=rejected_tools,  # 传递拒绝工具信息
            )

    def _generate_from_sketch(
        self,
        abstract_sketch: Any,
        current_step_index: int,
        available_tools: list[dict[str, Any]],
        user_intent: str,
        rejected_tools: list[dict[str, str]] | None = None,
    ) -> HypothesisTree:
        """基于Abstract Sketch生成假设树

        这是VIGIL论文中描述的正确方法：
        - 从Abstract Sketch的当前步骤获取tool_candidates
        - 为所有候选工具生成假设分支（不进行预筛选）
        - 进行符号化标注（Tool_Source, Required_Permissions, Estimated_Efficiency）
        - 让Neuro-Symbolic Verifier来判断安全性
        - 如果提供了 rejected_tools，会避开这些工具或降低它们的优先级

        Args:
            abstract_sketch: 抽象草图
            current_step_index: 当前步骤索引
            available_tools: 可用工具列表
            user_intent: 用户意图
            rejected_tools: 之前被拒绝的工具及理由（可选）

        Returns:
            假设树
        """
        current_step = abstract_sketch.steps[current_step_index]

        if self.config.log_hypothesis_generation:
            logger.info(f"[Hypothesizer] Current step: {current_step.step_type} - {current_step.description}")

        # 提取被拒绝的工具名称集合（用于过滤）
        rejected_tool_names = set()
        if rejected_tools:
            rejected_tool_names = {t["tool_name"] for t in rejected_tools}
            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[Hypothesizer] Excluding {len(rejected_tool_names)} rejected tools: "
                    f"{', '.join(list(rejected_tool_names)[:5])}"
                )

        # ===== 步骤1：获取候选工具 =====
        if current_step.tool_candidates:
            # 使用Abstract Sketch预先筛选的候选工具
            candidate_tool_names = set(current_step.tool_candidates)
            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[Hypothesizer] Using {len(candidate_tool_names)} tool candidates "
                    f"from Abstract Sketch: {list(candidate_tool_names)}..."
                )
        else:
            # 如果步骤没有tool_candidates，使用所有工具（最大探索空间）
            candidate_tool_names = {tool["name"] for tool in available_tools}
            if self.config.log_hypothesis_generation:
                logger.warning(
                    f"[Hypothesizer] Step has no tool_candidates, using all {len(candidate_tool_names)} available tools"
                )

        # 过滤出实际存在的候选工具，并排除之前被拒绝的工具
        candidate_tools = [
            tool for tool in available_tools
            if tool["name"] in candidate_tool_names and tool["name"] not in rejected_tool_names
        ]

        if self.config.log_hypothesis_generation:
            if rejected_tool_names:
                filtered_count = len(candidate_tool_names) - len(candidate_tools)
                logger.info(
                    f"[Hypothesizer] Filtered out {filtered_count} rejected tools, "
                    f"remaining {len(candidate_tools)} candidate tools"
                )
            else:
                logger.info(
                    f"[Hypothesizer] Found {len(candidate_tools)} candidate tools from Abstract Sketch"
                )

        # === 步骤2：使用 LLM 推理哪些工具真正适合此步骤及其参数 ===
        # 这是 Speculative Reasoner 的核心：利用 LLM 的推理能力
        # selected_tool_calls = self._reason_tool_paths(
        #     current_step=current_step,
        #     candidate_tools=candidate_tools,
        #     user_intent=user_intent,
        #     constraint=abstract_sketch.global_constraints if hasattr(abstract_sketch, 'global_constraints') else None,
        #     abstract_sketch=abstract_sketch,  # 传入完整sketch
        #     current_step_index=current_step_index,  # 传入当前步骤索引
        # )
        selected_tool_calls = self._reason_tool_paths_v2(
            current_step=current_step,
            candidate_tools=candidate_tools,
            user_intent=user_intent,
            constraint=abstract_sketch.global_constraints if hasattr(abstract_sketch, 'global_constraints') else None,
            abstract_sketch=abstract_sketch,  # 传入完整sketch
            current_step_index=current_step_index,  # 传入当前步骤索引
        )

        if self.config.log_hypothesis_generation:
            logger.info(
                f"[Hypothesizer] LLM reasoning reduced {len(candidate_tools)} candidates "
                f"to {len(selected_tool_calls)} relevant tool calls for this step"
            )

        # === 步骤3：为 LLM 选择的工具调用生成假设分支 ===
        branches = []
        # 用于跟踪每个工具名称的调用次数，以生成唯一的 branch_id
        tool_call_counters = {}

        # === 步骤3.1：分组迭代执行的 tool_calls ===
        # 识别具有相同 choice_id 的迭代调用，将它们合并为一个 branch
        grouped_tool_calls = []
        iterative_groups: dict[str, list[dict]] = {}  # choice_id -> list of tool_calls

        for tool_call_spec in selected_tool_calls:
            iteration_info = tool_call_spec.get("iteration_info")

            if iteration_info and iteration_info.get("is_iterative"):
                # 迭代执行：按 choice_id 分组
                choice_id = iteration_info.get("choice_id", "unknown")
                if choice_id not in iterative_groups:
                    iterative_groups[choice_id] = []
                iterative_groups[choice_id].append(tool_call_spec)
            else:
                # 非迭代执行：直接添加
                grouped_tool_calls.append(tool_call_spec)

        # 将迭代组转换为合并的 tool_call
        for choice_id, tool_calls_group in iterative_groups.items():
            if len(tool_calls_group) > 0:
                # 按 iteration_index 排序确保顺序正确
                tool_calls_group.sort(key=lambda x: x.get("iteration_info", {}).get("iteration_index", 0))

                # 创建一个合并的 tool_call，包含所有迭代的信息
                merged_tool_call = {
                    "tool_name": tool_calls_group[0].get("tool_name"),
                    "arguments": tool_calls_group[0].get("arguments"),  # 第一个作为主参数（向后兼容）
                    "reason": f"Iterative execution: {len(tool_calls_group)} calls",
                    "verification_metadata": tool_calls_group[0].get("verification_metadata"),
                    "is_merged_iterative": True,  # 标记为合并的迭代调用
                    "iterative_calls": tool_calls_group,  # 保存所有迭代调用
                }
                grouped_tool_calls.append(merged_tool_call)

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[Hypothesizer] Merged {len(tool_calls_group)} iterative calls "
                        f"for choice '{choice_id}' into a single branch"
                    )

        # === 步骤3.2：为分组后的 tool_calls 生成假设分支 ===
        for tool_call_spec in grouped_tool_calls:
            tool_name = tool_call_spec.get("tool_name", "unknown")
            tool_arguments = tool_call_spec.get("arguments", {})
            is_merged_iterative = tool_call_spec.get("is_merged_iterative", False)

            # === 特殊处理：__skip_step__ 分支 ===
            if tool_name == "__step_skip__":
                # LLM 认为当前步骤不需要调用任何工具
                skip_reason = tool_call_spec.get("reason", "No reason provided")

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[Hypothesizer] Creating __step_skip__ branch for step '{current_step.step_type}'. "
                        f"Reason: {skip_reason}"
                    )

                # 创建 SKIP STEP 假设分支
                skip_branch = HypothesisBranch(
                    branch_id=f"branch_skip_step",
                    tool_call={
                        "tool_name": "__step_skip__",
                        "arguments": {},
                        "reason": skip_reason,  # 保存跳过原因
                        "tool_call_id": None,
                    },
                    rationale=f"Skip current step: {skip_reason}",
                    risk_level="NONE",  # 跳过步骤没有风险
                    necessity_score=0.0,  # 不需要执行任何操作
                    redundancy_level="N/A",
                    has_side_effects=False,
                    requires_external_communication=False,
                    metadata={
                        "tool_description": "Skip current step without tool execution or LLM reasoning",
                        "tool_source": "System",
                        "required_permissions": [],
                        "estimated_efficiency": "Instant",
                        "step_type": current_step.step_type,
                        "step_description": current_step.description,
                        "skip_reason": skip_reason,
                        "verification_metadata": tool_call_spec.get("verification_metadata"),
                    },
                )

                branches.append(skip_branch)
                continue
            elif tool_name == "__internal_reasoning__":
                # LLM 认为当前步骤只需要内部推理，不需要调用外部工具
                reasoning_reason = tool_call_spec.get("reason", "No reason provided")

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[Hypothesizer] Creating __internal_reasoning__ branch for step '{current_step.step_type}'. "
                        f"Reason: {reasoning_reason}"
                    )

                # 创建 INTERNAL REASONING 假设分支
                reasoning_branch = HypothesisBranch(
                    branch_id=f"branch_internal_reasoning",
                    tool_call={
                        "tool_name": "__internal_reasoning__",
                        "arguments": {},
                        "reason": reasoning_reason,  # 保存推理原因
                        "tool_call_id": None,
                    },
                    rationale=f"Perform internal reasoning only: {reasoning_reason}",
                    risk_level="low",
                    necessity_score=0.8,  # 内部推理通常是必要的
                    redundancy_level="minimal",
                    has_side_effects=False,
                    requires_external_communication=False,
                    metadata={
                        "tool_description": "Perform internal reasoning without external tool execution",
                        "tool_source": "System",
                        "required_permissions": [],
                        "estimated_efficiency": "Fast",
                        "step_type": current_step.step_type,
                        "step_description": current_step.description,
                        "reasoning_reason": reasoning_reason,
                        "verification_metadata": tool_call_spec.get("verification_metadata"),
                    },
                )

                branches.append(reasoning_branch)
                continue
            elif tool_name == "__response__":
                # LLM 认为当前步骤是生成最终响应
                response_reason = tool_call_spec.get("reason", "No reason provided")

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[Hypothesizer] Creating __response__ branch for step '{current_step.step_type}'. "
                        f"Reason: {response_reason}"
                    )

                # 创建 RESPONSE 假设分支
                response_branch = HypothesisBranch(
                    branch_id=f"branch_response",
                    tool_call={
                        "tool_name": "__response__",
                        "arguments": tool_arguments,
                        "reason": response_reason,  # 保存响应原因
                        "tool_call_id": None,
                    },
                    rationale=f"Generate final user response: {response_reason}",
                    risk_level="low",
                    necessity_score=1.0,  # 最终响应是必要的
                    redundancy_level="minimal",
                    has_side_effects=False,
                    requires_external_communication=False,
                    metadata={
                        "tool_description": "Generate final response to the user without external tool execution",
                        "tool_source": "System",
                        "required_permissions": [],
                        "estimated_efficiency": "Fast",
                        "step_type": current_step.step_type,
                        "step_description": current_step.description,
                        "response_reason": response_reason,
                        "verification_metadata": tool_call_spec.get("verification_metadata"),
                    },
                )

                branches.append(response_branch)
                continue

            # === 正常工具调用：查找原始工具定义 ===
            # 查找原始工具定义（用于符号化标注）
            tool_def = next((t for t in candidate_tools if t["name"] == tool_name), None)
            if not tool_def:
                logger.warning(f"[Hypothesizer] Tool '{tool_name}' not found in candidates, skipping")
                continue

            # 符号化标注
            tool_source = self._identify_tool_source(tool_name)
            required_permissions = self._identify_permissions(tool_name, current_step)
            estimated_efficiency = self._estimate_efficiency(tool_def, current_step)
            risk_level = self._assess_risk_level(tool_def)
            has_side_effects = self._has_side_effects(tool_name)
            requires_comm = self._requires_communication(tool_name)
            necessity_score = self._calculate_necessity_from_step(tool_def, current_step, user_intent)
            redundancy_level = self._assess_redundancy(tool_def, candidate_tools, user_intent)

            # 生成推理理由
            rationale = self._generate_rationale(tool_def, current_step, tool_source)

            # 生成唯一的 branch_id（支持同一工具的多次调用）
            # 对于迭代执行，使用特殊的 ID
            if is_merged_iterative:
                iterative_calls = tool_call_spec.get("iterative_calls", [])
                first_choice_id = iterative_calls[0].get("iteration_info", {}).get("choice_id", "unknown") if iterative_calls else "unknown"
                branch_id = f"branch_{first_choice_id}_iterative"
            else:
                # 非迭代执行：使用工具名称和计数器生成唯一 ID
                if tool_name not in tool_call_counters:
                    tool_call_counters[tool_name] = 0
                else:
                    tool_call_counters[tool_name] += 1

                counter = tool_call_counters[tool_name]
                if counter == 0:
                    branch_id = f"branch_{tool_name}"
                else:
                    branch_id = f"branch_{tool_name}_{counter}"

            # 创建假设分支（现在包含 LLM 推理的参数）
            branch = HypothesisBranch(
                branch_id=branch_id,
                tool_call={
                    "tool_name": tool_name,
                    "arguments": tool_arguments,  # 使用 LLM 推理的参数
                    "tool_call_id": None,
                },
                rationale=rationale,
                risk_level=risk_level,
                necessity_score=necessity_score,
                redundancy_level=redundancy_level,
                has_side_effects=has_side_effects,
                requires_external_communication=requires_comm,
                metadata={
                    "tool_description": tool_def.get("description", ""),
                    "tool_source": tool_source,  # Official/Community/Unknown
                    "required_permissions": required_permissions,  # Read/Write/Delete/Send
                    "estimated_efficiency": estimated_efficiency,  # Fast/Medium/Slow
                    "step_type": current_step.step_type,
                    "step_description": current_step.description,
                    "is_merged_iterative": is_merged_iterative,  # 标记是否为迭代执行
                    "iterative_calls": tool_call_spec.get("iterative_calls") if is_merged_iterative else None,  # 保存所有迭代调用
                },
            )

            branches.append(branch)

        # === 步骤4：推荐最佳分支 ===
        recommended_id = self._recommend_branch(branches)

        hypothesis_tree = HypothesisTree(
            decision_point=f"{current_step.step_type}: {current_step.description}",
            branches=branches,
            recommended_branch_id=recommended_id,
        )

        if self.config.log_hypothesis_generation:
            logger.info(
                f"[Hypothesizer] Generated {len(branches)} hypothesis branches from sketch "
                f"(recommended: {recommended_id})"
            )

        return hypothesis_tree

    def _reason_tool_paths(
        self,
        current_step: Any,
        candidate_tools: list[dict[str, Any]],
        user_intent: str,
        constraint = None,
        abstract_sketch: Any = None,
        current_step_index: int = 0,
    ) -> list[dict[str, Any]]:
        """使用 LLM 推理哪些工具可能用于完成当前步骤，并生成参数

        这是 VIGIL Speculative Reasoner 的核心：
        利用 LLM 的推理能力来生成多条合理的执行路径，包括工具名称和预期参数。

        Args:
            current_step: Abstract Sketch 的当前步骤
            candidate_tools: 候选工具列表
            user_intent: 用户意图
            constraint: 全局约束
            abstract_sketch: 完整的abstract sketch
            current_step_index: 当前步骤索引

        Returns:
            LLM 推理出的工具调用列表，每个包含 tool_name 和 arguments
        """
        if not self.openai_client:
            # 没有 LLM client，返回所有候选工具（回退到非推理模式）
            logger.warning("[Hypothesizer] No OpenAI client available, returning all candidates")
            return [{"tool_name": tool["name"], "arguments": {}} for tool in candidate_tools]

        # 构建工具列表描述（包含参数信息）
        tools_description = []
        for i, tool in enumerate(candidate_tools, 1):
            tool_name = tool.get("name", "unknown")
            tool_desc = tool.get("full_docstring", "No description")
            # 添加参数信息
            parameters = tool.get("parameters", {})
            params_text = ""
            if parameters == {}:
                params_text = ""
            elif isinstance(parameters, dict):
                params_info = parameters.get("properties", {})
                required_params = parameters.get("required", [])
                param_list = []
                for param_name, param_info in params_info.items():
                    param_type = param_info.get("type", "any")
                    is_required = " (required)" if param_name in required_params else ""
                    param_list.append(f"  - {param_name}: {param_type}{is_required}")
                params_text = "\n".join(param_list) if param_list else "  (no parameters)"
                

            tools_description.append(f"{i}. {tool_name}:\n   Description: {tool_desc}\n")

        tools_text = "\n\n".join(tools_description)

        # === 构建之前步骤的描述 ===
        previous_steps_text = "None (this is the first step)"
        if abstract_sketch and hasattr(abstract_sketch, 'steps') and current_step_index > 0:
            prev_steps_desc = []
            for i in range(current_step_index):
                step = abstract_sketch.steps[i]
                prev_steps_desc.append(
                    f"Step {i + 1}: {step.step_type} - {step.description}"
                )
            previous_steps_text = "\n".join(prev_steps_desc)

        # === 构建执行历史描述 ===
        execution_history_text = "No previous executions yet (this is the first step)"
        if self.auditor and hasattr(self.auditor, 'execution_history') and self.auditor.execution_history:
            history_lines = []
            for record in self.auditor.execution_history:
                tool_name = record["tool_name"]
                args = record.get("arguments", {})
                result = record.get("result", "")
                # 简化参数显示
                import json
                args_str = json.dumps(args) if args else "{}"
                # 截断result
                result_preview =  result
                history_lines.append(
                    f"  - Step {record['step_index']}: {tool_name}({args_str})\n"
                    f"    Result: {result_preview}"
                )
            execution_history_text = "\n".join(history_lines)
        overall_execution_plan = ""
        for idx, step in enumerate(abstract_sketch.steps):
            if current_step_index == idx + 1:
                overall_execution_plan += f"- Step {idx + 1} (CURRENT STEP): {step.step_type} - {step.description}\n"
            else:
                overall_execution_plan += f"- Step {idx + 1}: {step.step_type} - {step.description}\n"
                prompt = f"""[ROLE]
You are the **Speculative Reasoner (Hypothesizer)** within the VIGIL framework.
Your task is to determine the best execution method for the **[Current Abstract Step]** based on available resources.

[INPUT CONTEXT]
1. **User Intent**: "{user_intent}"
2. **Current Abstract Step**:
   - Type: {current_step.step_type}
   - Description: {current_step.description}
   - Allowed Capabilities: {current_step.allowed_operations}
3. **Execution History (Observations)**:
{execution_history_text}
4. **Available Tools (Docstrings)**:
{tools_text}

[CRITICAL INSTRUCTIONS - EXECUTION HIERARCHY]

You MUST evaluate the following priorities in strict order (0 -> 1 -> 2 -> 3).

**PRIORITY 1: EXTERNAL TOOL EXECUTION**
- **Condition**: Does a tool exist that can retrieve the **Target Entity** or perform the **Core Action**?
- **Action**: Generate a concrete tool call.
- **Multi-Candidate Strategy (CRITICAL)**:
  - If **ONE** tool fits best, return an array containing that single tool.
  - If **MULTIPLE** tools are valid candidates (e.g., overlapping functionality or equally viable alternatives), **RETURN ALL OF THEM** as separate objects in the JSON array. Do not arbitrarily pick one if ambiguity exists.
- **Handling Coarse-Grained Tools (CRITICAL)**:
  - If the tool is broader than the request (e.g., "Get all" vs "Find specific"), **YOU CAN CALL THIS TOOL.**
- **Parameter Inference**: Use Reasonable Defaults (e.g., n=50) if parameters are missing.


**PRIORITY 2: INTERNAL REASONING (Fallback for Logic/Extraction)**
- **Condition**: 
  1. Priority 0 and 1 failed.
  2. The step involves **Information Extraction, Calculation, Comparison, or Summarization** based on existing History.
  3. No external data is needed.
- **Action**: Use the special virtual tool `__internal_reasoning__`.
- **Scope**: ✅ Calculation, Filtering, Summarizing intermediate steps.

**PRIORITY 3: FINAL USER RESPONSE**
- **Condition**: Does the [Current Abstract Step] type equal `GENERATE_FINAL_ANSWER` or `REPORT_RESULTS`?
- **Action**: Use the special virtual tool `__response__`.
- **Logic**: 
  - Do NOT call external tools.
  - Synthesize a final text response based on the [Execution History] and [User Intent].
  - Assign `operation_type` as `REASONING` (as strictly defined by the Intent Anchor).

**PRIORITY 4: SKIP / NO-OP (Last Resort)**
- **Condition**: No tool matches, and internal reasoning is impossible.
- **Action**: Return `null` structure with specific reasoning.

[METADATA & FORMAT RULES]

1. **Metadata Generation**:
   - **operation_type**: Strictly choose from: [`READ`, `WRITE`, `SEARCH`, `COMMUNICATE`, `TRANSACT`, `BOOK`, `GRANT_ACCESS`, `REASONING`].
   - **information_flow**: Format `Source_Step_ID -> Argument_Name`.

2. **Output Structure**:
   Return ONLY a valid JSON array.

[OUTPUT EXAMPLES]

**Case A: Priority 0 - Final Response (The End of Task)**
[
  {{
    "tool_name": "__response__",
    "arguments": {{
      "final_content": "The hotel 'Le Marais' has been booked. Rating: 4.8. Price: $180. Confirmation sent to your calendar."
    }},
    "verification_metadata": {{
      "operation_type": "REASONING",
      "information_flow": {{ "final_content": "History_All_Steps -> synthesis" }}
    }},
    "reasoning": "Step is 'GENERATE_FINAL_ANSWER'. Synthesizing all previous observations into a final response for the user."
  }}
]

**Case B: Priority 1 - Tool Found**
[
  {{
    "tool_name": "get_most_recent_transactions",
    "arguments": {{ "n": 50 }},
    "verification_metadata": {{
      "operation_type": "SEARCH",
      "information_flow": {{ "n": "Inferred_Default -> n" }}
    }},
    "reasoning": "Calling coarse-grained tool to fetch data for subsequent filtering."
  }}
]

**Case C: Priority 2 - Internal Reasoning**
[
  {{
    "tool_name": "__internal_reasoning__",
    "arguments": {{
      "task": "Filter transactions",
      "result": "List of March transactions",
      "source_data": "Output of get_transactions"
    }},
    "verification_metadata": {{
      "operation_type": "REASONING",
      "information_flow": {{ "source_data": "History_Step_1 -> content" }}
    }},
    "reasoning": "Filtering raw data internally."
  }}
]

**Case D: Priority 3 - No Match**
[
  {{
    "tool_name": null,
    "arguments": null,
    "verification_metadata": null,
    "reasoning": "No flight tools available."
  }}
]

Now, evaluate priorities 0->1->2->3 and generate the JSON for the CURRENT step:
"""
#                 prompt = f"""[ROLE]
# You are the **Speculative Reasoner (Hypothesizer)** within the VIGIL framework.
# Your task is to determine the best execution method for the **[Current Abstract Step]** based on available resources.

# [INPUT CONTEXT]
# 1. **User Intent**: "{user_intent}"
# 2. **Current Abstract Step**:
#    - Type: {current_step.step_type}
#    - Description: {current_step.description}
#    - Allowed Capabilities: {current_step.allowed_operations}
# 3. **Execution History (Observations)**:
# {execution_history_text}
# 4. **Available Tools (Docstrings)**:
# {tools_text}

# [CRITICAL INSTRUCTIONS - EXECUTION HIERARCHY]

# You MUST evaluate the following 3 priorities in strict order.

# **PRIORITY 1: EXTERNAL TOOL EXECUTION (Highest)**
# - **Condition**: Does a tool exist that can retrieve the **Target Entity** or perform the **Core Action**, even if it lacks specific filtering parameters?
# - **Action**: Generate a concrete tool call.
# - **Handling Coarse-Grained Tools (CRITICAL)**:
#   - Often, tools are broader than the specific request. **This is ACCEPTABLE.**
#   - **Rule**: If the Abstract Step asks to "Find X with condition Y", but the tool only supports "Get all X" or "Get recent X", **YOU MUST CALL THIS TOOL.**
# - **Parameter Inference**:
#   - If a tool requires a parameter (like `n`) not present in the query, use a **Reasonable Default** (e.g., n=50 or n=100) to ensure sufficient data coverage.
#   - Valid types against docstrings.

# **PRIORITY 2: INTERNAL REASONING (Fallback for Logic/Extraction)**
# - **Condition**: 
#   1. NO external tool matches the entity/action (Priority 1 failed).
#   2. AND the step involves **Information Extraction, Calculation, Comparison, or Summarization** based on existing [Execution History].
#   3. AND you can perform this strictly using the provided context (no external data needed).
# - **Action**: Use the special virtual tool `__internal_reasoning__`.
# - **Scope**: 
#   - ✅ Allowed: "Filter the list of transactions from step 1 to find only March ones", "Sum up the total".
#   - ❌ Forbidden: "Search for new info", "Guessing passwords".

# **PRIORITY 3: SKIP / NO-OP (Last Resort)**
# - **Condition**: 
#   1. NO external tool matches the entity (Priority 1 failed).
#   2. AND the task requires external action/data that you cannot simulate (Priority 2 failed).
#   3. OR the step is redundant.
# - **Action**: Return `null` structure with specific reasoning.

# [METADATA & FORMAT RULES]

# 1. **Metadata Generation**:
#    - **operation_type**: Strictly choose from: [`READ`, `WRITE`, `SEARCH`, `COMMUNICATE`, `TRANSACT`, `BOOK`, `GRANT_ACCESS`, `REASONING`].
#    - **information_flow**: Format `Source_Step_ID -> Argument_Name`.

# 2. **Output Structure**:
#    Return ONLY a valid JSON array.

# [OUTPUT EXAMPLES]

# **Case A: Priority 1 - Tool Found (Coarse-Grained Match)**
# [
#   {{
#     "tool_name": "get_most_recent_transactions",
#     "arguments": {{
#       "n": 50
#     }},
#     "verification_metadata": {{
#       "operation_type": "SEARCH",
#       "information_flow": {{ "n": "Inferred_Default -> n" }}
#     }},
#     "reasoning": "Abstract step requests specific transactions. Tool 'get_most_recent_transactions' retrieves a superset of data. I will fetch recent transactions now, and filtering will occur in the next step."
#   }}
# ]

# **Case B: Priority 2 - Internal Reasoning**
# [
#   {{
#     "tool_name": "__internal_reasoning__",
#     "arguments": {{
#       "task": "Filter transactions",
#       "result": "List of 3 transactions from March",
#       "source_data": "Output of get_most_recent_transactions from History"
#     }},
#     "verification_metadata": {{
#       "operation_type": "REASONING",
#       "information_flow": {{ "source_data": "History_Step_1 -> content" }}
#     }},
#     "reasoning": "I have the raw transaction list in history. Now I am internally filtering for 'March 2022'."
#   }}
# ]

# **Case C: Priority 3 - No Match**
# [
#   {{
#     "tool_name": null,
#     "arguments": null,
#     "verification_metadata": null,
#     "reasoning": "Abstract step is 'FIND_FLIGHT', but no flight tools are available."
#   }}
# ]

# Now, evaluate priorities 1->2->3 and generate the JSON for the CURRENT step:
# """
            # Hypothesizer Prompt (Abstract Sketch -> Concrete Tool)
#                 prompt = f"""[ROLE]
# You are the **Speculative Reasoner (Hypothesizer)** within the VIGIL framework.
# Your task is to translate a high-level **[Current Abstract Step]** into **Concrete Tool Calls**, based on the available tools and execution history.

# [INPUT CONTEXT]
# 1. **User Intent**: "{user_intent}"
# 2. **Current Abstract Step**:
#    - Type: {current_step.step_type}
#    - Description: {current_step.description}
#    - Allowed Capabilities: {current_step.allowed_operations}
# 3. **Execution History (Observations)**:
# {execution_history_text}
# 4. **Available Tools (Docstrings)**:
# {tools_text}

# [CRITICAL INSTRUCTIONS]

# 1. **METADATA GENERATION (For Verification)**:
#    - **operation_type**: Strictly choose from: [`READ`, `WRITE`, `SEARCH`, `COMMUNICATE`, `TRANSACT`, `BOOK`, `GRANT_ACCESS`, `REASONING`].
#    - **information_flow**: format `Source_Step_ID -> Argument_Name`.
# 2. **STRICT SEMANTIC ALIGNMENT (When Matching)**:
#    - Select tools that perform the *exact* action described in the [Current Abstract Step].
#    - **Prerequisite Data**: DO NOT fetch "prerequisite" data (like user IDs) unless the step explicitly asks for it.

# 3. **PARAMETER INFERENCE & TYPE CHECKING**:
#    - **Subject vs. Object**: Distinguish between data about the agent (Subject) and data about external entities (Object). Use Object data for actions like `transfer_money`.
#    - **Type Validation**: Ensure arguments match the tool's docstring type requirements (e.g., integer vs. string).

# 4. **NO MATCH STRATEGY (Explicit No-Op)**:
#    - The Abstract Plan is generated blindly. **Mismatches are expected.**
#    - If the [Available Tools] list does NOT contain a tool that *explicitly* matches the intent of the [Current Abstract Step], you must strictly acknowledge this.
#    - **Action**: You MUST return a JSON object where `tool_name`, `arguments`, and `verification_metadata` are `null` (or None), and provide a specific `reasoning`.
#    - **Reasoning Requirement**: Explain *why* no tool was selected (e.g., "The step requires booking a flight, but only banking tools are provided.").
#    - **Strict Prohibition**: Do NOT force a match. Do NOT call a tool just because it is available if it doesn't fit the step description.


# [OUTPUT FORMAT]
# Return ONLY a valid JSON array. Use `null` for empty fields in JSON.

# **Case 1: Tool Found (Normal Execution)**
# [
#   {{
#     "tool_name": "send_email",
#     "arguments": {{
#       "recipient": "jane@example.com",
#       "subject": "Hotel Info",
#       "body": "Stay at Le Marais..."
#     }},
#     "verification_metadata": {{
#       "operation_type": "COMMUNICATE",
#       "information_flow": {{
#         "recipient": "User_Query_Explicit -> recipient",
#         "body": "History_Step_2_Observation -> body"
#       }}
#     }},
#     "reasoning": "Found 'send_email' which matches the abstract step 'SEND_EMAIL'. Parameters inferred from query and history."
#   }}
# ]

# **Case 2: No Tool Matches (Explicit No-Op)**
# [
#   {{
#     "tool_name": null,
#     "arguments": null,
#     "verification_metadata": null,
#     "reasoning": "Current abstract step is 'FIND_FLIGHT', but the available tools are restricted to 'Banking Suite'. No flight search tool exists in the current environment."
#   }}
# ]

# Now, generate the tool calls for the CURRENT step:
# """

#             prompt = f"""You are the 'Hypothesizer' agent. Your goal is to generate concrete tool calls for the CURRENT step in a plan.

# [INPUT CONTEXT]
# 1. **User Goal**: "{user_intent}"
# 2. **Current Abstract Step**:
#    - Type: {current_step.step_type}
#    - Description: {current_step.description}
# 3. **Execution History**:
# {execution_history_text}
# 4. **Available Tools**:
# {tools_text}

# [CRITICAL INSTRUCTIONS]

# 1. **STRICT ACTION SCOPE (Crucial)**:
#    - You must ONLY select tools that perform the *exact* action described in the [Current Abstract Step].
#    - **DO NOT** fetch "prerequisite" or "context" data unless explicitly asked.
#    - **Example**: If the step is "READ - Read the bill file", ONLY call `read_file`.
#      - ❌ DO NOT call `get_iban` (User's account info is not needed to read a file).
#      - ❌ DO NOT call `get_balance` (Checking balance is not "Reading a file").
#    - **Rule**: If the tool retrieves data about the AGENT/USER (like `get_user_info`, `get_iban`), ONLY call it if the Step Description explicitly mentions "check user info" or "verify account".

# 2. **Avoid Redundancy**:
#    - Check [Execution History]. If a tool was already called and returned the needed data, DO NOT call it again.

# 3. **Parameter Inference**:
#    - Extract parameters from [User Goal] and [Execution History].
#    - If the previous step `read_file` output contains "IBAN: XYZ", use "XYZ" for the `recipient` parameter in the current step.
#    - Avoid Parameter Confusion (Role-based Inference)**:
#      - You MUST analyze the **Docstring** of previous tools to determine the "Role" of their return values.
#      - **Distinguish SUBJECT vs OBJECT**:
#        - If a tool's docstring says "Get **current** account" (e.g., `get_iban`), its output is the **SENDER** (Self).
#        - If a tool reads external data (e.g., `read_file`), its output usually contains the **RECIPIENT** (Target).
#      - **Logic**: If the current tool (e.g., `send_money`) asks for a `recipient` argument, you MUST use the data derived from external sources (Object), NOT the data from `get_iban` (Subject).
#    - **Example**:
#      - History: `get_iban` -> returned "IBAN_A" (Docstring: "Get current bank account").
#      - History: `read_file` -> returned "Pay to IBAN_B".
#      - Current Task: "Send money".
#      - **Inference**: `recipient` parameter MUST be "IBAN_B", NOT "IBAN_A".

# [OUTPUT FORMAT]
# Return ONLY a JSON array of tool calls:
# [
#   {{
#     "tool_name": "exact_tool_name",
#     "arguments": {{ "param": "value" }}
#   }}
# ]

# If no tools are relevant, return: []

# """
#         prompt = f"""You are the 'Hypothesizer' agent. Your goal is to generate concrete, executable tool calls for a specific step in a plan.

# [INPUT CONTEXT]

# 1. **User's Original Goal**:
# {user_intent}

# 2. **Overall Execution Plan** (All Steps):
# {previous_steps_text if current_step_index > 0 else ""}
# → **CURRENT STEP** (Step {current_step_index + 1}): {current_step.step_type if hasattr(current_step, 'step_type') else 'Unknown'} - {current_step.description if hasattr(current_step, 'description') else 'Unknown'}

# 3. **What Has Been Done** (Execution History):
# {execution_history_text}

# 4. **Current Step to Complete** (The specific action to perform NOW):
# - Type: {current_step.step_type if hasattr(current_step, 'step_type') else 'Unknown'}
# - Description: {current_step.description if hasattr(current_step, 'description') else 'Unknown'}

# 5. **Available Candidate Tools** (With Docstrings & Signatures):
# {tools_text}

# [CRITICAL INSTRUCTIONS]

# **MOST IMPORTANT - Avoid Redundancy**:
# 1. **Check Execution History First**: Review what tools have ALREADY been executed in previous steps
# 2. **Don't Repeat**: If a tool has already been called and returned the needed information (e.g., file content, balance), DO NOT call it again
# 3. **Focus on Current Step**: Only select tools that are needed for the CURRENT step's specific action
# 4. **Example**:
#    - If Step 1 (READ) already called `read_file('bill.txt')` and got the amount
#    - And Current Step is TRANSFER - Execute payment
#    - Then you should call `send_money` or `transfer`, NOT `read_file` again!

# **Tool Selection**:
#    - Identify ALL tools from the candidate list that can functionally complete the [Current Step]
#    - **Avoid tools already used** in previous steps unless absolutely necessary
#    - **Ambiguity Preservation**: If multiple tools seem valid (e.g., `send_money` and `send_money_v2`), select BOTH

# **Parameter Inference (Crucial)**:
#    - **Source of Truth**: Extract specific parameter values from:
#      1. The [Execution History] - information already obtained
#      2. The [User Original Goal]
#      3. The [Current Step Description]
#    - **Example**: If history shows `read_file` returned "amount: $100", and current step is "send payment", use `amount=100`

# **Signature Compliance (Strict)**:
#    - READ the provided tool definitions carefully
#    - **Do NOT hallucinate arguments**: Only use parameters explicitly defined in the tool's signature
#    - **Correct Types**: Ensure values match expected types

# [OUTPUT FORMAT]
# Return ONLY a valid JSON array of objects. Do not include markdown formatting or explanations.
# [
#   {{
#     "tool_name": "exact_tool_name_from_list",
#     "arguments": {{
#       "exact_param_name": "inferred_value",
#       "another_param": "inferred_value"
#     }}
#   }}
# ]

# If no tools are relevant, return: []
# """

        try:
            # 调用 LLM
            response = self.openai_client.chat.completions.create(
                model=self.config.hypothesizer_model,
                messages=[
                    {"role": "system", "content": "You are a precise reasoning assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.hypothesizer_temperature,
                max_tokens=8192,
            )

            # 记录 token 使用情况
            if response.usage:
                self.token_tracker.record_usage(
                    module=TokenStatsTracker.MODULE_SPECULATIVE_REASONER,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    model=self.config.hypothesizer_model,
                )

            # 解析响应
            import json
            import re

            response_text = response.choices[0].message.content.strip()

            # 提取 JSON（可能被代码块包裹）
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)

            # 如果响应不是以 [ 开头，尝试查找 JSON 数组
            if not response_text.startswith('['):
                json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)

            selected_tool_calls = json.loads(response_text)

            # 验证返回的工具调用格式和工具名称是否在候选列表中
            valid_tool_names = {tool["name"] for tool in candidate_tools}
            filtered_tool_calls = []

            for tool_call in selected_tool_calls:
                # 确保是字典格式
                if not isinstance(tool_call, dict):
                    continue

                tool_name = tool_call.get("tool_name")

                # === 特殊处理：tool_name 为 null（LLM 认为不需要调用任何工具）===
                if tool_name is None or tool_name == "null":
                    # LLM 明确表示当前步骤不需要调用工具
                    # 提取 reasoning 作为跳过原因
                    reasoning = tool_call.get("reasoning", "No reason provided")

                    if self.config.log_hypothesis_generation:
                        logger.info(
                            f"[Hypothesizer] LLM returned tool_name=null, converting to __skip_step__ branch. "
                            f"Reason: {reasoning}"
                        )

                    # 转换为 __skip_step__ 分支
                    skip_step_call = {
                        "tool_name": "__skip_step__",
                        "arguments": {},
                        "reason": reasoning,  # 保存跳过原因
                        "verification_metadata": tool_call.get("verification_metadata"),
                    }
                    filtered_tool_calls.append(skip_step_call)
                    continue
                elif tool_name == "__internal_reasoning__":
                    # 内部推理工具，直接接受
                    rationale = tool_call.get("reasoning", "No rationale provided")
                    if self.config.log_hypothesis_generation:
                        logger.info(
                            f"[Hypothesizer] LLM returned tool_name=null, converting to __internal_reasoning__ branch. "
                            f"Reason: {rationale}"
                        )
                    interal_reasoning_call = {
                        "tool_name": "__internal_reasoning__",
                        "arguments": {},
                        "reason": rationale,  # 保存跳过原因
                        "verification_metadata": tool_call.get("verification_metadata"),
                    }
                    filtered_tool_calls.append(interal_reasoning_call)
                    continue
                elif tool_name == "__response__":
                    # 最终响应工具，直接接受
                    rationale = tool_call.get("reasoning", "No rationale provided")
                    if self.config.log_hypothesis_generation:
                        logger.info(
                            f"[Hypothesizer] LLM returned tool_name=null, converting to __response__ branch. "
                            f"Reason: {rationale}"
                        )
                    response_call = {
                        "tool_name": "__response__",
                        "arguments": {},
                        "reason": rationale,  # 保存跳过原因
                        "verification_metadata": tool_call.get("verification_metadata"),
                    }
                    filtered_tool_calls.append(response_call)
                    continue
                # === 正常工具调用：验证工具名称是否在候选列表中 ===
                if tool_name not in valid_tool_names:
                    # 工具不在候选列表中，跳过
                    if self.config.log_hypothesis_generation:
                        logger.warning(
                            f"[Hypothesizer] LLM suggested tool '{tool_name}' not in candidate list, skipping"
                        )
                    continue

                # 确保有 arguments 字段
                if "arguments" not in tool_call:
                    tool_call["arguments"] = {}

                filtered_tool_calls.append(tool_call)

            # 限制分支数量
            if len(filtered_tool_calls) > self.config.max_hypothesis_branches:
                filtered_tool_calls = filtered_tool_calls[:self.config.max_hypothesis_branches]
                logger.info(
                    f"[Hypothesizer] Limiting to {self.config.max_hypothesis_branches} branches "
                    f"(LLM suggested {len(selected_tool_calls)})"
                )

            if self.config.log_hypothesis_generation:
                tool_names = [tc["tool_name"] for tc in filtered_tool_calls]
                logger.info(
                    f"[Hypothesizer] LLM reasoning selected {len(filtered_tool_calls)} tool calls "
                    f"for step '{current_step.step_type}': {tool_names}"
                )

            # 如果 LLM 没有选择任何工具，返回前3个候选（保守策略）
            if not filtered_tool_calls:
                logger.warning(
                    f"[Hypothesizer] LLM selected no tools, no need to call any tool for this step,"
                )
                return [{"tool_name": tool["name"], "arguments": {}} for tool in candidate_tools[:3]]

            return filtered_tool_calls

        except Exception as e:
            logger.error(f"[Hypothesizer] LLM reasoning failed: {e}, returning all candidates")
            # 出错时返回所有候选工具（保守策略）
            return [{"tool_name": tool["name"], "arguments": {}} for tool in candidate_tools]

    def _reason_tool_paths_v2(
        self,
        current_step: Any,
        candidate_tools: list[dict[str, Any]],
        user_intent: str,
        constraint = None,
        abstract_sketch: Any = None,
        current_step_index: int = 0,
    ) -> list[dict[str, Any]]:
        """使用 OpenAI Function Calling 推理工具执行路径（V2版本）

        这是 VIGIL Speculative Reasoner 的增强版本：
        利用 OpenAI function calling 机制来获取结构化的工具调用方案，
        包括多候选策略、迭代执行等高级特性。

        Args:
            current_step: Abstract Sketch 的当前步骤
            candidate_tools: 候选工具列表
            user_intent: 用户意图
            constraint: 全局约束
            abstract_sketch: 完整的abstract sketch
            current_step_index: 当前步骤索引

        Returns:
            LLM 推理出的工具调用列表，每个包含 tool_name 和 arguments
        """
        if not self.openai_client:
            # 没有 LLM client，返回所有候选工具（回退到非推理模式）
            logger.warning("[Hypothesizer V2] No OpenAI client available, returning all candidates")
            return [{"tool_name": tool["name"], "arguments": {}} for tool in candidate_tools]

        # 最大重试次数（如果解析失败）
        max_retries = 2
        last_error = None

        for retry_attempt in range(max_retries + 1):
            if retry_attempt > 0:
                logger.warning(
                    f"[Hypothesizer V2] Retry attempt {retry_attempt}/{max_retries} "
                    f"due to parsing error: {last_error}"
                )

            try:
                # 调用 LLM 并解析结果
                result = self._call_llm_and_parse_v2(
                    current_step=current_step,
                    candidate_tools=candidate_tools,
                    user_intent=user_intent,
                    execution_history_text=self._build_execution_history_text(),
                    retry_attempt=retry_attempt,
                    last_error=last_error,
                )

                # 解析成功，返回结果
                return result

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error at position {e.pos}: {str(e)}"
                logger.error(f"[Hypothesizer V2] Attempt {retry_attempt + 1} failed: {last_error}")
            except ValueError as e:
                last_error = f"Value error: {str(e)}"
                logger.error(f"[Hypothesizer V2] Attempt {retry_attempt + 1} failed: {last_error}")
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"[Hypothesizer V2] Attempt {retry_attempt + 1} failed: {last_error}")

        # 所有重试都失败，返回空列表
        logger.error(
            f"[Hypothesizer V2] All {max_retries + 1} attempts failed. "
            f"Last error: {last_error}. Returning empty list."
        )
        return []

    def _build_execution_history_text(self) -> str:
        """构建执行历史文本"""
        execution_history_text = "No previous executions yet (this is the first step)"
        if self.auditor and hasattr(self.auditor, 'execution_history') and self.auditor.execution_history:
            history_lines = []
            for record in self.auditor.execution_history:
                tool_name = record["tool_name"]
                args = record.get("arguments", {})
                result = record.get("result", "")
                # 简化参数显示
                import json
                args_str = json.dumps(args) if args else "{}"
                # 截断result
                result_preview = result[:300] if result else "No result"
                history_lines.append(
                    f"  - Step {record['step_index']}: {tool_name}({args_str})\n"
                    f"    Result: {result_preview}"
                )
            execution_history_text = "\n".join(history_lines)
        return execution_history_text

    def _call_llm_and_parse_v2(
        self,
        current_step: Any,
        candidate_tools: list[dict[str, Any]],
        user_intent: str,
        execution_history_text: str,
        retry_attempt: int = 0,
        last_error: str | None = None,
    ) -> list[dict[str, Any]]:
        """调用 LLM 并解析结果（可重试）

        Args:
            current_step: 当前步骤
            candidate_tools: 候选工具列表
            user_intent: 用户意图
            execution_history_text: 执行历史文本
            retry_attempt: 当前重试次数
            last_error: 上次的错误信息

        Returns:
            解析后的工具调用列表

        Raises:
            json.JSONDecodeError: JSON 解析失败
            ValueError: 数据格式错误
        """

        # 构建工具列表描述（包含参数信息）
        tools_description = []
        for i, tool in enumerate(candidate_tools, 1):
            tool_name = tool.get("name", "unknown")
            tool_desc = tool.get("full_docstring", "No description")
            # 添加参数信息
            parameters = tool.get("parameters", {})
            params_text = ""
            if parameters == {}:
                params_text = "  (no parameters)"
            elif isinstance(parameters, dict):
                params_info = parameters.get("properties", {})
                required_params = parameters.get("required", [])
                param_list = []
                for param_name, param_info in params_info.items():
                    param_type = param_info.get("type", "any")
                    is_required = " (required)" if param_name in required_params else ""
                    param_list.append(f"  - {param_name}: {param_type}{is_required}")
                params_text = "\n".join(param_list) if param_list else "  (no parameters)"

            tools_description.append(
                f"{i}. {tool_name}:\n"
                f"   Description: {tool_desc}\n"
                f"   Parameters:\n{params_text}"
            )

        tools_text = "\n\n".join(tools_description)

        # 格式化prompt
        prompt = OPTIMIZED_HYPOTHESIZER_PROMPT.format(
            user_intent=user_intent,
            current_step_type=current_step.step_type if hasattr(current_step, 'step_type') else 'Unknown',
            current_step_description=current_step.description if hasattr(current_step, 'description') else 'Unknown',
            current_step_capabilities=current_step.allowed_operations if hasattr(current_step, 'allowed_operations') else [],
            execution_history_text=execution_history_text,
            tools_text=tools_text,
        )

        # 如果是重试，添加错误信息到 prompt
        if retry_attempt > 0 and last_error:
            retry_message = f"""

**IMPORTANT - RETRY ATTEMPT {retry_attempt}**:
Your previous response had a formatting error and could not be parsed:
Error: {last_error}

Please ensure your response follows the EXACT JSON schema defined in the function.
- Use double quotes for ALL string values
- Ensure all brackets and braces are properly closed
- Do NOT include any markdown formatting or code blocks
- Return ONLY the function call with valid JSON"""
            prompt = prompt + retry_message

        # 调用 OpenAI API with function calling
        response = self.openai_client.chat.completions.create(
            model=self.config.hypothesizer_model,
            messages=[
                {"role": "system", "content": "You are a precise reasoning assistant within the VIGIL framework. You must use the provided function to submit your execution strategies."},
                {"role": "user", "content": prompt}
            ],
            tools=VIGIL_TOOL_SCHEMA,
            tool_choice={"type": "function", "function": {"name": "submit_candidate_strategies"}},  # 强制调用此函数
            temperature=self.config.hypothesizer_temperature,
            max_tokens=8192,
        )

        # 记录 token 使用情况
        if response.usage:
            self.token_tracker.record_usage(
                module=TokenStatsTracker.MODULE_SPECULATIVE_REASONER,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                model=self.config.hypothesizer_model,
            )

        # 解析 function call 响应
        import json

        message = response.choices[0].message

        # 检查是否有 tool_calls
        if not message.tool_calls or len(message.tool_calls) == 0:
            logger.warning("[Hypothesizer V2] No tool calls in response")
            raise ValueError("LLM did not return any tool calls")

        # 获取第一个 tool call（应该是 submit_candidate_strategies）
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        function_args_str = tool_call.function.arguments

        if function_name != "submit_candidate_strategies":
            logger.warning(
                f"[Hypothesizer V2] Unexpected function name '{function_name}', "
                f"expected 'submit_candidate_strategies'"
            )
            raise ValueError(f"Unexpected function name: {function_name}")

        # 解析 function arguments（抛出异常以触发重试）
        function_args = self._parse_function_arguments(function_args_str)

        # 验证并转换格式
        selected_tool_calls = self._convert_strategies_to_tool_calls(
            function_args,
            candidate_tools,
            current_step
        )

        return selected_tool_calls

    def _parse_function_arguments(self, function_args_str: str) -> list[dict]:
        """解析 function arguments，支持多层转义和正则提取

        Args:
            function_args_str: JSON 字符串

        Returns:
            解析后的 strategies 列表

        Raises:
            json.JSONDecodeError: 所有解析方法都失败时抛出
        """
        import json
        import re

        # === 特殊处理：检查是否包含特殊工具名 ===
        # 对于 __internal_reasoning__、__response__、__step_skip__，使用简化解析
        special_tools = ["__internal_reasoning__", "__response__", "__step_skip__"]

        # 检查是否包含特殊工具名（简化判断）
        detected_tool = None
        for tool in special_tools:
            if tool in function_args_str:
                detected_tool = tool
                break

        if detected_tool:
            logger.info(f"[Hypothesizer V2] Detected special tool '{detected_tool}', using simplified parsing")

            # 提取 reasoning 文本（通常在最后）
            reasoning = "No reasoning provided"
            # 找到最后一个 "reasoning" 的位置
            reasoning_idx = function_args_str.rfind('reasoning')
            if reasoning_idx != -1:
                # 找到 "reasoning" 后面的冒号
                start_idx = function_args_str.find(':', reasoning_idx)
                if start_idx != -1:
                    # 跳过冒号和可能的空格、引号
                    start_idx += 1
                    while start_idx < len(function_args_str) and function_args_str[start_idx] in ' \t\n"\\':
                        start_idx += 1

                    # 提取从这里到字符串末尾的内容
                    reasoning = function_args_str[start_idx:]

                    # 清理末尾的特殊字符和标记
                    # 移除末尾的 "}]}]}\n" 等标记
                    for end_pattern in ['"}]}]', '"}]}', '"}]', '\\"}]}', '\\"}]', '}]}]', '}]}', '}]', '"]', '"}}', '"}', '}"', '"']:
                        if reasoning.endswith(end_pattern):
                            reasoning = reasoning[:-len(end_pattern)]
                            break

                    # 清理转义字符
                    reasoning = reasoning.replace('\\"', '"')
                    reasoning = reasoning.replace('\\\\n', '\n')
                    reasoning = reasoning.replace('\\n', ' ')
                    reasoning = reasoning.replace('\\t', ' ')

                    # 移除开头和结尾的引号和空格
                    reasoning = reasoning.strip('"').strip('\\').strip()

            # 构造简化的 strategies
            simplified_strategy = {
                "choice_id": "choice1",
                "tool_name": detected_tool,
                "operation_type": "REASONING" if detected_tool == "__internal_reasoning__" else "RESPONSE" if detected_tool == "__response__" else "SKIP",
                "execution_args": [
                    {
                        "args": {},  # 特殊工具不需要复杂参数
                        "reasoning": reasoning,
                        "information_flow": {}  # 空的 information_flow
                    }
                ]
            }

            logger.info(
                f"[Hypothesizer V2] Simplified parsing successful: "
                f"tool={detected_tool}, reasoning='{reasoning}...'"
            )
            return [simplified_strategy]

        # === 标准解析流程 ===
        # 第一次解析
        function_args = json.loads(function_args_str)

        # 处理双重转义：如果解析后仍然是字符串，再次解析
        if isinstance(function_args, str):
            logger.warning(
                "[Hypothesizer V2] Function arguments is a string after first parse. "
                "Attempting second parse (double-escaped JSON)."
            )
            function_args = json.loads(function_args)  # 如果失败会抛出异常

        # 兼容性处理：如果 LLM 直接返回数组而不是 {"strategies": [...]}
        if isinstance(function_args, list):
            logger.warning(
                "[Hypothesizer V2] LLM returned array instead of object with 'strategies' field. "
                "Auto-wrapping for compatibility."
            )
            strategies = function_args
        else:
            strategies = function_args.get("strategies", [])

        # 处理 strategies 本身也是字符串的情况（三重转义）
        if isinstance(strategies, str):
            logger.warning(
                "[Hypothesizer V2] Strategies field is a string. "
                "Attempting to parse (triple-escaped JSON)."
            )
            try:
                strategies = json.loads(strategies)
            except json.JSONDecodeError:
                # 使用正则表达式提取 JSON 数组
                logger.warning("[Hypothesizer V2] Attempting regex extraction...")
                array_match = re.search(r'\[.*\]', strategies, re.DOTALL)
                if array_match:
                    extracted_json = array_match.group(0)
                    logger.info(f"[Hypothesizer V2] Extracted JSON array using regex: {extracted_json[:200]}...")

                    # 清理提取的 JSON 字符串
                    cleaned_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', extracted_json)
                    cleaned_json = cleaned_json.replace("\\'", "'")

                    try:
                        strategies = json.loads(cleaned_json)
                        logger.info("[Hypothesizer V2] Successfully parsed extracted JSON array")
                    except json.JSONDecodeError as e2:
                        # 最后尝试 ast.literal_eval
                        import ast
                        logger.warning("[Hypothesizer V2] Attempting ast.literal_eval as last resort...")
                        try:
                            strategies = ast.literal_eval(cleaned_json)
                            logger.info("[Hypothesizer V2] Successfully parsed using ast.literal_eval")
                        except (ValueError, SyntaxError) as e3:
                            # 抛出原始错误以触发重试
                            raise json.JSONDecodeError(
                                f"All parsing methods failed. Last error: {str(e3)}",
                                cleaned_json,
                                e2.pos if hasattr(e2, 'pos') else 0
                            )
                else:
                    raise json.JSONDecodeError("No JSON array pattern found", strategies, 0)

        # 确保 strategies 是列表
        if not isinstance(strategies, list):
            raise ValueError(f"Strategies is not a list. Got type: {type(strategies)}")

        if self.config.log_hypothesis_generation:
            logger.info(f"[Hypothesizer V2] Successfully parsed {len(strategies)} strategies")

        return strategies

    def _convert_strategies_to_tool_calls(
        self,
        strategies: list[dict],
        candidate_tools: list[dict[str, Any]],
        current_step: Any
    ) -> list[dict[str, Any]]:
        """将 strategies 转换为 tool_calls 格式

        Args:
            strategies: 解析后的 strategies 列表
            candidate_tools: 候选工具列表
            current_step: 当前步骤

        Returns:
            转换后的工具调用列表
        """
        selected_tool_calls = []
        valid_tool_names = {tool["name"] for tool in candidate_tools}

        for strategy in strategies:
            choice_id = strategy.get("choice_id", "unknown")
            tool_name = strategy.get("tool_name")
            operation_type = strategy.get("operation_type", "REASONING")  # 从strategy层级提取
            execution_args_list = strategy.get("execution_args", [])

            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[Hypothesizer V2] Processing strategy '{choice_id}': "
                    f"tool={tool_name}, operation_type={operation_type}, iterations={len(execution_args_list)}"
                )

            # 处理特殊工具名称
            if tool_name in ["__response__", "__internal_reasoning__", "__step_skip__"]:
                # 对于特殊工具，我们只取第一个 execution_args
                if execution_args_list:
                    first_exec = execution_args_list[0]
                    # 构建verification_metadata（兼容新旧格式）
                    verification_metadata = {
                        "operation_type": operation_type,
                        "information_flow": first_exec.get("information_flow", {})
                    }
                    selected_tool_calls.append({
                        "tool_name": tool_name,
                        "arguments": first_exec.get("args", {}),
                        "reason": first_exec.get("reasoning", "No reason provided"),
                        "verification_metadata": verification_metadata,
                    })
                else:
                    selected_tool_calls.append({
                        "tool_name": tool_name,
                        "arguments": {},
                        "reason": "No execution args provided",
                        "verification_metadata": {
                            "operation_type": operation_type,
                            "information_flow": {}
                        },
                    })
                continue

            # 验证工具名称是否在候选列表中
            if tool_name not in valid_tool_names:
                if self.config.log_hypothesis_generation:
                    logger.warning(
                        f"[Hypothesizer V2] Strategy '{choice_id}' suggests tool '{tool_name}' "
                        f"not in candidate list, skipping"
                    )
                continue

            # 处理迭代执行：如果有多个 execution_args，为每个创建一个工具调用
            if len(execution_args_list) > 1:
                # 迭代执行模式
                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[Hypothesizer V2] Iterative execution detected for '{tool_name}': "
                        f"{len(execution_args_list)} iterations"
                    )

                for idx, exec_args in enumerate(execution_args_list):
                    # 构建verification_metadata（从新格式提取）
                    verification_metadata = {
                        "operation_type": operation_type,
                        "information_flow": exec_args.get("information_flow", {})
                    }
                    selected_tool_calls.append({
                        "tool_name": tool_name,
                        "arguments": exec_args.get("args", {}),
                        "reason": exec_args.get("reasoning", f"Iteration {idx + 1}"),
                        "verification_metadata": verification_metadata,
                        "iteration_info": {
                            "is_iterative": True,
                            "iteration_index": idx,
                            "total_iterations": len(execution_args_list),
                            "choice_id": choice_id,
                        }
                    })
            elif len(execution_args_list) == 1:
                # 单次执行
                exec_args = execution_args_list[0]
                # 构建verification_metadata（从新格式提取）
                verification_metadata = {
                    "operation_type": operation_type,
                    "information_flow": exec_args.get("information_flow", {})
                }
                selected_tool_calls.append({
                    "tool_name": tool_name,
                    "arguments": exec_args.get("args", {}),
                    "reason": exec_args.get("reasoning", "No reason provided"),
                    "verification_metadata": verification_metadata,
                })
            else:
                # 没有 execution_args，使用空参数
                logger.warning(
                    f"[Hypothesizer V2] Strategy '{choice_id}' has no execution_args, "
                    f"using empty arguments"
                )
                selected_tool_calls.append({
                    "tool_name": tool_name,
                    "arguments": {},
                    "reason": "No execution args provided",
                    "verification_metadata": {
                        "operation_type": operation_type,
                        "information_flow": {}
                    },
                })

        # 限制分支数量
        if len(selected_tool_calls) > self.config.max_hypothesis_branches:
            original_count = len(selected_tool_calls)
            selected_tool_calls = selected_tool_calls[:self.config.max_hypothesis_branches]
            logger.info(
                f"[Hypothesizer V2] Limiting to {self.config.max_hypothesis_branches} branches "
                f"(LLM suggested {original_count})"
            )

        if self.config.log_hypothesis_generation:
            tool_names = [tc["tool_name"] for tc in selected_tool_calls]
            logger.info(
                f"[Hypothesizer V2] Final tool calls for step '{current_step.step_type}': {tool_names}"
            )

        # 如果没有选择任何工具，返回空列表（不像v1那样返回前3个候选）
        if not selected_tool_calls:
            logger.warning(
                f"[Hypothesizer V2] LLM selected no tools via function calling"
            )
            return []

        return selected_tool_calls

    def _assess_risk_level(self, tool: dict[str, Any]) -> str:
        """评估工具的风险等级

        Args:
            tool: 工具信息

        Returns:
            风险等级 ("low", "medium", "high")
        """
        tool_name = tool.get("name", "").lower()

        # 高风险操作
        if any(kw in tool_name for kw in ["delete", "remove", "drop", "destroy"]):
            return "high"

        # 中风险操作
        if any(kw in tool_name for kw in ["write", "update", "modify", "create", "send", "transfer"]):
            return "medium"

        # 低风险操作
        return "low"

    def _has_side_effects(self, tool_name: str) -> bool:
        """判断工具是否有副作用

        Args:
            tool_name: 工具名称

        Returns:
            是否有副作用
        """
        tool_lower = tool_name.lower()
        side_effect_keywords = ["write", "update", "modify", "create", "delete", "remove", "send", "transfer"]
        return any(kw in tool_lower for kw in side_effect_keywords)

    def _requires_communication(self, tool_name: str) -> bool:
        """判断工具是否需要外部通信

        Args:
            tool_name: 工具名称

        Returns:
            是否需要外部通信
        """
        tool_lower = tool_name.lower()
        comm_keywords = ["send", "email", "message", "notify", "post", "publish"]
        return any(kw in tool_lower for kw in comm_keywords)

    def _calculate_necessity(self, tool: dict[str, Any], user_intent: str) -> float:
        """计算工具对于用户意图的必要性得分

        Args:
            tool: 工具信息
            user_intent: 用户意图

        Returns:
            必要性得分 (0.0 - 1.0)
        """
        tool_name = tool.get("name", "").lower()
        tool_desc = tool.get("description", "").lower()
        intent_lower = user_intent.lower()

        # 停用词列表（这些词不具有语义价值）
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "should",
            "could", "may", "might", "must", "can", "could",
            "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
            "my", "your", "his", "her", "its", "our", "their",
            "this", "that", "these", "those",
            "and", "or", "but", "if", "when", "where", "why", "how",
            "in", "on", "at", "to", "for", "of", "with", "by", "from", "up", "down",
            "please", "can", "could"
        }

        # 提取工具名称中的关键词（权重更高）
        tool_name_words = set(tool_name.split("_")) - stop_words

        # 提取工具描述中的关键词
        tool_desc_words = set(tool_desc.split()) - stop_words

        # 提取用户意图中的关键词
        intent_words = set(intent_lower.split()) - stop_words

        # 语义相关词映射（简单的同义词表）
        semantic_relations = {
            "pay": {"send", "transfer", "money", "payment", "transaction"},
            "send": {"transfer", "money", "payment"},
            "read": {"get", "fetch", "retrieve", "file", "open"},
            "write": {"update", "modify", "save", "file"},
            "balance": {"account", "money", "amount"},
            "transaction": {"payment", "transfer", "money", "send"},
            "bill": {"file", "document", "payment", "pay"},
            "schedule": {"plan", "arrange", "transaction"},
        }

        # 扩展意图词（包括语义相关词）
        expanded_intent_words = set(intent_words)
        for word in intent_words:
            if word in semantic_relations:
                expanded_intent_words.update(semantic_relations[word])

        # 计算得分（工具名称权重3倍，描述权重1倍）
        name_overlap = len(tool_name_words & expanded_intent_words)
        desc_overlap = len(tool_desc_words & expanded_intent_words)

        # 加权得分
        weighted_overlap = (name_overlap * 3.0) + (desc_overlap * 1.0)

        # 归一化（基于意图词数量）
        max_possible_score = len(expanded_intent_words) * 3.0  # 假设所有词都在名称中
        score = min(1.0, weighted_overlap / max(max_possible_score, 1.0))

        return score

    def _assess_redundancy(self, tool: dict[str, Any], all_tools: list[dict[str, Any]], user_intent: str) -> str:
        """评估工具的冗余度

        检查是否存在功能更简单但足够的替代工具。

        Args:
            tool: 当前工具
            all_tools: 所有可用工具
            user_intent: 用户意图

        Returns:
            冗余度 ("minimal", "moderate", "high")
        """
        tool_name = tool.get("name", "").lower()

        # 如果工具名包含"advanced", "premium", "pro"等词，可能是冗余的
        if any(kw in tool_name for kw in ["advanced", "premium", "pro", "enhanced", "optimized"]):
            # 检查是否有基础版本
            basic_keywords = ["basic", "simple", "standard", "get", "read"]
            has_basic_alternative = any(
                any(kw in t.get("name", "").lower() for kw in basic_keywords)
                for t in all_tools if t.get("name") != tool.get("name")
            )

            if has_basic_alternative:
                return "high"
            else:
                return "moderate"

        return "minimal"

    def _recommend_branch(self, branches: list[HypothesisBranch]) -> str | None:
        """根据最小必要性原则推荐最佳分支

        选择标准：
        1. 优先选择低风险的分支
        2. 优先选择高必要性的分支
        3. 优先选择低冗余度的分支

        Args:
            branches: 所有分支

        Returns:
            推荐的分支ID
        """
        if not branches:
            return None

        # 评分函数
        def score_branch(branch: HypothesisBranch) -> float:
            score = 0.0

            # 必要性得分（权重最高）
            score += branch.necessity_score * 3.0

            # 风险惩罚
            risk_penalties = {"low": 0.0, "medium": -0.5, "high": -1.5}
            score += risk_penalties.get(branch.risk_level, 0.0)

            # 冗余度惩罚
            redundancy_penalties = {"minimal": 0.0, "moderate": -0.3, "high": -1.0}
            score += redundancy_penalties.get(branch.redundancy_level, 0.0)

            # 副作用惩罚
            if branch.has_side_effects:
                score -= 0.5

            # 外部通信惩罚
            if branch.requires_external_communication:
                score -= 0.3

            return score

        # 计算所有分支的得分
        scored_branches = [(branch, score_branch(branch)) for branch in branches]

        # 按得分排序
        scored_branches.sort(key=lambda x: x[1], reverse=True)

        # 返回最高分的分支
        best_branch = scored_branches[0][0]

        if self.config.log_hypothesis_generation:
            logger.debug(f"[Hypothesizer] Recommended branch: {best_branch.branch_id} (score: {scored_branches[0][1]:.2f})")

        return best_branch.branch_id

    def _extract_core_verbs(self, user_intent: str) -> set[str]:
        """从用户意图中提取核心动词

        Args:
            user_intent: 用户意图

        Returns:
            核心动词集合
        """
        # 常见动词列表
        common_verbs = [
            "get", "set", "read", "write", "send", "create", "update",
            "delete", "schedule", "list", "search", "fetch", "check",
            "pay", "transfer", "book", "cancel", "view", "open", "close"
        ]

        intent_lower = user_intent.lower()
        verbs = set()

        for verb in common_verbs:
            if verb in intent_lower:
                verbs.add(verb)

        return verbs

    def _extract_tool_core_verb(self, tool_name: str) -> str:
        """从工具名称中提取核心动词

        Args:
            tool_name: 工具名称

        Returns:
            核心动词
        """
        # 移除常见的修饰词
        modifiers = [
            "advanced", "premium", "pro", "basic", "simple", "standard",
            "official", "community", "enhanced", "optimized"
        ]

        name_parts = tool_name.lower().split("_")
        core_parts = [part for part in name_parts if part not in modifiers]

        # 查找动词
        common_verbs = [
            "get", "set", "read", "write", "send", "create", "update",
            "delete", "schedule", "list", "search", "fetch"
        ]

        for part in core_parts:
            if part in common_verbs:
                return part

        # 如果没找到动词，返回第一个非修饰词
        return core_parts[0] if core_parts else ""

    # ========== 新增：符号化标注方法（基于Abstract Sketch） ==========

    def _identify_tool_source(self, tool_name: str) -> str:
        """识别工具来源

        Args:
            tool_name: 工具名称

        Returns:
            工具来源 ("Official", "Community", "Unknown")
        """
        tool_lower = tool_name.lower()

        # 官方工具通常包含这些标识
        official_indicators = ["official", "standard", "core", "api"]
        if any(ind in tool_lower for ind in official_indicators):
            return "Official"

        # 社区工具通常包含这些标识
        community_indicators = ["community", "plugin", "extension", "contrib", "custom"]
        if any(ind in tool_lower for ind in community_indicators):
            return "Community"

        return "Unknown"

    def _identify_permissions(self, tool_name: str, step: Any) -> list[str]:
        """识别工具所需权限

        Args:
            tool_name: 工具名称
            step: Abstract Sketch的当前步骤

        Returns:
            所需权限列表 (e.g., ["Read"], ["Write", "Send"])
        """
        tool_lower = tool_name.lower()
        permissions = []

        # 基于工具名称推断权限
        if any(kw in tool_lower for kw in ["read", "get", "fetch", "list", "search", "view"]):
            permissions.append("Read")

        if any(kw in tool_lower for kw in ["write", "update", "modify", "create", "set"]):
            permissions.append("Write")

        if any(kw in tool_lower for kw in ["delete", "remove", "drop"]):
            permissions.append("Delete")

        if any(kw in tool_lower for kw in ["send", "email", "message", "notify", "post"]):
            permissions.append("Send")

        # 如果没有权限，检查step的allowed_operations
        if not permissions and hasattr(step, 'allowed_operations') and step.allowed_operations:
            permissions = step.allowed_operations

        # 如果还是没有权限，默认为Read
        if not permissions:
            permissions = ["Read"]

        return permissions

    def _estimate_efficiency(self, tool: dict[str, Any], step: Any) -> str:
        """估计工具效率

        Args:
            tool: 工具信息
            step: Abstract Sketch的当前步骤

        Returns:
            效率等级 ("Fast", "Medium", "Slow")
        """
        tool_name = tool.get("name", "").lower()
        tool_desc = tool.get("description", "").lower()

        # 快速操作关键词
        fast_keywords = ["cache", "index", "quick", "fast", "simple", "basic", "get", "read"]
        if any(kw in tool_name or kw in tool_desc for kw in fast_keywords):
            return "Fast"

        # 慢速操作关键词
        slow_keywords = ["analyze", "compute", "process", "optimize", "advanced", "complex", "search all"]
        if any(kw in tool_name or kw in tool_desc for kw in slow_keywords):
            return "Slow"

        return "Medium"

    def _calculate_necessity_from_step(
        self,
        tool: dict[str, Any],
        step: Any,
        user_intent: str,
    ) -> float:
        """基于Abstract Sketch步骤计算工具的必要性得分

        Args:
            tool: 工具信息
            step: Abstract Sketch的当前步骤
            user_intent: 用户意图

        Returns:
            必要性得分 (0.0 - 1.0)
        """
        tool_name = tool.get("name", "").lower()
        tool_desc = tool.get("description", "").lower()
        step_desc = step.description.lower() if hasattr(step, 'description') else ""
        step_type = step.step_type.lower() if hasattr(step, 'step_type') else ""

        # 停用词列表
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "should",
            "could", "may", "might", "must", "can",
            "i", "you", "he", "she", "it", "we", "they",
            "this", "that", "these", "those",
            "and", "or", "but", "if", "when", "where", "why", "how",
            "in", "on", "at", "to", "for", "of", "with", "by", "from"
        }

        # 提取关键词
        tool_name_words = set(tool_name.split("_")) - stop_words
        tool_desc_words = set(tool_desc.split()) - stop_words
        step_desc_words = set(step_desc.split()) - stop_words
        step_type_words = set(step_type.split()) - stop_words

        # 计算与步骤的匹配度
        # 步骤类型匹配（最重要）
        type_overlap = len(tool_name_words & step_type_words)
        type_score = min(1.0, type_overlap * 0.5)

        # 步骤描述匹配
        desc_overlap = len((tool_name_words | tool_desc_words) & step_desc_words)
        desc_score = min(1.0, desc_overlap * 0.3)

        # 总得分
        total_score = type_score + desc_score

        # 确保在0-1范围内
        return min(1.0, max(0.0, total_score))

    def _generate_rationale(
        self,
        tool: dict[str, Any],
        step: Any,
        tool_source: str,
    ) -> str:
        """生成工具选择的推理理由

        Args:
            tool: 工具信息
            step: Abstract Sketch的当前步骤
            tool_source: 工具来源

        Returns:
            推理理由
        """
        tool_name = tool.get("name", "unknown")
        step_type = step.step_type if hasattr(step, 'step_type') else "unknown"

        return (
            f"Use {tool_name} to complete step '{step_type}'. "
            f"Tool source: {tool_source}. "
            f"Aligns with step requirements."
        )

    def infer_parameters_for_cached_tool(
        self,
        cached_tool_name: str,
        abstract_step_description: str,
        user_query: str,
        tool_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """为缓存的工具推理参数（基于当前上下文）

        这是 Path Cache 机制的关键部分：
        1. Path Cache 提供了已验证安全的工具名称
        2. 但参数需要根据当前的上下文重新推理
        3. 这样既保证了安全性（工具已验证），又保证了适应性（参数是最新的）

        Args:
            cached_tool_name: 从 path cache 中取出的工具名称（已验证安全）
            abstract_step_description: 当前抽象步骤描述
            user_query: 用户查询
            tool_schema: 工具的参数定义（可选，用于验证参数类型）

        Returns:
            推理出的参数字典
        """
        if not self.openai_client:
            logger.warning("[Hypothesizer] No OpenAI client available for parameter inference")
            return {}

        # 获取执行历史
        execution_history_text = "No previous executions yet"
        if self.auditor and hasattr(self.auditor, 'execution_history') and self.auditor.execution_history:
            history_lines = []
            for record in self.auditor.execution_history:
                tool_name = record["tool_name"]
                args = record.get("arguments", {})
                result = record.get("result", "")
                # 简化参数显示
                import json
                args_str = json.dumps(args) if args else "{}"
                # 截断result
                result_preview = result[:200] if result else "No result"
                history_lines.append(
                    f"  - Step {record['step_index']}: {tool_name}({args_str})\n"
                    f"    Result: {result_preview}"
                )
            execution_history_text = "\n".join(history_lines)

        # 构建工具参数说明
        tool_params_text = "No parameter schema available"
        if tool_schema and "properties" in tool_schema:
            params_info = tool_schema.get("properties", {})
            required_params = tool_schema.get("required", [])
            param_list = []
            for param_name, param_info in params_info.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "No description")
                is_required = " (REQUIRED)" if param_name in required_params else " (optional)"
                param_list.append(f"  - {param_name}: {param_type}{is_required}\n    Description: {param_desc}")
            tool_params_text = "\n".join(param_list) if param_list else "This tool has no parameters"

        # 构建 LLM prompt
        prompt = f"""[ROLE]
You are the **Parameter Inference Agent** within the VIGIL framework.
Your task is to infer the appropriate parameters for a cached tool based on the current execution context.

[CONTEXT]
1. **User Query**: "{user_query}"

2. **Current Abstract Step**:
   Description: {abstract_step_description}

3. **Execution History** (What has been done so far):
{execution_history_text}

4. **Selected Tool** (from Path Cache - already verified as safe):
   Tool Name: {cached_tool_name}

5. **Tool Parameters** (Schema):
{tool_params_text}

[TASK]
Infer the appropriate parameter values for the tool `{cached_tool_name}` to complete the current step.

**Critical Instructions**:
1. **Use Execution History**: Extract parameter values from previous tool results when available
   - Example: If a previous step returned "IBAN: XYZ123", use "XYZ123" for an iban parameter

2. **Distinguish Subject vs Object**:
   - Subject data (about the agent/user): get_iban, get_user_info, get_balance
   - Object data (about external entities): read_file, search results
   - For actions like transfer/send, use Object data as recipient/target

3. **Match Current Step**: Ensure parameters align with the abstract step description
   - If step says "transfer to account X", the recipient should be X (not the user's own account)

4. **Type Compliance**: Match parameter types to the schema
   - If schema says "integer", provide a number not a string
   - If schema says "list", provide an array

5. **Required Parameters**: All REQUIRED parameters must have values
   - Use reasonable defaults if no specific value is available
   - Example: If "n" is required but no specific number given, use n=50 or n=100

[OUTPUT FORMAT]
Return ONLY a valid JSON object with the parameter values. Do not include markdown formatting or explanations.

Example responses:
{{"recipient": "IBAN_FROM_FILE", "amount": 100.50}}
{{"file_path": "/path/to/file.txt"}}
{{"n": 50}}
{{}}

Your response (JSON only):"""

        try:
            # 调用 LLM
            response = self.openai_client.chat.completions.create(
                model=self.config.hypothesizer_model,
                messages=[
                    {"role": "system", "content": "You are a precise parameter inference assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # 使用低温度保证一致性
                max_tokens=1024,
            )

            # 记录 token 使用情况
            if response.usage:
                self.token_tracker.record_usage(
                    module=TokenStatsTracker.MODULE_PATH_CACHING,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    model=self.config.hypothesizer_model,
                )

            # 解析响应
            import json
            import re

            response_text = response.choices[0].message.content.strip()

            # 提取 JSON（可能被代码块包裹）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)

            # 如果响应不是以 { 开头，尝试查找 JSON 对象
            if not response_text.startswith('{'):
                json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)

            inferred_params = json.loads(response_text)

            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[Hypothesizer] ✓ Inferred parameters for cached tool '{cached_tool_name}': "
                    f"{inferred_params}"
                )

            return inferred_params

        except json.JSONDecodeError as e:
            logger.error(f"[Hypothesizer] Failed to parse parameter inference response as JSON: {e}")
            logger.debug(f"[Hypothesizer] LLM response: {response_text}")
            return {}
        except Exception as e:
            logger.error(f"[Hypothesizer] Error during parameter inference: {e}")
            return {}

