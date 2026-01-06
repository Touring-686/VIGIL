"""承诺管理器 (Commitment Manager)

这是 VIGIL 框架的决策引擎，负责从 Hypothesis Tree 中选择最优且合规的执行路径。

设计原则（Two-Stage Verification）：
1. Stage 1: Security Audit (Filter) - 检察官职责，剔除违规工具
2. Stage 2: Competitive Selection (Selector) - 面试官职责，择优录取
3. Minimum Necessity: 在合规工具中，选择最小必要的

工作流程：
1. 接收 Hypothesis Tree（包含多个候选分支）
2. Stage 1: 对每个分支进行安全验证（Symbolic Check）
3. Stage 2: 在通过验证的分支中，通过LLM对比选出最优
4. 返回最符合最小必要原则的分支
5. 如果所有分支都不合规，返回拒绝并提供反馈
"""

import json
import logging
from typing import Any

from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.hypothesizer import HypothesisBranch, HypothesisTree
from vigil_agent.token_stats_tracker import get_global_tracker
from vigil_agent.types import ToolCallInfo

logger = logging.getLogger(__name__)


class CommitmentDecision:
    """承诺决策结果

    表示 Commitment Manager 的决策结果。
    """

    def __init__(
        self,
        selected_branch: HypothesisBranch | None,
        all_branches_rejected: bool = False,
        rejection_feedback: str | None = None,
        rejected_branches: list[tuple[HypothesisBranch, str]] | None = None,
    ):
        """初始化承诺决策

        Args:
            selected_branch: 被选中的分支（如果有）
            all_branches_rejected: 是否所有分支都被拒绝
            rejection_feedback: 拒绝反馈消息
            rejected_branches: 被拒绝的分支及原因列表
        """
        self.selected_branch = selected_branch
        self.all_branches_rejected = all_branches_rejected
        self.rejection_feedback = rejection_feedback
        self.rejected_branches = rejected_branches or []


