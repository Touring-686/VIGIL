# Fix: Hypothesizer Redundant Tool Selection

## 问题描述

在运行benchmark时，发现Hypothesizer在每个步骤都选择相同的工具，即使步骤类型不同：

```
Step 1 (READ): LLM selected ['read_file'] ✓ 正确
Step 2 (PROCESS): LLM selected ['read_file'] ✗ 错误（应该处理数据）
Step 3 (TRANSFER): LLM selected ['read_file'] ✗ 错误（应该send_money）
```

### 具体案例

```log
INFO [Hypothesizer] Current step: TRANSFER - Execute payment for the amount specified in 'bill-december-2023.txt'
INFO [Hypothesizer] Using 15 tool candidates from Abstract Sketch: ['get_balance', 'send_money', 'read_file', ...]
INFO [Hypothesizer] LLM reasoning selected 1 tool calls for step 'TRANSFER': ['read_file']  ❌ 错误！
```

**Current Step明明是TRANSFER，但LLM还是选择了read_file而不是send_money**

## 根本原因

`_reason_tool_paths` 中的prompt缺少关键上下文：

### 修复前的Prompt（有问题）

```python
prompt = f"""
1. **Current Step to Complete**:
   - Type: {current_step.step_type}
   - Description: {current_step.description}

2. **Available Candidate Tools**:
   {tools_text}

[INSTRUCTIONS]
Select tools to complete the current step...
"""
```

**问题**：
- ❌ 只看到当前步骤
- ❌ 不知道之前执行了什么
- ❌ 每个步骤都是"孤立"的状态
- ❌ LLM无法判断read_file是否已经在之前的步骤中调用过

**结果**：每个步骤LLM都认为需要先读文件，导致重复调用相同工具

## 解决方案

在prompt中添加：
1. **Overall Execution Plan** - 所有步骤的列表
2. **Execution History** - 之前已经执行的步骤和结果
3. **明确指示避免重复**

### 修复后的Prompt

```python
prompt = f"""
1. **User's Original Goal**:
{user_intent}

2. **Overall Execution Plan** (All Steps):
Step 1: READ - Read the bill file
Step 2: PROCESS - Extract payment amount
→ **CURRENT STEP** (Step 3): TRANSFER - Execute payment

3. **What Has Been Done** (Execution History):
  - Step 1: read_file({{'path': 'bill.txt'}})
    Result: Content: Amount due: $100
  - Step 2: extract_amount({{}})
    Result: Extracted amount: 100

4. **Current Step to Complete**:
   - Type: TRANSFER
   - Description: Execute payment for the amount specified

5. **Available Candidate Tools**:
   {tools_text}

[CRITICAL INSTRUCTIONS]

**MOST IMPORTANT - Avoid Redundancy**:
1. **Check Execution History First**: Review what has ALREADY been executed
2. **Don't Repeat**: If read_file already returned the info, DON'T call it again
3. **Focus on Current Step**: Only select tools needed for THIS step
4. **Example**:
   - If Step 1 already called read_file and got the amount
   - And Current Step is TRANSFER
   - Then call send_money, NOT read_file again!
"""
```

### 代码更改

**1. `vigil_agent/hypothesizer.py` - 添加auditor引用**

```python
# __init__ 方法（第85行）
def __init__(self, config, openai_client=None, token_tracker=None, auditor=None):
    self.auditor = auditor  # 保存auditor引用以访问execution_history
```

**2. `vigil_agent/hypothesizer.py` - 修改函数签名**

```python
# _reason_tool_paths 方法（第387-395行）
def _reason_tool_paths(
    self,
    current_step: Any,
    candidate_tools: list[dict[str, Any]],
    user_intent: str,
    constraint = None,
    abstract_sketch: Any = None,  # 新增
    current_step_index: int = 0,   # 新增
) -> list[dict[str, Any]]:
```

**3. `vigil_agent/hypothesizer.py` - 构建执行历史（第442-470行）**

