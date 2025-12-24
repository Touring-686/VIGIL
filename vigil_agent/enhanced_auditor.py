"""增强版运行时审计器 (Enhanced Runtime Auditor)

扩展原有的RuntimeAuditor,添加以下验证能力：
1. Minimum Necessity Check - 最小必要性检验
2. Redundancy Check - 冗余性检验
3. Relevance Check - 相关性检验
4. Consistency Check - 一致性检验（与Intent Anchor对比）

防御攻击类型：
- Type II-A: Reasoning Distortion
- Type II-B: Over-Optimization Attack
"""

import logging
from typing import Any

from vigil_agent.abstract_sketch import AbstractSketch
from vigil_agent.config import VIGILConfig
from vigil_agent.runtime_auditor import RuntimeAuditor
from vigil_agent.types import AuditResult, SecurityConstraint, ToolCallInfo

logger = logging.getLogger(__name__)


class EnhancedRuntimeAuditor(RuntimeAuditor):
    """增强版运行时审计器

    在原有审计器基础上增加了最小必要性验证。
    """

    def __init__(
        self,
        config: VIGILConfig,
        constraint_set=None,
        abstract_sketch: AbstractSketch | None = None,
    ):
        """初始化增强版审计器

        Args:
            config: VIGIL配置
            constraint_set: 约束集合
            abstract_sketch: 抽象草图（Intent Anchor）
        """
        super().__init__(config, constraint_set)
        self.abstract_sketch = abstract_sketch
        self.available_tools: list[dict[str, Any]] = []  # 将由pipeline设置

    def update_abstract_sketch(self, sketch: AbstractSketch) -> None:
        """更新抽象草图

        Args:
            sketch: 新的抽象草图
        """
        self.abstract_sketch = sketch
        if self.config.log_audit_decisions:
            logger.info(f"[EnhancedAuditor] Updated abstract sketch with {len(sketch.steps)} steps")

    def set_available_tools(self, tools: list[dict[str, Any]]) -> None:
        """设置可用工具列表（用于冗余性检查）

        Args:
            tools: 工具列表
        """
        self.available_tools = tools

    def audit_tool_call(self, tool_call_info: ToolCallInfo) -> AuditResult:
        """审计工具调用（增强版）

        Args:
            tool_call_info: 工具调用信息

        Returns:
            审计结果
        """
        # 先执行基础审计
        base_result = super().audit_tool_call(tool_call_info)

        # 如果基础审计就拒绝了，直接返回
        if not base_result.allowed:
            return base_result

        # 执行增强检查
        if self.config.enable_minimum_necessity_check:
            necessity_result = self._check_minimum_necessity(tool_call_info)
            if not necessity_result.allowed:
                return necessity_result

        if self.config.enable_redundancy_check and self.available_tools:
            redundancy_result = self._check_redundancy(tool_call_info)
            if not redundancy_result.allowed:
                return redundancy_result

        if self.config.enable_sketch_consistency_check and self.abstract_sketch:
            consistency_result = self._check_sketch_consistency(tool_call_info)
            if not consistency_result.allowed:
                return consistency_result

        # 所有检查都通过
        return base_result

    def _check_minimum_necessity(self, tool_call_info: ToolCallInfo) -> AuditResult:
        """检查最小必要性

        验证此工具调用是否是达成用户意图的最小必要路径。

        Args:
            tool_call_info: 工具调用信息

        Returns:
            审计结果
        """
        tool_name = tool_call_info["tool_name"]
        arguments = tool_call_info["arguments"]

        # 检查1: 工具操作是否在用户查询中提及
        if self.constraint_set is None:
            return AuditResult(allowed=True)

        user_query = self.constraint_set.user_query.lower()

        # 提取工具的主要操作类型
        operation = self._infer_operation_from_tool(tool_name, arguments)

        # 检查是否相关
        relevance_score = self._calculate_relevance(tool_name, arguments, user_query)

        if relevance_score < self.config.minimum_necessity_threshold:
            # 相关性太低，可能是不必要的操作
            self.stats["blocked"] += 1
            return AuditResult(
                allowed=False,
                feedback_message=(
                    f"Tool '{tool_name}' appears to be unnecessary for the user's request. "
                    f"The user query does not seem to require this operation. "
                    f"Relevance score: {relevance_score:.2f} < {self.config.minimum_necessity_threshold:.2f}. "
                    f"Please only use tools that are directly necessary for the task."
                ),
                violated_constraints=[
                    SecurityConstraint(
                        constraint_id="minimum_necessity",
                        constraint_type="forbid",
                        description="Tool is not minimally necessary for the user's request",
                        condition={"relevance_score": relevance_score},
                        priority=2,
                        violation_message="This tool is not necessary for the user's task",
                    )
                ],
            )

        return AuditResult(allowed=True)

    def _check_redundancy(self, tool_call_info: ToolCallInfo) -> AuditResult:
        """检查冗余性

        如果存在功能更简单但足够的工具，拒绝当前工具。

        Args:
            tool_call_info: 工具调用信息

        Returns:
            审计结果
        """
        tool_name = tool_call_info["tool_name"]
        tool_lower = tool_name.lower()

        # 检查是否是"高级"工具
        advanced_keywords = ["advanced", "premium", "pro", "enhanced", "optimized", "powerful", "community"]

        is_advanced = any(kw in tool_lower for kw in advanced_keywords)

        if not is_advanced:
            return AuditResult(allowed=True)

        # 查找是否有基础版本的替代工具
        basic_keywords = ["basic", "simple", "standard", "get", "read", "official", "api"]

        alternative_tools = [
            t for t in self.available_tools
            if any(kw in t.get("name", "").lower() for kw in basic_keywords)
            and self._tools_have_similar_function(tool_name, t.get("name", ""))
        ]

        if alternative_tools:
            # 存在基础替代工具
            alternative_names = [t.get("name", "unknown") for t in alternative_tools[:3]]
            self.stats["blocked"] += 1
            return AuditResult(
                allowed=False,
                feedback_message=(
                    f"Tool '{tool_name}' provides more functionality than necessary. "
                    f"Consider using simpler alternatives: {', '.join(alternative_names)}. "
                    f"According to the Minimum Necessity Principle, we should use the simplest tool "
                    f"that can accomplish the task to minimize security risks."
                ),
                violated_constraints=[
                    SecurityConstraint(
                        constraint_id="redundancy_check",
                        constraint_type="forbid",
                        description="Tool provides redundant functionality",
                        condition={"has_simpler_alternative": True, "alternatives": alternative_names},
                        priority=3,
                        violation_message="Use simpler alternative tools instead",
                    )
                ],
            )

        return AuditResult(allowed=True)

    def _check_sketch_consistency(self, tool_call_info: ToolCallInfo) -> AuditResult:
        """检查与抽象草图的一致性

        验证工具调用是否符合预定的执行草图。

        Args:
            tool_call_info: 工具调用信息

        Returns:
            审计结果
        """
        if self.abstract_sketch is None:
            return AuditResult(allowed=True)

        tool_name = tool_call_info["tool_name"]
        operation = self._infer_operation_from_tool(tool_name, tool_call_info["arguments"])

        # 检查是否违反全局约束
        for constraint in self.abstract_sketch.global_constraints:
            constraint_lower = constraint.lower()

            # 检查"no modification"约束
            if "no modif" in constraint_lower or "read-only" in constraint_lower:
                if operation in ["WRITE", "UPDATE", "DELETE", "CREATE"]:
                    self.stats["blocked"] += 1
                    return AuditResult(
                        allowed=False,
                        feedback_message=(
                            f"Tool '{tool_name}' violates the execution sketch constraint: '{constraint}'. "
                            f"The operation type '{operation}' is not allowed at this stage."
                        ),
                        violated_constraints=[
                            SecurityConstraint(
                                constraint_id="sketch_consistency",
                                constraint_type="forbid",
                                description=f"Violates sketch constraint: {constraint}",
                                condition={"operation": operation},
                                priority=1,
                                violation_message=constraint,
                            )
                        ],
                    )

            # 检查"no external communication"约束
            if "no external" in constraint_lower or "no communication" in constraint_lower:
                if operation == "SEND" or any(
                    kw in tool_name.lower() for kw in ["send", "email", "message", "notify"]
                ):
                    self.stats["blocked"] += 1
                    return AuditResult(
                        allowed=False,
                        feedback_message=(
                            f"Tool '{tool_name}' violates the execution sketch constraint: '{constraint}'. "
                            f"External communication is not allowed."
                        ),
                    )

        return AuditResult(allowed=True)

    def _calculate_relevance(self, tool_name: str, arguments: dict[str, Any], user_query: str) -> float:
        """计算工具与用户查询的相关性

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            user_query: 用户查询

        Returns:
            相关性得分 (0.0 - 1.0)
        """
        # 提取工具名称中的关键词
        tool_words = set(tool_name.lower().split("_"))

        # 提取参数中的值
        arg_words = set()
        for value in arguments.values():
            if isinstance(value, str):
                arg_words.update(value.lower().split())

        # 提取查询中的关键词
        query_words = set(user_query.lower().split())

        # 计算重叠度
        tool_overlap = len(tool_words & query_words)
        arg_overlap = len(arg_words & query_words)

        total_overlap = tool_overlap + arg_overlap
        max_possible = max(len(query_words), 1)

        relevance = min(1.0, total_overlap / max_possible)

        return relevance

    def _tools_have_similar_function(self, tool1: str, tool2: str) -> bool:
        """判断两个工具是否有相似的功能

        Args:
            tool1: 工具1名称
            tool2: 工具2名称

        Returns:
            是否相似
        """
        # 提取工具的核心动词（去除修饰词）
        def extract_core_verb(tool_name: str) -> str:
            name_lower = tool_name.lower()
            # 去除常见的修饰词
            for modifier in ["advanced", "premium", "pro", "basic", "simple", "standard", "official", "community"]:
                name_lower = name_lower.replace(modifier, "")

            # 提取第一个动词
            words = name_lower.split("_")
            for word in words:
                if word in ["get", "set", "read", "write", "send", "search", "list", "create", "update", "delete"]:
                    return word

            return name_lower

        core1 = extract_core_verb(tool1)
        core2 = extract_core_verb(tool2)

        return core1 == core2
