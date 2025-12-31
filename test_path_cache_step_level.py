"""测试 PathCache 的步骤级别缓存功能

验证 PathCache 能够：
1. 缓存 (user_intent, step_index, tool) 映射
2. 正确检索特定步骤的缓存路径
3. 区分不同步骤的相同工具
4. 支持向后兼容（不带 step_index 的查询）
"""

import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from vigil_agent.config import VIGILConfig
from vigil_agent.path_cache import PathCache


def test_step_level_caching():
    """测试步骤级别的缓存"""

    logger.info("=" * 80)
    logger.info("测试 PathCache 步骤级别缓存功能")
    logger.info("=" * 80)

    # 创建配置和缓存
    config = VIGILConfig()
    cache = PathCache(config)

    # ===== 测试场景 1: 多步骤任务 - 添加缓存 =====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 1: 添加多步骤任务的缓存")
    logger.info("=" * 80)

    user_query = "Pay the bill 'bill-december-2023.txt'"

    # 步骤 0: 读取账单文件
    cache.add_verified_path(
        user_query=user_query,
        tool_name="read_file",
        arguments={"path": "bill-december-2023.txt"},
        outcome="success",
        step_index=0,
        metadata={"step_description": "Read the bill file"}
    )

    # 步骤 1: 验证账单
    cache.add_verified_path(
        user_query=user_query,
        tool_name="get_user_info",
        arguments={},
        outcome="success",
        step_index=1,
        metadata={"step_description": "Verify user information"}
    )

    # 步骤 2: 执行支付
    cache.add_verified_path(
        user_query=user_query,
        tool_name="send_money",
        arguments={"recipient": "utility_company", "amount": 150.00},
        outcome="success",
        step_index=2,
        metadata={"step_description": "Initiate payment"}
    )

    logger.info("✅ 已添加 3 个步骤的缓存路径")

    # ===== 测试场景 2: 检索特定步骤的缓存 =====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 2: 检索特定步骤的缓存")
    logger.info("=" * 80)

    # 检索步骤 0 的路径
    step_0_paths = cache.retrieve_paths(user_query, step_index=0)
    assert len(step_0_paths) == 1, f"Expected 1 path for step 0, got {len(step_0_paths)}"
    assert step_0_paths[0].tool_name == "read_file"
    assert step_0_paths[0].step_index == 0
    logger.info(f"✅ Step 0: Retrieved tool '{step_0_paths[0].tool_name}'")

    # 检索步骤 1 的路径
    step_1_paths = cache.retrieve_paths(user_query, step_index=1)
    assert len(step_1_paths) == 1, f"Expected 1 path for step 1, got {len(step_1_paths)}"
    assert step_1_paths[0].tool_name == "get_user_info"
    assert step_1_paths[0].step_index == 1
    logger.info(f"✅ Step 1: Retrieved tool '{step_1_paths[0].tool_name}'")

    # 检索步骤 2 的路径
    step_2_paths = cache.retrieve_paths(user_query, step_index=2)
    assert len(step_2_paths) == 1, f"Expected 1 path for step 2, got {len(step_2_paths)}"
    assert step_2_paths[0].tool_name == "send_money"
    assert step_2_paths[0].step_index == 2
    logger.info(f"✅ Step 2: Retrieved tool '{step_2_paths[0].tool_name}'")

    # ===== 测试场景 3: 区分不同步骤的相同工具 =====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 3: 区分不同步骤的相同工具")
    logger.info("=" * 80)

    query_2 = "Read my account balance and then read transaction history"

    # 步骤 0: 读取余额（使用 get_balance）
    cache.add_verified_path(
        user_query=query_2,
        tool_name="get_balance",
        arguments={},
        outcome="success",
        step_index=0,
        metadata={"step_description": "Get account balance"}
    )

    # 步骤 1: 读取交易历史（也使用 get_balance 但参数不同）
    cache.add_verified_path(
        user_query=query_2,
        tool_name="get_transactions",
        arguments={"limit": 10},
        outcome="success",
        step_index=1,
        metadata={"step_description": "Get transaction history"}
    )

    # 验证可以正确区分
    step_0_tool = cache.get_recommended_tool(query_2, step_index=0)
    step_1_tool = cache.get_recommended_tool(query_2, step_index=1)

    assert step_0_tool == "get_balance", f"Expected 'get_balance' for step 0, got '{step_0_tool}'"
    assert step_1_tool == "get_transactions", f"Expected 'get_transactions' for step 1, got '{step_1_tool}'"

    logger.info(f"✅ Step 0 tool: {step_0_tool}")
    logger.info(f"✅ Step 1 tool: {step_1_tool}")
    logger.info("✅ Successfully distinguished same query at different steps")

    # ===== 测试场景 4: 向后兼容（不带 step_index）=====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 4: 向后兼容（不带 step_index 的查询）")
    logger.info("=" * 80)

    # 添加一个不带 step_index 的路径
    cache.add_verified_path(
        user_query="Get weather information",
        tool_name="get_weather",
        arguments={"city": "Paris"},
        outcome="success",
        step_index=None,  # 不指定步骤
        metadata={"note": "Simple single-step task"}
    )

    # 不带 step_index 检索
    weather_paths = cache.retrieve_paths("Get weather information")
    assert len(weather_paths) == 1, f"Expected 1 path, got {len(weather_paths)}"
    assert weather_paths[0].tool_name == "get_weather"
    assert weather_paths[0].step_index is None
    logger.info(f"✅ Retrieved tool '{weather_paths[0].tool_name}' without step_index")

    # 推荐工具（不带 step_index）
    recommended = cache.get_recommended_tool("Get weather information")
    assert recommended == "get_weather", f"Expected 'get_weather', got '{recommended}'"
    logger.info(f"✅ Recommended tool: {recommended}")

    # ===== 测试场景 5: 缓存统计 =====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 5: 缓存统计")
    logger.info("=" * 80)

    stats = cache.get_stats()
    logger.info(f"  Total cached paths: {stats['total_cached_paths']}")
    logger.info(f"  Successful paths: {stats['successful_paths']}")
    logger.info(f"  Failed paths: {stats['failed_paths']}")
    logger.info(f"  Total executions: {stats['total_executions']}")
    logger.info(f"  Unique queries: {stats['unique_queries']}")

    assert stats['total_cached_paths'] == 6, f"Expected 6 paths, got {stats['total_cached_paths']}"
    assert stats['successful_paths'] == 6, f"Expected 6 successful paths, got {stats['successful_paths']}"
    logger.info("✅ Cache statistics are correct")

    # ===== 测试场景 6: 导出和导入缓存 =====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 6: 导出和导入缓存")
    logger.info("=" * 80)

    # 导出缓存
    cache_data = cache.export_cache()
    logger.info(f"  Exported {len(cache_data['paths'])} paths")

    # 创建新的缓存并导入
    new_cache = PathCache(config)
    new_cache.import_cache(cache_data)

    # 验证导入成功
    new_stats = new_cache.get_stats()
    assert new_stats['total_cached_paths'] == stats['total_cached_paths']

    # 验证可以检索步骤级别的路径
    imported_step_0 = new_cache.retrieve_paths(user_query, step_index=0)
    assert len(imported_step_0) == 1
    assert imported_step_0[0].tool_name == "read_file"
    assert imported_step_0[0].step_index == 0

    logger.info("✅ Cache export and import successful")
    logger.info(f"✅ Step-level retrieval works after import")

    # ===== 测试场景 7: 执行计数 =====
    logger.info("\n" + "=" * 80)
    logger.info("测试场景 7: 执行计数和推荐")
    logger.info("=" * 80)

    query_3 = "Transfer money to Alice"

    # 添加同一步骤的多个工具调用
    cache.add_verified_path(
        user_query=query_3,
        tool_name="send_money_v1",
        arguments={"recipient": "Alice"},
        outcome="success",
        step_index=0,
    )

    cache.add_verified_path(
        user_query=query_3,
        tool_name="send_money_v2",
        arguments={"recipient": "Alice"},
        outcome="success",
        step_index=0,
    )

    # 再次添加 v2（应该增加计数）
    cache.add_verified_path(
        user_query=query_3,
        tool_name="send_money_v2",
        arguments={"recipient": "Alice"},
        outcome="success",
        step_index=0,
    )

    # 再次添加 v2（再次增加计数）
    cache.add_verified_path(
        user_query=query_3,
        tool_name="send_money_v2",
        arguments={"recipient": "Alice"},
        outcome="success",
        step_index=0,
    )

    # 获取推荐工具（应该是 v2，因为执行次数更多）
    recommended = cache.get_recommended_tool(query_3, step_index=0)
    assert recommended == "send_money_v2", f"Expected 'send_money_v2', got '{recommended}'"

    # 检查执行计数
    paths = cache.retrieve_paths(query_3, step_index=0)
    v2_path = next(p for p in paths if p.tool_name == "send_money_v2")
    assert v2_path.execution_count == 3, f"Expected count 3, got {v2_path.execution_count}"

    logger.info(f"✅ Recommended most-used tool: {recommended} (used {v2_path.execution_count} times)")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 所有测试通过！PathCache 步骤级别缓存功能正常工作")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_step_level_caching()
