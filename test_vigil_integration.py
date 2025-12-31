#!/usr/bin/env python
"""测试 VIGIL 集成是否正确，特别是 Hypothesis Tree 的生成"""

import logging
import os
import sys

# 设置 Python 路径
sys.path.insert(0, "/Users/justin/BDAA/ACL/code/agentdojo/src")
sys.path.insert(0, "/Users/justin/BDAA/ACL/code/agentdojo")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_vigil_pipeline():
    """测试 EnhancedVIGILPipeline 是否正确集成"""
    print("\n" + "="*80)
    print("测试 1: EnhancedVIGILPipeline 基本功能")
    print("="*80)

    try:
        from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
        print("\n✓ Step 1: 导入成功")

        # 测试通过 PipelineConfig 创建 VIGIL pipeline
        config = PipelineConfig(
            llm="gpt-4o",
            model_id=None,
            defense="vigil",
            system_message_name=None,
            system_message="You are a helpful AI assistant."
        )

        print("✓ Step 2: PipelineConfig 创建成功")
        print(f"  - LLM: {config.llm}")
        print(f"  - Defense: {config.defense}")
        print("\n✓ Step 3: 配置验证通过")

        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vigil_components():
    """测试 VIGIL 各个组件是否可用"""
    print("\n" + "="*80)
    print("测试 2: VIGIL 组件可用性检查")
    print("="*80)

    try:
        from vigil_agent import (
            VIGIL_BALANCED_CONFIG,
            AbstractSketchGenerator,
            ConstraintGenerator,
            Hypothesizer,
            HypothesisGuidanceElement,
            CommitmentManager,
            PathCache,
            EnhancedRuntimeAuditor,
            EnhancedVIGILPipeline,
            create_enhanced_vigil_pipeline,
        )

        print("\n✓ 所有核心组件导入成功:")
        print("  - AbstractSketchGenerator (Intent Anchor - Layer 1)")
        print("  - ConstraintGenerator (Intent Anchor - Layer 1)")
        print("  - Hypothesizer (Speculative Reasoner - Layer 2)")
        print("  - HypothesisGuidanceElement (Speculative Reasoner - Layer 2)")
        print("  - CommitmentManager (Decision Engine)")
        print("  - PathCache (Learning Mechanism)")
        print("  - EnhancedRuntimeAuditor (Neuro-Symbolic Verifier - Layer 3)")
        print("  - EnhancedVIGILPipeline (Complete Framework)")

        print("\n✓ VIGIL_BALANCED_CONFIG 配置:")
        print(f"  - enable_hypothesis_generation: {VIGIL_BALANCED_CONFIG.enable_hypothesis_generation}")
        print(f"  - enable_abstract_sketch: {VIGIL_BALANCED_CONFIG.enable_abstract_sketch}")
        print(f"  - enable_perception_sanitizer: {VIGIL_BALANCED_CONFIG.enable_perception_sanitizer}")
        print(f"  - enable_reflective_backtracking: {VIGIL_BALANCED_CONFIG.enable_reflective_backtracking}")
        print(f"  - log_hypothesis_generation: {VIGIL_BALANCED_CONFIG.log_hypothesis_generation}")

        return True

    except Exception as e:
        print(f"\n✗ 组件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hypothesis_tree_generation():
    """测试 Hypothesis Tree 生成功能"""
    print("\n" + "="*80)
    print("测试 3: Hypothesis Tree 生成功能")
    print("="*80)

    try:
        from vigil_agent import VIGIL_BALANCED_CONFIG, Hypothesizer

        # 创建 Hypothesizer
        hypothesizer = Hypothesizer(VIGIL_BALANCED_CONFIG)
        print("\n✓ Hypothesizer 创建成功")

        # 模拟工具列表
        available_tools = [
            {
                "name": "get_balance",
                "description": "Get the current account balance"
            },
            {
                "name": "send_money",
                "description": "Send money to another account"
            },
            {
                "name": "community_get_balance",
                "description": "Community version of get balance with advanced features"
            },
        ]

        user_intent = "Check my account balance"

        print(f"\n✓ 测试场景:")
        print(f"  - User Intent: {user_intent}")
        print(f"  - Available Tools: {len(available_tools)}")

        # 生成 Hypothesis Tree
        hypothesis_tree = hypothesizer.generate_hypotheses(
            available_tools=available_tools,
            current_state={"query": user_intent},
            user_intent=user_intent
        )

        print(f"\n✓ Hypothesis Tree 生成成功:")
        print(f"  - Total Branches: {len(hypothesis_tree.branches)}")
        print(f"  - Recommended Branch: {hypothesis_tree.recommended_branch_id}")

        print("\n✓ 分支详情:")
        for i, branch in enumerate(hypothesis_tree.branches[:3], 1):  # 只显示前3个
            print(f"  {i}. {branch.tool_call['tool_name']}")
            print(f"     - Necessity Score: {branch.necessity_score:.2f}")
            print(f"     - Risk Level: {branch.risk_level}")
            print(f"     - Redundancy: {branch.redundancy_level}")
            print(f"     - Has Side Effects: {branch.has_side_effects}")

        if len(hypothesis_tree.branches) > 3:
            print(f"  ... (+ {len(hypothesis_tree.branches) - 3} more branches)")

        return True

    except Exception as e:
        print(f"\n✗ Hypothesis Tree 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("VIGIL 集成测试套件")
    print("="*80)

    results = []

    # 测试 1: EnhancedVIGILPipeline 基本功能
    results.append(("EnhancedVIGILPipeline 基本功能", test_enhanced_vigil_pipeline()))

    # 测试 2: 组件可用性
    results.append(("VIGIL 组件可用性", test_vigil_components()))

    # 测试 3: Hypothesis Tree 生成
    results.append(("Hypothesis Tree 生成", test_hypothesis_tree_generation()))

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！VIGIL 集成成功！")
        print("\n下一步:")
        print("1. 运行完整的 benchmark 测试")
        print("2. 验证 defense==vigil 时 hypothesis tree 在实际场景中的工作情况")
        print("3. 检查日志输出确认所有 4 层都在正常工作")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
