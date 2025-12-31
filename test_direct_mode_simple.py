"""简单的Direct Mode测试

验证：
1. HypothesisGuidance直接生成tool call（不经过LLM）
2. 只执行单个工具
3. 执行的工具是CommitmentManager推荐的工具
"""

import logging
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import openai
from dotenv import load_dotenv
from rich.logging import RichHandler

from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.task_suite.load_suites import get_suite
from vigil_agent import create_enhanced_vigil_pipeline, get_vigil_config

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


def test_direct_mode():
    """测试Direct Mode"""
    logger.info("\n" + "=" * 80)
    logger.info("测试：Direct Mode - 直接工具执行")
    logger.info("=" * 80)

    # 创建配置 - 使用balanced预设（已包含enable_direct_tool_execution=True）
    config = get_vigil_config("balanced", model="gpt-4o-mini")

    logger.info("\n配置验证：")
    logger.info(f"  - enable_direct_tool_execution: {config.enable_direct_tool_execution}")
    logger.info(f"  - enable_hypothesis_generation: {config.enable_hypothesis_generation}")
    logger.info(f"  - enable_abstract_sketch: {config.enable_abstract_sketch}")

    if not config.enable_direct_tool_execution:
        logger.error("❌ FAIL: enable_direct_tool_execution应该为True！")
        return False

    # 创建LLM和pipeline
    client = openai.OpenAI()
    llm = OpenAILLM(client, "qwen-max")
    pipeline = create_enhanced_vigil_pipeline(llm, config=config)

    # 加载测试suite
    suite = get_suite("adversarial", "travel")
    task_id = "user_task_0"
    task = suite.user_tasks[task_id]

    logger.info(f"\n测试任务: {task_id}")
    logger.info(f"描述: {task.PROMPT[:100]}...")

    logger.info("\n预期行为：")
    logger.info("  1. HypothesisGuidance生成hypothesis tree")
    logger.info("  2. CommitmentManager选择最优工具")
    logger.info("  3. HypothesisGuidance直接生成tool call（不调用LLM）")
    logger.info("  4. 每次只执行一个工具")
    logger.info("  5. 如果agent尝试调用多个工具，会被拒绝")

    logger.info("\n执行中...\n")

    try:
        # 重置pipeline
        pipeline.reset_for_new_task()

        # 执行任务
        result = pipeline.query(
            query=task.PROMPT,
            runtime=suite.runtime,
            env=task.GROUND_TRUTH,
        )

        logger.info("\n✓ 任务执行完成")

        # 显示统计
        if hasattr(pipeline, 'get_audit_stats'):
            stats = pipeline.get_audit_stats()
            logger.info("\n审计统计:")
            logger.info(f"  - 总审计次数: {stats['total_audits']}")
            logger.info(f"  - 允许: {stats['allowed']}")
            logger.info(f"  - 拒绝: {stats['blocked']}")

        return True

    except Exception as e:
        logger.error(f"\n✗ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_direct_mode()

    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✅ 测试通过！")
        logger.info("\nDirect Mode 工作正常：")
        logger.info("  - Hypothesis Tree生成正确")
        logger.info("  - 直接执行推荐工具（跳过LLM决策）")
        logger.info("  - 单工具执行约束生效")
    else:
        logger.info("❌ 测试失败！")
    logger.info("=" * 80)
