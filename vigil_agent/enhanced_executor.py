"""增强版VIGIL执行器

整合了Perception Sanitizer的工具执行器。
"""

import logging
from collections.abc import Callable, Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionReturnType, FunctionsRuntime
from agentdojo.types import ChatMessage, ChatToolResultMessage, text_content_block_from_string

from vigil_agent.abstract_sketch import AbstractSketchGenerator
from vigil_agent.commitment_manager import CommitmentManager
from vigil_agent.config import VIGILConfig
from vigil_agent.constraint_generator import ConstraintGenerator
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.hypothesizer import Hypothesizer
from vigil_agent.path_cache import PathCache
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
        hypothesizer=None,
        commitment_manager: CommitmentManager | None = None,
        path_cache: PathCache | None = None,
        tool_output_formatter: Callable[[FunctionReturnType], str] = enhanced_tool_result_to_str,
    ):
        """初始化增强版VIGIL工具执行器

        Args:
            config: VIGIL配置
            auditor: 增强版运行时审计器
            sanitizer: 感知层清洗器
            hypothesizer: 假设推理器（可选，用于多分支推理）
            commitment_manager: 承诺管理器（可选，用于选择最优路径）
            path_cache: 路径缓存（可选，用于学习和优化）
            tool_output_formatter: 工具输出格式化函数
        """
        self.config = config
        self.auditor = auditor
        self.sanitizer = sanitizer
        self.hypothesizer = hypothesizer
        self.commitment_manager = commitment_manager
        self.path_cache = path_cache
        self.output_formatter = tool_output_formatter

        # 跟踪每个工具调用的回溯次数
        self._backtracking_counts: dict[str, int] = {}

        # 跟踪参数验证错误的重试次数
        self._validation_retry_counts: dict[str, int] = {}
        self._max_validation_retries = 3  # 每个工具最多重试3次参数

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
        # ===== 优先检查是否是 REASONING 步骤（__no_tool_call__）=====
        # REASONING 步骤：直接调用 LLM 进行推理，把 LLM 当作一个工具
        current_step_is_reasoning = extra_args.get('current_step_is_reasoning', False)
        current_step_is_response = extra_args.get('current_step_is_response', False)

        if current_step_is_reasoning:
            if current_step_is_response:
                logger.info(
                    "[EnhancedVIGILExecutor] 📝 RESPONSE step detected - calling LLM to generate final response"
                )
            else:
                logger.info(
                    "[EnhancedVIGILExecutor] 🧠 REASONING step detected - calling LLM as a reasoning tool (no tool execution allowed)"
                )

            # 调用 LLM 进行推理（不允许使用工具）
            reasoning_message = self._execute_reasoning_step(messages, query, extra_args)

            # 将 LLM 的推理结果作为 assistant message 添加到历史
            messages = [*messages, reasoning_message]

            # 如果是 __response__ 步骤，将输出存储到 extra_args 中
            if current_step_is_response:
                # 提取响应内容
                response_content = "Response completed."
                if reasoning_message and "content" in reasoning_message and reasoning_message["content"]:
                    if isinstance(reasoning_message["content"], list) and len(reasoning_message["content"]) > 0:
                        content_block = reasoning_message["content"][0]
                        response_content = content_block.get("content", response_content)

                # 存储到 extra_args，用于最终返回
                extra_args = {**extra_args, 'final_response': response_content}

                logger.info(
                    "[EnhancedVIGILExecutor] ✓ RESPONSE step completed - output stored in extra_args"
                )
            else:
                logger.info(
                    "[EnhancedVIGILExecutor] ✓ REASONING step completed - LLM provided analysis"
                )

            # === 记录 REASONING/RESPONSE 步骤到执行历史 ===
            if self.auditor:
                current_step_index = extra_args.get('current_step_index', 0)
                step_description = None

                # 从 abstract sketch 获取步骤描述
                if self.auditor.abstract_sketch and hasattr(self.auditor.abstract_sketch, 'steps'):
                    if current_step_index < len(self.auditor.abstract_sketch.steps):
                        step = self.auditor.abstract_sketch.steps[current_step_index - 1]
                        step_description = f"{step.step_type} - {step.description}"

                # 提取推理结果文本
                reasoning_result = "Reasoning completed."
                if reasoning_message and "content" in reasoning_message and reasoning_message["content"]:
                    if isinstance(reasoning_message["content"], list) and len(reasoning_message["content"]) > 0:
                        content_block = reasoning_message["content"][0]
                        reasoning_result = content_block.get("content", reasoning_result)

                # 创建虚拟的 tool_call_info 用于记录
                tool_name = "__llm_response__" if current_step_is_response else "__llm_reasoning__"
                reasoning_tool_call: ToolCallInfo = {
                    "tool_name": tool_name,
                    "arguments": {},
                    "tool_call_id": None,
                }

                self.auditor.record_execution_step(
                    step_index=current_step_index,
                    tool_call_info=reasoning_tool_call,
                    result=reasoning_result,
                    step_description=step_description,
                )

                if self.config.log_audit_decisions:
                    step_type = "RESPONSE" if current_step_is_response else "REASONING"
                    logger.info(
                        f"[EnhancedVIGILExecutor] Recorded {step_type} step {current_step_index + 1} "
                        f"to execution history: {reasoning_result[:100]}..."
                    )

            # 清除 REASONING 标志
            extra_args = {**extra_args, 'current_step_is_reasoning': False, 'finished_task': False}

            return query, runtime, env, messages, extra_args

        # ===== 正常的工具执行流程 =====
        # 检查是否有工具调用需要处理
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args

        if messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args

        # 检查是否有工具调用
        if messages[-1]["tool_calls"] is None or len(messages[-1]["tool_calls"]) == 0:
            return query, runtime, env, messages, extra_args

        # ===== CRITICAL: 检查是否尝试调用多个工具 =====
        # VIGIL的设计原则：每次只执行一个工具，确保可控性和安全性
        if len(messages[-1]["tool_calls"]) > 1:
            logger.warning(
                f"[EnhancedVIGILToolsExecutor] Agent attempted to call {len(messages[-1]['tool_calls'])} tools "
                f"simultaneously. VIGIL policy: ONE tool per turn."
            )

            # 拒绝所有工具调用，返回错误消息
            error_message = (
                f"❌ VIGIL Policy Violation: Multiple Tool Calls Detected\n\n"
                f"You attempted to call {len(messages[-1]['tool_calls'])} tools simultaneously:\n"
            )

            for i, tc in enumerate(messages[-1]["tool_calls"], 1):
                error_message += f"  {i}. {tc.function}({dict(tc.args)})\n"

            error_message += (
                f"\n**VIGIL Policy: You MUST call exactly ONE tool per turn.**\n\n"
                f"To complete this task:\n"
                f"1. Choose the MOST IMPORTANT tool for the current step\n"
                f"2. Call that tool alone and wait for its result\n"
                f"3. In subsequent turns, call additional tools if needed\n\n"
                f"Please retry with a SINGLE tool call."
            )

            # 生成一个错误结果消息（针对第一个工具调用）
            tool_call_results = [
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(error_message)],
                    tool_call_id=messages[-1]["tool_calls"][0].id,
                    tool_call=messages[-1]["tool_calls"][0],
                    error=error_message,
                )
            ]

            # 立即返回错误，不执行任何工具
            return query, runtime, env, [*messages, *tool_call_results], extra_args

        # 设置可用工具列表（用于冗余性检查）
        available_tools = [
            {"name": tool.name, "description": tool.description}
            for tool in runtime.functions.values()
        ]
        self.auditor.set_available_tools(available_tools)

        # 注意：Hypothesis Tree 生成已移至 HypothesisGuidanceElement
        # 该element在LLM推理之前运行，生成guidance并注入到context中
        # 这确保了正确的执行顺序：
        #   Hypothesis Generation → Verification → Commitment → LLM Decision
        # 而不是错误的：
        #   LLM Decision → Hypothesis Generation (事后分析)

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

            # ===== 检查是否需要审计 =====
            # 在 direct mode 下，如果工具已经通过 HypothesisGuidance 的完整审计，跳过重复审计
            skip_audit = extra_args.get('skip_audit', False) and extra_args.get('vigil_pre_approved') == tool_call.function

            if skip_audit:
                # 工具已经通过 Two-Stage Verification，直接执行
                if self.config.log_audit_decisions:
                    logger.info(
                        f"[EnhancedVIGILExecutor] Tool '{tool_call.function}' PRE-APPROVED by HypothesisGuidance "
                        f"(Two-Stage Verification passed), skipping redundant audit"
                    )

                # 直接执行工具（跳到执行部分）
                needs_backtrack = self._execute_tool(
                    tool_call=tool_call,
                    tool_call_info=tool_call_info,
                    runtime=runtime,
                    env=env,
                    query=query,
                    tool_call_results=tool_call_results,
                    extra_args=extra_args,
                )

                # 如果检测到需要回溯（SOP 注入），设置标志
                if needs_backtrack:
                    extra_args = {**extra_args, 'backtrack_needed': True}

                # 清除标志（避免影响下一轮）
                if 'skip_audit' in extra_args:
                    extra_args = {**extra_args, 'skip_audit': False, 'vigil_pre_approved': None}

                continue

            # ===== 进行安全审计 =====
            # 注意：这里的审计是针对以下场景：
            # 1. Guidance mode：LLM 可能不遵循 guidance，需要最后一道防线
            # 2. 非 direct mode：传统的审计流程
            if self.config.log_audit_decisions:
                logger.info(
                    f"[EnhancedVIGILExecutor] Auditing tool call: {tool_call.function} "
                    f"(not pre-approved, performing full security check)"
                )

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
                    logger.info(f"[EnhancedVIGILExecutor] ✓ Tool call ALLOWED: {tool_call.function}")

                # 执行工具
                needs_backtrack = self._execute_tool(
                    tool_call=tool_call,
                    tool_call_info=tool_call_info,
                    runtime=runtime,
                    env=env,
                    query=query,
                    tool_call_results=tool_call_results,
                    extra_args=extra_args,
                )

                # 如果检测到需要回溯（SOP 注入），设置标志
                if needs_backtrack:
                    extra_args = {**extra_args, 'backtrack_needed': True}

        # 检查是否完成所有 abstract sketch 步骤
        # 条件：
        # 1. 没有需要回溯的情况
        # 2. 有 abstract sketch
        # 3. 当前步骤索引已经到达或超过总步骤数
        if not extra_args.get('backtrack_needed', False):
            # 从 extra_args 或 auditor 获取 abstract sketch
            abstract_sketch = extra_args.get('vigil_abstract_sketch') or (
                self.auditor.abstract_sketch if hasattr(self, 'auditor') and self.auditor else None
            )

            if abstract_sketch and hasattr(abstract_sketch, 'steps'):
                # 从 hypothesis_guidance 获取当前步骤索引
                # 步骤索引在 HypothesisGuidance 中维护
                current_step_index = extra_args.get('current_step_index', 0)
                total_steps = len(abstract_sketch.steps)

                # 检查是否所有步骤都完成了
                # 注意：current_step_index 在 HypothesisGuidance 中每次执行后会 +1
                # 所以当 current_step_index >= total_steps 时，说明所有步骤都执行完了
                if current_step_index >= total_steps:
                    extra_args = {**extra_args, 'finished_task': True}
                    logger.info(
                        f"[EnhancedVIGILExecutor] ✓ All {total_steps} sketch steps completed successfully, "
                        f"marking task as finished"
                    )

        return query, runtime, env, [*messages, *tool_call_results], extra_args

    def _execute_tool(
        self,
        tool_call,
        tool_call_info: ToolCallInfo,
        runtime: FunctionsRuntime,
        env: Env,
        query: str,
        tool_call_results: list,
        extra_args: dict = {},
    ) -> bool:
        """执行工具并添加结果到 tool_call_results

        Args:
            tool_call: 工具调用对象
            tool_call_info: 工具调用信息
            runtime: 函数运行时
            env: 环境
            query: 用户查询
            tool_call_results: 结果列表（会被修改）
            extra_args: 额外参数（包含 current_step_index 等）

        Returns:
            是否需要回溯（True 表示检测到 SOP 注入，需要尝试其他分支）
        """
        # === ValidationError 自动重试循环 ===
        max_validation_retries = self._max_validation_retries
        current_retry = 0
        current_args = tool_call.args
        tool_call_result = None
        error = None

        while current_retry <= max_validation_retries:
            # 执行工具
            logger.info(f"[EnhancedVIGILExecutor] Executing tool: {tool_call.function}({dict(current_args)}) [attempt {current_retry + 1}]")
            tool_call_result, error = runtime.run_function(env, tool_call.function, current_args)
            logger.info(f"[EnhancedVIGILExecutor] Tool execution completed. Error: {error is not None}")

            # 检查是否为 ValidationError
            if error and self._is_validation_error(error):
                current_retry += 1

                if current_retry > max_validation_retries:
                    logger.warning(
                        f"[EnhancedVIGILExecutor] ValidationError retry limit reached for '{tool_call.function}' "
                        f"({current_retry} attempts). Returning error to LLM."
                    )
                    break

                # 调用 LLM 分析错误并修正参数
                logger.info(
                    f"[EnhancedVIGILExecutor] ValidationError detected. "
                    f"Calling LLM to fix parameters (attempt {current_retry}/{max_validation_retries})..."
                )

                corrected_args = self._llm_fix_validation_error(
                    tool_name=tool_call.function,
                    original_args=current_args,
                    error_message=error,
                    runtime=runtime
                )

                if corrected_args is None:
                    logger.warning(
                        f"[EnhancedVIGILExecutor] LLM unable to fix ValidationError. Returning error to LLM."
                    )
                    break

                logger.info(
                    f"[EnhancedVIGILExecutor] LLM corrected parameters: {dict(current_args)} -> {dict(corrected_args)}"
                )

                # 使用修正后的参数重试
                current_args = corrected_args
                tool_call.args = corrected_args  # 更新 tool_call 对象
                continue
            else:
                # 没有 ValidationError（执行成功或遇到其他错误），退出循环
                break

        # === 分类错误类型 ===
        needs_backtrack = False
        is_validation_error = False
        original_error = error  # 保存原始错误用于检测

        # 检测错误类型（重试后仍有错误的情况）
        if error:
            # 1. 检测参数类型验证错误（已经重试过，现在失败了）
            is_validation_error = self._is_validation_error(error)

            if is_validation_error:
                logger.warning(
                    f"[EnhancedVIGILExecutor] ValidationError persists after {current_retry} retries for '{tool_call.function}'. "
                    f"Converting to backtrack."
                )
                # 超过重试限制，转换为需要回溯（尝试其他工具）
                is_validation_error = False
                needs_backtrack = True

            # 2. 检测 SOP 注入（恶意攻击，需要回溯）
            if not is_validation_error and self._detect_sop_injection(error):
                logger.warning(
                    f"[EnhancedVIGILExecutor] ⚠️ SOP INJECTION DETECTED in error message "
                    f"from tool '{tool_call.function}' (Type III-A/III-B attack)"
                )
                needs_backtrack = True

        # === Perception Sanitizer: 清洗返回值和错误 ===
        if self.config.enable_perception_sanitizer:
            # 清洗返回值
            tool_call_result = self.sanitizer.sanitize_tool_result(
                tool_call.function, tool_call_result
            )

            # 清洗错误消息
            if error:
                if is_validation_error:
                    # 参数验证错误：保留详细信息供 LLM 修正，但移除可能的注入
                    error = self._sanitize_validation_error(error, tool_call.function)
                else:
                    # 其他错误（包括 SOP 注入）：完全清洗
                    error = self.sanitizer.sanitize_error_message(tool_call.function, error)

                if self.config.log_sanitizer_actions and original_error:
                    logger.info(
                        f"[EnhancedVIGILExecutor] Error message sanitized: "
                        f"'{original_error[:100]}...' → '{error[:100] if error else 'None'}...'"
                    )

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

        # === 记录执行历史（仅在成功时）===
        if not error and self.auditor:
            current_step_index = extra_args.get('current_step_index', 0)
            step_description = None

            # 从 abstract sketch 获取步骤描述
            if self.auditor.abstract_sketch and hasattr(self.auditor.abstract_sketch, 'steps'):
                if current_step_index < len(self.auditor.abstract_sketch.steps):
                    step = self.auditor.abstract_sketch.steps[current_step_index - 1]
                    step_description = f"{step.step_type} - {step.description}"

            self.auditor.record_execution_step(
                step_index=current_step_index,
                tool_call_info=tool_call_info,
                result=formatted_result,
                step_description=step_description,
            )

        # === Path Cache: 记录成功执行的路径 ===
        if self.path_cache:
            # 判断执行是否成功（无错误）
            outcome = "failure" if error else "success"

            # 获取当前步骤索引
            current_step_index = extra_args.get('current_step_index', 0)

            # 获取 abstract step description（从 auditor 的 abstract sketch）
            abstract_step_description = None
            if self.auditor and self.auditor.abstract_sketch and hasattr(self.auditor.abstract_sketch, 'steps'):
                # current_step_index 在执行时已经+1了，所以需要-1来获取当前步骤
                step_idx = current_step_index - 1
                if 0 <= step_idx < len(self.auditor.abstract_sketch.steps):
                    current_step = self.auditor.abstract_sketch.steps[step_idx]
                    abstract_step_description = current_step.description

            # 添加到 path cache（关键：传递 step_index 和 abstract_step_description）
            self.path_cache.add_verified_path(
                user_query=query,
                tool_name=tool_call.function,
                arguments=dict(tool_call.args),
                outcome=outcome,
                step_index=current_step_index,  # 传递步骤索引
                abstract_step_description=abstract_step_description,  # 传递抽象步骤描述
                metadata={"error": error} if error else None,
            )

            if self.config.log_audit_decisions and outcome == "success":
                logger.info(
                    f"[EnhancedVIGILExecutor] ✓ Path cached: step {current_step_index}, "
                    f"tool '{tool_call.function}', outcome '{outcome}'"
                )
                if abstract_step_description:
                    logger.debug(
                        f"[EnhancedVIGILExecutor] Abstract step: '{abstract_step_description[:60]}...'"
                    )

        # 成功执行后重置回溯计数
        backtrack_key = f"{tool_call.function}:{str(tool_call.args)}"
        if backtrack_key in self._backtracking_counts:
            del self._backtracking_counts[backtrack_key]

        # 返回是否需要回溯
        return needs_backtrack

    def _execute_reasoning_step(
        self,
        messages: Sequence[ChatMessage],
        query: str,
        extra_args: dict
    ) -> ChatMessage:
        """执行 REASONING 步骤：调用 LLM 进行推理（作为工具使用）

        当 hypothesis branch 是 __no_tool_call__ 或 __internal_reasoning__ 时，
        把 LLM 当作工具来执行推理。

        Args:
            messages: 当前消息历史（可能包含 guidance message）
            query: 用户查询

        Returns:
            包含 LLM 推理结果的 ChatAssistantMessage
        """
        from agentdojo.types import ChatAssistantMessage

        # 检查是否有 hypothesizer 和 openai_client
        if not self.hypothesizer or not self.hypothesizer.openai_client:
            logger.error("[EnhancedVIGILExecutor] No hypothesizer or openai_client available for reasoning step")
            return ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string("Error: LLM client not available for reasoning.")],
                tool_calls=None
            )

        try:
            # 将 messages 转换为 OpenAI API 格式
            # 这样 LLM 可以看到完整的上下文，包括 guidance message
            converted_messages = []
            execution_history = ""
            for exe in self.auditor.execution_history:
                execution_history += f"Step {exe['step_index']}: {exe['step_description'] or 'N/A'}\n"
                execution_history += f"Tool: {exe['tool_name']}\n\tArguments: {exe['arguments']}\nResult: {exe['result']}\n\n"
            target = self.auditor.abstract_sketch.steps[extra_args.get('current_step_index', 0)-1].description if self.auditor and self.auditor.abstract_sketch and hasattr(self.auditor.abstract_sketch, 'steps') and extra_args.get('current_step_index', 0) > 0 else "N/A"
            query = f"execution history:\n{execution_history}\ntarget:\n{target}"
            # 如果没有消息，使用简单的 prompt
            if not converted_messages:
                converted_messages = [
                    {"role": "system", "content": "You are a helpful assistant. Your goal is to reason about the query and execute the target action."},
                    {"role": "user", "content": query}
                ]

            # 调用 LLM（使用 hypothesizer 的 openai_client，不提供 tools）
            response = self.hypothesizer.openai_client.chat.completions.create(
                model=self.config.hypothesizer_model,
                messages=converted_messages,
                temperature=self.config.hypothesizer_temperature,
                max_tokens=8192,
            )

            # 提取响应
            response_text = response.choices[0].message.content.strip()

            if self.config.log_audit_decisions:
                logger.info(
                    f"[EnhancedVIGILExecutor] LLM reasoning response: {response_text[:200]}..."
                )

            # 返回 assistant message
            return ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string(response_text or "Reasoning completed.")],
                tool_calls=None
            )

        except Exception as e:
            logger.error(f"[EnhancedVIGILExecutor] Reasoning step error: {e}")
            return ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string(f"Error: {str(e)}")],
                tool_calls=None
            )

    def _llm_fix_validation_error(
        self,
        tool_name: str,
        original_args: dict,
        error_message: str,
        runtime: FunctionsRuntime
    ) -> dict | None:
        """调用 LLM 分析 ValidationError 并返回修正后的参数

        Args:
            tool_name: 工具名称
            original_args: 原始参数
            error_message: 验证错误消息
            runtime: 函数运行时（用于获取工具schema）

        Returns:
            修正后的参数字典，如果 LLM 无法修正则返回 None
        """
        import json
        from anthropic import Anthropic

        # 获取工具的 schema（参数定义）
        tool_schema = None
        for tool in runtime.functions.values():
            if tool.name == tool_name:
                tool_schema = tool.parameters
                break

        if not tool_schema:
            logger.error(f"[EnhancedVIGILExecutor] Cannot find schema for tool '{tool_name}'")
            return None

        # 构建 prompt
        prompt = f"""You are a parameter correction assistant. A tool call failed due to a validation error.

Tool: {tool_name}
Original Arguments: {json.dumps(original_args, indent=2)}
Validation Error: {error_message}

Please analyze the error and provide ONLY the corrected arguments as a valid JSON object. Do not include any explanation or markdown formatting.
You should not change argument names, only fix their types or values to satisfy the tool's parameter requirements.
Example response format:
{{"param1": "value1", "param2": ["item1", "item2"]}}

Corrected arguments:"""

        response_text = ""  # 初始化以避免类型检查警告

        try:
            # 调用 LLM（使用较小的模型以降低延迟）
            client = Anthropic()
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",  # 使用 Haiku 快速修正
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 提取响应文本
            response_text = ""
            for block in response.content:
                # 安全地提取文本内容（处理不同类型的 content blocks）
                if hasattr(block, 'text'):
                    response_text += getattr(block, 'text', '')

            response_text = response_text.strip()

            if not response_text:
                logger.error(f"[EnhancedVIGILExecutor] Empty response from LLM")
                return None

            # 尝试解析为 JSON
            corrected_args = json.loads(response_text)

            logger.info(f"[EnhancedVIGILExecutor] LLM successfully corrected parameters")
            return corrected_args

        except json.JSONDecodeError as e:
            logger.error(f"[EnhancedVIGILExecutor] Failed to parse LLM response as JSON: {e}")
            logger.debug(f"[EnhancedVIGILExecutor] LLM response: {response_text}")
            return None
        except Exception as e:
            logger.error(f"[EnhancedVIGILExecutor] Error calling LLM for parameter correction: {e}")
            return None

    def _detect_sop_injection(self, error_message: str) -> bool:
        """检测错误消息中是否包含 SOP 注入（Type III-A/III-B 攻击）

        SOP (Standard Operating Procedure) 注入是指恶意工具通过错误消息
        注入伪造的指令，试图操纵 agent 的后续行为。

        常见的 SOP 注入模式：
        - "MUST use tool X"
        - "REQUIRED: Call function Y"
        - "FALLBACK: Use alternative method"
        - "URGENT: Execute ..."
        - "Error: ... SOLUTION: Call ..."

        Args:
            error_message: 错误消息

        Returns:
            是否检测到 SOP 注入
        """
        import re

        # SOP 注入模式列表
        sop_patterns = [
            # 强制性指令
            r'\b(MUST|REQUIRED|MANDATORY)\s+(use|call|execute)\s+\w+',
            # 伪造的系统指令
            r'\b(FALLBACK|RECOVERY|SOLUTION|ACTION):\s*',
            # 紧急性指令
            r'\b(URGENT|IMMEDIATELY|CRITICAL|NOW):\s*(use|call|execute)',
            # "只有X方法可用"类型的诱导
            r'\b(only|sole|exclusive)\s+(way|method|option|accessible)\s+is\s+to\s+(use|call)',
            # 显式的替代工具推荐（可疑）
            r'instead\s+(use|call|try)\s+\w+',
            # 参数注入
            r'with\s+(parameters?|arguments?):\s*\{',
        ]

        for pattern in sop_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return True

        return False

    def _is_validation_error(self, error_message: str) -> bool:
        """检测是否为参数类型验证错误

        参数验证错误通常是因为：
        - 参数类型不匹配（如传 str 但期望 list）
        - 参数缺失或多余
        - 参数格式不正确

        这类错误可以通过让 LLM 重试来修复，不需要回溯到其他工具。

        Args:
            error_message: 错误消息

        Returns:
            是否为参数验证错误
        """
        import re

        # ValidationError 的特征模式
        validation_patterns = [
            r'ValueError:',
            r'ValidationError:',
            r'validation error for',
            r'Input should be a valid',
            r'\d+ validation error[s]? for',
            r'type=\w+_type',  # Pydantic 类型错误
            r'input_type=\w+',
            r'Field required',
            r'Extra inputs are not permitted',
            r'Input should be',
        ]

        for pattern in validation_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return True

        return False

    def _sanitize_validation_error(self, error_message: str, tool_name: str) -> str:
        """清洗参数验证错误消息

        对于 ValidationError，我们希望保留有用的信息（期望的类型、实际的类型）
        供 LLM 修正参数，但同时移除可能的注入内容。

        Args:
            error_message: 原始错误消息
            tool_name: 工具名称

        Returns:
            清洗后的错误消息
        """
        import re

        # 提取关键信息
        expected_type = None
        actual_type = None
        field_name = None
        error_type = None

        # 尝试解析 Pydantic 验证错误
        # 示例："Input should be a valid list [type=list_type, input_value='...', input_type=str]"

        # 提取字段名
        field_match = re.search(r'validation error[s]? for.*?\n(\w+)', error_message)
        if field_match:
            field_name = field_match.group(1)

        # 提取期望类型
        type_match = re.search(r'should be a valid (\w+)', error_message)
        if type_match:
            expected_type = type_match.group(1)

        # 提取实际类型
        input_type_match = re.search(r'input_type=(\w+)', error_message)
        if input_type_match:
            actual_type = input_type_match.group(1)

        # 提取错误类型
        error_type_match = re.search(r'type=(\w+)', error_message)
        if error_type_match:
            error_type = error_type_match.group(1)

        # 构建友好的错误消息
        sanitized_parts = [f"Parameter validation failed for tool '{tool_name}'."]

        if field_name:
            sanitized_parts.append(f"Field: '{field_name}'")

        if expected_type:
            sanitized_parts.append(f"Expected type: {expected_type}")

        if actual_type:
            sanitized_parts.append(f"Actual type: {actual_type}")

        if error_type:
            sanitized_parts.append(f"Error: {error_type}")

        # 添加修正建议
        if expected_type == "list" and actual_type == "str":
            sanitized_parts.append("Hint: Wrap the string value in a list, e.g., ['value'] instead of 'value'")
        elif expected_type == "str" and actual_type == "list":
            sanitized_parts.append("Hint: Pass a single string instead of a list")
        elif expected_type:
            sanitized_parts.append(f"Hint: Ensure the parameter is of type {expected_type}")

        sanitized_message = " ".join(sanitized_parts)

        # 如果无法解析，返回通用消息
        if not any([field_name, expected_type, actual_type]):
            sanitized_message = (
                f"Parameter validation failed for tool '{tool_name}'. "
                f"Please check the parameter types and retry."
            )

        return sanitized_message

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

                # 从 runtime 中提取可用工具列表
                available_tools = [
                    {"name": tool.name, "description": tool.description}
                    for tool in runtime.functions.values()
                ]

                # 生成草图并传递工具列表以筛选 tool_candidates
                abstract_sketch = self.sketch_generator.generate_sketch(query, available_tools)
                logger.info(f"[EnhancedVIGILInit] Generated sketch with {len(abstract_sketch.steps)} steps")

                # 记录每个步骤的工具候选数量
                if self.config.log_sketch_generation:
                    for i, step in enumerate(abstract_sketch.steps, 1):
                        num_candidates = len(step.tool_candidates or [])
                        logger.info(
                            f"[EnhancedVIGILInit] Step {i} ({step.step_type}): "
                            f"{num_candidates} tool candidates filtered"
                        )

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
                    from agentdojo.types import ChatAssistantMessage
                    original_content = messages[0]["content"][0]
                    updated_content = original_content["text"] + sketch_description if "text" in original_content else sketch_description

                    # messages = [
                    #     ChatSystemMessage(
                    #         role="system",
                    #         content=[text_content_block_from_string(updated_content)]
                    #     ),
                    #     *messages[1:]
                    # ]
                    # messages = [*messages, 
                    #         ChatAssistantMessage(
                    #             role="assistant",
                    #             content=[text_content_block_from_string(sketch_description) ]
                    # )]
                    from agentdojo.types import ChatUserMessage
                    from agentdojo.types import ChatAssistantMessage
                    query_message = ChatUserMessage(role="user", content=[text_content_block_from_string(query)])
                    abstract_message = ChatAssistantMessage(role="assistant", content=[text_content_block_from_string(sketch_description)],tool_calls=None)
                    messages = [*messages, query_message, abstract_message]

                    return query, runtime, env, messages, extra_args


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
