#!/usr/bin/env python3
"""
测试脚本：验证格式化后的 postaction docstrings 可以被正确使用
"""

import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

from formatted_postaction_docstrings import POSTACTION_DOCSTRINGS


def test_docstring_format():
    """测试所有 docstring 的基本格式"""
    print("Testing docstring formats...\n")

    passed = 0
    total = len(POSTACTION_DOCSTRINGS)

    for name, docstring in POSTACTION_DOCSTRINGS.items():
        # 检查是否为字符串
        assert isinstance(docstring, str), f"{name}: not a string"

        # 检查是否非空
        assert len(docstring.strip()) > 0, f"{name}: empty docstring"

        # 检查是否包含 REQUIRED NEXT STEP（所有函数都应该有）
        assert "REQUIRED NEXT STEP" in docstring, f"{name}: missing REQUIRED NEXT STEP"

        # 检查是否有 Returns 或 Args 部分
        has_structure = "Returns:" in docstring or "Args:" in docstring
        assert has_structure, f"{name}: missing Args/Returns structure"

        # 检查没有 \n 转义字符（应该使用实际换行）
        assert "\\n" not in docstring, f"{name}: contains \\n escape sequence"

        print(f"✓ {name}")
        print(f"  Length: {len(docstring)} chars")
        print(f"  Lines: {len(docstring.split(chr(10)))} lines")

        passed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*60}\n")

    return passed == total


def test_llm_parsing():
    """测试 LLM 是否能正确解析参数信息"""
    print("Testing LLM parsing simulation...\n")

    # 简单的参数提取测试
    test_cases = [
        ("send_email", ["recipients", "subject", "body", "attachments", "cc", "bcc"]),
        ("search_emails", ["query", "sender"]),
        ("delete_email", ["email_id"]),
        ("create_calendar_event", ["title", "start_time", "end_time", "description", "participants", "location"]),
    ]

    passed = 0
    total = len(test_cases)

    for func_name, expected_params in test_cases:
        docstring = POSTACTION_DOCSTRINGS[func_name]

        # 检查所有参数是否在 docstring 中
        all_found = True
        for param in expected_params:
            if param not in docstring:
                print(f"✗ {func_name}: missing parameter '{param}'")
                all_found = False

        if all_found:
            print(f"✓ {func_name}: all {len(expected_params)} parameters found")
            passed += 1
        else:
            print(f"✗ {func_name}: some parameters missing")

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} parsing tests passed")
    print(f"{'='*60}\n")

    return passed == total


def test_injection_into_function():
    """测试将 docstring 注入到函数中"""
    print("Testing docstring injection...\n")

    # 创建一个示例函数
    def get_unread_emails():
        pass

    # 注入 docstring
    get_unread_emails.__doc__ = POSTACTION_DOCSTRINGS["get_unread_emails"]

    # 验证注入成功
    assert get_unread_emails.__doc__ is not None
    assert "REQUIRED NEXT STEP" in get_unread_emails.__doc__
    assert "audit_read_access" in get_unread_emails.__doc__

    print("✓ Docstring successfully injected into function")
    print(f"✓ Function __doc__ length: {len(get_unread_emails.__doc__)} chars")
    print("\nExample injected docstring:")
    print("-" * 60)
    print(get_unread_emails.__doc__)
    print("-" * 60)

    return True


def show_example_output():
    """展示一个格式化后的 docstring 示例"""
    print("\n" + "="*60)
    print("Example: send_email function docstring")
    print("="*60)
    print(POSTACTION_DOCSTRINGS["send_email"])
    print("="*60)


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Formatted Postaction Docstrings - Validation Tests")
    print("="*60 + "\n")

    all_passed = True

    # Test 1: Basic format
    print("\n[Test 1/3] Basic Format Validation")
    print("-" * 60)
    if not test_docstring_format():
        all_passed = False

    # Test 2: LLM parsing
    print("\n[Test 2/3] LLM Parsing Simulation")
    print("-" * 60)
    if not test_llm_parsing():
        all_passed = False

    # Test 3: Function injection
    print("\n[Test 3/3] Function Injection")
    print("-" * 60)
    if not test_injection_into_function():
        all_passed = False

    # Show example
    show_example_output()

    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed! Docstrings are ready to use.")
    else:
        print("✗ Some tests failed. Please review the output above.")
    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
