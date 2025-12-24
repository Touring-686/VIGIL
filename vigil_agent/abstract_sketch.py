"""抽象草图生成器 (Abstract Sketch Generator)

这是VIGIL框架的Intent Anchor增强组件，负责生成任务的抽象执行草图。

设计原则：
1. High-Level Planning: 生成抽象的执行步骤，不涉及具体工具
2. Immutable Anchor: 作为不可变的"北极星"指导整个执行过程
3. Constraint-Rich: 包含约束条件，防止任务漂移

Example:
  Query: "Book a hotel in Paris"
  Sketch: Search → Filter → Select → Book
  Constraints: Read-Only until Book, No External Communication
"""

import json
import logging
from typing import Any

import openai
from pydantic import BaseModel

from vigil_agent.config import VIGILConfig

logger = logging.getLogger(__name__)


class AbstractStep(BaseModel):
    """抽象执行步骤"""

    step_id: str
    """步骤ID"""

    step_type: str
    """步骤类型 (SEARCH, FILTER, SELECT, CREATE, UPDATE, DELETE, SEND, etc.)"""

    description: str
    """步骤描述"""

    allowed_operations: list[str] | None = None
    """允许的操作类型"""

    forbidden_operations: list[str] | None = None
    """禁止的操作类型"""

    expected_tools: list[str] | None = None
    """预期使用的工具名称（可选）"""


class AbstractSketch(BaseModel):
    """抽象执行草图"""

    user_query: str
    """用户查询"""

    steps: list[AbstractStep]
    """执行步骤序列"""

    global_constraints: list[str]
    """全局约束"""

    expected_outcome: str
    """预期结果"""

    metadata: dict[str, Any] | None = None
    """元数据"""


# 默认的草图生成提示模板 (原始版本 - 已弃用)
DEFAULT_SKETCH_PROMPT_LEGACY = """You are an AI task planner that generates ABSTRACT execution sketches.

Your task is to analyze the user's query and create a high-level execution plan WITHOUT specifying concrete tools.

IMPORTANT PRINCIPLES:
1. Generate ABSTRACT steps (e.g., "Search", "Filter", "Select", "Execute") not concrete tool names
2. Define what operations are ALLOWED and FORBIDDEN at each step
3. Create a SEQUENTIAL plan that serves as an immutable guide
4. Consider security: minimize permissions, avoid unnecessary operations

USER QUERY:
{user_query}

Generate a JSON object with the following structure:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "step_type": "SEARCH" | "FILTER" | "SELECT" | "CREATE" | "UPDATE" | "DELETE" | "SEND" | "READ" | "VERIFY",
            "description": "Human-readable description of what this step does",
            "allowed_operations": ["READ"],
            "forbidden_operations": ["WRITE", "DELETE", "SEND"]
        }}
    ],
    "global_constraints": [
        "No data modification until final confirmation",
        "No external communication except for the primary task",
        "Only interact with resources mentioned in user query"
    ],
    "expected_outcome": "What the user expects to achieve"
}}

COMMON STEP TYPES:
- SEARCH: Find relevant information
- FILTER: Narrow down results based on criteria
- SELECT: Choose a specific option
- READ: Retrieve detailed information
- CREATE: Create a new resource
- UPDATE: Modify existing resource
- DELETE: Remove a resource
- SEND: Send message/data to external party
- VERIFY: Confirm operation success

Generate the abstract sketch now:"""

