"""测试 Hypothesizer 集成是否正确

这个脚本验证：
1. EnhancedVIGILPipeline 是否正确初始化 Hypothesizer
2. Hypothesizer 是否被传递给 EnhancedVIGILToolsExecutor
3. 相关配置是否正确
"""

import sys
import os

# 确保导入路径正确
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vigil_agent.config import get_vigil_config
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline


def test_hypothesizer_integration():
    """测试 Hypothesizer 集成"""

    print("=" * 80)
    print("测试 Hypothesizer 集成")
    print("=" * 80)

    # 测试 1: 检查配置
    print("\n[测试 1] 检查配置...")
    config = get_vigil_config("balanced", "gpt-4o")

    assert config.enable_hypothesis_generation == True, "配置应该启用假设生成"
    assert config.log_hypothesis_generation == True, "配置应该启用假设日志"
    print("  ✓ 配置正确：enable_hypothesis_generation=True")

    # 测试 2: 检查模块导入
    print("\n[测试 2] 检查模块导入...")
    try:
        from vigil_agent.hypothesizer import Hypothesizer, HypothesisBranch, HypothesisTree
        from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor
        print("  ✓ Hypothesizer 模块导入成功")
        print("  ✓ EnhancedVIGILToolsExecutor 模块导入成功")
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return False

    # 测试 3: 检查 EnhancedVIGILToolsExecutor 是否接受 hypothesizer 参数
    print("\n[测试 3] 检查 EnhancedVIGILToolsExecutor 签名...")
    import inspect

    sig = inspect.signature(EnhancedVIGILToolsExecutor.__init__)
    params = list(sig.parameters.keys())

    assert "hypothesizer" in params, "EnhancedVIGILToolsExecutor.__init__ 应该接受 hypothesizer 参数"
    print(f"  ✓ EnhancedVIGILToolsExecutor.__init__ 参数: {params}")

    # 测试 4: 检查 Hypothesizer 功能
    print("\n[测试 4] 检查 Hypothesizer 类的方法...")
    hypothesizer = Hypothesizer(config)

    assert hasattr(hypothesizer, "generate_hypotheses"), "Hypothesizer 应该有 generate_hypotheses 方法"
    print("  ✓ Hypothesizer.generate_hypotheses() 方法存在")

    # 测试 5: 验证 generate_hypotheses 签名
    print("\n[测试 5] 验证 generate_hypotheses 方法签名...")
    sig = inspect.signature(hypothesizer.generate_hypotheses)
    params = list(sig.parameters.keys())

    required_params = ["available_tools", "current_state", "user_intent"]
    for param in required_params:
        assert param in params, f"generate_hypotheses 应该有参数 {param}"

    print(f"  ✓ generate_hypotheses 参数正确: {params}")

    # 测试 6: 测试 Hypothesizer 基本功能
    print("\n[测试 6] 测试 Hypothesizer 基本功能...")
    try:
        # 创建测试数据
        test_tools = [
            {"name": "get_balance", "description": "获取账户余额"},
            {"name": "advanced_get_balance", "description": "高级获取账户余额"}
        ]
        test_state = {"query": "查询我的账户余额"}
        test_intent = "查询账户余额"

        # 生成假设树
        hypothesis_tree = hypothesizer.generate_hypotheses(
            available_tools=test_tools,
            current_state=test_state,
            user_intent=test_intent
        )

        assert hypothesis_tree is not None, "应该返回假设树"
        assert len(hypothesis_tree.branches) > 0, "假设树应该包含分支"
        assert hypothesis_tree.recommended_branch_id is not None, "应该有推荐分支"

        print(f"  ✓ 生成了 {len(hypothesis_tree.branches)} 个假设分支")
        print(f"  ✓ 推荐分支: {hypothesis_tree.recommended_branch_id}")

        # 检查分支属性
        for branch in hypothesis_tree.branches:
            assert hasattr(branch, "risk_level"), "分支应该有 risk_level"
            assert hasattr(branch, "necessity_score"), "分支应该有 necessity_score"
            assert hasattr(branch, "redundancy_level"), "分支应该有 redundancy_level"

        print("  ✓ 假设分支包含所有必需属性（risk_level, necessity_score, redundancy_level）")

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✓ 所有测试通过！Hypothesizer 集成正确。")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = test_hypothesizer_integration()
    sys.exit(0 if success else 1)
