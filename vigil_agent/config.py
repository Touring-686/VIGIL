"""VIGIL框架的配置

定义了VIGIL框架的配置选项，使得框架易于定制和扩展。
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class VIGILConfig(BaseModel):
    """VIGIL框架的配置类

    这个配置类允许用户自定义VIGIL框架的各种行为，
    使得框架可以适应不同的使用场景和需求。
    """

    # ============ Constraint Generator 配置 ============
    constraint_generator_model: str = "gpt-4o-2024-08-06"
    """用于生成约束的LLM模型"""

    constraint_generator_temperature: float = 0.0
    """约束生成的温度参数"""

    enable_constraint_caching: bool = True
    """是否启用约束缓存（对相同查询不重复生成）"""

    constraint_generation_prompt_template: str | None = None
    """自定义的约束生成提示模板（如果为None则使用默认模板）"""

    # ============ Runtime Auditor 配置 ============
    auditor_mode: Literal["strict", "permissive", "hybrid"] = "hybrid"
    """审计模式：
    - strict: 严格模式，任何违反约束的操作都会被拦截
    - permissive: 宽松模式，只记录违规但不拦截
    - hybrid: 混合模式，根据约束类型决定是否拦截
    """

    enable_symbolic_verification: bool = True
    """是否启用符号化验证（基于规则的快速验证）"""

    enable_llm_verification: bool = False
    """是否启用LLM辅助验证（用于复杂场景）"""

    llm_verifier_model: str | None = "gpt-4o-mini"
    """LLM验证器使用的模型（仅当enable_llm_verification=True时使用）"""

    # ============ Reflective Backtracking 配置 ============
    enable_reflective_backtracking: bool = True
    """是否启用反思回溯机制"""

    max_backtracking_attempts: int = 3
    """每个工具调用的最大回溯尝试次数"""

    feedback_verbosity: Literal["minimal", "detailed", "verbose"] = "detailed"
    """反馈详细程度：
    - minimal: 最小反馈，只告诉agent操作被拒绝
    - detailed: 详细反馈，包括违反的约束和建议
    - verbose: 详尽反馈，包括所有审计细节
    """

    # ============ 日志和调试配置 ============
    enable_logging: bool = True
    """是否启用日志"""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    """日志级别"""

    log_constraint_generation: bool = True
    """是否记录约束生成过程"""

    log_audit_decisions: bool = True
    """是否记录审计决策"""

    # ============ 性能优化配置 ============
    max_constraints_per_query: int = 20
    """每个查询的最大约束数量"""

    constraint_deduplication: bool = True
    """是否去重约束"""

    # ============ 高级配置 ============
    allow_tool_whitelist: list[str] | None = None
    """始终允许的工具白名单（不进行审计）"""

    block_tool_blacklist: list[str] | None = None
    """始终阻止的工具黑名单"""

    custom_constraint_verifiers: dict[str, Any] | None = None
    """自定义的约束验证器（高级用法）"""

    enable_dynamic_constraint_update: bool = False
    """是否启用动态约束更新（实验性功能）"""

    # ============ Perception Sanitizer 配置 ============
    enable_perception_sanitizer: bool = True
    """是否启用感知层清洗器"""

    sanitizer_model: str = "gpt-4o-mini"
    """清洗器使用的LLM模型"""

    log_sanitizer_actions: bool = True
    """是否记录清洗操作"""

    # ============ Abstract Sketch Generator 配置 ============
    enable_abstract_sketch: bool = True
    """是否启用抽象草图生成"""

    sketch_generator_model: str = "gpt-4o-2024-08-06"
    """草图生成器使用的LLM模型"""

    sketch_generator_temperature: float = 0.0
    """草图生成的温度参数"""

    enable_sketch_caching: bool = True
    """是否启用草图缓存"""

    log_sketch_generation: bool = True
    """是否记录草图生成过程"""

    # ============ Hypothesizer 配置 ============
    enable_hypothesis_generation: bool = True
    """是否启用假设生成（多分支推理）"""

    log_hypothesis_generation: bool = True
    """是否记录假设生成过程"""

    # ============ Enhanced Auditor 配置 ============
    enable_minimum_necessity_check: bool = True
    """是否启用最小必要性检查"""

    minimum_necessity_threshold: float = 0.3
    """最小必要性阈值（0.0-1.0），低于此值的操作会被拒绝"""

    enable_redundancy_check: bool = True
    """是否启用冗余性检查（拒绝过于强大的工具）"""

    enable_sketch_consistency_check: bool = True
    """是否启用草图一致性检查"""

    class Config:
        """Pydantic配置"""

        arbitrary_types_allowed = True


def get_vigil_config(preset: str, model: str = "gpt-4o") -> VIGILConfig:
    """获取VIGIL配置预设

    Args:
        preset: 配置预设名称 ("strict", "balanced", "fast")
        model: LLM模型名称，将用于配置中的各个组件

    Returns:
        VIGIL配置
    """
    # 根据preset生成配置
    if preset == "strict":
        return VIGILConfig(
            # 模型配置 - 所有组件都使用传入的 model
            constraint_generator_model=model,
            sketch_generator_model=model,
            sanitizer_model=model,
            llm_verifier_model=model,
            # 审计模式
            auditor_mode="strict",
            enable_llm_verification=False,
            feedback_verbosity="detailed",
            max_backtracking_attempts=5,
            # 完整VIGIL框架组件
            enable_perception_sanitizer=True,
            enable_abstract_sketch=True,
            enable_hypothesis_generation=True,
            enable_minimum_necessity_check=True,
            enable_redundancy_check=True,
            enable_sketch_consistency_check=True,
            minimum_necessity_threshold=0.4,  # 严格模式：更高的相关性要求
        )
    elif preset == "balanced":
        return VIGILConfig(
            # 模型配置 - 所有组件都使用传入的 model
            constraint_generator_model=model,
            sketch_generator_model=model,
            sanitizer_model=model,
            llm_verifier_model=model,
            # 审计模式
            auditor_mode="hybrid",
            enable_llm_verification=False,
            feedback_verbosity="detailed",
            max_backtracking_attempts=3,
            # 完整VIGIL框架组件
            enable_perception_sanitizer=True,
            enable_abstract_sketch=True,
            enable_hypothesis_generation=True,
            enable_minimum_necessity_check=True,
            enable_redundancy_check=True,
            enable_sketch_consistency_check=True,
            minimum_necessity_threshold=0.3,  # 平衡模式：中等相关性要求
        )
    elif preset == "fast":
        return VIGILConfig(
            # 模型配置 - 所有组件都使用传入的 model
            constraint_generator_model=model,
            sketch_generator_model=model,
            sanitizer_model=model,
            llm_verifier_model=model,
            # 审计模式
            auditor_mode="permissive",
            enable_llm_verification=False,
            enable_constraint_caching=True,
            feedback_verbosity="minimal",
            max_backtracking_attempts=1,
            # 快速模式：关闭部分耗时组件
            enable_perception_sanitizer=True,  # 保留清洗器
            enable_abstract_sketch=False,  # 关闭草图生成
            enable_hypothesis_generation=False,  # 关闭假设生成
            enable_minimum_necessity_check=True,  # 保留最小必要性
            enable_redundancy_check=False,  # 关闭冗余检查
            enable_sketch_consistency_check=False,  # 关闭一致性检查
            minimum_necessity_threshold=0.2,  # 快速模式：较低的相关性要求
        )
    else:
        raise ValueError(f"Unknown preset: {preset}. Choose from 'strict', 'balanced', or 'fast'")


# 预定义配置（为了向后兼容，保留这些常量）
VIGIL_STRICT_CONFIG = get_vigil_config("strict", "gpt-4o")
"""严格模式配置：最大化安全性，启用所有VIGIL层"""

VIGIL_BALANCED_CONFIG = get_vigil_config("balanced", "gpt-4o")
"""平衡模式配置：安全性和性能的平衡，启用所有VIGIL层"""

VIGIL_FAST_CONFIG = get_vigil_config("fast", "gpt-4o")
"""快速模式配置：最小开销，只启用核心VIGIL组件"""
