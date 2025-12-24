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
from vigil_agent.types import ToolCallInfo

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, config: VIGILConfig):
        """初始化假设推理器

        Args:
            config: VIGIL配置
        """
        self.config = config

    def generate_hypotheses(
        self,
        available_tools: list[dict[str, Any]],
        current_state: dict[str, Any],
        user_intent: str,
    ) -> HypothesisTree:
        """生成假设树

        Args:
            available_tools: 可用工具列表（包含名称、描述等）
            current_state: 当前状态
            user_intent: 用户意图描述

        Returns:
            假设树
        """
        if self.config.log_hypothesis_generation:
            logger.info(f"[Hypothesizer] Generating hypotheses for intent: {user_intent[:50]}...")

        branches = []

        # 为每个可用工具生成一个假设分支
        for tool in available_tools:
            tool_name = tool.get("name", "unknown")

            # 分析工具特征
            risk_level = self._assess_risk_level(tool)
            has_side_effects = self._has_side_effects(tool_name)
            requires_comm = self._requires_communication(tool_name)
            necessity_score = self._calculate_necessity(tool, user_intent)
            redundancy_level = self._assess_redundancy(tool, available_tools, user_intent)

            # 创建假设分支
            branch = HypothesisBranch(
                branch_id=f"branch_{tool_name}",
                tool_call={
                    "tool_name": tool_name,
                    "arguments": {},  # 参数将在后续填充
                    "tool_call_id": None,
                },
                rationale=f"Use {tool_name} for this task",
                risk_level=risk_level,
                necessity_score=necessity_score,
                redundancy_level=redundancy_level,
                has_side_effects=has_side_effects,
                requires_external_communication=requires_comm,
                metadata={"tool_description": tool.get("description", "")},
            )

            branches.append(branch)

        # 根据最小必要性原则推荐分支
        recommended_id = self._recommend_branch(branches)

        hypothesis_tree = HypothesisTree(
            decision_point=user_intent,
            branches=branches,
            recommended_branch_id=recommended_id,
        )

        if self.config.log_hypothesis_generation:
            logger.info(f"[Hypothesizer] Generated {len(branches)} hypothesis branches")
            logger.info(f"[Hypothesizer] Recommended: {recommended_id}")

        return hypothesis_tree

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
        # 简化实现：基于关键词匹配
        tool_name = tool.get("name", "").lower()
        tool_desc = tool.get("description", "").lower()
        intent_lower = user_intent.lower()

        # 计算重叠度
        tool_words = set(tool_name.split("_") + tool_desc.split())
        intent_words = set(intent_lower.split())

        overlap = len(tool_words & intent_words)
        score = min(1.0, overlap / max(len(intent_words), 1))

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
