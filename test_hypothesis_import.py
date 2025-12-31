"""验证修复后的代码语法和导入

这个脚本验证所有修改的文件可以正常导入，没有语法错误。
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """测试所有组件可以正常导入"""
    print("=" * 80)
    print("测试：验证修复后的代码可以正常导入")
    print("=" * 80)

    try:
        # 测试导入HypothesisGuidanceElement
        print("\n[1] 导入 HypothesisGuidanceElement...")
        from vigil_agent.hypothesis_guidance import HypothesisGuidanceElement
        print("✅ HypothesisGuidanceElement 导入成功")

        # 测试导入修改后的enhanced_executor
        print("\n[2] 导入 Enhanced Executor...")
        from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor, EnhancedVIGILInitQuery
        print("✅ Enhanced Executor 导入成功")

        # 测试导入修改后的enhanced_pipeline
        print("\n[3] 导入 Enhanced Pipeline...")
        from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline, create_enhanced_vigil_pipeline
        print("✅ Enhanced Pipeline 导入成功")

        # 测试从__init__导入
        print("\n[4] 从 vigil_agent 包导入...")
        from vigil_agent import (
            HypothesisGuidanceElement,
            Hypothesizer,
            CommitmentManager,
            EnhancedRuntimeAuditor,
            PathCache,
            create_enhanced_vigil_pipeline,
        )
        print("✅ 所有组件从 vigil_agent 包导入成功")

        # 测试创建实例（不实际运行）
        print("\n[5] 测试创建配置和组件...")
        from vigil_agent.config import VIGILConfig

        config = VIGILConfig(
            enable_hypothesis_generation=True,
            enable_abstract_sketch=True,
            log_hypothesis_generation=True,
        )
        print("✅ VIGILConfig 创建成功")

        # 测试创建Hypothesizer
        hypothesizer = Hypothesizer(config)
        print("✅ Hypothesizer 创建成功")

        # 测试创建EnhancedRuntimeAuditor
        auditor = EnhancedRuntimeAuditor(config)
        print("✅ EnhancedRuntimeAuditor 创建成功")

        # 测试创建CommitmentManager
        commitment_manager = CommitmentManager(config, auditor)
        print("✅ CommitmentManager 创建成功")

        # 测试创建PathCache
        path_cache = PathCache(config)
        print("✅ PathCache 创建成功")

        # 测试创建HypothesisGuidanceElement
        guidance = HypothesisGuidanceElement(
            config=config,
            hypothesizer=hypothesizer,
            commitment_manager=commitment_manager,
            path_cache=path_cache,
        )
        print("✅ HypothesisGuidanceElement 创建成功")

        # 验证guidance element有必要的方法
        assert hasattr(guidance, 'query'), "HypothesisGuidanceElement 缺少 query 方法"
        assert hasattr(guidance, 'reset'), "HypothesisGuidanceElement 缺少 reset 方法"
        print("✅ HypothesisGuidanceElement 有所需的方法")

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)

        print("\n修复摘要:")
        print("1. ✅ 创建了新的 HypothesisGuidanceElement 模块")
        print("2. ✅ 移除了 enhanced_executor.py 中错误位置的 hypothesis 生成")
        print("3. ✅ 在 enhanced_pipeline.py 中集成了 HypothesisGuidanceElement")
        print("4. ✅ 更新了 __init__.py 导出新模块")
        print("5. ✅ 所有模块可以正常导入和实例化")

        print("\n执行流程修复:")
        print("修复前 (错误):")
        print("  LLM决策 → Hypothesis生成 → 事后对比")
        print("\n修复后 (正确):")
        print("  Hypothesis生成 → Verification → Commitment → LLM决策")

        print("\nToolsExecutionLoop 新顺序:")
        print("  1. EnhancedVIGILToolsExecutor - 执行工具调用")
        print("  2. HypothesisGuidanceElement  - 生成下一步的 guidance")
        print("  3. LLM                         - 基于 guidance 做决策")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
