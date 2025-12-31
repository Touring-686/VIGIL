"""Test execution history tracking in EnhancedAuditor

This test verifies that:
1. Execution history is properly tracked after each tool execution
2. The history is included in _llm_verify_constraints prompts
3. The verifier can see previous execution steps and their results
"""

import json
from unittest.mock import MagicMock, patch

from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.abstract_sketch import AbstractSketch, AbstractStep
from vigil_agent.types import ToolCallInfo


def test_execution_history_tracking():
    """Test that execution history is properly tracked"""
    config = VIGILConfig(
        enable_llm_constraint_verification=False,  # Disable for unit test
        log_audit_decisions=True,
    )

    auditor = EnhancedRuntimeAuditor(config=config)

    # Verify initial state
    assert len(auditor.execution_history) == 0

    # Record first step
    tool_call_1: ToolCallInfo = {
        "tool_name": "read_file",
        "arguments": {"path": "bill.txt"},
        "tool_call_id": "call_1",
    }
    auditor.record_execution_step(
        step_index=0,
        tool_call_info=tool_call_1,
        result="File content: Amount due: $100",
        step_description="READ - Read the bill file",
    )

    assert len(auditor.execution_history) == 1
    assert auditor.execution_history[0]["tool_name"] == "read_file"
    assert auditor.execution_history[0]["result"] == "File content: Amount due: $100"

    # Record second step
    tool_call_2: ToolCallInfo = {
        "tool_name": "send_payment",
        "arguments": {"amount": 100},
        "tool_call_id": "call_2",
    }
    auditor.record_execution_step(
        step_index=1,
        tool_call_info=tool_call_2,
        result="Payment sent successfully",
        step_description="SEND - Send the payment",
    )

    assert len(auditor.execution_history) == 2
    assert auditor.execution_history[1]["tool_name"] == "send_payment"

    print("✓ Execution history tracking works correctly")

    # Test reset
    auditor.reset_stats()
    assert len(auditor.execution_history) == 0
    print("✓ Reset clears execution history")


def test_execution_history_in_prompt():
    """Test that execution history is included in LLM verification prompt"""
    config = VIGILConfig(
        enable_llm_constraint_verification=True,
        llm_constraint_verifier_model="gpt-4o-mini",
        log_audit_decisions=True,
    )

    # Create mock constraint set
    from vigil_agent.types import SecurityConstraint, ConstraintSet
    constraint_set = ConstraintSet(
        user_query="Pay the bill bill.txt",
        constraints=[
            SecurityConstraint(
                constraint_id="allow_read_bill",
                constraint_type="allow",
                description="Allow reading the specified bill file",
                condition={},
                priority=1,
            ),
            SecurityConstraint(
                constraint_id="allow_payment",
                constraint_type="allow",
                description="Allow sending the payment after reading the bill",
                condition={},
                priority=1,
            ),
        ],
    )

    # Create abstract sketch
    sketch = AbstractSketch(
        sketch_id="test_sketch",
        user_query="Pay the bill bill.txt",
        expected_outcome="Payment sent successfully",
        steps=[
            AbstractStep(
                step_id="step_1",
                step_type="READ",
                description="Read the bill file",
                tool_candidates=["read_file"],
            ),
            AbstractStep(
                step_id="step_2",
                step_type="SEND",
                description="Send the payment",
                tool_candidates=["send_payment"],
            ),
        ],
        global_constraints=["Allow reading the specified bill file", "Allow sending payment"],
        global_constraint="Allow reading and payment operations for the specified bill",
    )

    # Mock the LLM client to capture the prompt
    captured_prompt = None

    def mock_create(**kwargs):
        nonlocal captured_prompt
        captured_prompt = kwargs["messages"][1]["content"]  # User message

        # Return a mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "is_violation": False,
            "reasoning": "The agent has already read the bill in Step 1. Now it's executing Step 2 to send payment, which is allowed.",
            "violated_constraint": "",
            "confidence": 0.9,
        })
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        return mock_response

    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_openai.return_value = mock_client

        # Create auditor with mocked client
        auditor = EnhancedRuntimeAuditor(
            config=config,
            constraint_set=constraint_set,
            abstract_sketch=sketch,
        )

        # Record first step execution
        tool_call_1: ToolCallInfo = {
            "tool_name": "read_file",
            "arguments": {"path": "bill.txt"},
            "tool_call_id": "call_1",
        }
        auditor.record_execution_step(
            step_index=0,
            tool_call_info=tool_call_1,
            result="File content: Amount due: $100",
            step_description="READ - Read the bill file",
        )

        # Now verify the second tool call
        tool_call_2: ToolCallInfo = {
            "tool_name": "send_payment",
            "arguments": {"amount": 100},
            "tool_call_id": "call_2",
        }

        result = auditor._llm_verify_constraints(tool_call_2, current_step_index=1)

        # Verify the prompt includes execution history
        assert captured_prompt is not None
        assert "Previous Execution History" in captured_prompt
        assert "read_file" in captured_prompt
        assert "bill.txt" in captured_prompt
        assert "File content: Amount due: $100" in captured_prompt

        print("✓ Execution history is included in LLM verification prompt")
        print(f"\nPrompt excerpt:\n{captured_prompt[500:1500]}...")

        # Verify the result
        assert result.allowed
        print("✓ LLM correctly allowed the tool call based on execution history")


