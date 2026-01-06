"""增强版VIGIL Pipeline

整合了完整的VIGIL框架四层架构：
- Layer 0: Perception Sanitizer (数据清洗)
- Layer 1: Intent Anchor (意图锚点 + 抽象草图)
- Layer 2: Speculative Reasoner (假设推理器)
- Layer 3: Neuro-Symbolic Verifier (增强审计器)

这是完整的VIGIL框架实现，包含了论文中描述的所有核心组件。
"""

import logging

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import SystemMessage
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop

from vigil_agent.abstract_sketch import AbstractSketchGenerator
from vigil_agent.commitment_manager import CommitmentManager
from vigil_agent.conditional_llm import ConditionalLLM
from vigil_agent.config import VIGILConfig
from vigil_agent.constraint_generator import ConstraintGenerator
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor, EnhancedVIGILInitQuery
from vigil_agent.enhanced_tools_loop import EnhancedToolsExecutionLoop
from vigil_agent.hypothesis_guidance import HypothesisGuidanceElement
from vigil_agent.hypothesizer import Hypothesizer
from vigil_agent.path_cache import PathCache
from vigil_agent.perception_sanitizer import PerceptionSanitizer
from vigil_agent.token_stats_tracker import TokenStatsTracker, get_global_tracker
from vigil_agent.tool_sanitizer_element import ToolDocstringSanitizer

logger = logging.getLogger(__name__)


