"""测试 Path Cache 配置功能

验证：
1. 可以通过配置参数控制 path cache 的启用/禁用
2. 不同预设（strict, balanced, fast）有正确的 path cache 配置
3. path cache 在启用时正常工作
"""

import logging

from vigil_agent.config import VIGILConfig, get_vigil_config
from vigil_agent.path_cache import PathCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_config_enable_path_cache():
    """测试配置项 enable_path_cache"""
    print("\n=== Test 1: 配置项 enable_path_cache ===")

    # 测试默认值（应该是 False）
    config_default = VIGILConfig()
    print(f"默认配置 enable_path_cache: {config_default.enable_path_cache}")
    assert config_default.enable_path_cache == False, "默认应该禁用 path cache"

    # 测试显式启用
    config_enabled = VIGILConfig(enable_path_cache=True)
    print(f"启用配置 enable_path_cache: {config_enabled.enable_path_cache}")
    assert config_enabled.enable_path_cache == True

    # 测试显式禁用
    config_disabled = VIGILConfig(enable_path_cache=False)
    print(f"禁用配置 enable_path_cache: {config_disabled.enable_path_cache}")
    assert config_disabled.enable_path_cache == False

    print("✓ 配置项测试通过")


def test_preset_configs():
    """测试预设配置的 path cache 设置"""
    print("\n=== Test 2: 预设配置 ===")

    # strict 模式：应该禁用 path cache（最大化安全性）
    strict_config = get_vigil_config("strict", "gpt-4o")
    print(f"strict 模式 enable_path_cache: {strict_config.enable_path_cache}")
    assert strict_config.enable_path_cache == False, "strict 模式应该禁用 path cache"

    # balanced 模式：应该启用 path cache（平衡性能和安全）
    balanced_config = get_vigil_config("balanced", "gpt-4o")
    print(f"balanced 模式 enable_path_cache: {balanced_config.enable_path_cache}")
    assert balanced_config.enable_path_cache == True, "balanced 模式应该启用 path cache"

    # fast 模式：应该启用 path cache（最大化速度）
    fast_config = get_vigil_config("fast", "gpt-4o")
    print(f"fast 模式 enable_path_cache: {fast_config.enable_path_cache}")
    assert fast_config.enable_path_cache == True, "fast 模式应该启用 path cache"

    print("✓ 预设配置测试通过")


def test_path_cache_basic_functionality():
    """测试 PathCache 基本功能"""
    print("\n=== Test 3: PathCache 基本功能 ===")

    # 创建启用 path cache 的配置
    config = VIGILConfig(enable_path_cache=True)
    cache = PathCache(config)

    # 添加一个验证路径
    cache.add_verified_path(
        user_query="查询账户余额",
        tool_name="get_account_balance",
        arguments={"account_id": "12345"},
        outcome="success",
        step_index=0,
    )

    # 检索路径
    paths = cache.retrieve_paths("查询账户余额", step_index=0)
    print(f"检索到 {len(paths)} 条路径")
    assert len(paths) == 1, "应该检索到1条路径"

    # 获取推荐工具
    recommended_tool = cache.get_recommended_tool("查询账户余额", step_index=0)
    print(f"推荐工具: {recommended_tool}")
    assert recommended_tool == "get_account_balance", "应该推荐正确的工具"

    # 获取统计信息
    stats = cache.get_stats()
    print(f"缓存统计: {stats}")
    assert stats["total_cached_paths"] == 1
    assert stats["successful_paths"] == 1

    print("✓ PathCache 基本功能测试通过")


def test_pipeline_with_path_cache():
    """测试 Pipeline 中的 path cache 集成"""
    print("\n=== Test 4: Pipeline 中的 Path Cache 集成 ===")

    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("⊘ 跳过测试（需要 OPENAI_API_KEY）")
        return

    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
    import openai

    # 创建配置（启用 path cache）
    config = VIGILConfig(enable_path_cache=True)
    print(f"配置 enable_path_cache: {config.enable_path_cache}")

    # 创建 LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o-mini")

    # 创建 Pipeline
    pipeline = EnhancedVIGILPipeline(config=config, llm=llm)

    # 验证 path cache 已启用
    assert pipeline.path_cache is not None, "Pipeline 应该有 path_cache 实例"
    print("✓ Pipeline path_cache 已启用")

    # 获取统计信息（应该为空）
    stats = pipeline.get_path_cache_stats()
    print(f"初始缓存统计: {stats}")
    assert stats["total_cached_paths"] == 0

    print("✓ Pipeline 集成测试通过")


def test_pipeline_without_path_cache():
    """测试 Pipeline 中禁用 path cache"""
    print("\n=== Test 5: Pipeline 中禁用 Path Cache ===")

    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("⊘ 跳过测试（需要 OPENAI_API_KEY）")
        return

    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
    import openai

    # 创建配置（禁用 path cache）
    config = VIGILConfig(enable_path_cache=False)
    print(f"配置 enable_path_cache: {config.enable_path_cache}")

    # 创建 LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o-mini")

    # 创建 Pipeline
    pipeline = EnhancedVIGILPipeline(config=config, llm=llm)

    # 验证 path cache 已禁用
    assert pipeline.path_cache is None, "Pipeline 不应该有 path_cache 实例"
    print("✓ Pipeline path_cache 已禁用")

    # 获取统计信息（应该返回空字典）
    stats = pipeline.get_path_cache_stats()
    print(f"禁用时的缓存统计: {stats}")
    assert stats["total_cached_paths"] == 0
    assert stats["successful_paths"] == 0

    print("✓ Pipeline 禁用测试通过")


if __name__ == "__main__":
    try:
        test_config_enable_path_cache()
        test_preset_configs()
        test_path_cache_basic_functionality()
        test_pipeline_with_path_cache()
        test_pipeline_without_path_cache()

        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)

        print("\n使用说明：")
        print("1. 在配置中设置 enable_path_cache=True 来启用 path cache")
        print("2. 在配置中设置 enable_path_cache=False 来禁用 path cache")
        print("3. 预设配置：")
        print("   - strict 模式：默认禁用（最大化安全性）")
        print("   - balanced 模式：默认启用（平衡性能和安全）")
        print("   - fast 模式：默认启用（最大化速度）")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
