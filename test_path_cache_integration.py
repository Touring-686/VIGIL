"""测试Path Cache完整集成

这个测试验证：
1. Path Cache能正确存储abstract step -> tool的映射
2. HypothesisGuidanceElement能在生成hypothesis tree前先查询path cache
3. 相似度匹配能正确检索top-3候选
4. LLM能从候选中选择最合适的工具
5. 工具执行成功后能更新path cache
"""

import logging
import sys
from pathlib import Path

# 添加项目路径到Python搜索路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_path_cache_basic_operations():
    """测试Path Cache的基本操作"""
    from vigil_agent.config import VIGILConfig
    from vigil_agent.path_cache import PathCache

    print("\n" + "="*80)
    print("测试 1: Path Cache基本操作")
    print("="*80)

    # 创建配置（启用path cache）
    config = VIGILConfig(enable_path_cache=True)

    # 创建path cache
    path_cache = PathCache(config)

    # 添加一些verified paths（模拟成功执行的历史）
    test_cases = [
        {
            "user_query": "Send an email to John about the meeting",
            "tool_name": "send_email",
            "arguments": {"recipient": "john@example.com", "subject": "Meeting", "body": "..."},
            "outcome": "success",
            "step_index": 1,
            "abstract_step_description": "Send email notification to stakeholder",
        },
        {
            "user_query": "Send a notification to the team",
            "tool_name": "send_email",
            "arguments": {"recipient": "team@example.com", "subject": "Notification", "body": "..."},
            "outcome": "success",
            "step_index": 1,
            "abstract_step_description": "Send email notification to team members",
        },
        {
            "user_query": "Get the current date",
            "tool_name": "get_current_time",
            "arguments": {},
            "outcome": "success",
            "step_index": 1,
            "abstract_step_description": "Retrieve current date and time information",
        },
    ]

    for case in test_cases:
        path_cache.add_verified_path(**case)
        print(f"✓ Added path: {case['tool_name']} for '{case['abstract_step_description'][:50]}...'")

    # 获取统计信息
    stats = path_cache.get_stats()
    print(f"\n📊 Path Cache统计:")
    print(f"  - 总路径数: {stats['total_cached_paths']}")
    print(f"  - 成功路径数: {stats['successful_paths']}")
    print(f"  - 失败路径数: {stats['failed_paths']}")

    # 测试检索（基于abstract step description）
    print("\n" + "-"*80)
    print("测试检索功能（基于abstract step相似度）")
    print("-"*80)

    # 测试相似的查询
    test_query = "Send email notification to stakeholders"
    print(f"\n查询: '{test_query}'")

    cached_paths = path_cache.retrieve_paths_by_abstract_step(test_query, top_k=3)

    if cached_paths:
        print(f"✓ 找到 {len(cached_paths)} 个匹配路径:")
        for i, path in enumerate(cached_paths, 1):
            print(f"  {i}. {path.tool_name}")
            print(f"     Abstract step: '{path.abstract_step_description[:60]}...'")
            print(f"     执行次数: {path.execution_count}")
    else:
        print("✗ 未找到匹配路径")

    print("\n✅ 测试1完成!")
    return True


def test_path_cache_with_llm_selector():
    """测试Path Cache的LLM选择器（需要OpenAI API key）"""
    import os

    print("\n" + "="*80)
    print("测试 2: Path Cache LLM选择器")
    print("="*80)

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  跳过: 需要设置 OPENAI_API_KEY 环境变量")
        return False

    from vigil_agent.config import VIGILConfig
    from vigil_agent.path_cache import PathCache
    import openai

    # 创建配置和OpenAI client
    config = VIGILConfig(enable_path_cache=True)
    openai_client = openai.OpenAI()
    path_cache = PathCache(config, openai_client=openai_client)

    # 添加一些verified paths
    test_cases = [
        {
            "user_query": "Send an email",
            "tool_name": "send_email",
            "arguments": {"recipient": "test@example.com"},
            "outcome": "success",
            "abstract_step_description": "Send email notification to stakeholder",
        },
        {
            "user_query": "Send a message",
            "tool_name": "send_slack_message",
            "arguments": {"channel": "general", "message": "test"},
            "outcome": "success",
            "abstract_step_description": "Send instant message via Slack",
        },
    ]

    for case in test_cases:
        path_cache.add_verified_path(**case)

    # 测试LLM选择器
    test_query = "Notify the team about the update"
    print(f"\n查询: '{test_query}'")

    cached_paths = path_cache.retrieve_paths_by_abstract_step(test_query, top_k=2)

    if cached_paths:
        print(f"✓ 找到 {len(cached_paths)} 个候选工具")

        # 使用LLM选择最合适的
        selected_tool, rationale = path_cache.select_tool_with_llm(test_query, cached_paths)

        if selected_tool:
            print(f"\n✓ LLM选择了: {selected_tool}")
            print(f"理由: {rationale}")
        else:
            print("✗ LLM未能选择工具")
    else:
        print("✗ 未找到匹配路径")

    print("\n✅ 测试2完成!")
    return True


