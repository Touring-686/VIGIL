"""测试单工具执行约束

验证VIGIL框架的两个修复：
1. 确保每次只执行一个工具（拒绝多工具调用）
2. 支持REASONING步骤（无需工具调用的推理步骤）
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
from vigil_agent import create_enhanced_vigil_pipeline, VIGILConfig

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


def test_single_tool_constraint():
    """测试单工具执行约束"""
    logger.info("\n" + "=" * 80)
    logger.info("测试1：单工具执行约束")
    logger.info("=" * 80)

    # 创建配置（启用所有VIGIL层）
    config = VIGILConfig(
        # 基本配置
        enable_abstract_sketch=True,
        enable_hypothesis_generation=True,
        enable_direct_tool_execution=False,  # 使用guidance模式（LLM仍有决策权）

        # 日志配置
        log_hypothesis_generation=True,
        log_sketch_generation=True,

        # 模型配置
        constraint_generator_model="gpt-4o-mini",
        sketch_generator_model="gpt-4o-mini",
        hypothesizer_model="gpt-4o-mini",
    )

    # 创建LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "qwen-max")

    # 创建pipeline
    pipeline = create_enhanced_vigil_pipeline(llm, config=config)

    logger.info("\n配置：")
    logger.info(f"  - Abstract Sketch: {config.enable_abstract_sketch}")
    logger.info(f"  - Hypothesis Generation: {config.enable_hypothesis_generation}")
    logger.info(f"  - Direct Tool Execution: {config.enable_direct_tool_execution}")
    logger.info(f"  - 单工具执行约束: 已启用（在system message和executor中）")

    logger.info("\n测试场景：")
    logger.info("  - 如果agent尝试同时调用多个工具，应该被拒绝")
    logger.info("  - 每次只能调用一个工具")

    # 加载一个简单的suite进行测试
    suite = get_suite("adversarial", "travel")

    # 选择一个可能触发多工具调用的任务
    task_id = "user_task_0"
    task = suite.user_tasks[task_id]

    logger.info(f"\n测试任务: {task_id}")
    logger.info(f"任务描述: {task.PROMPT}")

    # 执行任务
    try:
        result = pipeline.query(
            query=task.PROMPT,
            runtime=suite.runtime,
            env=task.GROUND_TRUTH,
        )

        logger.info("\n✓ 任务执行完成")
        logger.info("\n审计统计:")
        if hasattr(pipeline, 'get_audit_stats'):
            stats = pipeline.get_audit_stats()
            logger.info(f"  - 总审计次数: {stats['total_audits']}")
            logger.info(f"  - 允许: {stats['allowed']}")
            logger.info(f"  - 拒绝: {stats['blocked']}")

    except Exception as e:
        logger.error(f"\n✗ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()


def test_reasoning_step():
    """测试REASONING步骤支持"""
    logger.info("\n" + "=" * 80)
    logger.info("测试2：REASONING步骤支持")
    logger.info("=" * 80)

    # 创建配置
    config = VIGILConfig(
        enable_abstract_sketch=True,
        enable_hypothesis_generation=True,
        enable_direct_tool_execution=False,

        log_hypothesis_generation=True,
        log_sketch_generation=True,

        constraint_generator_model="gpt-4o-mini",
        sketch_generator_model="gpt-4o-mini",
        hypothesizer_model="gpt-4o-mini",
    )

    # 创建LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "qwen-max")

    # 创建pipeline
    pipeline = create_enhanced_vigil_pipeline(llm, config=config)

    logger.info("\n测试场景：")
    logger.info("  - Abstract Sketch可能包含REASONING步骤")
    logger.info("  - REASONING步骤不需要工具调用，只需要LLM推理")
    logger.info("  - Hypothesizer应该生成__no_tool_call__分支")
    logger.info("  - LLM应该能够直接进行推理而不调用工具")

    # 使用一个需要分析和比较的任务
    suite = get_suite("adversarial", "travel")
    task_id = "user_task_0"
    task = suite.user_tasks[task_id]

    logger.info(f"\n测试任务: {task_id}")
    logger.info(f"任务描述: {task.PROMPT}")
    logger.info("\n注意观察Abstract Sketch是否包含REASONING步骤")

    try:
        result = pipeline.query(
            query=task.PROMPT,
            runtime=suite.runtime,
            env=task.GROUND_TRUTH,
        )

        logger.info("\n✓ 任务执行完成")

    except Exception as e:
        logger.error(f"\n✗ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行测试
    test_single_tool_constraint()
    test_reasoning_step()

    logger.info("\n" + "=" * 80)
    logger.info("测试完成！")
    logger.info("=" * 80)
    logger.info("\n总结：")
    logger.info("1. 单工具执行约束：")
    logger.info("   - System message中添加了明确约束")
    logger.info("   - EnhancedVIGILToolsExecutor会检测并拒绝多工具调用")
    logger.info("\n2. REASONING步骤支持：")
    logger.info("   - Abstract Sketch支持REASONING步骤类型")
    logger.info("   - Hypothesizer为REASONING步骤生成特殊分支")
    logger.info("   - HypothesisGuidance生成推理guidance而不是工具调用")
    logger.info("   - LLM可以进行推理而不调用工具")
