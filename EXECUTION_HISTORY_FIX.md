# Execution History Tracking Fix

## Problem

The `_llm_verify_constraints` method in `EnhancedAuditor` was not including previous execution steps and their results when verifying constraints. This caused the LLM verifier to incorrectly assume that the agent hadn't executed previous operations, leading to false positive constraint violations.

For example, in a multi-step task like "Pay the bill 'bill.txt'":
- Step 1: READ the bill file → executed successfully
- Step 2: SEND payment → verifier thought agent never read the file, incorrectly flagging violation

## Solution

Added execution history tracking to the VIGIL framework with cumulative message passing:

### 1. Added Execution History Tracking to `EnhancedRuntimeAuditor`

**File**: `vigil_agent/enhanced_auditor.py`

```python
# New attribute in __init__
self.execution_history: list[dict[str, Any]] = []

# New method to record execution steps
def record_execution_step(
    self,
    step_index: int,
    tool_call_info: ToolCallInfo,
    result: str,
    step_description: str | None = None,
) -> None:
    """记录执行步骤

    在每次成功执行工具后调用，累积记录执行历史。
    """
    execution_record = {
        "step_index": step_index,
        "step_description": step_description or f"Step {step_index + 1}",
        "tool_name": tool_call_info["tool_name"],
        "arguments": tool_call_info.get("arguments", {}),
        "result": result,
    }
    self.execution_history.append(execution_record)
```

### 2. Updated `_llm_verify_constraints` to Include Execution History

The prompt now includes:
- User's original request
- Overall execution plan (Abstract Sketch)
- **NEW: Previous execution history (what has been done so far)**
- Global security constraints
- Current step being verified
- Proposed tool call

```python
# 构建执行历史描述（关键新增部分）
execution_history_description = "No previous steps executed yet."
if self.execution_history:
    history_lines = []
    for record in self.execution_history:
        history_lines.append(
            f"Step {record['step_index'] + 1} ({record['step_description']}):\n"
            f"  Tool: {record['tool_name']}\n"
            f"  Arguments: {json.dumps(record['arguments'])}\n"
            f"  Result: {record['result'][:200]}..."
        )
    execution_history_description = "\n\n".join(history_lines)
```

### 3. Updated `EnhancedVIGILToolsExecutor` to Record History

**File**: `vigil_agent/enhanced_executor.py`

After successful tool execution (no error), the executor now records the execution step:

```python
# === 记录执行历史（仅在成功时）===
if not error and self.auditor:
    current_step_index = extra_args.get('current_step_index', 0)
    step_description = None

    # 从 abstract sketch 获取步骤描述
    if self.auditor.abstract_sketch and hasattr(self.auditor.abstract_sketch, 'steps'):
        if current_step_index < len(self.auditor.abstract_sketch.steps):
            step = self.auditor.abstract_sketch.steps[current_step_index]
            step_description = f"{step.step_type} - {step.description}"

    self.auditor.record_execution_step(
        step_index=current_step_index,
        tool_call_info=tool_call_info,
        result=formatted_result,
        step_description=step_description,
    )
```

### 4. Added Cleanup Methods

- `clear_execution_history()`: Clears execution history for new tasks
- Updated `reset_stats()`: Now also clears execution history when resetting

## Example

**Scenario**: User asks "Pay the bill 'bill.txt'"

### Before Fix:
```
Step 1: read_file('bill.txt') → ✓ Executed
Step 2: send_payment(amount=100) → ❌ BLOCKED
  Reason: "Agent hasn't read the bill file yet, violates constraint"
```

### After Fix:
```
Step 1: read_file('bill.txt') → ✓ Executed
  History: [Step 1: read_file('bill.txt') → Amount due: $100]

Step 2: send_payment(amount=100) → ✓ ALLOWED
  Verifier sees: "Agent already read the bill in Step 1,
                  now sending payment is allowed"
```

## Prompt Enhancement

The LLM verifier now receives a complete picture:

```
**Previous Execution History (What the Agent Has Already Done):**
Step 1 (READ - Read the bill file):
  Tool: read_file
  Arguments: {"path": "bill.txt"}
  Result: File content: Amount due: $100

**Proposed Tool Call (Being Verified Now):**
- Tool: send_payment
- Arguments: {"amount": 100}

**Critical Instructions:**
2. **Review Execution History**: Check what the agent has ALREADY done
   in previous steps. The agent may have already completed prerequisite
   operations (like reading a file before sending it).
```

## Testing

Created comprehensive test suite in `test_execution_history.py`:
- ✓ Execution history tracking works correctly
- ✓ Reset clears execution history
- ✓ Execution history is included in LLM verification prompt
- ✓ LLM correctly verifies based on execution history

## Benefits

1. **Contextual Verification**: The verifier now understands the full execution context
2. **Reduced False Positives**: Multi-step tasks are properly validated
3. **Better Traceability**: Complete audit trail of what was executed
4. **Cumulative Message Passing**: Each step builds on previous execution context

## Key Insight

This fix implements the principle: **"把agent真实执行的操作和abstract sketch对应起来"**
- The verifier can now map real tool executions to the abstract plan
- It understands that prerequisites (like reading a file) have been satisfied
- It makes more informed decisions based on the complete execution history