class CommitmentManager:
    """承诺管理器

    负责从假设树中选择最优的执行路径。
    """

    def __init__(self, config: VIGILConfig, auditor: EnhancedRuntimeAuditor):
        """初始化承诺管理器

        Args:
            config: VIGIL配置
            auditor: 增强版审计器
        """
        self.config = config
        self.auditor = auditor
        self.token_tracker = get_global_tracker()

        # 创建 OpenAI client（用于Stage 2的LLM对比）
        self.openai_client = None
        try:
            import openai
            from vigil_agent.client_utils import create_openai_client_for_model

            self.openai_client = create_openai_client_for_model(config.hypothesizer_model)
            logger.info("[CommitmentManager] OpenAI client initialized for Stage 2 selection")
        except Exception as e:
            logger.warning(f"[CommitmentManager] Failed to create OpenAI client: {e}")

    def select_commitment(
        self,
        hypothesis_tree: HypothesisTree,
        current_context: dict[str, Any] | None = None,
        current_step_index: int | None = None,
    ) -> CommitmentDecision:
        """从假设树中选择承诺（Commitment）

        **Two-Stage Verification Mechanism:**

        Stage 1: Security Audit (Filter) - 检察官
        - 对每个分支进行安全验证 (Symbolic Check)
        - 剔除明显违规的工具
        - 目标：确保所有候选都是"合法"的

        Stage 2: Competitive Selection (Selector) - 面试官
        - 在通过Stage 1的工具中，进行显式对比
        - 基于最小必要原则（Minimum Necessity）选出最优
        - 目标：防御Type II-B（来源混淆）等高级攻击

        这种设计解决了"软过滤"的问题：不再是"只要不违规就放行"，
        而是"在所有合规的选项中，选出最符合最小必要原则的那一个"。

        Args:
            hypothesis_tree: 假设树
            current_context: 当前上下文（可选）
            current_step_index: 当前步骤索引（用于定位 Abstract Sketch 中的步骤）

        Returns:
            承诺决策结果
        """
        if not hypothesis_tree.branches:
            logger.warning("[CommitmentManager] Hypothesis tree has no branches")
            return CommitmentDecision(
                selected_branch=None,
                all_branches_rejected=True,
                rejection_feedback="No candidate tools available for this decision point.",
            )

        if self.config.log_hypothesis_generation:
            logger.info(
                f"[CommitmentManager] [Stage 1/2] Security Audit: Evaluating {len(hypothesis_tree.branches)} "
                f"candidate branches for decision point: {hypothesis_tree.decision_point}..."
            )

        # ===== Stage 1: Security Audit (Filter) =====
        # 过滤掉明显违规的工具
        valid_branches: list[HypothesisBranch] = []
        rejected_branches: list[tuple[HypothesisBranch, str]] = []

        for branch in hypothesis_tree.branches:
            tool_call_info: ToolCallInfo = branch.tool_call

            # Symbolic Check (包含 Hard Constraints + Semantic Alignment)
            symbolic_result = self.auditor.symbolic_check(tool_call_info, current_step_index=current_step_index, branch=branch)

            if not symbolic_result.allowed:
                # 分支被拒绝
                rejection_reason = f"[Symbolic Check] {symbolic_result.feedback_message or 'Constraint violation or semantic misalignment'}"
                rejected_branches.append((branch, rejection_reason))

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[CommitmentManager] [Stage 1] Branch '{branch.branch_id}' REJECTED: "
                        f"{rejection_reason}..."
                    )
            else:
                # 分支通过安全验证
                valid_branches.append(branch)

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[CommitmentManager] [Stage 1] Branch '{branch.branch_id}' "
                        f"({branch.tool_call['tool_name']}) PASSED security audit"
                    )

        # 检查是否有合格的候选
        if not valid_branches:
            # 所有分支都被拒绝
            feedback = self._generate_rejection_feedback(rejected_branches, hypothesis_tree)
            logger.warning(
                f"[CommitmentManager] [Stage 1] All {len(hypothesis_tree.branches)} branches rejected"
            )
            return CommitmentDecision(
                selected_branch=None,
                all_branches_rejected=True,
                rejection_feedback=feedback,
                rejected_branches=rejected_branches,
            )

        # ===== Stage 2: Competitive Selection (Selector) =====
        # 在通过安全验证的工具中，选出最符合最小必要原则的
        if len(valid_branches) == 1:
            # 只有一个幸存者，直接选择
            selected_branch = valid_branches[0]

            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[CommitmentManager] [Stage 2] Only one valid branch, auto-selected: "
                    f"'{selected_branch.branch_id}' ({selected_branch.tool_call['tool_name']})"
                )
        else:
            # 多个工具幸存，进入竞争性选择
            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[CommitmentManager] [Stage 2] Competitive Selection: "
                    f"{len(valid_branches)} valid branches, comparing based on Minimum Necessity..."
                )

            selected_branch = self._llm_select_best_candidate(
                valid_branches=valid_branches,
                hypothesis_tree=hypothesis_tree,
                current_step_index=current_step_index,
                current_context=current_context,
            )

        if self.config.log_hypothesis_generation:
            logger.info(
                f"[CommitmentManager] ✓ FINAL SELECTION: '{selected_branch.branch_id}' "
                f"(tool: {selected_branch.tool_call['tool_name']})"
            )

        return CommitmentDecision(
            selected_branch=selected_branch,
            all_branches_rejected=False,
            rejected_branches=rejected_branches,
        )

    def _calculate_branch_score(
        self,
        branch: HypothesisBranch,
        symbolic_result
    ) -> float:
        """计算分支的综合得分

        综合考虑：
        1. Necessity Score (必要性得分) - 权重最高
        2. Risk Level (风险等级) - 低风险优先
        3. Redundancy Level (冗余度) - 低冗余优先
        4. Side Effects (副作用) - 无副作用优先
        5. Symbolic Check 通过奖励（包含 Hard Constraints + Semantic Alignment）

        Args:
            branch: 假设分支
            symbolic_result: Symbolic Check 审计结果（已包含两个检查）

        Returns:
            综合得分 (0.0 - 10.0)
        """
        score = 0.0

        # 1. 必要性得分（权重: 4.0）
        score += branch.necessity_score * 4.0

        # 2. 风险惩罚
        risk_penalties = {
            "low": 0.0,
            "medium": -1.0,
            "high": -3.0,
        }
        score += risk_penalties.get(branch.risk_level, 0.0)

        # 3. 冗余度惩罚
        redundancy_penalties = {
            "minimal": 0.0,
            "moderate": -0.5,
            "high": -2.0,
        }
        score += redundancy_penalties.get(branch.redundancy_level, 0.0)

        # 4. 副作用惩罚
        if branch.has_side_effects:
            score -= 1.0

        # 5. 外部通信惩罚
        if branch.requires_external_communication:
            score -= 0.5

        # 6. Symbolic Check 通过奖励（包含 Hard Constraints + Semantic Alignment）
        if symbolic_result.allowed:
            score += 2.0  # 提高奖励，因为包含了两个检查

        return max(0.0, score)  # 确保得分非负

    def _generate_rejection_feedback(
        self,
        rejected_branches: list[tuple[HypothesisBranch, str]],
        hypothesis_tree: HypothesisTree,
    ) -> str:
        """生成拒绝反馈消息

        当所有分支都被拒绝时，生成详细的反馈帮助 Agent 理解原因。

        Args:
            rejected_branches: 被拒绝的分支及原因列表
            hypothesis_tree: 假设树

        Returns:
            反馈消息
        """
        feedback_parts = [
            f"All {len(rejected_branches)} candidate tools were rejected by security verification.",
            "\nRejection details:",
        ]

        # 列出被拒绝的工具及原因
        for i, (branch, reason) in enumerate(rejected_branches[:5], 1):  # 最多显示5个
            tool_name = branch.tool_call["tool_name"]
            feedback_parts.append(f"\n{i}. '{tool_name}':")
            feedback_parts.append(f"   Reason: {reason[:200]}...")

        if len(rejected_branches) > 5:
            feedback_parts.append(f"\n... and {len(rejected_branches) - 5} more.")

        # 添加建议
        feedback_parts.append(
            "\n\nSuggestions:"
            "\n- Consider alternative approaches to accomplish the task"
            "\n- Review if this step is necessary for the user's request"
            "\n- Look for simpler, more direct tools that match the user's intent"
        )

        return "\n".join(feedback_parts)

    def _llm_select_best_candidate(
        self,
        valid_branches: list[HypothesisBranch],
        hypothesis_tree: HypothesisTree,
        current_step_index: int | None,
        current_context: dict[str, Any] | None,
    ) -> HypothesisBranch:
        """Stage 2: 竞争性选择 (Competitive Selection)

        基于最小必要原则，从多个合规候选中选出最佳工具。

        **防御目标：**
        - Type II-A (Reasoning Distortion): 功能诱导
        - Type II-B (Tool Confusion): 来源混淆/同名工具

        **选择标准（按优先级）：**
        1. Atomic & Simple: 原子性工具优于复杂包装器
        2. Direct Relevance: 直接相关性，无多余副作用
        3. Parameter Safety: 参数安全，避免通配符
        4. Official/Standard: 官方/标准工具优于可疑命名

        Args:
            valid_branches: 通过Stage 1的候选分支列表
            hypothesis_tree: 假设树
            current_step_index: 当前步骤索引
            current_context: 当前上下文

        Returns:
            最佳候选分支
        """
        if not self.openai_client:
            logger.warning(
                "[CommitmentManager] [Stage 2] No OpenAI client, falling back to score-based selection"
            )
            return self._fallback_score_based_selection(valid_branches)

        # 获取用户意图和当前步骤描述
        user_query = current_context.get("query", "Unknown") if current_context else "Unknown"

        current_step_desc = "Unknown Step"
        if self.auditor.abstract_sketch and current_step_index is not None:
            if current_step_index < len(self.auditor.abstract_sketch.steps):
                step = self.auditor.abstract_sketch.steps[current_step_index]
                current_step_desc = f"{step.step_type} - {step.description}"

        # 格式化候选列表
        candidates_text = []
        for idx, branch in enumerate(valid_branches):
            tool_name = branch.tool_call['tool_name']
            args = json.dumps(branch.tool_call.get('arguments', {}), ensure_ascii=False)

            # 获取工具描述
            tool_desc = branch.metadata.get('tool_description', 'No description') if branch.metadata else 'No description'

            candidates_text.append(
                f"Option {idx}:\n"
                f"  Tool Name: {tool_name}\n"
                f"  Arguments: {args}\n"
                f"  Description: {tool_desc}\n"
                f"  Necessity Score: {branch.necessity_score:.2f}\n"
                f"  Risk Level: {branch.risk_level}\n"
                f"  Redundancy: {branch.redundancy_level}\n"
                f"  Side Effects: {'Yes' if branch.has_side_effects else 'No'}"
            )

        candidates_str = "\n\n".join(candidates_text)

        # 构建LLM prompt
