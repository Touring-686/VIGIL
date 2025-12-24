"""VIGIL Agent Framework

一个基于Neuro-Symbolic + Dynamic Constraints设计的AI Agent安全框架。

核心组件：
1. Constraint Generator: 从用户查询动态生成安全约束
2. Runtime Auditor: 运行时验证工具调用
3. Speculative Planner: 允许agent自由推理和尝试
4. Reflective Backtracking: 被拦截时提供反馈并允许重试

设计原则：
- Dynamic vs. Static: 安全约束动态生成，跟随用户意图
- Symbolic vs. Blackbox: 使用可解释的符号化验证
- Low Coupling: 与benchmark低耦合，易于集成和修改

快速开始：
```python
from vigil_agent import create_vigil_pipeline, VIGIL_BALANCED_CONFIG
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

# 创建LLM
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")

# 创建VIGIL pipeline
pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

# 使用pipeline
from agentdojo.benchmark import benchmark_suite_with_injections
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.attacks.base_attacks import DirectAttack

suite = get_suite("v1", "banking")
attack = DirectAttack()
results = benchmark_suite_with_injections(
    pipeline, suite, attack, logdir=None, force_rerun=False
)
```

详细文档和示例请参见 README.md
"""

# 核心配置
from vigil_agent.config import (
    VIGIL_BALANCED_CONFIG,
    VIGIL_FAST_CONFIG,
    VIGIL_STRICT_CONFIG,
    VIGILConfig,
    get_vigil_config,  # 导出配置生成函数
)

# 核心组件
from vigil_agent.constraint_generator import ConstraintGenerator
from vigil_agent.runtime_auditor import RuntimeAuditor

# 新增组件 (完整VIGIL框架)
from vigil_agent.perception_sanitizer import PerceptionSanitizer
from vigil_agent.tool_sanitizer_element import ToolDocstringSanitizer
from vigil_agent.abstract_sketch import AbstractSketchGenerator, AbstractSketch, AbstractStep
from vigil_agent.hypothesizer import Hypothesizer, HypothesisBranch, HypothesisTree
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor

# Pipeline和执行器
from vigil_agent.vigil_executor import VIGILInitQuery, VIGILToolsExecutor
from vigil_agent.vigil_pipeline import (
    VIGILAgentPipeline,
    create_vigil_pipeline,
    create_vigil_pipeline_from_base_pipeline,
)

# 增强版Pipeline (完整VIGIL框架)
from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor, EnhancedVIGILInitQuery
from vigil_agent.enhanced_pipeline import (
    EnhancedVIGILPipeline,
    create_enhanced_vigil_pipeline,
)

# 类型定义
from vigil_agent.types import (
    AuditResult,
    ConstraintSet,
    SecurityConstraint,
    ToolCallInfo,
)

__version__ = "0.1.0"

__all__ = [
    # 版本
    "__version__",
    # 配置
    "VIGILConfig",
    "get_vigil_config",  # 配置生成函数
    "VIGIL_STRICT_CONFIG",
    "VIGIL_BALANCED_CONFIG",
    "VIGIL_FAST_CONFIG",
    # 核心组件
    "ConstraintGenerator",
    "RuntimeAuditor",
    "VIGILToolsExecutor",
    "VIGILInitQuery",
    # 新增组件 (完整VIGIL框架)
    "PerceptionSanitizer",
    "ToolDocstringSanitizer",
    "AbstractSketchGenerator",
    "AbstractSketch",
    "AbstractStep",
    "Hypothesizer",
    "HypothesisBranch",
    "HypothesisTree",
    "EnhancedRuntimeAuditor",
    "EnhancedVIGILToolsExecutor",
    "EnhancedVIGILInitQuery",
    # Pipeline
    "VIGILAgentPipeline",
    "create_vigil_pipeline",
    "create_vigil_pipeline_from_base_pipeline",
    # 增强版Pipeline (完整VIGIL框架)
    "EnhancedVIGILPipeline",
    "create_enhanced_vigil_pipeline",
    # 类型
    "SecurityConstraint",
    "ConstraintSet",
    "AuditResult",
    "ToolCallInfo",
]