class EnhancedVIGILPipeline(AgentPipeline):
    """增强版VIGIL Agent Pipeline

    实现了完整的VIGIL框架四层架构：

    Layer 0: Perception Sanitizer
    - 清洗工具文档、返回值和错误消息
    - 防止Type I-A, I-B, III-A攻击

    Layer 1: Intent Anchor
    - 约束生成器：生成安全约束
    - 抽象草图生成器：生成高层执行计划
    - 作为不可变的"北极星"指导执行

    Layer 2: Speculative Reasoner (Hypothesizer)
    - 生成多条可能的执行路径
    - 符号化标记风险、必要性、冗余度
    - 延迟执行决策

    Layer 3: Neuro-Symbolic Verifier (Enhanced Auditor)
    - 最小必要性检验
    - 冗余性检验
    - 一致性检验（与Intent Anchor对比）
    - 反思回溯机制

    架构：
    1. SystemMessage: 设置系统提示
    2. EnhancedVIGILInitQuery: 生成约束 + 抽象草图
    3. LLM: 执行推理（Speculative Planning）
    4. ToolsExecutionLoop:
       - EnhancedVIGILToolsExecutor: 清洗 + 审计 + 执行
       - LLM: 继续推理
    """

    def __init__(
        self,
        config: VIGILConfig,
        llm: BasePipelineElement,
        system_message: str | None = None,
        token_tracker: TokenStatsTracker | None = None,
        path_cache: PathCache | None = None,
        use_tool_cache: bool = False,
    ):
        """初始化增强版VIGIL Pipeline

        Args:
            config: VIGIL配置
            llm: LLM组件
            system_message: 系统消息（可选）
            token_tracker: Token 统计追踪器（可选，默认使用全局追踪器）
            path_cache: Path Cache 实例（可选，只有传入时才启用路径缓存）
            use_tool_cache: 是否使用工具缓存（可选，默认 False，只有启用才从磁盘加载已清洗的工具）
        """
        self.vigil_config = config
        self.llm = llm
        self.token_tracker = token_tracker or get_global_tracker()

        # ===== 包装LLM为ConditionalLLM（支持direct mode跳过） =====
        # 在direct mode下，HypothesisGuidance生成tool call后，通过skip_llm标志告诉LLM跳过
        self.conditional_llm = ConditionalLLM(llm)
        logger.info("[EnhancedVIGIL] Wrapped LLM in ConditionalLLM for direct mode support")

        # ===== Layer 0: Perception Sanitizer =====
        self.perception_sanitizer = PerceptionSanitizer(config)
        logger.info("[EnhancedVIGIL] Layer 0: Perception Sanitizer initialized")

        # Tool Docstring Sanitizer (防止Type I-A攻击)
        self.tool_docstring_sanitizer = ToolDocstringSanitizer(
            config,
            self.perception_sanitizer,
            use_disk_cache=use_tool_cache,
        )
        logger.info("[EnhancedVIGIL] Layer 0: Tool Docstring Sanitizer initialized")

        # ===== Layer 1: Intent Anchor =====
        # 1.1 Constraint Generator
        self.constraint_generator = ConstraintGenerator(config)

        # 1.2 Abstract Sketch Generator
        self.sketch_generator = (
            AbstractSketchGenerator(config, token_tracker=self.token_tracker)
            if config.enable_abstract_sketch
            else None
        )
        logger.info("[EnhancedVIGIL] Layer 1: Intent Anchor initialized (Constraints + Sketch)")

        # ===== Layer 2: Speculative Reasoner =====
        # 创建共享的 OpenAI client（如果需要）
        openai_client = None
        if config.enable_hypothesis_generation:
            try:
                import openai
                from vigil_agent.client_utils import create_openai_client_for_model

                openai_client = create_openai_client_for_model(config.hypothesizer_model)
                logger.info("[EnhancedVIGIL] Created shared OpenAI client for Hypothesizer")
            except Exception as e:
                logger.warning(f"[EnhancedVIGIL] Failed to create OpenAI client: {e}")

        self.hypothesizer = (
            Hypothesizer(config, openai_client, token_tracker=self.token_tracker)
            if config.enable_hypothesis_generation
            else None
        )
        if self.hypothesizer:
            logger.info("[EnhancedVIGIL] Layer 2: Speculative Reasoner initialized and will be integrated")
        else:
            logger.info("[EnhancedVIGIL] Layer 2: Speculative Reasoner disabled (enable_hypothesis_generation=False)")

        # ===== Layer 3: Neuro-Symbolic Verifier =====
        self.auditor = EnhancedRuntimeAuditor(config, token_tracker=self.token_tracker)
        logger.info("[EnhancedVIGIL] Layer 3: Neuro-Symbolic Verifier initialized")

        # ===== 设置 Hypothesizer 的 auditor 引用（用于访问执行历史）=====
        if self.hypothesizer:
            self.hypothesizer.auditor = self.auditor
            logger.info("[EnhancedVIGIL] Connected Hypothesizer to Auditor (for execution history access)")

        # ===== Path Cache (学习机制) =====
        # Path Cache 通过参数传入，只有传入时才启用
        # 如果没有传入但 config.enable_path_cache 为 True，则自动创建（向后兼容）
        if path_cache is not None:
            # 使用传入的 Path Cache
            self.path_cache = path_cache
            logger.info("[EnhancedVIGIL] Path Cache provided via parameter (learning enabled)")
        elif config.enable_path_cache:
            # 向后兼容：根据配置自动创建
            self.path_cache = PathCache(
                config,
                openai_client=openai_client,  # 传递 OpenAI client 用于 LLM 选择器
                token_tracker=self.token_tracker,  # 传递 token tracker
            )
            logger.info("[EnhancedVIGIL] Path Cache auto-created from config (learning enabled)")
        else:
            # 不使用 Path Cache
            self.path_cache = None
            logger.info("[EnhancedVIGIL] Path Cache disabled (not provided and config.enable_path_cache=False)")

        # ===== Commitment Manager (决策引擎) =====
        # Commitment Manager 使用 Hypothesizer 和 Auditor 来选择最优路径
        self.commitment_manager = None
        self.hypothesis_guidance = None
        if self.hypothesizer:
            self.commitment_manager = CommitmentManager(config, self.auditor)
            logger.info("[EnhancedVIGIL] Commitment Manager initialized (bridges Layer 2 & 3)")

            # 创建 Hypothesis Guidance Element
            # 这个element在LLM推理之前生成hypothesis tree并提供guidance
            self.hypothesis_guidance = HypothesisGuidanceElement(
                config=config,
                hypothesizer=self.hypothesizer,
                commitment_manager=self.commitment_manager,
                auditor=self.auditor,  # 传递 auditor 以访问 Abstract Sketch
                path_cache=self.path_cache,
                sanitizer=self.perception_sanitizer,  # 传递 sanitizer 进行二次清洗
                sketch_generator=self.sketch_generator,  # 传递 sketch_generator 用于动态更新
            )
            logger.info("[EnhancedVIGIL] Hypothesis Guidance Element initialized (provides pre-decision guidance)")

        # ===== Pipeline Elements =====
        # Enhanced executor with sanitization and hypothesis generation
        self.vigil_tools_executor = EnhancedVIGILToolsExecutor(
            config=config,
            auditor=self.auditor,
            sanitizer=self.perception_sanitizer,
            hypothesizer=self.hypothesizer,  # 传递 hypothesizer 实现 Layer 2 集成
            commitment_manager=self.commitment_manager,  # 传递 commitment manager
            path_cache=self.path_cache,  # 传递 path cache
            openai_client=openai_client,  # 传递 openai_client 用于 LLM 调用
        )

        # Enhanced init query with sketch generation
        self.vigil_init_query = EnhancedVIGILInitQuery(
            config=config,
            constraint_generator=self.constraint_generator,
            sketch_generator=self.sketch_generator,
            auditor=self.auditor,
        )

        # 构建pipeline元素
        elements = []

        # 系统消息
        if system_message is None:
            system_message = self._get_default_system_message()
        elements.append(SystemMessage(system_message))

        # === Layer 0: Tool Docstring Sanitizer (必须在所有其他组件之前) ===
        # 清洗工具文档，防止Type I-A (Goal Hijacking via Docstring)攻击
        elements.append(self.tool_docstring_sanitizer)

        # VIGIL初始化查询（生成约束 + 草图）
        elements.append(self.vigil_init_query)

        # === 工具执行循环（包含第一轮和后续轮次）===
        # 重要：不要在循环外部单独调用HypothesisGuidance！
        # ToolsExecutionLoop会处理所有轮次，包括第一轮
        #
        # 执行顺序：
        #   1. HypothesisGuidance - 生成hypothesis tree并选择工具
        #   2. ConditionalLLM - 根据模式决定是否调用LLM
        #   3. EnhancedVIGILToolsExecutor - 执行工具调用
        #   4. (重复直到没有tool_calls)

        if self.hypothesis_guidance:
            # 启用了Hypothesis Guidance
            # 循环包含：HypothesisGuidance → ConditionalLLM → Executor
            tools_loop = EnhancedToolsExecutionLoop(
                [self.hypothesis_guidance, self.conditional_llm, self.vigil_tools_executor],
                max_iters=15
            )
            if config.enable_direct_tool_execution:
                logger.info(
                    "[EnhancedVIGIL] EnhancedToolsExecutionLoop configured: "
                    "HypothesisGuidance → ConditionalLLM (skip) → Executor (direct mode)"
                )
            else:
                logger.info(
                    "[EnhancedVIGIL] EnhancedToolsExecutionLoop configured: "
                    "HypothesisGuidance → ConditionalLLM → Executor (guidance mode)"
                )
        else:
            # 未启用Hypothesis Guidance，使用传统流程
            tools_loop = EnhancedToolsExecutionLoop([self.conditional_llm, self.vigil_tools_executor], max_iters=15)
            logger.info("[EnhancedVIGIL] EnhancedToolsExecutionLoop configured: LLM → Executor (traditional mode)")

        elements.append(tools_loop)

        # 初始化父类
        super().__init__(elements)

        # 设置名称
        llm_name = getattr(llm, "name", "unknown_llm")
        self.name = f"{llm_name}-vigil-enhanced"

        logger.info(f"[EnhancedVIGILPipeline] Initialized complete VIGIL framework: {self.name}")
        logger.info("[EnhancedVIGILPipeline] All 4 layers active and integrated:")
        logger.info("  - Layer 0: Perception Sanitizer ✓")
        logger.info("  - Layer 1: Intent Anchor (Constraints + Sketch) ✓")
        logger.info(f"  - Layer 2: Speculative Reasoner {'✓ (integrated)' if self.hypothesizer else '✗ (disabled)'}")
        logger.info("  - Layer 3: Neuro-Symbolic Verifier ✓")
        logger.info(f"  - Commitment Manager {'✓ (active)' if self.commitment_manager else '✗ (inactive)'}")
        logger.info(f"  - Path Cache {'✓ (learning enabled)' if self.path_cache else '✗ (disabled)'}")


    def _get_default_system_message(self) -> str:
        """获取默认的系统消息

        Returns:
            系统消息
        """
        return """You are a helpful AI assistant with access to various tools.

IMPORTANT INSTRUCTIONS:
1. Always focus on the user's request and complete it to the best of your ability
2. You will receive an execution plan (sketch) - follow it as a guide
3. If a tool call is blocked due to security constraints, carefully read the feedback message
4. Try alternative approaches when a tool is blocked - there is usually another way to achieve the goal
5. Never give up after one failed attempt - you can make multiple attempts with different approaches
6. Use the security feedback to guide your next attempt
7. Prefer simpler, more targeted tools over complex ones when possible
8. Only use tools that are directly necessary for the user's request

CRITICAL CONSTRAINT:
**YOU MUST CALL EXACTLY ONE TOOL PER TURN.**
- Do NOT call multiple tools in a single response
- Each turn should contain AT MOST ONE tool call
- Execute tools step-by-step, waiting for each tool's result before proceeding
- If you need to use multiple tools, call them one at a time across multiple turns
- Calling multiple tools simultaneously is STRICTLY FORBIDDEN

SECURITY PRINCIPLES:
- Minimum Necessity: Only use tools that are minimally necessary for the task
- Avoid Redundancy: Don't use overly powerful tools when simpler ones suffice
- Stay On Track: Follow the execution plan and don't deviate from the user's intent

Remember: Security constraints are there to protect the user and ensure you complete tasks safely and efficiently."""

    def reset_for_new_task(self) -> None:
        """为新任务重置pipeline状态

        在开始新任务时调用此方法来清理之前的状态。
        """
        self.constraint_generator.clear_cache()
        if self.sketch_generator:
            self.sketch_generator.clear_cache()
        self.perception_sanitizer.clear_cache()
        # self.tool_docstring_sanitizer.clear_cache()  # 清空工具文档清洗器缓存
        self.auditor.reset_stats()
        self.vigil_tools_executor.reset_backtracking_counts()
        if self.hypothesis_guidance:
            self.hypothesis_guidance.reset()  # 重置hypothesis guidance状态
        logger.info("[EnhancedVIGILPipeline] Reset for new task")

    def get_audit_stats(self) -> dict:
        """获取审计统计信息

        Returns:
            审计统计字典
        """
        return self.auditor.get_stats()

    def get_path_cache_stats(self) -> dict:
        """获取路径缓存统计信息

        Returns:
            路径缓存统计字典，如果未启用则返回空字典
        """
        if self.path_cache:
            return self.path_cache.get_stats()
        return {
            "total_cached_paths": 0,
            "successful_paths": 0,
            "failed_paths": 0,
            "total_executions": 0,
            "unique_queries": 0,
        }


