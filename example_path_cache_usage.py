"""Path Cache 使用示例

演示如何通过配置参数控制 path cache 的启用/禁用
"""

from vigil_agent.config import VIGILConfig, get_vigil_config


def example_1_basic_usage():
    """示例 1: 基本使用 - 手动配置"""
    print("=" * 60)
    print("示例 1: 基本使用 - 手动配置")
    print("=" * 60)

    # 方式 1: 启用 path cache
    config_enabled = VIGILConfig(enable_path_cache=True)
    print(f"\n✓ 创建配置（启用 path cache）")
    print(f"  enable_path_cache = {config_enabled.enable_path_cache}")

    # 方式 2: 禁用 path cache
    config_disabled = VIGILConfig(enable_path_cache=False)
    print(f"\n✓ 创建配置（禁用 path cache）")
    print(f"  enable_path_cache = {config_disabled.enable_path_cache}")

    # 方式 3: 使用默认值（默认禁用）
    config_default = VIGILConfig()
    print(f"\n✓ 创建配置（默认值）")
    print(f"  enable_path_cache = {config_default.enable_path_cache}")


def example_2_preset_configs():
    """示例 2: 使用预设配置"""
    print("\n" + "=" * 60)
    print("示例 2: 使用预设配置")
    print("=" * 60)

    # strict 模式 - 最大化安全性
    strict_config = get_vigil_config("strict", "gpt-4o")
    print(f"\n✓ strict 模式")
    print(f"  enable_path_cache = {strict_config.enable_path_cache}")
    print(f"  说明: 最大化安全性，每次都重新验证")

    # balanced 模式 - 平衡性能和安全
    balanced_config = get_vigil_config("balanced", "gpt-4o")
    print(f"\n✓ balanced 模式")
    print(f"  enable_path_cache = {balanced_config.enable_path_cache}")
    print(f"  说明: 平衡性能和安全，启用学习机制")

    # fast 模式 - 最大化速度
    fast_config = get_vigil_config("fast", "gpt-4o")
    print(f"\n✓ fast 模式")
    print(f"  enable_path_cache = {fast_config.enable_path_cache}")
    print(f"  说明: 最大化速度，充分利用缓存")


def example_3_dynamic_selection():
    """示例 3: 根据任务类型动态选择配置"""
    print("\n" + "=" * 60)
    print("示例 3: 根据任务类型动态选择配置")
    print("=" * 60)

    def get_config_for_task(task_type: str) -> VIGILConfig:
        """根据任务类型返回合适的配置"""
        if task_type == "critical":
            # 关键任务：禁用缓存，最大化安全性
            return get_vigil_config("strict", "gpt-4o")
        elif task_type == "routine":
            # 常规任务：启用缓存，最大化速度
            return get_vigil_config("fast", "gpt-4o")
        else:
            # 默认：平衡模式
            return get_vigil_config("balanced", "gpt-4o")

    # 测试不同任务类型
    task_types = ["critical", "routine", "normal"]
    for task_type in task_types:
        config = get_config_for_task(task_type)
        print(f"\n✓ 任务类型: {task_type}")
        print(f"  enable_path_cache = {config.enable_path_cache}")


def example_4_custom_configuration():
    """示例 4: 自定义配置组合"""
    print("\n" + "=" * 60)
    print("示例 4: 自定义配置组合")
    print("=" * 60)

    # 创建自定义配置：启用 path cache，但使用严格的审计模式
    custom_config = VIGILConfig(
        # Path Cache 配置
        enable_path_cache=True,

        # 审计模式 - 严格
        auditor_mode="strict",

        # 启用所有验证
        enable_llm_verification=True,
        enable_minimum_necessity_check=True,
        enable_redundancy_check=True,
        enable_sketch_consistency_check=True,

        # 启用假设生成
        enable_hypothesis_generation=True,
        enable_direct_tool_execution=True,

        # 模型配置
        constraint_generator_model="gpt-4o",
        sketch_generator_model="gpt-4o",
        hypothesizer_model="gpt-4o-mini",
    )

    print(f"\n✓ 自定义配置创建成功")
    print(f"  enable_path_cache = {custom_config.enable_path_cache}")
    print(f"  auditor_mode = {custom_config.auditor_mode}")
    print(f"  enable_hypothesis_generation = {custom_config.enable_hypothesis_generation}")
    print(f"  说明: 启用 path cache 的同时保持严格的安全验证")


def example_5_pipeline_integration():
    """示例 5: 在 Pipeline 中使用（需要 OPENAI_API_KEY）"""
    print("\n" + "=" * 60)
    print("示例 5: 在 Pipeline 中使用")
    print("=" * 60)

    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⊘ 跳过此示例（需要设置 OPENAI_API_KEY 环境变量）")
        print("\n示例代码：")
        print("""
from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

# 创建配置（启用 path cache）
config = VIGILConfig(enable_path_cache=True)

# 创建 LLM
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")

# 创建 Pipeline
pipeline = EnhancedVIGILPipeline(config=config, llm=llm)

# 检查 path cache 是否启用
if pipeline.path_cache:
    print("✓ Path Cache 已启用")
else:
    print("✗ Path Cache 未启用")

# 获取缓存统计
stats = pipeline.get_path_cache_stats()
print(f"缓存统计: {stats}")
        """)
        return

    # 实际运行代码
    from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    import openai

    config = VIGILConfig(enable_path_cache=True)
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o-mini")
    pipeline = EnhancedVIGILPipeline(config=config, llm=llm)

    print(f"\n✓ Pipeline 创建成功")
    print(f"  Path Cache 状态: {'已启用' if pipeline.path_cache else '未启用'}")

    stats = pipeline.get_path_cache_stats()
    print(f"  初始缓存统计: {stats}")


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Path Cache 使用示例" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")

    example_1_basic_usage()
    example_2_preset_configs()
    example_3_dynamic_selection()
    example_4_custom_configuration()
    example_5_pipeline_integration()

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("""
Path Cache 是 VIGIL 框架的可选学习机制，可以通过以下方式控制：

1. 手动配置: VIGILConfig(enable_path_cache=True/False)

2. 预设配置:
   - strict:   enable_path_cache=False (最大化安全性)
   - balanced: enable_path_cache=True  (平衡性能和安全)
   - fast:     enable_path_cache=True  (最大化速度)

3. 动态选择: 根据任务类型选择不同的配置

4. 自定义配置: 结合其他配置项创建最适合的配置

更多信息请查看: PATH_CACHE_USAGE.md
    """)


if __name__ == "__main__":
    main()