# 改进的草图生成提示模板 (推荐用于非OpenAI模型)
DEFAULT_SKETCH_PROMPT = """You are an AI task planner that generates ABSTRACT execution sketches.

Your task: Analyze the user's query and create a high-level execution plan in JSON format.

CRITICAL FORMAT REQUIREMENTS:
1. "allowed_operations" MUST be an array (list), NEVER a string
2. "forbidden_operations" MUST be an array (list), NEVER a string
3. Each operation in the arrays must be a separate string element

WRONG FORMAT ❌:
{{
  "allowed_operations": "READ",  // ❌ WRONG: string instead of array
  "forbidden_operations": "WRITE, DELETE, SEND"  // ❌ WRONG: comma-separated string
}}

CORRECT FORMAT ✅:
{{
  "allowed_operations": ["READ"],  // ✅ CORRECT: array with one element
  "forbidden_operations": ["WRITE", "DELETE", "SEND"]  // ✅ CORRECT: array with multiple elements
}}

IMPORTANT PRINCIPLES:
1. Generate ABSTRACT steps (e.g., "Search", "Filter", "Select") not concrete tool names
2. Define what operations are ALLOWED and FORBIDDEN at each step
3. Create a SEQUENTIAL plan that serves as an immutable guide
4. Consider security: minimize permissions, avoid unnecessary operations

USER QUERY: {user_query}

You MUST output a JSON object. Here are examples:

Example 1 - For "Book a hotel in Paris":
{{
  "steps": [
    {{
      "step_id": "step_1",
      "step_type": "SEARCH",
      "description": "Search for hotels in Paris",
      "allowed_operations": ["READ"],
      "forbidden_operations": ["WRITE", "DELETE", "SEND"]
    }},
    {{
      "step_id": "step_2",
      "step_type": "FILTER",
      "description": "Filter hotels by criteria",
      "allowed_operations": ["READ"],
      "forbidden_operations": ["WRITE", "DELETE", "SEND"]
    }},
    {{
      "step_id": "step_3",
      "step_type": "SELECT",
      "description": "Select the best hotel option",
      "allowed_operations": ["READ"],
      "forbidden_operations": ["WRITE", "DELETE", "SEND"]
    }},
    {{
      "step_id": "step_4",
      "step_type": "CREATE",
      "description": "Create hotel booking",
      "allowed_operations": ["READ", "WRITE", "CREATE"],
      "forbidden_operations": ["DELETE", "SEND"]
    }},
    {{
      "step_id": "step_5",
      "step_type": "VERIFY",
      "description": "Verify booking was successful",
      "allowed_operations": ["READ"],
      "forbidden_operations": ["WRITE", "DELETE", "SEND"]
    }}
  ],
  "global_constraints": [
    "Read-only until final booking step",
    "No external communication except for booking confirmation",
    "Only interact with Paris hotels"
  ],
  "expected_outcome": "Successfully book a hotel in Paris"
}}

Example 2 - For "Send email to John with meeting notes":
{{
  "steps": [
    {{
      "step_id": "step_1",
      "step_type": "READ",
      "description": "Retrieve meeting notes",
      "allowed_operations": ["READ"],
      "forbidden_operations": ["WRITE", "DELETE", "SEND"]
    }},
    {{
      "step_id": "step_2",
      "step_type": "SEND",
      "description": "Send email to John",
      "allowed_operations": ["READ", "SEND"],
      "forbidden_operations": ["WRITE", "DELETE"]
    }},
    {{
      "step_id": "step_3",
      "step_type": "VERIFY",
      "description": "Confirm email was sent",
      "allowed_operations": ["READ"],
      "forbidden_operations": ["WRITE", "DELETE", "SEND"]
    }}
  ],
  "global_constraints": [
    "Only send to John, no other recipients",
    "Only access meeting notes, no other files",
    "No modifications to original notes"
  ],
  "expected_outcome": "Email with meeting notes sent to John"
}}

FIELD SPECIFICATIONS:
- step_type: String - one of "SEARCH", "FILTER", "SELECT", "READ", "CREATE", "UPDATE", "DELETE", "SEND", "VERIFY"
- allowed_operations: Array of strings - operations allowed in this step (e.g., ["READ", "WRITE"])
- forbidden_operations: Array of strings - operations forbidden in this step (e.g., ["DELETE", "SEND"])
- expected_tools: Array of strings (optional) - specific tool names expected to be used (e.g., ["read_file", "send_email"])
- Available operations: "READ", "WRITE", "DELETE", "SEND", "CREATE", "UPDATE"

REMINDER: allowed_operations and forbidden_operations are ALWAYS arrays [], NEVER strings!

Now generate the abstract sketch for the user query. Output ONLY valid JSON:"""


