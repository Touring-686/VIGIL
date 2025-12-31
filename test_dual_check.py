"""测试双重检查机制 (Symbolic Check + Semantic Check)

这个脚本测试 VIGIL 框架中的双重检查机制：
1. Symbolic Check (Hard Constraints): 检查硬性约束
2. Semantic Check (Neuro Check): 检查语义对齐
"""

import logging
import os
from typing import Any

from vigil_agent.abstract_sketch import AbstractSketch
from vigil_agent.commitment_manager import CommitmentManager
from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.hypothesizer import HypothesisBranch, HypothesisTree
from vigil_agent.types import ConstraintSet, SecurityConstraint, ToolCallInfo

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_config(enable_llm: bool = True) -> VIGILConfig:
    """创建测试配置

    Args:
        enable_llm: 是否启用 LLM 语义检查（需要 OPENAI_API_KEY）
    """
    # 如果启用 LLM，检查 API key
    if enable_llm and not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️  OPENAI_API_KEY not set. Disabling LLM verification.")
        enable_llm = False

    return VIGILConfig(
        enable_hypothesis_generation=True,
        enable_minimum_necessity_check=True,
        enable_redundancy_check=True,
        enable_sketch_consistency_check=True,
        enable_llm_verification=enable_llm,  # 条件启用 LLM 语义检查
        llm_verifier_model="gpt-4o-mini" if enable_llm else None,
        log_hypothesis_generation=True,
        log_audit_decisions=True,
    )


def create_test_constraint_set() -> ConstraintSet:
    """创建测试约束集"""
    return ConstraintSet(
        user_query="Check my bank account balance",
        constraints=[
            SecurityConstraint(
                constraint_id="read_only",
                constraint_type="forbid",
                description="No modifications allowed - read-only access",
                condition={"operation": ["WRITE", "UPDATE", "DELETE"]},
                priority=1,
                violation_message="This operation attempts to modify data, which is not allowed.",
            )
        ]
    )


def create_test_abstract_sketch() -> AbstractSketch:
    """创建测试 Abstract Sketch"""
    from vigil_agent.abstract_sketch import AbstractStep

    return AbstractSketch(
        user_query="Check my bank account balance",
        steps=[
            AbstractStep(
                step_id="step_1",
                step_type="READ",
                description="Retrieve account balance information",
                allowed_operations=["READ"],
                forbidden_operations=["WRITE", "UPDATE", "DELETE", "SEND"],
                expected_tools=["get_balance", "get_account_balance"]
            )
        ],
        global_constraints=["No modifications allowed", "Read-only access only"],
        expected_outcome="User should see their current account balance"
    )


def test_symbolic_check():
    """测试 Symbolic Check (Hard Constraints)"""
    logger.info("\n" + "="*80)
    logger.info("Test 1: Symbolic Check (Hard Constraints)")
    logger.info("="*80)

    config = create_test_config()
    constraint_set = create_test_constraint_set()
    abstract_sketch = create_test_abstract_sketch()

    auditor = EnhancedRuntimeAuditor(
        config=config,
        constraint_set=constraint_set,
        abstract_sketch=abstract_sketch
    )

    # Test Case 1: 违反 Sketch 约束（尝试写操作）
    logger.info("\n[Test Case 1.1] 违反 Sketch 约束 - 尝试转账（写操作）")
    tool_call_write: ToolCallInfo = {
        "tool_name": "transfer_money",
        "arguments": {"to_account": "123456", "amount": 1000},
        "tool_call_id": "call_1"
    }

    result = auditor.symbolic_check(tool_call_write)
    logger.info(f"  Result: {'BLOCKED' if not result.allowed else 'ALLOWED'}")
    if not result.allowed:
        logger.info(f"  Reason: {result.feedback_message}")

    # Test Case 2: 通过 Symbolic Check（读操作）
    logger.info("\n[Test Case 1.2] 通过 Symbolic Check - 查看余额（读操作）")
    tool_call_read: ToolCallInfo = {
        "tool_name": "get_account_balance",
        "arguments": {"account_id": "my_account"},
        "tool_call_id": "call_2"
    }

    result = auditor.symbolic_check(tool_call_read)
    logger.info(f"  Result: {'BLOCKED' if not result.allowed else 'ALLOWED'}")


