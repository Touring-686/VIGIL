"""增强版VIGIL执行器

整合了Perception Sanitizer的工具执行器。
"""

import logging
from collections.abc import Callable, Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionReturnType, FunctionsRuntime
from agentdojo.types import ChatMessage, ChatToolResultMessage, text_content_block_from_string

from vigil_agent.abstract_sketch import AbstractSketchGenerator
from vigil_agent.config import VIGILConfig
from vigil_agent.constraint_generator import ConstraintGenerator
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.perception_sanitizer import PerceptionSanitizer
from vigil_agent.types import ToolCallInfo

logger = logging.getLogger(__name__)


def enhanced_tool_result_to_str(tool_result: FunctionReturnType) -> str:
    """工具结果格式化器"""
    from agentdojo.agent_pipeline.tool_execution import tool_result_to_str

    return tool_result_to_str(tool_result)


class EnhancedVIGILToolsExecutor(BasePipelineElement):
    """增强版VIGIL工具执行器

    整合了以下功能：
    1. Perception Sanitizer: 清洗工具返回值和错误消息
    2. Runtime Auditor: 安全审计
    3. Reflective Backtracking: 反思回溯

    执行流程：
    1. 提取工具调用
    2. 进行安全审计
    3. 如果允许：执行工具 + 清洗返回值
    4. 如果拒绝：返回反馈消息（触发回溯）
    """

    def __init__(
        self,
        config: VIGILConfig,
        auditor: EnhancedRuntimeAuditor,
        sanitizer: PerceptionSanitizer,
        tool_output_formatter: Callable[[FunctionReturnType], str] = enhanced_tool_result_to_str,
    ):
        """初始化增强版VIGIL工具执行器

        Args:
            config: VIGIL配置
            auditor: 增强版运行时审计器
            sanitizer: 感知层清洗器
            tool_output_formatter: 工具输出格式化函数
        """
        self.config = config
        self.auditor = auditor
        self.sanitizer = sanitizer
        self.output_formatter = tool_output_formatter

        # 跟踪每个工具调用的回溯次数
        self._backtracking_counts: dict[str, int] = {}

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """执行pipeline元素

        Args:
            query: 用户查询
            runtime: 函数运行时
            env: 环境
            messages: 消息历史
            extra_args: 额外参数

        Returns:
            更新后的查询、运行时、环境、消息和额外参数
        """
        # 检查是否有工具调用需要处理
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args

        if messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args

        if messages[-1]["tool_calls"] is None or len(messages[-1]["tool_calls"]) == 0:
            return query, runtime, env, messages, extra_args

        # 设置可用工具列表（用于冗余性检查）
        available_tools = [
            {"name": tool.name, "description": tool.description}
            for tool in runtime.functions.values()
        ]
        self.auditor.set_available_tools(available_tools)

        # 处理工具调用
        tool_call_results = []

        for tool_call in messages[-1]["tool_calls"]:
            # 创建工具调用信息
            tool_call_info: ToolCallInfo = {
                "tool_name": tool_call.function,
                "arguments": dict(tool_call.args),
                "tool_call_id": tool_call.id,
            }

            # 检查工具是否存在
            if tool_call.function not in (tool.name for tool in runtime.functions.values()):
                tool_call_results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string("")],
                        tool_call_id=tool_call.id,
                        tool_call=tool_call,
                        error=f"Invalid tool {tool_call.function} provided.",
                    )
                )
                continue

            # 进行安全审计
            audit_result = self.auditor.audit_tool_call(tool_call_info)

            if not audit_result.allowed:
                # 工具调用被拦截
                if self.config.log_audit_decisions:
                    logger.warning(f"[EnhancedVIGILExecutor] Tool call blocked: {tool_call.function}")

                # 检查回溯次数
                backtrack_key = f"{tool_call.function}:{str(tool_call.args)}"
                backtrack_count = self._backtracking_counts.get(backtrack_key, 0)

                if (
                    self.config.enable_reflective_backtracking
                    and backtrack_count < self.config.max_backtracking_attempts
                ):
                    # 启用回溯：返回反馈消息
                    self._backtracking_counts[backtrack_key] = backtrack_count + 1

                    feedback_message = audit_result.feedback_message or (
                        f"The tool call '{tool_call.function}' was blocked by security constraints. "
                        "Please try a different approach."
                    )

                    # 添加回溯提示
                    if self.config.feedback_verbosity in ["detailed", "verbose"]:
                        feedback_message += (
                            f"\n\nAttempt {backtrack_count + 1}/{self.config.max_backtracking_attempts}. "
                            "Consider alternative tools or different parameters."
                        )

                    tool_call_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string(feedback_message)],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error="SecurityConstraintViolation",
                        )
                    )

                    logger.info(
                        f"[EnhancedVIGILExecutor] Reflective backtracking enabled for {tool_call.function} "
                        f"(attempt {backtrack_count + 1}/{self.config.max_backtracking_attempts})"
                    )
                else:
                    # 超过回溯次数或未启用回溯：返回错误
                    error_message = (
                        audit_result.feedback_message
                        or f"Tool '{tool_call.function}' cannot be executed due to security constraints."
                    )

                    if backtrack_count >= self.config.max_backtracking_attempts:
                        error_message += f"\n\nMaximum backtracking attempts ({self.config.max_backtracking_attempts}) reached."

                    tool_call_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string(error_message)],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error="SecurityConstraintViolation",
                        )
                    )

                    logger.warning(
                        f"[EnhancedVIGILExecutor] Tool call permanently blocked: {tool_call.function}"
                    )

            else:
                # 工具调用被允许，执行它
                if self.config.log_audit_decisions:
                    logger.debug(f"[EnhancedVIGILExecutor] Tool call allowed: {tool_call.function}")

                # 执行工具
                tool_call_result, error = runtime.run_function(env, tool_call.function, tool_call.args)

                # === Perception Sanitizer: 清洗返回值和错误 ===
                if self.config.enable_perception_sanitizer:
                    # 清洗返回值
                    tool_call_result = self.sanitizer.sanitize_tool_result(
                        tool_call.function, tool_call_result
                    )

                    # 清洗错误消息（Type III-A防御）
                    if error:
                        error = self.sanitizer.sanitize_error_message(tool_call.function, error)

                formatted_result = self.output_formatter(tool_call_result)

                tool_call_results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string(formatted_result)],
                        tool_call_id=tool_call.id,
                        tool_call=tool_call,
                        error=error,
                    )
                )

                # 成功执行后重置回溯计数
                backtrack_key = f"{tool_call.function}:{str(tool_call.args)}"
                if backtrack_key in self._backtracking_counts:
                    del self._backtracking_counts[backtrack_key]

        return query, runtime, env, [*messages, *tool_call_results], extra_args

    def reset_backtracking_counts(self) -> None:
        """重置回溯计数（用于新的任务）"""
        self._backtracking_counts.clear()
        logger.debug("[EnhancedVIGILExecutor] Backtracking counts reset")


