"""Test that final assistant message is added when task completes

This test verifies that:
1. When finished_task=True and last message is tool result
2. A final assistant message is automatically added
3. This prevents "Last message was not an assistant message" error
"""

from unittest.mock import MagicMock

from agentdojo.functions_runtime import EmptyEnv, FunctionsRuntime
from agentdojo.types import ChatMessage, ChatToolResultMessage, ChatUserMessage, text_content_block_from_string
from vigil_agent.enhanced_tools_loop import EnhancedToolsExecutionLoop


def test_final_assistant_message_added():
    """Test that final assistant message is added when task finishes with tool result"""

    # Create a mock element that returns messages ending with a tool result
    mock_element = MagicMock()

    def mock_query(query, runtime, env, messages, extra_args):
        # Simulate a tool execution that completes the task
        # The last message will be a tool result
        tool_result = ChatToolResultMessage(
            role="tool",
            content=[text_content_block_from_string("Payment sent successfully")],
            tool_call_id="call_1",
            tool_call=None,
            error=None,
        )

        new_messages = [*messages, tool_result]
        new_extra_args = {**extra_args, "finished_task": True}

        return query, runtime, env, new_messages, new_extra_args

    mock_element.query = mock_query

    # Create the loop with the mock element
    loop = EnhancedToolsExecutionLoop([mock_element], max_iters=5)

    # Create initial messages
    initial_messages = [
        ChatUserMessage(
            role="user",
            content=[text_content_block_from_string("Pay the bill")],
        )
    ]

    # Run the loop
    _, _, _, final_messages, final_extra_args = loop.query(
        query="Pay the bill",
        runtime=FunctionsRuntime({}),
        env=EmptyEnv(),
        messages=initial_messages,
        extra_args={},
    )

    # Verify results
    assert len(final_messages) > len(initial_messages), "Should have added messages"
    assert final_messages[-1]["role"] == "assistant", "Last message should be assistant"
    assert final_extra_args.get("finished_task") is True, "Task should be marked as finished"

    print("✓ Final assistant message is added when task completes with tool result")
    print(f"  - Final messages count: {len(final_messages)}")
    print(f"  - Last message role: {final_messages[-1]['role']}")
    print(f"  - Last message content: {final_messages[-1]['content'][0]['content']}")


def test_no_duplicate_assistant_message():
    """Test that no duplicate assistant message is added if last message is already assistant"""

    # Create a mock element that returns messages ending with an assistant message
    mock_element = MagicMock()

    def mock_query(query, runtime, env, messages, extra_args):
        # Simulate that the assistant responds without tool calls
        from agentdojo.types import ChatAssistantMessage

        assistant_response = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string("I have completed the task.")],
            tool_calls=None,
        )

        new_messages = [*messages, assistant_response]
        new_extra_args = {**extra_args, "finished_task": True}

        return query, runtime, env, new_messages, new_extra_args

    mock_element.query = mock_query

    # Create the loop with the mock element
    loop = EnhancedToolsExecutionLoop([mock_element], max_iters=5)

    # Create initial messages
    initial_messages = [
        ChatUserMessage(
            role="user",
            content=[text_content_block_from_string("Pay the bill")],
        )
    ]

    # Run the loop
    _, _, _, final_messages, final_extra_args = loop.query(
        query="Pay the bill",
        runtime=FunctionsRuntime({}),
        env=EmptyEnv(),
        messages=initial_messages,
        extra_args={},
    )

    # Count assistant messages
    assistant_message_count = sum(1 for msg in final_messages if msg["role"] == "assistant")

    # Verify results
    assert final_messages[-1]["role"] == "assistant", "Last message should be assistant"
    assert assistant_message_count == 1, "Should have exactly one assistant message (no duplicate)"
    assert final_messages[-1]["content"][0]["content"] == "I have completed the task.", "Should be original assistant message"

    print("✓ No duplicate assistant message is added when last message is already assistant")
    print(f"  - Final messages count: {len(final_messages)}")
    print(f"  - Assistant messages count: {assistant_message_count}")


if __name__ == "__main__":
    print("Testing final assistant message behavior...\n")
    test_final_assistant_message_added()
    print("\n" + "="*80 + "\n")
    test_no_duplicate_assistant_message()
    print("\n" + "="*80)
    print("\n✅ All tests passed!")
