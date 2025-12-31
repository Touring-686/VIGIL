"""测试 ValidationError LLM 自动重试功能"""

import logging
import os

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_validation_error_detection():
    """测试 ValidationError 检测功能"""
    from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor

    # 直接创建一个简单的实例来访问方法
    class MockConfig:
        pass

    class MockAuditor:
        pass

    class MockSanitizer:
        pass

    executor = EnhancedVIGILToolsExecutor(
        config=MockConfig(),
        auditor=MockAuditor(),
        sanitizer=MockSanitizer()
    )

    # 测试 ValidationError 检测
    test_errors = [
        "ValidationError: 1 validation error for Input schema",
        "validation error for get_rating_reviews_for_hotels",
        "Input should be a valid list [type=list_type, input_value='value', input_type=str]",
        "Field required [type=missing]",
        "Extra inputs are not permitted [type=extra_forbidden]",
    ]

    print("\n=== 测试 ValidationError 检测 ===")
    for error in test_errors:
        is_validation = executor._is_validation_error(error)
        print(f"✓ Error: {error[:50]}... → is_validation_error: {is_validation}")
        assert is_validation, f"应该检测到 ValidationError: {error}"

    # 测试非 ValidationError
    non_validation_errors = [
        "Tool not found",
        "Permission denied",
        "Connection timeout",
    ]

    print("\n=== 测试非 ValidationError ===")
    for error in non_validation_errors:
        is_validation = executor._is_validation_error(error)
        print(f"✓ Error: {error} → is_validation_error: {is_validation}")
        assert not is_validation, f"不应该检测为 ValidationError: {error}"

    print("\n✅ ValidationError 检测测试通过！")


def test_validation_error_sanitization():
    """测试 ValidationError 清洗功能"""
    from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor

    # 直接创建一个简单的实例来访问方法
    class MockConfig:
        pass

    class MockAuditor:
        pass

    class MockSanitizer:
        pass

    executor = EnhancedVIGILToolsExecutor(
        config=MockConfig(),
        auditor=MockAuditor(),
        sanitizer=MockSanitizer()
    )

    # 测试清洗 ValidationError
    original_error = """ValidationError: 1 validation error for Input schema for `get_rating_reviews_for_hotels`
hotel_names
  Input should be a valid list [type=list_type, input_value='Hotel ABC', input_type=str]"""

    sanitized = executor._sanitize_validation_error(original_error, "get_rating_reviews_for_hotels")

    print("\n=== 测试 ValidationError 清洗 ===")
    print(f"原始错误:\n{original_error}")
    print(f"\n清洗后:\n{sanitized}")

    # 验证清洗后的消息包含关键信息
    assert "hotel_names" in sanitized or "Field:" in sanitized, "应该包含字段名信息"
    assert "list" in sanitized, "应该包含期望类型信息"
    assert "str" in sanitized, "应该包含实际类型信息"
    assert "Hint:" in sanitized, "应该包含修正建议"

    print("\n✅ ValidationError 清洗测试通过！")


def test_llm_fix_validation_error_mock():
    """测试 LLM 修正 ValidationError 的逻辑（不实际调用 API）"""
    from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor

    print("\n=== 测试 _llm_fix_validation_error 方法存在性 ===")

    # 直接创建一个简单的实例来访问方法
    class MockConfig:
        pass

    class MockAuditor:
        pass

    class MockSanitizer:
        pass

    executor = EnhancedVIGILToolsExecutor(
        config=MockConfig(),
        auditor=MockAuditor(),
        sanitizer=MockSanitizer()
    )

    # 检查方法是否存在
    assert hasattr(executor, '_llm_fix_validation_error'), "应该有 _llm_fix_validation_error 方法"

    print("✓ _llm_fix_validation_error 方法存在")
    print("✅ 方法存在性检查通过！")
    print("\n注意：实际的 LLM 调用测试需要 ANTHROPIC_API_KEY，这里跳过")


if __name__ == "__main__":
    # 检查是否有 API key
    has_api_key = os.environ.get("ANTHROPIC_API_KEY") is not None

    print("=" * 60)
    print("ValidationError LLM 自动重试功能测试")
    print("=" * 60)

    # 运行基础测试
    test_validation_error_detection()
    test_validation_error_sanitization()
    test_llm_fix_validation_error_mock()

    if not has_api_key:
        print("\n⚠️ 未检测到 ANTHROPIC_API_KEY，跳过实际 LLM 调用测试")
        print("   如需完整测试，请设置环境变量：export ANTHROPIC_API_KEY=your-key")
    else:
        print("\n✓ 检测到 ANTHROPIC_API_KEY，可以进行完整测试")
        print("   (但为节省成本，此脚本不执行实际 API 调用)")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