class AbstractSketchGenerator:
    """抽象草图生成器

    负责从用户查询生成抽象的执行草图。
    """

    def __init__(self, config: VIGILConfig):
        """初始化草图生成器

        Args:
            config: VIGIL配置
        """
        self.config = config
        self.client = openai.OpenAI()
        self._sketch_cache: dict[str, AbstractSketch] = {}

    def generate_sketch(self, user_query: str) -> AbstractSketch:
        """从用户查询生成抽象草图

        Args:
            user_query: 用户查询

        Returns:
            抽象执行草图
        """
        # 检查缓存
        if self.config.enable_sketch_caching and user_query in self._sketch_cache:
            if self.config.log_sketch_generation:
                logger.info(f"[AbstractSketchGenerator] Using cached sketch for query: {user_query}...")
            return self._sketch_cache[user_query]

        if self.config.log_sketch_generation:
            logger.info(f"[AbstractSketchGenerator] Generating sketch for query: {user_query}...")

        # 准备提示
        prompt = DEFAULT_SKETCH_PROMPT.format(user_query=user_query)

        # 调用LLM生成草图
        try:
            response = self.client.chat.completions.create(
                model=self.config.sketch_generator_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a task planner. Generate abstract execution sketches in JSON format."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.sketch_generator_temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty content")

            # 清理JSON内容（移除可能的markdown代码块标记）
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # 移除 ```json
            if content.startswith("```"):
                content = content[3:]  # 移除 ```
            if content.endswith("```"):
                content = content[:-3]  # 移除末尾的 ```
            content = content.strip()

            # 验证JSON格式
            try:
                sketch_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"[AbstractSketchGenerator] JSON parsing failed: {e}")
                logger.error(f"[AbstractSketchGenerator] Raw content: {content[:500]}...")
                raise ValueError(f"Invalid JSON from LLM: {e}")

            # 转换为AbstractSketch
            steps = []
            for i, s in enumerate(sketch_data.get("steps", []), 1):
                # 获取 allowed_operations 和 forbidden_operations
                allowed_ops = s.get("allowed_operations")
                forbidden_ops = s.get("forbidden_operations")
                expected_tools = s.get("expected_tools")

                # 自动修复：如果是字符串，转换为数组
                if isinstance(allowed_ops, str):
                    logger.warning(f"[AbstractSketchGenerator] Auto-fixing allowed_operations in step {i}: string -> array")
                    original_value = allowed_ops
                    # 处理逗号分隔的字符串
                    allowed_ops = [op.strip() for op in allowed_ops.split(",") if op.strip()]
                    if not allowed_ops and original_value.strip():
                        # 如果分割后为空但原字符串不为空，使用原字符串
                        allowed_ops = [original_value.strip()]
                    logger.info(f"[AbstractSketchGenerator] Fixed: '{original_value}' -> {allowed_ops}")

                if isinstance(forbidden_ops, str):
                    logger.warning(f"[AbstractSketchGenerator] Auto-fixing forbidden_operations in step {i}: string -> array")
                    original_value = forbidden_ops
                    # 处理逗号分隔的字符串
                    forbidden_ops = [op.strip() for op in forbidden_ops.split(",") if op.strip()]
                    if not forbidden_ops and original_value.strip():
                        # 如果分割后为空但原字符串不为空，使用原字符串
                        forbidden_ops = [original_value.strip()]
                    logger.info(f"[AbstractSketchGenerator] Fixed: '{original_value}' -> {forbidden_ops}")

                # 自动修复：expected_tools 如果是字符串，转换为数组
                if isinstance(expected_tools, str):
                    logger.warning(f"[AbstractSketchGenerator] Auto-fixing expected_tools in step {i}: string -> array")
                    original_value = expected_tools
                    expected_tools = [tool.strip() for tool in expected_tools.split(",") if tool.strip()]
                    if not expected_tools and original_value.strip():
                        expected_tools = [original_value.strip()]
                    logger.info(f"[AbstractSketchGenerator] Fixed: '{original_value}' -> {expected_tools}")

                step = AbstractStep(
                    step_id=s.get("step_id", f"step_{i}"),
                    step_type=s.get("step_type", "READ"),
                    description=s.get("description", ""),
                    allowed_operations=allowed_ops,
                    forbidden_operations=forbidden_ops,
                    expected_tools=expected_tools,
                )
                steps.append(step)

            sketch = AbstractSketch(
                user_query=user_query,
                steps=steps,
                global_constraints=sketch_data.get("global_constraints", []),
                expected_outcome=sketch_data.get("expected_outcome", ""),
                metadata={"model": self.config.sketch_generator_model, "raw_response": sketch_data}
            )

            # 缓存结果
            if self.config.enable_sketch_caching:
                self._sketch_cache[user_query] = sketch

            if self.config.log_sketch_generation:
                logger.info(f"[AbstractSketchGenerator] Generated sketch with {len(steps)} steps")
                for i, step in enumerate(steps, 1):
                    logger.debug(f"  Step {i}: {step.step_type} - {step.description}")

            return sketch

        except Exception as e:
            logger.error(f"[AbstractSketchGenerator] Failed to generate sketch: {e}")
            # 返回默认的保守草图
            return self._get_default_sketch(user_query)

    def _get_default_sketch(self, user_query: str) -> AbstractSketch:
        """获取默认的保守草图

        Args:
            user_query: 用户查询

        Returns:
            默认草图
        """
        logger.warning("[AbstractSketchGenerator] Using default conservative sketch")
        return AbstractSketch(
            user_query=user_query,
            steps=[
                AbstractStep(
                    step_id="step_1",
                    step_type="READ",
                    description="Gather necessary information",
                    allowed_operations=["READ"],
                    forbidden_operations=["WRITE", "DELETE", "SEND"],
                ),
                AbstractStep(
                    step_id="step_2",
                    step_type="VERIFY",
                    description="Verify the action is necessary",
                    allowed_operations=["READ"],
                    forbidden_operations=["WRITE", "DELETE", "SEND"],
                ),
            ],
            global_constraints=[
                "Default conservative mode: Minimize operations",
                "No modifications without explicit verification",
            ],
            expected_outcome="Complete the user's request safely",
        )

    def clear_cache(self) -> None:
        """清空缓存"""
        self._sketch_cache.clear()
        logger.info("[AbstractSketchGenerator] Cache cleared")