class EnhancedVIGILInitQuery(BasePipelineElement):
    """增强版VIGIL初始化查询组件

    在接收用户查询时：
    1. 先生成抽象草图（Abstract Sketch Generator）- 了解执行计划
    2. 基于草图生成安全约束（Constraint Generator）- 针对具体步骤的安全控制
    3. 更新审计器

    设计理念：
    - Plan-First Approach: 先规划后约束
    - Context-Aware Constraints: 约束基于具体执行计划，更精确
    - Fine-Grained Control: 可以为每个步骤生成特定约束
    """

    def __init__(
        self,
        config: VIGILConfig,
        constraint_generator: ConstraintGenerator,
        sketch_generator: AbstractSketchGenerator | None,
        auditor: EnhancedRuntimeAuditor,
    ):
        """初始化增强版VIGIL查询组件

        Args:
            config: VIGIL配置
            constraint_generator: 约束生成器
            sketch_generator: 抽象草图生成器（可选）
            auditor: 增强版审计器
        """
        self.config = config
        self.constraint_generator = constraint_generator
        self.sketch_generator = sketch_generator
        self.auditor = auditor

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """处理查询并生成约束 + 草图

        Args:
            query: 用户查询
            runtime: 函数运行时
            env: 环境
            messages: 消息历史
            extra_args: 额外参数

        Returns:
            更新后的查询、运行时、环境、消息和额外参数
        """
        # 检查是否是新的用户查询（只在初始查询时生成约束和草图）
        if len(messages) == 0 or (len(messages) == 1 and messages[0]["role"] == "system"):
            # === Layer 1.1: 先生成抽象草图（执行计划）===
            abstract_sketch = None
            if self.sketch_generator and self.config.enable_abstract_sketch:
                logger.info(f"[EnhancedVIGILInit] Generating abstract sketch for query: {query}...")
                abstract_sketch = self.sketch_generator.generate_sketch(query)
                logger.info(f"[EnhancedVIGILInit] Generated sketch with {len(abstract_sketch.steps)} steps")

            # === Layer 1.2: 基于规划生成安全约束 ===
            logger.info(f"[EnhancedVIGILInit] Generating constraints for query: {query}")
            if abstract_sketch:
                logger.info(f"[EnhancedVIGILInit] Using abstract sketch to inform constraint generation")

            constraint_set = self.constraint_generator.generate_constraints(query, abstract_sketch)

            # 更新审计器（先更新约束，再更新草图）
            self.auditor.update_constraints(constraint_set)
            logger.info(f"[EnhancedVIGILInit] Generated {len(constraint_set.constraints)} constraints")

            if abstract_sketch:
                # 更新审计器的草图
                self.auditor.update_abstract_sketch(abstract_sketch)

                # 在系统消息中添加草图信息
                if messages and messages[0]["role"] == "system":
                    sketch_description = "\n\n=== EXECUTION PLAN ===\n"
                    for i, step in enumerate(abstract_sketch.steps, 1):
                        sketch_description += f"{i}. {step.step_type}: {step.description}\n"
                    sketch_description += "\nFollow this plan as a guide for completing the task.\n"

                    # 更新系统消息
                    from agentdojo.types import ChatSystemMessage

                    original_content = messages[0]["content"][0]
                    updated_content = original_content["text"] + sketch_description if "text" in original_content else sketch_description

                    messages = [
                        ChatSystemMessage(
                            role="system",
                            content=[text_content_block_from_string(updated_content)]
                        ),
                        *messages[1:]
                    ]

            # 可选：在extra_args中保存约束集和草图供后续使用
            extra_args = {
                **extra_args,
                "vigil_constraint_set": constraint_set,
                "vigil_abstract_sketch": abstract_sketch,
            }

        # 添加用户消息
        from agentdojo.types import ChatUserMessage

        query_message = ChatUserMessage(role="user", content=[text_content_block_from_string(query)])
        messages = [*messages, query_message]

        return query, runtime, env, messages, extra_args
