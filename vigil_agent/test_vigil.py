"""
VIGIL Framework - 快速测试脚本

用于验证VIGIL框架是否正确安装和配置。
"""

import sys


def test_imports():
    """测试所有导入是否正常"""
    print("Testing imports...")

    try:
        from vigil_agent import (
            VIGIL_BALANCED_CONFIG,
            VIGIL_FAST_CONFIG,
            VIGIL_STRICT_CONFIG,
            VIGILConfig,
            ConstraintGenerator,
            RuntimeAuditor,
            create_vigil_pipeline,
        )

        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_config_creation():
    """测试配置创建"""
    print("\nTesting config creation...")

    try:
        from vigil_agent import VIGILConfig

        # 测试默认配置
        config = VIGILConfig()
        assert config.auditor_mode in ["strict", "permissive", "hybrid"]

        # 测试自定义配置
        custom_config = VIGILConfig(
            auditor_mode="strict", max_backtracking_attempts=5, enable_reflective_backtracking=True
        )
        assert custom_config.auditor_mode == "strict"
        assert custom_config.max_backtracking_attempts == 5

        print("✓ Config creation successful")
        return True
    except Exception as e:
        print(f"✗ Config creation failed: {e}")
        return False


def test_constraint_generator():
    """测试约束生成器"""
    print("\nTesting constraint generator...")

    try:
        from vigil_agent import ConstraintGenerator, VIGILConfig

        config = VIGILConfig(constraint_generator_model="gpt-4o-mini")  # 使用较小的模型测试
        generator = ConstraintGenerator(config)

        # 注意：这个测试需要OpenAI API key
        # 如果没有key，会失败
        print("  (Note: This test requires OpenAI API key)")

        constraint_set = generator.generate_constraints("Please show me my account balance")

        print(f"✓ Generated {len(constraint_set.constraints)} constraints")
        return True
    except Exception as e:
        print(f"✗ Constraint generation failed: {e}")
        print("  (This is expected if you don't have OpenAI API key configured)")
        return False


def test_runtime_auditor():
    """测试运行时审计器"""
    print("\nTesting runtime auditor...")

    try:
        from vigil_agent import RuntimeAuditor, VIGILConfig
        from vigil_agent.types import ConstraintSet, SecurityConstraint, ToolCallInfo

        # 创建一个简单的约束集
        constraint_set = ConstraintSet(
            user_query="Test query",
            constraints=[
                SecurityConstraint(
                    constraint_id="test_forbid",
                    constraint_type="forbid",
                    description="Forbid delete operations",
                    condition={"operation": "DELETE"},
                    priority=1,
                    violation_message="Delete operations are forbidden",
                )
            ],
        )

        config = VIGILConfig()
        auditor = RuntimeAuditor(config, constraint_set)

        # 测试审计
        tool_call: ToolCallInfo = {
            "tool_name": "delete_account",
            "arguments": {"account_id": "123"},
            "tool_call_id": "call_1",
        }

        result = auditor.audit_tool_call(tool_call)

        print(f"✓ Audit result: {'Allowed' if result.allowed else 'Blocked'}")
        print(f"  Stats: {auditor.get_stats()}")
        return True
    except Exception as e:
        print(f"✗ Runtime auditor test failed: {e}")
        return False


def test_pipeline_creation():
    """测试pipeline创建"""
    print("\nTesting pipeline creation...")

    try:
        from vigil_agent import VIGIL_BALANCED_CONFIG, create_vigil_pipeline

        # 创建一个mock LLM（用于测试）
        class MockLLM:
            name = "mock-llm"

            def query(self, query, runtime, env, messages, extra_args):
                return query, runtime, env, messages, extra_args

        mock_llm = MockLLM()
        pipeline = create_vigil_pipeline(mock_llm, config=VIGIL_BALANCED_CONFIG)

        print(f"✓ Pipeline created: {pipeline.name}")
        return True
    except Exception as e:
        print(f"✗ Pipeline creation failed: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 80)
    print("VIGIL Framework - Quick Test")
    print("=" * 80)

    tests = [
        test_imports,
        test_config_creation,
        test_runtime_auditor,
        test_pipeline_creation,
        test_constraint_generator,  # 放在最后因为需要API key
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)

    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
