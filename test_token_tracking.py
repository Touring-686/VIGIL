"""测试 Token 统计功能

验证 VIGIL 框架中4个模块的 token 消耗统计：
1. Intent Anchor (Abstract Sketch Generator)
2. Speculative Reasoner (Hypothesizer)
3. Neuro-Symbolic Verifier (Semantic Check)
4. Path Caching (暂无LLM调用)

测试场景：
- 模拟一个完整的任务执行流程
- 记录各模块的 token 使用情况
- 保存统计结果到文件
"""

import logging
import os
import sys

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from vigil_agent.abstract_sketch import AbstractSketchGenerator, AbstractStep
from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.hypothesizer import Hypothesizer, HypothesisTree
from vigil_agent.token_stats_tracker import TokenStatsTracker, get_global_tracker
from vigil_agent.types import ConstraintSet, SecurityConstraint


def test_token_tracking():
    """测试 token 统计功能"""

    # 检查 API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY not set. Please set it to run this test.")
        sys.exit(1)

    logger.info("="*80)
    logger.info("开始测试 Token 统计功能")
    logger.info("="*80)

    # 创建 token tracker
    tracker = get_global_tracker(output_dir="./test_token_stats")

    # 创建配置
    config = VIGILConfig(
        enable_abstract_sketch=True,
        sketch_generator_model="gpt-4o-mini",
        enable_hypothesis_generation=True,
        hypothesizer_model="gpt-4o-mini",
        enable_llm_verification=True,
        llm_verifier_model="gpt-4o-mini",
        log_hypothesis_generation=True,
        log_audit_decisions=True,
    )

    # 开始追踪任务
    task_id = "test_task_001"
    tracker.start_task(task_id)
    logger.info(f"\n[Task] Started tracking task: {task_id}")

    # ===== Test 1: Intent Anchor (Abstract Sketch Generator) =====
    logger.info("\n" + "="*80)
    logger.info("Test 1: Intent Anchor - Abstract Sketch Generator")
    logger.info("="*80)

    user_query = "Book a hotel in Paris for 2 nights"
    sketch_generator = AbstractSketchGenerator(config, token_tracker=tracker)

    try:
        sketch = sketch_generator.generate_sketch(user_query)
        logger.info(f"✅ Generated sketch with {len(sketch.steps)} steps")
        logger.info(f"   Global constraints: {sketch.global_constraints}")
    except Exception as e:
        logger.error(f"❌ Failed to generate sketch: {e}")

    # 查看当前统计
    task_stats = tracker.get_task_stats(task_id)
    if task_stats:
        intent_anchor_tokens = task_stats.get_module_tokens(TokenStatsTracker.MODULE_INTENT_ANCHOR)
        logger.info(f"   Intent Anchor tokens used: {intent_anchor_tokens}")

    # ===== Test 2: Speculative Reasoner (Hypothesizer) =====
    logger.info("\n" + "="*80)
    logger.info("Test 2: Speculative Reasoner - Hypothesizer")
    logger.info("="*80)

    import openai
    openai_client = openai.OpenAI()
    hypothesizer = Hypothesizer(config, openai_client, token_tracker=tracker)

    # 模拟候选工具
    candidate_tools = [
        {
            "name": "search_hotels",
            "description": "Search for available hotels in a city",
            "parameters": {
                "city": {"type": "string"},
                "check_in": {"type": "string"},
                "check_out": {"type": "string"}
            }
        },
        {
            "name": "book_hotel",
            "description": "Book a hotel room",
            "parameters": {
                "hotel_id": {"type": "string"},
                "nights": {"type": "integer"}
            }
        },
        {
            "name": "get_weather",
            "description": "Get weather information",
            "parameters": {
                "city": {"type": "string"}
            }
        }
    ]

    try:
        # 生成 hypothesis tree
        hypothesis_tree = hypothesizer.generate_tree(
            user_query=user_query,
            candidate_tools=candidate_tools,
            current_step=AbstractStep(
                step_id="step_1",
                step_type="SEARCH",
                description="Search for hotels",
                allowed_operations=["READ"],
                forbidden_operations=["WRITE", "DELETE"]
            ),
            conversation_history=[]
        )

        logger.info(f"✅ Generated hypothesis tree with {len(hypothesis_tree.branches)} branches")
        for branch in hypothesis_tree.branches[:3]:
            logger.info(f"   - {branch.tool_call['tool_name']} (necessity: {branch.necessity_score:.2f})")
    except Exception as e:
        logger.error(f"❌ Failed to generate hypothesis tree: {e}")

    # 查看当前统计
    task_stats = tracker.get_task_stats(task_id)
    if task_stats:
        reasoner_tokens = task_stats.get_module_tokens(TokenStatsTracker.MODULE_SPECULATIVE_REASONER)
        logger.info(f"   Speculative Reasoner tokens used: {reasoner_tokens}")

    # ===== Test 3: Neuro-Symbolic Verifier (Semantic Check) =====
    logger.info("\n" + "="*80)
    logger.info("Test 3: Neuro-Symbolic Verifier - Semantic Check")
    logger.info("="*80)

    constraint_set = ConstraintSet(
        user_query=user_query,
        constraints=[
            SecurityConstraint(
                constraint_id="read_only",
                constraint_type="forbid",
                description="No modifications allowed during search phase",
                condition={"operation": ["WRITE", "DELETE"]},
                priority=1,
                violation_message="Modification not allowed",
            )
        ]
    )

    auditor = EnhancedRuntimeAuditor(
        config=config,
        constraint_set=constraint_set,
        token_tracker=tracker
    )

    # Test Case 3.1: 合逻辑的工具调用
    logger.info("\n[Test Case 3.1] Logical tool call - search_hotels")
    tool_call_logical = {
        "tool_name": "search_hotels",
        "arguments": {"city": "Paris", "check_in": "2024-01-01", "check_out": "2024-01-03"},
        "tool_call_id": "call_1"
    }

    result = auditor.semantic_check(tool_call_logical)
    logger.info(f"   Result: {'ALLOWED' if result.allowed else 'BLOCKED'}")

    # Test Case 3.2: 不合逻辑的工具调用
    logger.info("\n[Test Case 3.2] Illogical tool call - verify_user_session")
    tool_call_illogical = {
        "tool_name": "verify_user_session",
        "arguments": {"session_id": "abc123"},
        "tool_call_id": "call_2"
    }

    result = auditor.semantic_check(tool_call_illogical)
    logger.info(f"   Result: {'ALLOWED' if result.allowed else 'BLOCKED'}")
    if not result.allowed:
        logger.info(f"   Reason: {result.feedback_message[:100]}...")

    # 查看当前统计
    task_stats = tracker.get_task_stats(task_id)
    if task_stats:
        verifier_tokens = task_stats.get_module_tokens(TokenStatsTracker.MODULE_NEURO_SYMBOLIC_VERIFIER)
        logger.info(f"   Neuro-Symbolic Verifier tokens used: {verifier_tokens}")

    # ===== Test 4: Path Caching =====
    logger.info("\n" + "="*80)
    logger.info("Test 4: Path Caching")
    logger.info("="*80)
    logger.info("   ℹ️  Path Caching does not use LLM, so no tokens consumed")

    # 结束任务追踪
    tracker.end_task(task_id, save=True)

    # ===== 汇总统计 =====
    logger.info("\n" + "="*80)
    logger.info("汇总统计")
    logger.info("="*80)

    task_stats = tracker.get_task_stats(task_id)
    if task_stats:
        logger.info(f"\nTask ID: {task_id}")
        logger.info(f"Total tokens: {task_stats.get_total_tokens()}")
        logger.info("\nModule breakdown:")
        for module, stats in task_stats.module_stats.items():
            logger.info(
                f"  {module}:\n"
                f"    - Total: {stats['total_tokens']} tokens\n"
                f"    - Prompt: {stats['prompt_tokens']} tokens\n"
                f"    - Completion: {stats['completion_tokens']} tokens\n"
                f"    - Calls: {stats['call_count']}"
            )

    # 保存所有统计
    tracker.save_all_stats()

    logger.info("\n" + "="*80)
    logger.info("✅ Token 统计测试完成!")
    logger.info(f"📊 统计文件已保存到: {tracker.output_dir}")
    logger.info("="*80)

    # 显示文件列表
    logger.info("\n生成的文件:")
    for filename in os.listdir(tracker.output_dir):
        filepath = os.path.join(tracker.output_dir, filename)
        size = os.path.getsize(filepath)
        logger.info(f"  - {filename} ({size} bytes)")


if __name__ == "__main__":
    test_token_tracking()
