"""测试ToolDocstringSanitizer的持久化缓存功能

验证：
1. 首次运行会清洗工具并保存到磁盘
2. 第二次运行会直接从磁盘加载，无需重新清洗
3. 可以手动清除缓存
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from rich.logging import RichHandler

from agentdojo.task_suite.load_suites import get_suite
from vigil_agent.config import VIGILConfig
from vigil_agent.perception_sanitizer import PerceptionSanitizer
from vigil_agent.tool_sanitizer_element import ToolDocstringSanitizer

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
    handlers=[RichHandler(show_path=False, markup=True)],
)

logger = logging.getLogger(__name__)


def test_sanitizer_cache():
    """测试持久化缓存功能"""
    logger.info("\n" + "=" * 80)
    logger.info("测试：ToolDocstringSanitizer 持久化缓存")
    logger.info("=" * 80)

    # 创建配置和sanitizer
    config = VIGILConfig(
        enable_perception_sanitizer=True,
        log_sanitizer_actions=True,
    )

    perception_sanitizer = PerceptionSanitizer(config)

    # 创建ToolDocstringSanitizer（使用自定义缓存目录）
    cache_dir = Path("./test_cache/sanitized_tools")
    tool_sanitizer = ToolDocstringSanitizer(
        config=config,
        sanitizer=perception_sanitizer,
        cache_dir=cache_dir,
    )

    logger.info(f"\n缓存目录: {cache_dir}")

    # 加载测试suite
    suite = get_suite("adversarial", "travel")
    logger.info(f"加载的suite: {suite.name}")
    logger.info(f"工具数量: {len(suite.runtime.functions)}")

    # ===== 第一次运行：清洗并保存 =====
    logger.info("\n" + "=" * 80)
    logger.info("第一次运行：清洗工具并保存到磁盘")
    logger.info("=" * 80)

    query1, runtime1, env1, messages1, extra_args1 = tool_sanitizer.query(
        query="test query",
        runtime=suite.runtime,
        env=suite.user_tasks["user_task_0"].GROUND_TRUTH,
        messages=[],
        extra_args={},
    )

    logger.info(f"\n✓ 第一次运行完成")
    logger.info(f"  - 清洗后的runtime有 {len(runtime1.functions)} 个工具")

    # ===== 第二次运行：从磁盘加载 =====
    logger.info("\n" + "=" * 80)
    logger.info("第二次运行：从磁盘缓存加载")
    logger.info("=" * 80)

    # 创建新的sanitizer实例（模拟重启）
    tool_sanitizer2 = ToolDocstringSanitizer(
        config=config,
        sanitizer=perception_sanitizer,
        cache_dir=cache_dir,
    )

    query2, runtime2, env2, messages2, extra_args2 = tool_sanitizer2.query(
        query="test query",
        runtime=suite.runtime,
        env=suite.user_tasks["user_task_0"].GROUND_TRUTH,
        messages=[],
        extra_args={},
    )

    logger.info(f"\n✓ 第二次运行完成（应该从缓存加载）")
    logger.info(f"  - 加载的runtime有 {len(runtime2.functions)} 个工具")

    # ===== 检查缓存文件 =====
    logger.info("\n" + "=" * 80)
    logger.info("检查缓存文件")
    logger.info("=" * 80)

    cache_files = list(cache_dir.glob("*"))
    logger.info(f"\n缓存文件数量: {len(cache_files)}")
    for f in cache_files:
        logger.info(f"  - {f.name} ({f.stat().st_size} bytes)")

    # ===== 清除缓存（可选）=====
    logger.info("\n" + "=" * 80)
    logger.info("如何清除缓存")
    logger.info("=" * 80)

    logger.info("\n方法1: 清除内存缓存（保留磁盘缓存）")
    logger.info("  tool_sanitizer.clear_cache()")

    logger.info("\n方法2: 清除磁盘缓存（删除所有缓存文件）")
    logger.info("  tool_sanitizer.clear_disk_cache()")

    # 取消注释以下行来清除缓存
    # tool_sanitizer.clear_disk_cache()

    logger.info("\n" + "=" * 80)
    logger.info("测试完成！")
    logger.info("=" * 80)
    logger.info("\n总结：")
    logger.info("1. 首次运行会清洗工具并保存到磁盘（速度较慢，需要调用LLM）")
    logger.info("2. 后续运行直接从磁盘加载（速度很快，无需调用LLM）")
    logger.info("3. 缓存文件保存在 ./vigil_cache/sanitized_tools/")
    logger.info("4. 可以使用 clear_disk_cache() 清除缓存重新开始")


if __name__ == "__main__":
    test_sanitizer_cache()
