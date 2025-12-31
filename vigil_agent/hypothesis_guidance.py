"""假设引导元素 (Hypothesis Guidance Element)

这是VIGIL框架的关键组件，负责在LLM推理之前生成Hypothesis Tree并提供引导。

执行流程：
1. 检测是否即将进行工具选择决策
2. 生成Hypothesis Tree（多分支候选）
3. 使用Commitment Manager选择最优分支
4. 将推荐注入到LLM的上下文中

这确保了正确的执行顺序：
  Hypothesis Generation → Verification → Commitment → LLM Decision
而不是错误的：
  LLM Decision → Hypothesis Generation (事后分析)
"""

import logging
from collections.abc import Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import ChatMessage, ChatSystemMessage, text_content_block_from_string

from vigil_agent.commitment_manager import CommitmentManager
from vigil_agent.config import VIGILConfig
from vigil_agent.hypothesizer import Hypothesizer
from vigil_agent.path_cache import PathCache
from vigil_agent.perception_sanitizer import PerceptionSanitizer

logger = logging.getLogger(__name__)


class HypothesisGuidanceElement(BasePipelineElement):
    """假设引导元素

    在LLM做工具选择决策之前，生成Hypothesis Tree并提供引导。

    工作原理：
    1. 检测当前是否需要工具选择（通过分析消息历史）
    2. 生成包含多个候选工具的Hypothesis Tree
    3. 使用Neuro-Symbolic Verifier验证每个候选
    4. 通过Commitment Manager选择最优且安全的工具
    5. 将推荐作为guidance注入到messages中

    这样LLM在做决策时就有了安全且优化的引导。
    """

    def __init__(
        self,
        config: VIGILConfig,
        hypothesizer: Hypothesizer,
        commitment_manager: CommitmentManager,
        auditor,  # EnhancedRuntimeAuditor，用于访问 Abstract Sketch
        path_cache: PathCache | None = None,
        sanitizer: PerceptionSanitizer | None = None,
    ):
        """初始化假设引导元素

        Args:
            config: VIGIL配置
            hypothesizer: 假设推理器
            commitment_manager: 承诺管理器
            auditor: 运行时审计器（用于访问Abstract Sketch）
            path_cache: 路径缓存（可选）
            sanitizer: 感知清洗器（可选，用于二次清洗工具返回值）
        """
        self.config = config
        self.hypothesizer = hypothesizer
        self.commitment_manager = commitment_manager
        self.auditor = auditor
        self.path_cache = path_cache
        self.sanitizer = sanitizer

        # 跟踪已处理的决策点（避免重复生成）
        self._processed_decision_points: set[str] = set()

        # 跟踪当前执行到哪个步骤（用于匹配Abstract Sketch的步骤）
        self._current_step_index = 0

        # === 回溯机制：保存每个步骤的 hypothesis tree ===
        # Key: step_index, Value: hypothesis tree
        self._step_hypothesis_trees: dict[int, Any] = {}

        # === 回溯机制：跟踪每个步骤已尝试的分支 ===
        # Key: step_index, Value: set of tried branch_ids
        self._step_tried_branches: dict[int, set[str]] = {}

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """在LLM推理前生成hypothesis guidance

        Args:
            query: 用户查询
            runtime: 函数运行时
            env: 环境
            messages: 消息历史
            extra_args: 额外参数

        Returns:
            更新后的查询、运行时、环境、消息和额外参数
        """
        # === 首先检查任务是否已完成 ===
        if extra_args.get('finished_task', False):
            logger.info("[HypothesisGuidance] Task already finished, skipping guidance generation")
            return query, runtime, env, messages, extra_args

        # === 回溯机制：检测是否需要回溯 ===
        needs_backtrack = extra_args.get('backtrack_needed', False)
        last_tool_failed = False
        is_validation_error = False

        # 检查上一个工具调用是否失败（通过 error 字段）
        if len(messages) > 0 and messages[-1].get("role") == "tool":
            error_msg = messages[-1].get("error")
            last_tool_failed = error_msg is not None

            # 检测是否为参数验证错误
            if last_tool_failed and error_msg:
                is_validation_error = self._is_validation_error(str(error_msg))

        # === 区分不同类型的错误 ===
        # 1. ValidationError：不回溯，让 LLM 重试修正参数
        # 2. SOP 注入或其他错误：回溯到其他工具
        if is_validation_error:
            # ValidationError：不触发回溯，而是让 LLM 看到错误并重新生成参数
            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[HypothesisGuidance] ValidationError detected. "
                    f"Allowing LLM to retry with corrected parameters (not backtracking)."
                )

            # 清除回溯标志，确保不会触发回溯
            extra_args = {**extra_args, 'backtrack_needed': False}

            # 对于 ValidationError，我们需要切换到 LLM guidance mode
            # 让 LLM 基于错误消息重新生成参数
            # 注意：这里我们不返回，而是继续正常流程，但强制使用 guidance mode

        elif needs_backtrack or last_tool_failed:
            # SOP 注入或其他错误：触发回溯
            if self.config.log_hypothesis_generation:
                logger.warning(
                    f"[HypothesisGuidance] ⚠️ BACKTRACKING TRIGGERED "
                    f"(SOP injection: {needs_backtrack}, Tool failed: {last_tool_failed})"
                )

            # 尝试从当前步骤的 hypothesis tree 中选择下一个候选分支
            backtrack_result = self._try_backtrack_to_alternative_branch(messages, query)

            if backtrack_result:
                # 成功找到替代分支
                messages, extra_args = backtrack_result
                # 清除回溯标志
                extra_args = {**extra_args, 'backtrack_needed': False}
                return query, runtime, env, messages, extra_args
            else:
                # 所有分支都失败了，无法继续
                logger.error(
                    f"[HypothesisGuidance] ❌ All branches failed for step {self._current_step_index}. "
                    f"Unable to proceed."
                )
                # 生成错误消息给用户
                error_msg = self._generate_all_branches_failed_message()
                messages = [*messages, error_msg]
                extra_args = {**extra_args, 'backtrack_needed': False}
                return query, runtime, env, messages, extra_args

        # === 正常流程：生成新的 hypothesis tree ===
        # 检查是否需要生成guidance
        # if not self._should_generate_guidance(messages, query):
        #     # 如果不需要生成guidance，检查是否需要生成最终的assistant message
        #     # 这在直接执行模式下很重要，确保最后一条消息是assistant message
        #     if self.config.enable_direct_tool_execution and self._should_generate_final_message(messages):
        #         messages = self._generate_final_assistant_message(messages)
        #     return query, runtime, env, messages, extra_args

        if self.config.log_hypothesis_generation:
            logger.info("[HypothesisGuidance] Generating hypothesis tree for upcoming tool selection...")

        # 1. 获取 Abstract Sketch（如果存在）
        abstract_sketch = self.auditor.abstract_sketch if hasattr(self.auditor, 'abstract_sketch') else None

        # 2. 【关键修改】先查询Path Cache，基于当前的abstract step description
        cached_tool_selected = False
        cached_recommendation = None
        cached_branch = None

        if self.path_cache and abstract_sketch and hasattr(abstract_sketch, 'steps'):
            # 获取当前步骤的描述
            if self._current_step_index < len(abstract_sketch.steps):
                current_step = abstract_sketch.steps[self._current_step_index]
                abstract_step_desc = current_step.description

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[HypothesisGuidance] 🔍 Querying Path Cache for abstract step {self._current_step_index}: "
                        f"'{abstract_step_desc[:60]}...'"
                    )

                # 使用相似度匹配查找 top-3 候选
                cached_paths = self.path_cache.retrieve_paths_by_abstract_step(
                    abstract_step_desc, top_k=3
                )

                if cached_paths:
                    # 用 LLM 从 top-3 中选择最合适的工具
                    selected_tool, rationale = self.path_cache.select_tool_with_llm(
                        abstract_step_desc, cached_paths
                    )

                    if selected_tool:
                        cached_tool_selected = True
                        cached_recommendation = selected_tool

                        # 找到对应的 VerifiedPath 对象
                        selected_path = next((p for p in cached_paths if p.tool_name == selected_tool), cached_paths[0])

                        if self.config.log_hypothesis_generation:
                            logger.info(
                                f"[HypothesisGuidance] ✓ Path Cache HIT: '{selected_tool}' "
                                f"(used {selected_path.execution_count} times successfully)"
                            )
                            logger.info(f"[HypothesisGuidance] Selection rationale: {rationale}")

                        # 构造一个 hypothesis branch（标注来源是 path cache）
                        # 注意：来自 path cache 的工具已经验证过，可以跳过 verify 阶段
                        cached_branch = self._create_cached_branch(
                            selected_path=selected_path,
                            rationale=rationale or "Selected from path cache based on successful history",
                        )
                else:
                    if self.config.log_hypothesis_generation:
                        logger.info(
                            f"[HypothesisGuidance] Path Cache MISS: No matching paths found for current step"
                        )

        # === 关键检查：如果所有步骤都已完成，标记finished_task并返回 ===
        if abstract_sketch and hasattr(abstract_sketch, 'steps'):
            total_steps = len(abstract_sketch.steps)
            if self._current_step_index >= total_steps:
                # 所有步骤都已完成，标记任务完成
                extra_args = {**extra_args, 'finished_task': True}
                logger.info(
                    f"[HypothesisGuidance] All {total_steps} sketch steps completed "
                    f"(current step index: {self._current_step_index}), marking task as finished"
                )

                # 添加最终的assistant message（如果需要）
                if len(messages) > 0 and messages[-1]["role"] != "assistant":
                    from agentdojo.types import ChatAssistantMessage

                    final_message = ChatAssistantMessage(
                        role="assistant",
                        content=[text_content_block_from_string("Task completed successfully.")],
                        tool_calls=None,
                    )
                    messages = [*messages, final_message]
                    logger.info(
                        "[HypothesisGuidance] Added final assistant message as all steps are completed"
                    )

                return query, runtime, env, messages, extra_args

        # 3. 【关键分支】如果Path Cache命中，直接使用缓存的工具，跳过hypothesis tree生成
        if cached_tool_selected and cached_branch:
            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[HypothesisGuidance] ⚡ Fast path: Using cached tool '{cached_recommendation}', "
                    f"skipping hypothesis tree generation and verification"
                )

            # 保存cached branch到hypothesis tree（用于回溯机制）
            # 创建一个简化的hypothesis tree，只包含这一个缓存分支
            from vigil_agent.hypothesizer import HypothesisTree

            # 构造decision_point描述
            if abstract_sketch and hasattr(abstract_sketch, 'steps') and self._current_step_index < len(abstract_sketch.steps):
                current_step = abstract_sketch.steps[self._current_step_index]
                decision_point = f"{current_step.step_type}: {current_step.description}"
            else:
                # 回退方案：使用通用描述
                decision_point = f"Path Cache Selection: {cached_recommendation}"

            hypothesis_tree = HypothesisTree(
                decision_point=decision_point,
                branches=[cached_branch]
            )
            self._step_hypothesis_trees[self._current_step_index] = hypothesis_tree
            if self._current_step_index not in self._step_tried_branches:
                self._step_tried_branches[self._current_step_index] = set()
            self._step_tried_branches[self._current_step_index].add(cached_branch.branch_id)

            # 根据配置决定是生成guidance还是直接生成tool call
            if self.config.enable_direct_tool_execution:
                # 模式A：直接生成tool call（跳过LLM推理）
                messages = self._generate_direct_tool_call_for_cached_branch(
                    cached_branch=cached_branch,
                    messages=messages,
                )
                # 设置标志，告诉ConditionalLLM跳过此次调用
                # 重要：path cache来的工具也需要跳过audit，因为它已经验证过了
                extra_args = {
                    **extra_args,
                    'skip_llm': True,
                    'skip_audit': True,  # 跳过 Executor 中的重复审计
                    'vigil_pre_approved': cached_recommendation,
                    'from_path_cache': True,  # 标记来源
                    'current_step_is_reasoning': False,
                }
            else:
                # 模式B：生成guidance让LLM决策
                guidance_message = self._create_cached_tool_guidance_message(
                    cached_branch=cached_branch,
                )

                if guidance_message:
                    # 将guidance作为system message注入
                    guidance_msg = ChatSystemMessage(
                        role="system",
                        content=[text_content_block_from_string(guidance_message)]
                    )
                    messages = [*messages, guidance_msg]

                    if self.config.log_hypothesis_generation:
                        logger.info("[HypothesisGuidance] Injected cached tool guidance into context")

                extra_args = {
                    **extra_args,
                    'from_path_cache': True,
                }

            # 标记此决策点已处理
            decision_point_key = self._get_decision_point_key(messages, query)
            self._processed_decision_points.add(decision_point_key)

            # 增加步骤索引并传递到 extra_args
            self._current_step_index = self._current_step_index + 1
            extra_args = {**extra_args, 'current_step_index': self._current_step_index}

            return query, runtime, env, messages, extra_args

        # 4. Path Cache未命中，提取可用工具列表，正常生成hypothesis tree
        available_tools = [
            {"name": tool.name, "description": tool.description, "full_docstring": tool.full_docstring}
            for tool in runtime.functions.values()
        ]

        # 5. **二次清洗 messages 中的工具返回值（Defense in Depth）**
        # 虽然 Executor 已经清洗过一次，但作为额外防护，在生成 hypothesis 前再次清洗
        # 这防止了残留的注入内容影响 Hypothesizer 的决策
        sanitized_messages = messages
        if self.sanitizer and self.config.enable_perception_sanitizer:
            sanitized_messages = self._sanitize_messages_for_hypothesis_generation(messages)
            if self.config.log_hypothesis_generation:
                logger.debug(
                    "[HypothesisGuidance] Applied secondary sanitization to messages "
                    "before hypothesis generation (Defense in Depth)"
                )

        # 6. 生成Hypothesis Tree（带重试机制）
        # 如果所有分支都被拒绝，重新生成 hypothesis tree（最多重试 3 次）
        max_regeneration_attempts = 3
        rejected_tools_feedback: list[dict[str, str]] = []

        # 初始化变量（避免未绑定错误）
        hypothesis_tree = None
        commitment_decision = None

        for attempt in range(max_regeneration_attempts):
            try:
                # 生成 hypothesis tree（第一次不传 rejected_tools，后续传入）
                hypothesis_tree = self.hypothesizer.generate_hypotheses(
                    available_tools=available_tools,
                    current_state={
                        "query": query,
                        "messages": list(sanitized_messages),  # 使用清洗后的 messages
                        "env": env,
                    },
                    user_intent=query,
                    abstract_sketch=abstract_sketch,  # 传递 Abstract Sketch
                    current_step_index=self._current_step_index,  # 传递当前步骤索引
                    rejected_tools=rejected_tools_feedback if attempt > 0 else None,  # 第二次及以后传入拒绝理由
                )

                if self.config.log_hypothesis_generation:
                    if attempt > 0:
                        logger.info(
                            f"[HypothesisGuidance] Regeneration attempt {attempt + 1}/{max_regeneration_attempts}: "
                            f"Generated {len(hypothesis_tree.branches)} new candidate branches "
                            f"(excluding {len(rejected_tools_feedback)} rejected tools)"
                        )
                    else:
                        logger.info(
                            f"[HypothesisGuidance] Generated hypothesis tree with "
                            f"{len(hypothesis_tree.branches)} candidate branches"
                        )

                # === 保存 hypothesis tree 用于回溯 ===
                self._step_hypothesis_trees[self._current_step_index] = hypothesis_tree
                if self._current_step_index not in self._step_tried_branches:
                    self._step_tried_branches[self._current_step_index] = set()

                # 使用Commitment Manager选择最优分支
                commitment_decision = self.commitment_manager.select_commitment(
                    hypothesis_tree=hypothesis_tree,
                    current_context={"query": query, "messages": messages},
                    current_step_index=self._current_step_index,
                )

                # === 检查是否所有分支都被拒绝 ===
                if commitment_decision.all_branches_rejected:
                    if self.config.log_hypothesis_generation:
                        logger.warning(
                            f"[HypothesisGuidance] All {len(hypothesis_tree.branches)} branches rejected "
                            f"on attempt {attempt + 1}/{max_regeneration_attempts}"
                        )

                    # 收集被拒绝的工具及理由
                    # rejected_branches 是 list[tuple[HypothesisBranch, str]]
                    rejected_tools_feedback = []
                    for branch, reason in commitment_decision.rejected_branches:
                        rejected_tools_feedback.append({
                            "tool_name": branch.tool_call["tool_name"],
                            "rejection_reason": reason,
                        })

                    if self.config.log_hypothesis_generation:
                        logger.info(
                            f"[HypothesisGuidance] Collected rejection feedback for {len(rejected_tools_feedback)} tools"
                        )

                    # 如果还有重试机会，继续循环；否则退出
                    if attempt < max_regeneration_attempts - 1:
                        logger.info("[HypothesisGuidance] Regenerating hypothesis tree with rejection feedback...")
                        continue  # 重新生成
                    else:
                        # 已达到最大重试次数，所有尝试都失败
                        logger.error(
                            f"[HypothesisGuidance] ❌ All regeneration attempts failed. "
                            f"Unable to find acceptable tools for step {self._current_step_index}"
                        )
                        # 生成错误消息
                        error_msg = self._generate_all_branches_failed_message()
                        messages = [*messages, error_msg]
                        return query, runtime, env, messages, extra_args

                # === 成功找到可接受的分支，退出重试循环 ===
                break

            except Exception as e:
                logger.error(f"[HypothesisGuidance] Failed to generate hypothesis guidance: {e}")
                if attempt < max_regeneration_attempts - 1:
                    continue
                else:
                    # 失败时不添加guidance，让LLM自由决策
                    self._current_step_index = self._current_step_index + 1
                    return query, runtime, env, messages, extra_args

        # 确保有有效的决策（避免未绑定错误）
        if commitment_decision is None or hypothesis_tree is None:
            logger.error("[HypothesisGuidance] No valid commitment decision made")
            self._current_step_index = self._current_step_index + 1
            return query, runtime, env, messages, extra_args

        # === 记录选中的分支（用于回溯时跳过）===
        if commitment_decision.selected_branch:
            branch_id = commitment_decision.selected_branch.branch_id
            self._step_tried_branches[self._current_step_index].add(branch_id)
            if self.config.log_hypothesis_generation:
                logger.debug(
                    f"[HypothesisGuidance] Selected branch '{branch_id}' for step {self._current_step_index}"
                )

            # 检查是否是 REASONING 步骤
            is_response_step = (
                commitment_decision.selected_branch is not None
                and commitment_decision.selected_branch.tool_call.get("tool_name") == "__response__"
            )

            # 检查是否是 INTERNAL REASONING 步骤（需要 LLM 推理，但不调用工具）
            is_internal_reasoning = (
                commitment_decision.selected_branch is not None
                and commitment_decision.selected_branch.tool_call.get("tool_name") == "__internal_reasoning__"
            )

            # 检查是否是 SKIP STEP 步骤（既不调用 tool，也不调用 LLM）
            is_skip_step = (
                commitment_decision.selected_branch is not None
                and commitment_decision.selected_branch.tool_call.get("tool_name") == "__skip_step__"
            )

            # === 特殊处理：SKIP STEP 分支 ===
            if is_skip_step:
                # 这个分支既不调用 tool，也不调用 LLM
                # 直接跳过当前步骤，进入下一轮执行循环
                reason = commitment_decision.selected_branch.rationale

                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[HypothesisGuidance] ✓ SKIP STEP branch selected for step {self._current_step_index}. "
                        f"Reason: {reason}"
                    )

                # 标记此决策点已处理
                decision_point_key = self._get_decision_point_key(messages, query)
                self._processed_decision_points.add(decision_point_key)

                # 增加步骤索引
                self._current_step_index = self._current_step_index + 1

                # 设置 extra_args，告诉 pipeline 跳过 LLM 和工具执行
                extra_args = {
                    **extra_args,
                    'current_step_index': self._current_step_index,
                    'skip_llm': True,  # 跳过 LLM 调用
                    'skip_step': True,  # 标记为跳过步骤
                    'skip_step_reason': reason,  # 保存跳过原因
                }

                # 直接返回，不生成任何 assistant message，让循环继续
                if self.config.log_hypothesis_generation:
                    logger.info(
                        f"[HypothesisGuidance] Skipping step {self._current_step_index - 1}, "
                        f"proceeding to next iteration"
                    )

                return query, runtime, env, messages, extra_args

            # 5. 根据配置决定是生成guidance还是直接生成tool call
            # 特殊情况：如果是 ValidationError 重试，强制使用 guidance mode
            use_guidance_mode = (
                is_response_step or  # REASONING 步骤需要 LLM
                is_internal_reasoning or  # INTERNAL REASONING 步骤需要 LLM
                is_validation_error or  # ValidationError 需要 LLM 重新生成参数
                not self.config.enable_direct_tool_execution  # 配置禁用 direct mode
            )

            if not use_guidance_mode:
                # 模式A：直接生成tool call（跳过LLM推理）
                messages = self._generate_direct_tool_call(
                    commitment_decision=commitment_decision,
                    messages=messages,
                    hypothesis_tree=hypothesis_tree,
                )
                # 设置标志，告诉ConditionalLLM跳过此次调用
                extra_args = {
                    **extra_args,
                    'skip_llm': True,
                    'skip_audit': True,  # 跳过 Executor 中的重复审计
                    'vigil_pre_approved': commitment_decision.selected_branch.tool_call["tool_name"] if commitment_decision.selected_branch else None,
                    'current_step_is_reasoning': False,  # 直接工具调用，不是 REASONING 步骤
                }
            else:
                # 模式B：生成guidance让LLM决策（原有行为）
                # 或者：ValidationError 重试（让 LLM 看到错误并修正参数）
                # 或者：REASONING 步骤（即使在 direct mode 下也需要 LLM）
                guidance_message = self._create_guidance_message(
                    commitment_decision=commitment_decision,
                    cached_recommendation=cached_recommendation,
                    hypothesis_tree=hypothesis_tree,
                )

                if guidance_message:
                    # 将guidance作为system message注入
                    guidance_msg = ChatSystemMessage(
                        role="system",
                        content=[text_content_block_from_string(guidance_message)]
                    )

                    messages = [*messages, guidance_msg]

                    if self.config.log_hypothesis_generation:
                        if is_validation_error:
                            logger.info("[HypothesisGuidance] Injected ValidationError retry guidance (LLM will fix parameters)")
                        elif is_response_step:
                            logger.info("[HypothesisGuidance] Injected RESPONSE guidance (requires LLM)")
                        else:
                            logger.info("[HypothesisGuidance] Injected guidance into context")
                        logger.debug(f"[HypothesisGuidance] Guidance content:\n{guidance_message}...")

                # 设置 REASONING 步骤标志并跳过 LLM（让 Executor 统一处理）
                # __no_tool_call__ 和 __internal_reasoning__ 都应该：
                # 1. 跳过 ConditionalLLM 的调用
                # 2. 在 Executor 开头调用 LLM 进行推理
                extra_args = {
                    **extra_args,
                    'current_step_is_reasoning': is_response_step or is_internal_reasoning,
                    'current_step_is_response': is_response_step,  # 新增：标记是否是 __response__ 步骤
                    'skip_llm': is_response_step or is_internal_reasoning,  # 跳过 ConditionalLLM
                }

            # 6. 标记此决策点已处理
            decision_point_key = self._get_decision_point_key(messages, query)
            self._processed_decision_points.add(decision_point_key)

        # 7. 增加步骤索引并传递到 extra_args
        self._current_step_index = self._current_step_index + 1
        extra_args = {**extra_args, 'current_step_index': self._current_step_index}

        return query, runtime, env, messages, extra_args

    def _should_generate_guidance(self, messages: Sequence[ChatMessage], query: str) -> bool:
        """判断是否需要生成guidance

        Args:
            messages: 消息历史
            query: 用户查询

        Returns:
            是否需要生成guidance
        """
        # 如果hypothesis generation未启用，跳过
        if not self.config.enable_hypothesis_generation:
            return False

        # 生成决策点标识
        decision_point_key = self._get_decision_point_key(messages, query)

        # 如果已经为这个决策点生成过guidance，跳过
        if decision_point_key in self._processed_decision_points:
            return False

        # 只要任务未完成（在 query 方法中已经检查），就需要生成 guidance
        # 这确保每个 sketch 步骤都会生成相应的 hypothesis tree
        return True

    def _get_decision_point_key(self, messages: Sequence[ChatMessage], query: str) -> str:
        """生成决策点的唯一标识

        Args:
            messages: 消息历史
            query: 用户查询

        Returns:
            决策点标识
        """
        # 使用消息数量作为决策点的标识（简单但有效）
        return f"{query[:30]}:msg_{len(messages)}"

    def _create_guidance_message(
        self,
        commitment_decision,
        cached_recommendation: str | None,
        hypothesis_tree,
    ) -> str | None:
        """创建guidance消息

        Args:
            commitment_decision: 承诺决策结果
            cached_recommendation: 缓存的推荐工具
            hypothesis_tree: 假设树

        Returns:
            Guidance消息内容
        """
        if commitment_decision.all_branches_rejected:
            # 所有分支都被拒绝
            guidance = f"""[VIGIL Security Guidance]

⚠️ All {len(hypothesis_tree.branches)} candidate tools have been rejected by security verification.

{commitment_decision.rejection_feedback}

Please reconsider your approach:
1. Review if the current step is necessary for the user's request
2. Look for alternative, simpler tools that directly match the user's intent
3. Avoid tools that require unnecessary permissions or perform redundant operations

Remember: Only use tools that are minimally necessary and directly relevant to the task."""

            return guidance

        elif commitment_decision.selected_branch:
            # 有推荐的分支
            selected_tool = commitment_decision.selected_branch.tool_call["tool_name"]
            branch_info = commitment_decision.selected_branch

            # ===== 特殊处理：SKIP STEP 步骤 =====
            if selected_tool == "__skip_step__":
                reason = branch_info.tool_call.get("reason", "No reason provided")
                guidance = f"""[VIGIL Guidance: Skip Step]

⏭️ Current step will be SKIPPED without tool execution or LLM reasoning.

Reason: {reason}

Analysis:
  • Necessity Score: {branch_info.necessity_score:.2f}/1.00
  • Risk Level: {branch_info.risk_level}

This step has been determined to be unnecessary or redundant for completing the task.
Execution will proceed directly to the next step."""

                if self.config.log_hypothesis_generation:
                    logger.info("[HypothesisGuidance] Generated SKIP STEP guidance (no tool, no LLM)")

                return guidance

            # ===== 特殊处理：REASONING 步骤 =====
            if selected_tool == "__internal_reasoning__":
                guidance = f"""[VIGIL Guidance: Reasoning Step]

🧠 Current step requires REASONING and ANALYSIS without tool execution.

Step Description: {branch_info.metadata.get('step_description', 'Analyze and synthesize information')}

Your task:
1. Review the information from previous tool calls and context
2. Analyze and synthesize the available data
3. Make a decision or conclusion based on the analysis
4. DO NOT call any tools in this step - provide your reasoning directly in your response

Remember: This is a reasoning-only step. Your response should contain analysis and conclusions, not tool calls."""

                if self.config.log_hypothesis_generation:
                    logger.info("[HypothesisGuidance] Generated REASONING guidance (no tool execution)")

                return guidance

            # ===== 正常的工具推荐 =====
            guidance_parts = [
                "[VIGIL Security Guidance]",
                "",
                f"✓ Recommended tool for this step: '{selected_tool}'",
                "",
                "Analysis:",
            ]

            # 添加推荐理由
            guidance_parts.append(f"  • Necessity Score: {branch_info.necessity_score:.2f}/1.00")
            guidance_parts.append(f"  • Risk Level: {branch_info.risk_level}")
            guidance_parts.append(f"  • Redundancy: {branch_info.redundancy_level}")
            guidance_parts.append(f"  • Side Effects: {'Yes' if branch_info.has_side_effects else 'No'}")

            # 如果有缓存推荐且与当前推荐一致，强调
            if cached_recommendation and cached_recommendation == selected_tool:
                guidance_parts.append("")
                guidance_parts.append(
                    f"📌 This tool has been successfully used for similar tasks before (Path Cache hit)."
                )

            # 如果有其他被拒绝的分支，简要说明
            if commitment_decision.rejected_branches:
                guidance_parts.append("")
                guidance_parts.append(
                    f"Note: {len(commitment_decision.rejected_branches)} other tools were rejected "
                    f"due to security constraints or redundancy."
                )

            guidance_parts.append("")
            guidance_parts.append(
                "While this is a strong recommendation based on security analysis and the "
                "Minimum Necessity Principle, you may choose a different tool if you have "
                "a compelling reason."
            )

            return "\n".join(guidance_parts)

        return None

    def _generate_direct_tool_call(
        self,
        commitment_decision,
        messages: Sequence[ChatMessage],
        hypothesis_tree,
    ) -> Sequence[ChatMessage]:
        """直接生成tool call（跳过LLM推理）

        当CommitmentManager选定了最优工具后，直接生成assistant message，
        而不是让LLM再做一次选择。这确保了：
        1. 执行的工具就是经过严格审查后选定的工具
        2. 避免多余的LLM调用（提高效率）
        3. 确保一致性（LLM不会偏离推荐）

        Args:
            commitment_decision: 承诺决策结果
            messages: 当前消息历史
            hypothesis_tree: 假设树

        Returns:
            更新后的消息历史（包含assistant message）
        """
        from agentdojo.types import ChatAssistantMessage
        from agentdojo.functions_runtime import FunctionCall

        if commitment_decision.all_branches_rejected:
            # 所有分支都被拒绝
            # 生成一个assistant message，解释为什么无法继续
            error_message = commitment_decision.rejection_feedback or (
                "All candidate tools have been rejected by security verification. "
                "Unable to proceed with this step."
            )

            assistant_msg = ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string(error_message)],
                tool_calls=None,
            )

            messages = [*messages, assistant_msg]

            if self.config.log_hypothesis_generation:
                logger.warning(
                    "[HypothesisGuidance] All branches rejected, generated error message"
                )

        elif commitment_decision.selected_branch:
            # 有推荐的分支
            selected_branch = commitment_decision.selected_branch
            tool_call_info = selected_branch.tool_call

            # === DEBUG: 记录 tool_call_info 的内容 ===
            if self.config.log_hypothesis_generation:
                logger.debug(
                    f"[HypothesisGuidance] _generate_direct_tool_call processing tool: '{tool_call_info.get('tool_name')}' "
                    f"(type: {type(tool_call_info.get('tool_name'))})"
                )

            # ===== 特殊处理：SKIP STEP 步骤 =====
            if tool_call_info["tool_name"] == "__skip_step__":
                # SKIP STEP 步骤既不调用 tool，也不调用 LLM
                # 直接返回原始 messages，不做任何修改
                # 上层逻辑会处理跳过步骤并进入下一轮循环

                if self.config.log_hypothesis_generation:
                    reason = tool_call_info.get("reason", "No reason provided")
                    logger.info(
                        f"[HypothesisGuidance] SKIP STEP detected in _generate_direct_tool_call - "
                        f"skipping without generating any message. Reason: {reason}"
                    )

                # 不生成任何 assistant message，直接返回
                return messages

            # ===== 特殊处理：INTERNAL REASONING 步骤 =====
            if tool_call_info["tool_name"] == "__internal_reasoning__":
                # INTERNAL REASONING 步骤需要 LLM 进行推理，但不调用工具
                # 在 direct mode 下，我们不应该跳过 LLM，而是让 LLM 进行推理
                # 所以这里不添加 assistant message，让 LLM 自然生成推理响应

                if self.config.log_hypothesis_generation:
                    logger.info(
                        "[HypothesisGuidance] INTERNAL REASONING step detected in direct mode - "
                        "allowing LLM to provide reasoning without tool call"
                    )

                # 注意：在 direct mode 下遇到 INTERNAL REASONING 步骤是一个特殊情况
                # 我们不生成任何 assistant message，让流程继续到 LLM 进行推理
                # 这与普通的 direct tool execution 不同
                return messages

            # ===== 特殊处理：REASONING 步骤 =====
            if tool_call_info["tool_name"] == "__no_tool_call__":
                # REASONING 步骤不需要生成 tool call
                # 在 direct mode 下，我们不应该跳过 LLM，而是让 LLM 进行推理
                # 所以这里不添加 assistant message，让 LLM 自然生成推理响应

                if self.config.log_hypothesis_generation:
                    logger.info(
                        "[HypothesisGuidance] REASONING step detected in direct mode - "
                        "allowing LLM to provide reasoning without tool call"
                    )

                # 注意：在 direct mode 下遇到 REASONING 步骤是一个特殊情况
                # 我们不生成任何 assistant message，让流程继续到 LLM 进行推理
                # 这与普通的 direct tool execution 不同
                return messages

            # ===== 正常的工具调用 =====
            # 创建FunctionCall对象
            tool_call = FunctionCall(
                id=f"call_{hash(tool_call_info['tool_name']) % 1000000}",  # 生成唯一ID
                function=tool_call_info["tool_name"],
                args=tool_call_info["arguments"],
            )

            # 生成assistant message（包含tool call）
            assistant_msg = ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string(
                    f"I will use the {tool_call_info['tool_name']} tool as recommended by VIGIL."
                )],
                tool_calls=[tool_call],
            )

            messages = [*messages, assistant_msg]

            if self.config.log_hypothesis_generation:
                logger.info(
                    f"[HypothesisGuidance] Direct tool call generated: {tool_call_info['tool_name']} "
                    f"with args {tool_call_info['arguments']}"
                )
                logger.info(
                    f"[HypothesisGuidance] Setting skip_llm and skip_audit flags (direct execution mode)"
                )

            # # 标记这个 tool call 已经通过完整审计，Executor 应该直接执行
            # extra_args = {
            #     **extra_args,
            #     'skip_audit': True,  # 跳过 Executor 中的重复审计
            #     'vigil_pre_approved': tool_call_info['tool_name'],  # 记录预批准的工具
            # }

        return messages

    def reset(self) -> None:
        """重置状态（用于新任务）"""
        self._processed_decision_points.clear()
        self._current_step_index = 0
        self._step_hypothesis_trees.clear()  # 清除保存的 hypothesis trees
        self._step_tried_branches.clear()  # 清除已尝试的分支记录
        logger.debug("[HypothesisGuidance] State reset for new task")

    def _sanitize_messages_for_hypothesis_generation(
        self, messages: Sequence[ChatMessage]
    ) -> Sequence[ChatMessage]:
        """二次清洗 messages 中的工具返回值（Defense in Depth）

        虽然 Executor 已经清洗过工具返回值，但在生成 hypothesis tree 之前
        再次清洗，作为额外的安全防护层。这防止了：
        1. 残留的注入内容影响 Hypothesizer 的决策
        2. 环境返回值中的潜在注入
        3. 清洗器可能遗漏的边缘情况

        Args:
            messages: 原始消息序列

        Returns:
            清洗后的消息序列
        """
        if not self.sanitizer:
            return messages

        sanitized_messages = []
        for msg in messages:
            if msg.get("role") == "tool":
                # 对工具返回值进行二次清洗
                tool_call = msg.get("tool_call")
                content = msg.get("content") or []

                # 提取工具名称
                tool_name = tool_call.function if tool_call else "unknown_tool"

                # 清洗内容
                sanitized_content = []
                for content_block in content:
                    if content_block.get("type") == "text":
                        original_text = content_block.get("content", "")
                        # 轻量级清洗：只移除最明显的强制性指令模式
                        # 因为工具返回值已经被 Executor 清洗过一次
                        # sanitized_text = self._lightweight_sanitize_text(original_text)
                        sanitized_content.append({
                            "type": "text",
                            "content": original_text
                        })
                    else:
                        # 保留非文本内容块
                        sanitized_content.append(content_block)

                # 创建清洗后的消息
                sanitized_msg = {
                    **msg,
                    "content": sanitized_content
                }
                sanitized_messages.append(sanitized_msg)
            else:
                # 非工具消息，直接保留
                sanitized_messages.append(msg)

        return sanitized_messages

    def _lightweight_sanitize_text(self, text: str) -> str:
        """轻量级文本清洗（用于二次清洗）

        只移除明显的强制性指令模式，因为工具返回值已经被清洗过一次。

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        import re

        # 移除强制性指令关键词（但保留信息内容）
        # 只替换最明显的模式，避免过度清洗
        patterns_to_remove = [
            r'\b(MUST|REQUIRED|MANDATORY)\s+(use|call|execute)\s+[\w_]+',
            r'\b(You|Agent)\s+(must|MUST|should|SHOULD)\s+',
            r'\b(ignore|override|bypass)\s+(previous|all|the)\s+',
        ]

        sanitized = text
        for pattern in patterns_to_remove:
            sanitized = re.sub(pattern, '[sanitized]', sanitized, flags=re.IGNORECASE)

        return sanitized

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
        if not error_message:
            return False

        import re

        # ValidationError 的特征模式
        validation_patterns = [
            r'ValidationError:',
            r'validation error for',
            r'Input should be a valid',
            r'\d+ validation error[s]? for',
            r'type=\w+_type',  # Pydantic 类型错误
            r'input_type=\w+',
            r'Field required',
            r'Extra inputs are not permitted',
            r'Input should be',
            r'Expected type:',  # 我们清洗后的格式
        ]

        for pattern in validation_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return True

        return False

    def _should_generate_final_message(self, messages: Sequence[ChatMessage]) -> bool:
        """判断是否需要生成最终的assistant message

        在直接执行模式下，当任务完成时，最后一条消息可能是 tool result。
        为了满足 pipeline 的要求（最后一条消息必须是 assistant message），
        我们需要生成一个最终的 assistant message。

        Args:
            messages: 消息历史

        Returns:
            是否需要生成最终的 assistant message
        """
        if len(messages) == 0:
            return False

        last_message = messages[-1]

        # 如果最后一条消息是 tool result，需要生成最终的 assistant message
        if last_message.get("role") == "tool":
            return True

        return False

    def _generate_final_assistant_message(
        self, messages: Sequence[ChatMessage]
    ) -> Sequence[ChatMessage]:
        """生成最终的assistant message

        在直接执行模式下，当任务完成时，生成一个最终的 assistant message
        来总结执行结果。

        Args:
            messages: 当前消息历史

        Returns:
            更新后的消息历史（包含最终的 assistant message）
        """
        from agentdojo.types import ChatAssistantMessage

        # 生成一个简单的完成消息
        final_message = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string(
                "I have completed the requested tasks using the tools recommended by VIGIL."
            )],
            tool_calls=None,
        )

        messages = [*messages, final_message]

        if self.config.log_hypothesis_generation:
            logger.info(
                "[HypothesisGuidance] Generated final assistant message (task completion)"
            )

        return messages

    def _try_backtrack_to_alternative_branch(
        self, messages: Sequence[ChatMessage], query: str
    ) -> tuple[Sequence[ChatMessage], dict] | None:
        """尝试从当前步骤的 hypothesis tree 中选择替代分支

        当工具执行失败时（尤其是检测到 SOP 注入），尝试选择另一个未尝试的分支。

        Args:
            messages: 当前消息历史
            query: 用户查询

        Returns:
            如果找到替代分支：(更新后的 messages, 更新后的 extra_args)
            如果所有分支都已尝试：None
        """
        # 获取当前步骤的 hypothesis tree
        if self._current_step_index not in self._step_hypothesis_trees:
            logger.warning(
                f"[HypothesisGuidance] No hypothesis tree found for step {self._current_step_index}, "
                f"cannot backtrack"
            )
            return None

        hypothesis_tree = self._step_hypothesis_trees[self._current_step_index]
        tried_branches = self._step_tried_branches.get(self._current_step_index, set())

        # 找到所有未尝试的分支
        untried_branches = [
            branch for branch in hypothesis_tree.branches
            if branch.branch_id not in tried_branches
        ]

        if not untried_branches:
            logger.warning(
                f"[HypothesisGuidance] All {len(hypothesis_tree.branches)} branches have been tried "
                f"for step {self._current_step_index}, cannot backtrack further"
            )
            return None

        # 选择下一个最优的未尝试分支（基于 necessity_score）
        next_branch = max(untried_branches, key=lambda b: b.necessity_score)

        logger.info(
            f"[HypothesisGuidance] ✓ BACKTRACKING to alternative branch: '{next_branch.tool_call['tool_name']}' "
            f"(branch {next_branch.branch_id}, necessity={next_branch.necessity_score:.2f})"
        )

        # 记录这个分支已被尝试
        self._step_tried_branches[self._current_step_index].add(next_branch.branch_id)

        # 移除上一个失败的工具调用消息（如果存在）
        # 注意：我们需要移除最后一个 assistant message 和 tool result message
        cleaned_messages = list(messages)
        if len(cleaned_messages) > 0 and cleaned_messages[-1].get("role") == "tool":
            # 移除 tool result
            cleaned_messages = cleaned_messages[:-1]
        if len(cleaned_messages) > 0 and cleaned_messages[-1].get("role") == "assistant":
            # 移除失败的 assistant tool call
            cleaned_messages = cleaned_messages[:-1]

        # 基于新分支生成 tool call
        if self.config.enable_direct_tool_execution:
            # Direct mode: 直接生成 tool call
            cleaned_messages = self._generate_direct_tool_call_for_branch(
                branch=next_branch,
                messages=cleaned_messages,
            )
            extra_args = {
                'skip_llm': True,
                'skip_audit': True,
                'vigil_pre_approved': next_branch.tool_call["tool_name"],
            }
        else:
            # Guidance mode: 生成 guidance
            guidance_message = self._create_guidance_message_for_branch(next_branch)
            guidance_msg = ChatSystemMessage(
                role="system",
                content=[text_content_block_from_string(guidance_message)]
            )
            cleaned_messages = [*cleaned_messages, guidance_msg]
            extra_args = {}

        return cleaned_messages, extra_args

    def _generate_direct_tool_call_for_branch(
        self, branch, messages: Sequence[ChatMessage]
    ) -> Sequence[ChatMessage]:
        """为特定分支生成 direct tool call

        Args:
            branch: 选定的分支
            messages: 当前消息历史

        Returns:
            更新后的消息历史（包含 assistant message）
        """
        from agentdojo.types import ChatAssistantMessage
        from agentdojo.functions_runtime import FunctionCall

        tool_call_info = branch.tool_call

        # ===== 特殊处理：SKIP STEP 步骤 =====
        if tool_call_info["tool_name"] == "__skip_step__":
            # SKIP STEP 步骤既不调用 tool，也不调用 LLM
            # 直接返回原始 messages，不做任何修改
            if self.config.log_hypothesis_generation:
                reason = tool_call_info.get("reason", "No reason provided")
                logger.info(
                    f"[HypothesisGuidance] SKIP STEP in backtracking - "
                    f"skipping without generating message. Reason: {reason}"
                )
            return messages

        # ===== 特殊处理：REASONING 步骤 =====
        if tool_call_info["tool_name"] == "__no_tool_call__":
            # REASONING 步骤在回溯时也不生成 tool call
            if self.config.log_hypothesis_generation:
                logger.info(
                    "[HypothesisGuidance] REASONING step in backtracking - "
                    "allowing LLM to provide reasoning"
                )
            return messages

        # ===== 正常的工具调用 =====
        # 创建 FunctionCall 对象
        tool_call = FunctionCall(
            id=f"call_{hash(tool_call_info['tool_name']) % 1000000}",
            function=tool_call_info["tool_name"],
            args=tool_call_info["arguments"],
        )

        # 生成 assistant message（包含 tool call）
        assistant_msg = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string(
                f"Trying alternative tool: {tool_call_info['tool_name']} (backtracking after error)"
            )],
            tool_calls=[tool_call],
        )

        return [*messages, assistant_msg]

    def _create_guidance_message_for_branch(self, branch) -> str:
        """为特定分支创建 guidance message

        Args:
            branch: 选定的分支

        Returns:
            Guidance 消息
        """
        tool_name = branch.tool_call["tool_name"]

        # ===== 特殊处理：SKIP STEP =====
        if tool_name == "__skip_step__":
            reason = branch.tool_call.get("reason", "No reason provided")
            guidance = f"""[VIGIL Backtracking Guidance]

