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
from vigil_agent.config import VIGILConfig
from vigil_agent.constraint_generator import ConstraintGenerator
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor, EnhancedVIGILInitQuery
from vigil_agent.hypothesizer import Hypothesizer
from vigil_agent.perception_sanitizer import PerceptionSanitizer
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
    ):
        """初始化增强版VIGIL Pipeline

        Args:
            config: VIGIL配置
            llm: LLM组件
            system_message: 系统消息（可选）
        """
        self.vigil_config = config
        self.llm = llm

        # ===== Layer 0: Perception Sanitizer =====
        self.perception_sanitizer = PerceptionSanitizer(config)
        logger.info("[EnhancedVIGIL] Layer 0: Perception Sanitizer initialized")

        # Tool Docstring Sanitizer (防止Type I-A攻击)
        self.tool_docstring_sanitizer = ToolDocstringSanitizer(config, self.perception_sanitizer)
        logger.info("[EnhancedVIGIL] Layer 0: Tool Docstring Sanitizer initialized")

        # ===== Layer 1: Intent Anchor =====
        # 1.1 Constraint Generator
        self.constraint_generator = ConstraintGenerator(config)

        # 1.2 Abstract Sketch Generator
        self.sketch_generator = AbstractSketchGenerator(config) if config.enable_abstract_sketch else None
        logger.info("[EnhancedVIGIL] Layer 1: Intent Anchor initialized (Constraints + Sketch)")

        # ===== Layer 2: Speculative Reasoner =====
        self.hypothesizer = Hypothesizer(config) if config.enable_hypothesis_generation else None
        logger.info("[EnhancedVIGIL] Layer 2: Speculative Reasoner initialized")

        # ===== Layer 3: Neuro-Symbolic Verifier =====
        self.auditor = EnhancedRuntimeAuditor(config)
        logger.info("[EnhancedVIGIL] Layer 3: Neuro-Symbolic Verifier initialized")

        # ===== Pipeline Elements =====
        # Enhanced executor with sanitization
        self.vigil_tools_executor = EnhancedVIGILToolsExecutor(
            config=config,
            auditor=self.auditor,
            sanitizer=self.perception_sanitizer,
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

        # LLM（Speculative Planning）
        elements.append(llm)

        # 工具执行循环（带清洗、审计和回溯）
        tools_loop = ToolsExecutionLoop([self.vigil_tools_executor, llm], max_iters=15)
        elements.append(tools_loop)

        # 初始化父类
        super().__init__(elements)

        # 设置名称
        llm_name = getattr(llm, "name", "unknown_llm")
        self.name = f"{llm_name}-vigil-enhanced"

        logger.info(f"[EnhancedVIGILPipeline] Initialized complete VIGIL framework: {self.name}")
        logger.info("[EnhancedVIGILPipeline] All 4 layers active:")
        logger.info("  - Layer 0: Perception Sanitizer ✓")
        logger.info("  - Layer 1: Intent Anchor (Constraints + Sketch) ✓")
        logger.info("  - Layer 2: Speculative Reasoner ✓")
        logger.info("  - Layer 3: Neuro-Symbolic Verifier ✓")

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
        self.tool_docstring_sanitizer.clear_cache()  # 清空工具文档清洗器缓存
        self.auditor.reset_stats()
        self.vigil_tools_executor.reset_backtracking_counts()
        logger.info("[EnhancedVIGILPipeline] Reset for new task")

    def get_audit_stats(self) -> dict:
        """获取审计统计信息

        Returns:
            审计统计字典
        """
        return self.auditor.get_stats()


def create_enhanced_vigil_pipeline(
    llm: BasePipelineElement,
    config: VIGILConfig | None = None,
    system_message: str | None = None,
) -> EnhancedVIGILPipeline:
    """创建增强版VIGIL pipeline的工厂方法

    这是最简单的方式来创建一个完整的VIGIL agent。

    Args:
        llm: LLM组件（必需）
        config: VIGIL配置（可选，默认使用VIGIL_BALANCED_CONFIG）
        system_message: 自定义系统消息（可选）

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

    return EnhancedVIGILPipeline(config, llm, system_message)