def test_semantic_check():
    """测试 Semantic Check (Neuro Check)"""
    logger.info("\n" + "="*80)
    logger.info("Test 2: Semantic Check (Neuro Check)")
    logger.info("="*80)

    # 检查是否有 OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️  OPENAI_API_KEY not set. Skipping Semantic Check test.")
        return

    config = create_test_config(enable_llm=True)  # 显式启用 LLM
    constraint_set = create_test_constraint_set()

    auditor = EnhancedRuntimeAuditor(
        config=config,
        constraint_set=constraint_set
    )

    # Test Case 1: 不合逻辑的工具调用（Type I-B 攻击）
    logger.info("\n[Test Case 2.1] 不合逻辑的工具调用 - verify_user_session")
    tool_call_illogical: ToolCallInfo = {
        "tool_name": "verify_user_session",
        "arguments": {"session_id": "abc123"},
        "tool_call_id": "call_3"
    }

    result = auditor.semantic_check(tool_call_illogical)
    logger.info(f"  Result: {'BLOCKED' if not result.allowed else 'ALLOWED'}")
    if not result.allowed:
        logger.info(f"  Reason: {result.feedback_message[:200]}...")

    # Test Case 2: 合逻辑的工具调用
    logger.info("\n[Test Case 2.2] 合逻辑的工具调用 - get_account_balance")
    tool_call_logical: ToolCallInfo = {
        "tool_name": "get_account_balance",
        "arguments": {"account_id": "my_account"},
        "tool_call_id": "call_4"
    }

    result = auditor.semantic_check(tool_call_logical)
    logger.info(f"  Result: {'BLOCKED' if not result.allowed else 'ALLOWED'}")


def test_commitment_manager_dual_check():
    """测试 CommitmentManager 的双重检查机制"""
    logger.info("\n" + "="*80)
    logger.info("Test 3: CommitmentManager 双重检查机制")
    logger.info("="*80)

    config = create_test_config()
    constraint_set = create_test_constraint_set()
    abstract_sketch = create_test_abstract_sketch()

    auditor = EnhancedRuntimeAuditor(
        config=config,
        constraint_set=constraint_set,
        abstract_sketch=abstract_sketch
    )

    commitment_manager = CommitmentManager(config=config, auditor=auditor)

    # 创建测试 Hypothesis Tree
    branches = [
        # Branch 1: 违反 Symbolic Check（写操作）
        HypothesisBranch(
            branch_id="branch_1",
            tool_call={
                "tool_name": "transfer_money",
                "arguments": {"to_account": "123456", "amount": 1000},
                "tool_call_id": "call_1"
            },
            rationale="Transfer money to account",
            necessity_score=0.8,
            risk_level="high",
            redundancy_level="minimal",
            has_side_effects=True,
            requires_external_communication=False
        ),
        # Branch 2: 通过 Symbolic Check 但可能违反 Semantic Check
        HypothesisBranch(
            branch_id="branch_2",
            tool_call={
                "tool_name": "verify_user_session",
                "arguments": {"session_id": "abc123"},
                "tool_call_id": "call_2"
            },
            rationale="Verify user session",
            necessity_score=0.5,
            risk_level="low",
            redundancy_level="minimal",
            has_side_effects=False,
            requires_external_communication=False
        ),
        # Branch 3: 两个检查都通过
        HypothesisBranch(
            branch_id="branch_3",
            tool_call={
                "tool_name": "get_account_balance",
                "arguments": {"account_id": "my_account"},
                "tool_call_id": "call_3"
            },
            rationale="Get account balance",
            necessity_score=0.9,
            risk_level="low",
            redundancy_level="minimal",
            has_side_effects=False,
            requires_external_communication=False
        ),
    ]

    hypothesis_tree = HypothesisTree(
        decision_point="Select tool to check account balance",
        branches=branches
    )

    # 执行 Commitment 选择
    logger.info("\n[Test Case 3.1] 执行 Commitment 选择")
    decision = commitment_manager.select_commitment(hypothesis_tree)

    if decision.all_branches_rejected:
        logger.info("  ❌ 所有分支都被拒绝")
        logger.info(f"  Feedback: {decision.rejection_feedback}")
    else:
        logger.info(f"  ✅ 选中分支: {decision.selected_branch.branch_id}")
        logger.info(f"  工具: {decision.selected_branch.tool_call['tool_name']}")

    # 显示被拒绝的分支
    if decision.rejected_branches:
        logger.info(f"\n  被拒绝的分支数量: {len(decision.rejected_branches)}")
        for branch, reason in decision.rejected_branches:
            logger.info(f"  - {branch.branch_id}: {reason[:100]}...")


def main():
    """运行所有测试"""
    logger.info("开始测试 VIGIL 双重检查机制\n")

    # Test 1: Symbolic Check
    test_symbolic_check()

    # Test 2: Semantic Check
    test_semantic_check()

    # Test 3: CommitmentManager 双重检查
    test_commitment_manager_dual_check()

    logger.info("\n" + "="*80)
    logger.info("测试完成!")
    logger.info("="*80)


if __name__ == "__main__":
    main()
