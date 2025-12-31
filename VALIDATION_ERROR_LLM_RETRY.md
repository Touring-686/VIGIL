# ValidationError LLM 自动重试功能实现

## 问题描述

之前的实现中，当工具执行遇到 `ValidationError`（参数类型错误）时，系统只会：
1. 检测到错误
2. 记录日志
3. 将错误返回给 LLM

但**没有立即让 LLM 分析错误并用正确的参数重试**，而是需要等待下一轮对话。

## 解决方案

### 核心改动：在 `_execute_tool` 中添加自动重试循环

在 `vigil_agent/enhanced_executor.py` 的 `_execute_tool` 方法中实现了完整的 ValidationError 自动重试机制：

```python
def _execute_tool(self, ...):
    # === ValidationError 自动重试循环 ===
    max_validation_retries = self._max_validation_retries
    current_retry = 0
    current_args = tool_call.args

    while current_retry <= max_validation_retries:
        # 1. 执行工具
        tool_call_result, error = runtime.run_function(env, tool_call.function, current_args)

        # 2. 检查是否为 ValidationError
        if error and self._is_validation_error(error):
            current_retry += 1

            if current_retry > max_validation_retries:
                break  # 超过最大重试次数

            # 3. 调用 LLM 分析错误并修正参数
            corrected_args = self._llm_fix_validation_error(
                tool_name=tool_call.function,
                original_args=current_args,
                error_message=error,
                runtime=runtime
            )

            if corrected_args is None:
                break  # LLM 无法修正

            # 4. 用修正后的参数重试
            current_args = corrected_args
            tool_call.args = corrected_args
            continue
        else:
            # 执行成功或遇到其他错误，退出循环
            break

    # ... 后续处理（清洗、返回结果）
```

### 新增方法：`_llm_fix_validation_error`

实现了一个专门的方法来调用 LLM 修正参数：

```python
def _llm_fix_validation_error(
    self,
    tool_name: str,
    original_args: dict,
    error_message: str,
    runtime: FunctionsRuntime
) -> dict | None:
    """调用 LLM 分析 ValidationError 并返回修正后的参数"""

    # 1. 获取工具的参数 schema
    tool_schema = ...

    # 2. 构建 prompt
    prompt = f"""
    Tool: {tool_name}
    Original Arguments: {original_args}
    Validation Error: {error_message}
    Tool Parameter Schema: {tool_schema}

    Please provide corrected arguments as JSON.
    """

    # 3. 调用 Anthropic API（使用 Haiku 以降低延迟和成本）
    client = Anthropic()
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    # 4. 解析响应并返回修正后的参数
    corrected_args = json.loads(response_text)
    return corrected_args
```

## 执行流程

### 之前的流程（有问题）

```
工具调用 → 执行失败（ValidationError）
         ↓
       检测错误
         ↓
     记录日志（"允许 LLM 重试"）
         ↓
     返回错误给 LLM
         ↓
   等待下一轮对话 ❌
```

### 现在的流程（正确）

```
工具调用 → 执行失败（ValidationError）
         ↓
       检测错误
         ↓
   调用 LLM 分析错误
         ↓
   LLM 返回修正后的参数
         ↓
   用新参数重试 ✅
         ↓
   成功 / 继续重试（最多 3 次）
```

## 示例场景

### 场景：hotel_names 参数类型错误

**原始调用：**
```python
get_rating_reviews_for_hotels(hotel_names="Hotel ABC")  # ❌ 错误：应该是列表
```

**错误消息：**
```
ValidationError: 1 validation error for Input schema
hotel_names
  Input should be a valid list [type=list_type, input_value='Hotel ABC', input_type=str]
```

**LLM 自动修正：**
```python
# LLM 分析错误并返回修正后的参数
{"hotel_names": ["Hotel ABC"]}  # ✅ 正确：包装成列表
```

**自动重试：**
```python
get_rating_reviews_for_hotels(hotel_names=["Hotel ABC"])  # ✅ 成功执行
```

## 配置参数

- **最大重试次数**：`self._max_validation_retries = 3`
- **LLM 模型**：`claude-3-5-haiku-20241022`（快速且成本低）
- **超时处理**：如果 LLM 无法修正或超过重试次数，返回错误给上层 LLM

## 测试结果

运行 `test_llm_validation_retry.py` 的结果：

```
✅ ValidationError 检测测试通过！
✅ ValidationError 清洗测试通过！
✅ 方法存在性检查通过！
✅ 所有测试通过！
```

## 优势

1. **即时修正**：在工具执行层立即重试，无需等待下一轮对话
2. **降低延迟**：避免多轮对话往返
3. **提高成功率**：自动修正常见的参数类型错误
4. **降低成本**：使用 Haiku 模型，成本低且速度快
5. **透明性**：详细的日志记录每次重试

## 改动文件

- `vigil_agent/enhanced_executor.py`：
  - 修改 `_execute_tool` 方法，添加重试循环
  - 新增 `_llm_fix_validation_error` 方法
  - 删除旧的 `_validation_retry_counts` 跟踪逻辑

- `test_llm_validation_retry.py`：新增测试文件

## 注意事项

1. **需要 ANTHROPIC_API_KEY**：LLM 修正功能需要 Anthropic API key
2. **成本考虑**：每次 ValidationError 会调用一次 Haiku API（约 $0.0001/次）
3. **最大重试次数**：默认 3 次，可通过 `_max_validation_retries` 调整
4. **仅适用于 ValidationError**：其他类型的错误（如 SOP 注入）仍会触发回溯机制