def test_reasoning_step_recording():
    """Test that REASONING steps are recorded to execution history"""
    config = VIGILConfig(
        enable_llm_constraint_verification=False,
        log_audit_decisions=True,
    )

    auditor = EnhancedRuntimeAuditor(config=config)

    # Simulate recording a REASONING step
    reasoning_tool_call: ToolCallInfo = {
        "tool_name": "__llm_reasoning__",
        "arguments": {},
        "tool_call_id": None,
    }

    auditor.record_execution_step(
        step_index=0,
        tool_call_info=reasoning_tool_call,
        result="After analyzing the situation, I believe we should first check the account balance before proceeding with the transaction.",
        step_description="REASONING - Analyze the situation",
    )

    assert len(auditor.execution_history) == 1
    assert auditor.execution_history[0]["tool_name"] == "__llm_reasoning__"
    assert "analyzing the situation" in auditor.execution_history[0]["result"]

    print("✓ REASONING step recording works correctly")

    # Now test a mixed sequence: REASONING → TOOL → REASONING
    tool_call: ToolCallInfo = {
        "tool_name": "get_balance",
        "arguments": {"account_id": "123"},
        "tool_call_id": "call_1",
    }
    auditor.record_execution_step(
        step_index=1,
        tool_call_info=tool_call,
        result="Balance: $1000",
        step_description="READ - Get account balance",
    )

    reasoning_tool_call_2: ToolCallInfo = {
        "tool_name": "__llm_reasoning__",
        "arguments": {},
        "tool_call_id": None,
    }
    auditor.record_execution_step(
        step_index=2,
        tool_call_info=reasoning_tool_call_2,
        result="The balance is sufficient. We can proceed with the payment.",
        step_description="REASONING - Determine next action",
    )

    assert len(auditor.execution_history) == 3
    assert auditor.execution_history[0]["tool_name"] == "__llm_reasoning__"
    assert auditor.execution_history[1]["tool_name"] == "get_balance"
    assert auditor.execution_history[2]["tool_name"] == "__llm_reasoning__"

    print("✓ Mixed REASONING and TOOL steps recorded correctly")


if __name__ == "__main__":
    print("Testing execution history tracking...\n")
    test_execution_history_tracking()
    print("\n" + "="*80 + "\n")
    print("Testing REASONING step recording...\n")
    test_reasoning_step_recording()
    print("\n" + "="*80 + "\n")
    print("Testing execution history in LLM prompt...\n")
    test_execution_history_in_prompt()
    print("\n" + "="*80)
    print("\n✅ All tests passed!")
