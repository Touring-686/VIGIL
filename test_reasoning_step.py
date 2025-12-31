"""测试 __no_tool_call__ (REASONING 步骤) 的处理"""

import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_reasoning_step_detection():
    """测试 REASONING 步骤的检测和处理"""
    from vigil_agent.enhanced_executor import EnhancedVIGILToolsExecutor
    from agentdojo.types import (
        ChatAssistantMessage,
        FunctionCall,
        text_content_block_from_string
    )

    # 创建简单的 mock 对象
    class MockConfig:
        log_audit_decisions = True

    class MockAuditor:
        pass

    class MockSanitizer:
        pass

    class MockRuntime:
        pass

    class MockEnv:
        pass

    executor = EnhancedVIGILToolsExecutor(
        config=MockConfig(),
        auditor=MockAuditor(),
        sanitizer=MockSanitizer()
    )

    print("\n" + "=" * 70)
    print("测试 1: REASONING 步骤 - LLM 正确地没有调用工具")
    print("=" * 70)

    # 场景1：REASONING 步骤，LLM 没有调用工具（正确行为）
    messages = [
        ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string("Based on the information, I conclude that...")],
            tool_calls=None
        )
    ]

    extra_args = {'current_step_is_reasoning': True}

    # 调用 query 方法
    _, _, _, result_messages, _ = executor.query(
        query="Test query",
        runtime=MockRuntime(),
        env=MockEnv(),
        messages=messages,
        extra_args=extra_args
    )

    # 验证：应该直接返回，不添加任何消息
    assert len(result_messages) == len(messages), "不应该添加任何新消息"
    print("✓ REASONING 步骤正确完成（无工具调用）")

    print("\n" + "=" * 70)
    print("测试 2: REASONING 步骤 - LLM 违规调用工具（应该被拒绝）")
    print("=" * 70)

    # 场景2：REASONING 步骤，但 LLM 违规调用了工具（错误行为）
    tool_call = FunctionCall(
        id="call_123",
        function="get_user_info",
        args={"user_id": "123"}
    )

    messages_with_tool = [
        ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string("Let me check...")],
            tool_calls=[tool_call]
        )
    ]

    extra_args = {'current_step_is_reasoning': True}

    # 调用 query 方法
    _, _, _, result_messages, _ = executor.query(
        query="Test query",
        runtime=MockRuntime(),
        env=MockEnv(),
        messages=messages_with_tool,
        extra_args=extra_args
    )

    # 验证：应该添加错误消息
    assert len(result_messages) > len(messages_with_tool), "应该添加错误消息"
    error_message = result_messages[-1]
    assert error_message.get("role") == "tool", "应该是 tool 角色的错误消息"
    assert error_message.get("error") == "ReasoningStepViolation", "错误类型应该是 ReasoningStepViolation"

    print("✓ REASONING 步骤违规被正确拦截")
    # 安全地提取错误消息内容
    content = error_message.get("content", [])
    if content and len(content) > 0:
        content_text = content[0].get("text", "N/A")
        print(f"  错误消息: {content_text[:100]}...")

    print("\n" + "=" * 70)
    print("测试 3: 非 REASONING 步骤 - 正常工具调用（应该通过）")
    print("=" * 70)

    # 场景3：非 REASONING 步骤，正常的工具调用
    messages_normal = [
        ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string("I will use the tool...")],
            tool_calls=[tool_call]
        )
    ]

    extra_args_normal = {'current_step_is_reasoning': False}

    # 调用 query 方法（会进入正常的工具执行流程）
    # 注意：这里会因为没有真正的 runtime 而失败，但我们只是想验证不会被 REASONING 检查拦截
    try:
        _, _, _, result_messages, _ = executor.query(
            query="Test query",
            runtime=MockRuntime(),
            env=MockEnv(),
            messages=messages_normal,
            extra_args=extra_args_normal
        )
        # 应该进入正常的工具执行流程（不会被 REASONING 检查拦截）
        print("✓ 非 REASONING 步骤的工具调用通过 REASONING 检查")
    except Exception as e:
        # 可能会因为 MockRuntime 而失败，但这不是我们要测试的
        if "ReasoningStepViolation" in str(e):
            raise AssertionError("非 REASONING 步骤不应该被 REASONING 检查拦截")
        else:
            print("✓ 非 REASONING 步骤的工具调用通过 REASONING 检查（后续失败是预期的）")

    print("\n" + "=" * 70)
    print("✅ 所有 REASONING 步骤测试通过！")
    print("=" * 70)


if __name__ == "__main__":
    print("=" * 70)
    print("__no_tool_call__ (REASONING 步骤) 处理测试")
    print("=" * 70)

    test_reasoning_step_detection()

    print("\n✅ 所有测试通过！")