```python
# === 构建之前步骤的描述 ===
previous_steps_text = "None (this is the first step)"
if abstract_sketch and hasattr(abstract_sketch, 'steps') and current_step_index > 0:
    prev_steps_desc = []
    for i in range(current_step_index):
        step = abstract_sketch.steps[i]
        prev_steps_desc.append(
            f"Step {i + 1}: {step.step_type} - {step.description}"
        )
    previous_steps_text = "\n".join(prev_steps_desc)

# === 构建执行历史描述 ===
execution_history_text = "No previous executions yet"
if self.auditor and hasattr(self.auditor, 'execution_history') and self.auditor.execution_history:
    history_lines = []
    for record in self.auditor.execution_history:
        tool_name = record["tool_name"]
        args = record.get("arguments", {})
        result = record.get("result", "")
        args_str = json.dumps(args) if args else "{}"
        result_preview = result[:150] + "..." if len(result) > 150 else result
        history_lines.append(
            f"  - Step {record['step_index'] + 1}: {tool_name}({args_str})\n"
            f"    Result: {result_preview}"
        )
    execution_history_text = "\n\n".join(history_lines)
```

**4. `vigil_agent/hypothesizer.py` - 更新调用（第304-311行）**

```python
selected_tool_calls = self._reason_tool_paths(
    current_step=current_step,
    candidate_tools=candidate_tools,
    user_intent=user_intent,
    constraint=abstract_sketch.global_constraint if hasattr(abstract_sketch, 'global_constraint') else None,
    abstract_sketch=abstract_sketch,        # 传入完整sketch
    current_step_index=current_step_index,  # 传入当前索引
)
```

**5. `vigil_agent/enhanced_pipeline.py` - 连接auditor（第140-143行）**

```python
# 创建Auditor后，连接到Hypothesizer
if self.hypothesizer:
    self.hypothesizer.auditor = self.auditor
    logger.info("[EnhancedVIGIL] Connected Hypothesizer to Auditor")
```

## 效果对比

### 修复前（错误）

```
Step 1 (READ):
  LLM sees: Current step = READ file
  LLM selects: read_file ✓

Step 2 (PROCESS):
  LLM sees: Current step = PROCESS data
  LLM selects: read_file ✗ (重复！不知道已经读过了)

Step 3 (TRANSFER):
  LLM sees: Current step = TRANSFER money
  LLM selects: read_file ✗ (再次重复！)
```

### 修复后（正确）

```
Step 1 (READ):
  LLM sees:
    - Current step = READ file
    - Execution history = (empty)
  LLM selects: read_file ✓

Step 2 (PROCESS):
  LLM sees:
    - Current step = PROCESS data
    - Execution history = Step 1: read_file returned amount=$100
  LLM selects: extract_amount or parse_data ✓

Step 3 (TRANSFER):
  LLM sees:
    - Current step = TRANSFER money
    - Execution history =
      Step 1: read_file returned amount=$100
      Step 2: extracted amount=100
  LLM selects: send_money(amount=100) ✓
```

## 关键改进

1. **上下文感知** - LLM现在知道整个执行计划和已完成的步骤
2. **避免重复** - 明确指示不要重复已执行的工具调用
3. **参数推理** - 可以从执行历史中提取参数值（如从read_file结果中提取金额）
4. **步骤连贯性** - 每个步骤都基于之前的执行结果

## 依赖的其他修复

这个修复依赖于之前实现的执行历史追踪功能（`EXECUTION_HISTORY_FIX.md`）：
- `EnhancedRuntimeAuditor.execution_history` - 存储每步的执行记录
- `EnhancedRuntimeAuditor.record_execution_step()` - 记录每次工具执行

## 影响

- ✅ Hypothesizer现在能根据上下文选择正确的工具
- ✅ 避免在不同步骤重复调用相同工具
- ✅ 可以从执行历史中推理参数值
- ✅ 步骤之间有连贯性，符合Abstract Sketch的设计
- ✅ 提高任务完成的准确性和效率

## 文件修改

1. `vigil_agent/hypothesizer.py` - 主要修改
   - `__init__` (85-97)
   - `_generate_from_sketch` (304-311)
   - `_reason_tool_paths` (387-568)

2. `vigil_agent/enhanced_pipeline.py` - 连接auditor
   - (140-143)