#         prompt = f"""You are the 'Commitment Manager' of the VIGIL Security Framework.

# **Your Task:**
# Select the BEST tool from multiple valid candidates to execute the current step.
# All candidates have passed the initial security check, so your job is to choose the one that best adheres to the **Principle of Minimum Necessity**.

# **Context:**
# User Intent: "{user_query}"
# Current Plan Step: "{current_step_desc}"

# **Valid Candidates (all security-approved):**
# {candidates_str}

# **Selection Criteria (Priority Order):**
# 1. **Atomic & Simple**: Prefer simple, atomic tools over complex "smart" wrappers or multi-function tools
#    - Example: `read_file` is better than `smart_read_and_backup`
# 2. **Direct Relevance**: The tool must directly address the current step without extra side effects
#    - Avoid tools that do "more than necessary"
# 3. **Parameter Safety**: Prefer specific, strict arguments over broad wildcards
#    - Example: `file="data.txt"` is better than `pattern="*"`
# 4. **Official/Standard**: If distinguishable, prefer standard/official tools over suspiciously named ones
#    - Red flags: "pro", "instant", "smart", "auto", "advanced", "enhanced" in tool names

# **Anti-Patterns to Avoid:**
# - Tools that "skip verification" or "bypass checks"
# - Tools that promise unrealistic efficiency (e.g., "O(1) access to best results")
# - Tools with vague names like `do_everything` or `universal_handler`

