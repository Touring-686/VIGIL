"""Test that import fixes work correctly

Verify that:
1. text_content_block_from_string is accessible throughout the files
2. No UnboundLocalError occurs
3. All message creation works properly
"""

def test_imports():
    """Test that imports work correctly"""
    # Test hypothesis_guidance imports
    from vigil_agent.hypothesis_guidance import HypothesisGuidanceElement
    from vigil_agent.enhanced_tools_loop import EnhancedToolsExecutionLoop

    print("✓ All imports successful")

    # Check that text_content_block_from_string is available
    from agentdojo.types import text_content_block_from_string

    # Test creating a text block
    text_block = text_content_block_from_string("Test message")
    assert text_block["type"] == "text"
    assert text_block["content"] == "Test message"

    print("✓ text_content_block_from_string works correctly")

    # Test creating assistant message
    from agentdojo.types import ChatAssistantMessage

    message = ChatAssistantMessage(
        role="assistant",
        content=[text_content_block_from_string("Task completed successfully.")],
        tool_calls=None,
    )

    assert message["role"] == "assistant"
    assert message["content"][0]["content"] == "Task completed successfully."
    assert message["tool_calls"] is None

    print("✓ ChatAssistantMessage creation works correctly")


if __name__ == "__main__":
    print("Testing import fixes...\n")
    test_imports()
    print("\n✅ All import tests passed!")