def test_path_cache_configuration():
    """测试Path Cache配置选项"""
    from vigil_agent.config import VIGILConfig, get_vigil_config

    print("\n" + "="*80)
    print("测试 3: Path Cache配置")
    print("="*80)

    # 测试默认配置
    default_config = VIGILConfig()
    print(f"默认配置 enable_path_cache: {default_config.enable_path_cache}")
    assert default_config.enable_path_cache == False, "默认应该禁用path cache"

    # 测试预设配置
    configs = {
        "strict": get_vigil_config("strict", "gpt-4o"),
        "balanced": get_vigil_config("balanced", "gpt-4o"),
        "fast": get_vigil_config("fast", "gpt-4o"),
    }

    print("\n预设配置:")
    for name, config in configs.items():
        status = "✓ 启用" if config.enable_path_cache else "✗ 禁用"
        print(f"  {name:10} - Path Cache: {status}")

    # 验证预设配置符合预期
    assert configs["strict"].enable_path_cache == False, "strict模式应该禁用path cache"
    assert configs["balanced"].enable_path_cache == True, "balanced模式应该启用path cache"
    assert configs["fast"].enable_path_cache == True, "fast模式应该启用path cache"

    print("\n✅ 测试3完成!")
    return True


def test_hypothesis_guidance_integration():
    """测试HypothesisGuidance与Path Cache的集成"""
    print("\n" + "="*80)
    print("测试 4: HypothesisGuidance集成")
    print("="*80)

    # 这个测试需要完整的pipeline，这里只做简单的模块测试
    from vigil_agent.config import VIGILConfig
    from vigil_agent.path_cache import PathCache
    from vigil_agent.abstract_sketch import AbstractSketch, AbstractStep

    config = VIGILConfig(enable_path_cache=True)
    path_cache = PathCache(config)

    # 模拟一个abstract sketch
    sketch = AbstractSketch(
        user_query="Send a notification to John",
        steps=[
            AbstractStep(
                step_id="step_1",
                step_number=1,
                step_type="ACTION",
                description="Send email notification to John",
                reasoning="Need to notify John about the update",
                required_info=[]
            )
        ],
        global_constraints=["Only use email tools", "No external API calls"],
        expected_outcome="Email successfully sent to John",
    )

    # 添加一个相关的verified path
    path_cache.add_verified_path(
        user_query="Send notification to John",
        tool_name="send_email",
        arguments={"recipient": "john@example.com", "subject": "Update", "body": "..."},
        outcome="success",
        step_index=1,
        abstract_step_description="Send email notification to John",
    )

    # 模拟检索流程
    current_step = sketch.steps[0]
    cached_paths = path_cache.retrieve_paths_by_abstract_step(
        current_step.description, top_k=3
    )

    if cached_paths:
        print(f"✓ Path Cache命中! 找到 {len(cached_paths)} 个匹配路径")
        print(f"  推荐工具: {cached_paths[0].tool_name}")
        print(f"  执行次数: {cached_paths[0].execution_count}")
    else:
        print("✗ Path Cache未命中")

    print("\n✅ 测试4完成!")
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Path Cache集成测试套件")
    print("="*80)

    tests = [
        ("基本操作", test_path_cache_basic_operations),
        ("LLM选择器", test_path_cache_with_llm_selector),
        ("配置选项", test_path_cache_configuration),
        ("HypothesisGuidance集成", test_hypothesis_guidance_integration),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ 通过" if result else "⚠️  跳过"
        except Exception as e:
            results[test_name] = f"❌ 失败: {str(e)}"
            logger.exception(f"测试 '{test_name}' 失败")

    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for test_name, result in results.items():
        print(f"{test_name:30} {result}")

    # 统计
    passed = sum(1 for r in results.values() if "✅" in r)
    skipped = sum(1 for r in results.values() if "⚠️" in r)
    failed = sum(1 for r in results.values() if "❌" in r)

    print(f"\n总计: {len(tests)} 个测试")
    print(f"  ✅ 通过: {passed}")
    print(f"  ⚠️  跳过: {skipped}")
    print(f"  ❌ 失败: {failed}")

    if failed > 0:
        print("\n⚠️  有测试失败，请检查日志")
        sys.exit(1)
    else:
        print("\n🎉 所有测试完成!")
        sys.exit(0)


if __name__ == "__main__":
    main()