def create_enhanced_vigil_pipeline(
    llm: BasePipelineElement,
    config: VIGILConfig | None = None,
    system_message: str | None = None,
    use_tool_cache: bool = False,
) -> EnhancedVIGILPipeline:
    """创建增强版VIGIL pipeline的工厂方法

    这是最简单的方式来创建一个完整的VIGIL agent。

    Args:
        llm: LLM组件（必需）
        config: VIGIL配置（可选，默认使用VIGIL_BALANCED_CONFIG）
        system_message: 自定义系统消息（可选）
        use_tool_cache: 是否使用工具缓存（可选，默认 False）

    Returns:
        配置好的增强版VIGIL pipeline

    Example:
        ```python
        from vigil_agent import create_enhanced_vigil_pipeline, VIGIL_BALANCED_CONFIG
        from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
        import openai

        # 创建LLM
        client = openai.OpenAI()
        llm = OpenAILLM(client, "gpt-4o")

        # 创建增强版VIGIL pipeline
        pipeline = create_enhanced_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

        # 在benchmark中使用
        from agentdojo.benchmark import benchmark_suite_with_injections
        results = benchmark_suite_with_injections(pipeline, suite, attack, logdir, force_rerun=False)
        ```
    """
    from vigil_agent.config import VIGIL_BALANCED_CONFIG

    if config is None:
        config = VIGIL_BALANCED_CONFIG
        logger.info("[create_enhanced_vigil_pipeline] Using default VIGIL_BALANCED_CONFIG")

    return EnhancedVIGILPipeline(config, llm, system_message, use_tool_cache=use_tool_cache)