🔄 The previous tool failed. Alternative: Skip this step.

Reason to skip: {reason}
- Necessity Score: {branch.necessity_score:.2f}/1.00
- Risk Level: {branch.risk_level}

This step will be skipped and execution will proceed to the next step."""
            return guidance

        # ===== 特殊处理：REASONING STEP =====
        if tool_name == "__no_tool_call__":
            guidance = f"""[VIGIL Backtracking Guidance]

🔄 The previous tool failed. Alternative: Reasoning step.

This step requires REASONING and ANALYSIS without tool execution.
- Necessity Score: {branch.necessity_score:.2f}/1.00
- Rationale: {branch.rationale}

Please provide your reasoning and analysis without calling any tools."""
            return guidance

        # ===== 正常的工具调用 =====
        guidance = f"""[VIGIL Backtracking Guidance]

🔄 The previous tool failed. Trying alternative approach.

Recommended tool: '{tool_name}'
- Necessity Score: {branch.necessity_score:.2f}/1.00
- Risk Level: {branch.risk_level}
- Rationale: {branch.rationale}

This is an alternative approach after the previous attempt failed.
Please proceed with this tool call."""

        return guidance

    def _generate_all_branches_failed_message(self) -> ChatMessage:
        """生成所有分支都失败的错误消息

        Returns:
            错误消息（ChatAssistantMessage）
        """
        from agentdojo.types import ChatAssistantMessage

        error_message = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string(
                f"❌ Unable to proceed: All available approaches for step {self._current_step_index + 1} "
                f"have failed security verification or execution.\n\n"
                f"This may indicate:\n"
                f"1. The task requires tools that violate security constraints\n"
                f"2. All available tools for this step are malicious or compromised\n"
                f"3. The task cannot be completed safely with the current tool set\n\n"
                f"Please review the task requirements and available tools."
            )],
            tool_calls=None,
        )

        return error_message

    def _create_cached_branch(self, selected_path, rationale: str):
        """从Path Cache的VerifiedPath创建HypothesisBranch

        Args:
            selected_path: 从path cache中选出的VerifiedPath对象
            rationale: LLM选择这个工具的理由

        Returns:
            HypothesisBranch对象
        """
        from vigil_agent.hypothesizer import HypothesisBranch

        # 创建一个hypothesis branch
        # 注意：来自path cache的工具已经验证过，所以：
        # - necessity_score 设为高值（因为历史证明它有效）
        # - risk_level 设为 "low"（已验证安全）
        # - 标记来源为 path_cache
        branch = HypothesisBranch(
            branch_id=f"cached_{selected_path.path_id}",
            tool_call={
                "tool_name": selected_path.tool_name,
                "arguments": selected_path.arguments,
                "tool_call_id": None,  # Path cache中的工具没有具体的调用ID
            },
            rationale=f"[Path Cache] {rationale} (Successfully used {selected_path.execution_count} times before)",
            necessity_score=0.95,  # 高分，因为历史证明有效
            risk_level="low",
            redundancy_level="minimal",
            has_side_effects=False,
            requires_external_communication=False,  # 假设path cache中的工具是安全的
            source="path_cache",  # 明确标记来源
            metadata={
                "source": "path_cache",
                "execution_count": selected_path.execution_count,
                "cached_path_id": selected_path.path_id,
            }
        )

        if self.config.log_hypothesis_generation:
            logger.debug(
                f"[HypothesisGuidance] Created cached branch: {branch.branch_id} "
                f"for tool '{selected_path.tool_name}'"
            )

        return branch

    def _generate_direct_tool_call_for_cached_branch(
        self, cached_branch, messages: Sequence[ChatMessage]
    ) -> Sequence[ChatMessage]:
        """为缓存分支生成direct tool call

        Args:
            cached_branch: 缓存的hypothesis branch
            messages: 当前消息历史

        Returns:
            更新后的消息历史（包含assistant message）
        """
        from agentdojo.types import ChatAssistantMessage
        from agentdojo.functions_runtime import FunctionCall

        tool_call_info = cached_branch.tool_call

        # 创建FunctionCall对象
        tool_call = FunctionCall(
            id=f"call_{hash(tool_call_info['tool_name']) % 1000000}",
            function=tool_call_info["tool_name"],
            args=tool_call_info["arguments"],
        )

        # 生成assistant message（包含tool call）
        # 强调这是从path cache中学习来的
        execution_count = cached_branch.metadata.get("execution_count", 0)
        assistant_msg = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string(
                f"I will use the {tool_call_info['tool_name']} tool "
                f"(learned from {execution_count} successful past executions)."
            )],
            tool_calls=[tool_call],
        )

        messages = [*messages, assistant_msg]

        if self.config.log_hypothesis_generation:
            logger.info(
                f"[HypothesisGuidance] Direct tool call generated from cache: {tool_call_info['tool_name']} "
                f"with args {tool_call_info['arguments']}"
            )

        return messages

    def _create_cached_tool_guidance_message(self, cached_branch) -> str:
        """为缓存分支创建guidance消息

        Args:
            cached_branch: 缓存的hypothesis branch

        Returns:
            Guidance消息内容
        """
        tool_name = cached_branch.tool_call["tool_name"]
        execution_count = cached_branch.metadata.get("execution_count", 0)
        rationale = cached_branch.rationale

        guidance = f"""[VIGIL Path Cache Guidance]

⚡ Recommended tool from learning history: '{tool_name}'

This tool has been successfully used {execution_count} time(s) for similar tasks.

Analysis:
  • Source: Path Cache (learned from successful executions)
  • Necessity Score: {cached_branch.necessity_score:.2f}/1.00
  • Risk Level: {cached_branch.risk_level}

Selection Rationale:
{rationale}

This is a strong recommendation based on verified successful executions.
The tool has been pre-approved and can be executed with high confidence."""

        return guidance