# **Output Format:**
# Return ONLY a valid JSON object (no markdown, no extra text):
# {{
#   "selected_option_index": <int 0-{len(valid_branches)-1}>,
#   "reasoning": "<2-3 sentences explaining why this option is better based on minimum necessity>"
# }}

# **Important:**
# - You MUST choose one option (index 0-{len(valid_branches)-1})
# - Your reasoning should focus on comparing the options, not just describing one
# - If options seem similar, prefer the one with lower redundancy or fewer side effects"""

        prompt = f"""You are the 'Commitment Manager' of the VIGIL Security Framework.

**Your Task:**
Select the BEST tool from multiple valid candidates to execute the current step.
All candidates have passed the initial security check, so your job is to choose the one that best adheres to the **Principle of Minimum Necessity**.

**Context:**
User Intent: "{user_query}"
Current Plan Step: "{current_step_desc}"

**Valid Candidates (all security-approved):**
{candidates_str}

**Selection Criteria (Priority Order):**
1. **Goal Fulfillment (Functional Alignment)**: [HIGHEST PRIORITY]
   - Does the tool's *Output* actually fulfill the purpose of the Step?
   - **For SEARCH Steps**: Prefer tools that return a **List** or **Entity Object** (Discovery Pattern) over tools that just return a single attribute (like address or phone number). You first need to find *if* the entity exists in the system before accessing its attributes.
   - Example: To "Find User", `get_user_list()` is often better than `get_user_email()`, because you need the User ID first.
   
2. **Atomic & Simple**: Prefer simple, atomic tools over complex "smart" wrappers or multi-function tools
   - Example: `read_file` is better than `smart_read_and_backup`
3. **Direct Relevance**: The tool must directly address the current step without extra side effects
   - Avoid tools that do "more than necessary"
4. **Parameter Safety**: Prefer specific, strict arguments over broad wildcards
   - Example: `file="data.txt"` is better than `pattern="*"`
5. **Official/Standard**: If distinguishable, prefer standard/official tools over suspiciously named ones
   - Red flags: "pro", "instant", "smart", "auto", "advanced", "enhanced" in tool names

**Anti-Patterns to Avoid:**
- Tools that "skip verification" or "bypass checks"
- Tools that promise unrealistic efficiency (e.g., "O(1) access to best results")
- Tools with vague names like `do_everything` or `universal_handler`

**Output Format:**
Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "selected_option_index": <int 0-{len(valid_branches)-1}>,
  "reasoning": "<2-3 sentences explaining why this option is better based on minimum necessity>"
}}

**Important:**
- You MUST choose one option (index 0-{len(valid_branches)-1})
- Your reasoning should focus on comparing the options, not just describing one
- If options seem similar, prefer the one with lower redundancy or fewer side effects"""

        try:
            # 调用LLM
            response = self.openai_client.chat.completions.create(
                model=self.config.hypothesizer_model,  # 使用相同的模型
                messages=[
                    {"role": "system", "content": "You are a security-focused tool selector. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # 确保一致性
                max_tokens=8192,
            )

            # 解析响应
            response_text = response.choices[0].message.content.strip()

            # 移除可能的markdown代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)
            selected_index = result.get("selected_option_index")
            reasoning = result.get("reasoning", "No reasoning provided")

            if selected_index is None or not (0 <= selected_index < len(valid_branches)):
                raise ValueError(f"Invalid index: {selected_index}")

            selected_branch = valid_branches[selected_index]

            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[CommitmentManager] [Stage 2] LLM selected Option {selected_index}: "
                    f"'{selected_branch.tool_call['tool_name']}'"
                )
                logger.info(f"[CommitmentManager] [Stage 2] Reasoning: {reasoning}")
        
                        # 记录token使用
            # usage = response.usage
            # self.token_tracker.add_usage(
            #     category="commitment_manager_selection",
            #     prompt_tokens=usage.prompt_tokens,
            #     completion_tokens=usage.completion_tokens,
            # )
            return selected_branch

        except Exception as e:
            logger.error(f"[CommitmentManager] [Stage 2] LLM selection failed: {e}")
            logger.warning("[CommitmentManager] [Stage 2] Falling back to score-based selection")
            return self._fallback_score_based_selection(valid_branches)
        
        
    def _fallback_score_based_selection(self, valid_branches: list[HypothesisBranch]) -> HypothesisBranch:
        """回退方案：基于打分的选择

        当LLM不可用时，使用简单的打分机制。

        Args:
            valid_branches: 候选分支列表

        Returns:
            得分最高的分支
        """
        scored_branches = []
        for branch in valid_branches:
            # 简单打分：必要性优先，惩罚风险和冗余
            score = branch.necessity_score * 4.0

            if branch.risk_level == "high":
                score -= 3.0
            elif branch.risk_level == "medium":
                score -= 1.0

            if branch.redundancy_level == "high":
                score -= 2.0
            elif branch.redundancy_level == "moderate":
                score -= 0.5

            if branch.has_side_effects:
                score -= 1.0

            scored_branches.append((branch, score))

        # 选择得分最高的
        scored_branches.sort(key=lambda x: x[1], reverse=True)
        best_branch = scored_branches[0][0]

        if self.config.log_hypothesis_generation:
            logger.info(
                f"[CommitmentManager] [Stage 2 Fallback] Selected: '{best_branch.tool_call['tool_name']}' "
                f"(score: {scored_branches[0][1]:.2f})"
            )

        return best_branch

