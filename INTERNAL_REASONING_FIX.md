# __internal_reasoning__ 修复文档

## 问题描述

之前的实现中，`__internal_reasoning__` 被误当成普通工具来调用，导致报错：
```
Invalid tool __internal_reasoning__ provided.
```

## 根本原因

`__internal_reasoning__` 是一个**虚拟工具**，表示需要 LLM 进行内部推理（而不是调用外部工具）。但是之前的实现：
1. 将它当作普通工具在工具调用循环中处理
2. 没有统一处理 `__no_tool_call__` 和 `__internal_reasoning__` 两种推理步骤

## 修复方案

### 1. 统一推理步骤处理逻辑

**修改文件：** `vigil_agent/hypothesis_guidance.py` (第465-473行)

```python
# 设置 REASONING 步骤标志并跳过 LLM（让 Executor 统一处理）
# __no_tool_call__ 和 __internal_reasoning__ 都应该：
# 1. 跳过 ConditionalLLM 的调用
# 2. 在 Executor 开头调用 LLM 进行推理
extra_args = {
    **extra_args,
    'current_step_is_reasoning': is_reasoning_step or is_internal_reasoning,
    'skip_llm': is_reasoning_step or is_internal_reasoning,  # 跳过 ConditionalLLM
}
```

**关键改变：**
- 当检测到 `__internal_reasoning__` 时，设置 `current_step_is_reasoning=True`
- 同时设置 `skip_llm=True`，跳过 ConditionalLLM，避免重复调用
- 让 Executor 统一处理所有推理步骤

### 2. 改进 Executor 的推理步骤实现

**修改文件：** `vigil_agent/enhanced_executor.py` (第596-680行)

```python
def _execute_reasoning_step(
    self,
    messages: Sequence[ChatMessage],
    query: str
) -> ChatMessage:
    """执行 REASONING 步骤：调用 LLM 进行推理（作为工具使用）

    当 hypothesis branch 是 __no_tool_call__ 或 __internal_reasoning__ 时，
    把 LLM 当作工具来执行推理。
    """
    # 将整个消息历史转换为 OpenAI API 格式
    # 这样 LLM 可以看到完整的上下文，包括 guidance message
    converted_messages = []
    for msg in messages:
        role = msg["role"]
        content_blocks = msg.get("content", [])
        text_parts = []
        for block in content_blocks:
            if "text" in block:
                text_parts.append(block["text"])
        if text_parts:
            converted_messages.append({
                "role": role,
                "content": "\n".join(text_parts)
            })

    # 调用 LLM（不提供 tools）
    response = self.hypothesizer.openai_client.chat.completions.create(
        model=self.config.hypothesizer_model,
        messages=converted_messages,
        temperature=self.config.hypothesizer_temperature,
        max_tokens=8192,
    )

    # 返回推理结果
    return ChatAssistantMessage(...)
```

**关键改进：**
- 将整个消息历史传递给 LLM（包括 guidance message）
- 正确提取文本内容（使用 `"text"` 字段）
- 统一处理 `__no_tool_call__` 和 `__internal_reasoning__`

### 3. 删除冗余的工具调用处理

**修改文件：** `vigil_agent/enhanced_executor.py` (第231-253行)

删除了之前在工具调用循环中对 `__internal_reasoning__` 的特殊处理，因为现在统一在 `if current_step_is_reasoning:` 分支中处理。

## 执行流程

### 对于 `__internal_reasoning__` 的完整流程：

```
1. Hypothesizer
   └─> 识别需要内部推理（如从已有数据中提取信息）
   └─> 生成 __internal_reasoning__ 分支

2. HypothesisGuidance
   └─> 检测到 is_internal_reasoning=True
   └─> 进入 guidance mode
   └─> 生成 guidance message（告诉 LLM 应该如何推理）
   └─> 设置 current_step_is_reasoning=True
   └─> 设置 skip_llm=True

3. ConditionalLLM
   └─> 检测到 skip_llm=True
   └─> 跳过调用

4. EnhancedVIGILToolsExecutor
   └─> 检测到 current_step_is_reasoning=True
   └─> 调用 _execute_reasoning_step()
   └─> 将完整消息历史（包括 guidance）传递给 LLM
   └─> LLM 生成推理响应（不包含工具调用）
   └─> 记录到执行历史
   └─> 继续下一步
```

### 对比：`__no_tool_call__` 的流程

两者流程完全相同，只是 guidance message 的内容不同：
- `__no_tool_call__`: "This is a REASONING step..."
- `__internal_reasoning__`: "Current step requires REASONING and ANALYSIS..."

## 优势

1. **统一处理：** `__no_tool_call__` 和 `__internal_reasoning__` 使用相同的处理逻辑
2. **避免误报：** 不会再报错 "Invalid tool __internal_reasoning__ provided"
3. **避免重复调用：** 通过 `skip_llm` 标志避免 ConditionalLLM 重复调用
4. **完整上下文：** LLM 能看到完整的消息历史和 guidance
5. **代码简洁：** 删除了冗余的特殊处理代码

## 测试验证

运行测试：
```bash
PYTHONPATH=/Users/justin/BDAA/ACL/code/agentdojo/src:/Users/justin/BDAA/ACL/code/agentdojo:$PYTHONPATH \
python test_internal_reasoning.py
```

所有测试通过：
- ✓ 字符串比较逻辑正常工作
- ✓ FunctionCall 对象处理正确

## 相关文件

- `vigil_agent/hypothesis_guidance.py`: 设置推理标志
- `vigil_agent/enhanced_executor.py`: 执行推理步骤
- `vigil_agent/hypothesizer.py`: 生成 `__internal_reasoning__` 分支

## 使用场景

`__internal_reasoning__` 适用于以下场景：
1. 从已有数据中提取信息（如从文件内容中提取金额）
2. 对已有信息进行分析和比较
3. 基于上下文进行推理和决策
4. 不需要调用外部工具的纯逻辑处理

## 示例

```python
# 场景：从已读取的文件内容中提取支付金额
# Step 1: READ - 读取账单文件（调用 read_file 工具）
# Step 2: EXTRACT_PAYMENT_DETAILS - 提取支付详情（__internal_reasoning__）
# Step 3: TRANSFER - 执行转账（调用 send_money 工具）

# 在 Step 2，Hypothesizer 会生成 __internal_reasoning__ 分支
# Executor 调用 LLM 进行推理，从 Step 1 的结果中提取金额
# 不需要再次调用任何外部工具
```
