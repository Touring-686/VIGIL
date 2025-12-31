# REASONING 步骤 (__no_tool_call__) 处理实现

## 问题描述

在 VIGIL framework 中，某些执行步骤不需要调用工具，而只需要 LLM 进行推理和分析（例如：综合之前的工具返回结果，做出决策）。这些步骤在 Abstract Sketch 中被标记为 `__no_tool_call__`。

之前的实现虽然能够检测这类步骤并生成相应的 guidance，但在 `EnhancedVIGILToolsExecutor` 中缺少对这些步骤的显式处理和违规检测。

## 解决方案

### 1. 在 `HypothesisGuidanceElement` 中设置标志

在 `vigil_agent/hypothesis_guidance.py` 中，当检测到 REASONING 步骤（`__no_tool_call__`）时，设置 `extra_args` 中的 `current_step_is_reasoning` 标志：

```python
# 检查是否是 REASONING 步骤
is_reasoning_step = (
    commitment_decision.selected_branch is not None
    and commitment_decision.selected_branch.tool_call.get("tool_name") == "__no_tool_call__"
)

# 强制使用 guidance mode（即使在 direct mode 下）
use_guidance_mode = (
    is_reasoning_step or  # REASONING 步骤需要 LLM
    is_validation_error or
    not self.config.enable_direct_tool_execution
)

# ... 生成 guidance ...

# 设置 REASONING 步骤标志
extra_args = {
    **extra_args,
    'current_step_is_reasoning': is_reasoning_step,
}
```

### 2. 在 `EnhancedVIGILToolsExecutor` 中处理 REASONING 步骤

在 `vigil_agent/enhanced_executor.py` 的 `query` 方法中添加以下逻辑：

```python
def query(self, ...):
    # 从 extra_args 中获取当前步骤信息
    current_step_is_reasoning = extra_args.get('current_step_is_reasoning', False)

    # 检查是否有工具调用需要处理
    if messages[-1]["tool_calls"] is None or len(messages[-1]["tool_calls"]) == 0:
        # 没有工具调用
        if current_step_is_reasoning:
            # REASONING 步骤完成，LLM 正确地没有调用工具
            logger.info("✓ REASONING step completed correctly")
        return query, runtime, env, messages, extra_args

    # 检查 REASONING 步骤违规
    if current_step_is_reasoning:
        logger.warning("⚠️ REASONING STEP VIOLATION DETECTED")

        # 拒绝所有工具调用，返回错误消息
        error_message = (
            "❌ VIGIL Policy Violation: Tool Call in REASONING Step\n\n"
            "This step is marked as a REASONING step (no tool execution allowed).\n"
            "Please provide your reasoning directly without tool calls."
        )

        # 返回错误消息
        tool_call_results = [ChatToolResultMessage(..., error="ReasoningStepViolation")]
        return query, runtime, env, [*messages, *tool_call_results], extra_args

    # 继续正常的工具执行流程...
```

## 执行流程

### REASONING 步骤的正常流程

```
用户查询
    ↓
HypothesisGuidance 检测到 __no_tool_call__
    ↓
设置 current_step_is_reasoning = True
    ↓
生成 REASONING guidance
    ↓
ConditionalLLM 调用 LLM
    ↓
LLM 生成推理结果（没有 tool_calls）
    ↓
EnhancedVIGILToolsExecutor 检测到:
  - 没有 tool_calls
  - current_step_is_reasoning = True
    ↓
记录日志：✓ REASONING step completed correctly
    ↓
继续下一步
```

### REASONING 步骤的违规检测

```
用户查询
    ↓
HypothesisGuidance 检测到 __no_tool_call__
    ↓
设置 current_step_is_reasoning = True
    ↓
生成 REASONING guidance
    ↓
ConditionalLLM 调用 LLM
    ↓
LLM 违规生成工具调用 ❌
    ↓
EnhancedVIGILToolsExecutor 检测到:
  - 有 tool_calls
  - current_step_is_reasoning = True
    ↓
记录警告：⚠️ REASONING STEP VIOLATION DETECTED
    ↓
拒绝工具调用，返回错误消息
    ↓
LLM 收到错误，重新生成推理结果
```

## 示例场景

### 场景：酒店推荐任务

**步骤 1-3**：调用工具收集酒店信息
- `get_hotels_address`
- `get_rating_reviews_for_hotels`
- `get_hotels_prices`

**步骤 4**：REASONING 步骤（`__no_tool_call__`）
- **任务**：综合前 3 步的信息，推荐最佳酒店
- **预期行为**：LLM 应该分析数据并给出推荐，**不调用工具**
- **违规情况**：如果 LLM 尝试调用 `recommend_hotel` 或其他工具
- **处理**：Executor 拒绝工具调用，要求 LLM 直接提供推理

**步骤 5**：继续后续步骤（如果需要）

## 测试结果

运行 `test_reasoning_step.py`：

```
✓ REASONING 步骤正确完成（无工具调用）
✓ REASONING 步骤违规被正确拦截
✓ 非 REASONING 步骤的工具调用通过 REASONING 检查
✅ 所有测试通过！
```

## 改动文件

1. **vigil_agent/enhanced_executor.py**：
   - 在 `query` 方法开头添加 REASONING 步骤检测
   - 在没有工具调用时记录 REASONING 步骤完成
   - 在有工具调用时检测 REASONING 步骤违规并拒绝

2. **vigil_agent/hypothesis_guidance.py**：
   - 在生成 guidance 时设置 `current_step_is_reasoning` 标志
   - 在 direct mode 下也设置该标志（标记为 False）

3. **test_reasoning_step.py**：新增测试文件

## 优势

1. **双重保护**：即使 LLM 忽略 guidance，Executor 也会拒绝违规的工具调用
2. **清晰的错误提示**：明确告诉 LLM 这是 REASONING 步骤，不应调用工具
3. **日志记录**：详细记录 REASONING 步骤的完成和违规情况
4. **不影响正常流程**：非 REASONING 步骤的工具调用不受影响

## 注意事项

1. **REASONING 步骤的定义**：在 Hypothesizer 中生成 hypothesis tree 时，将不需要工具的步骤标记为 `__no_tool_call__`
2. **Guidance 的重要性**：虽然 Executor 会拦截违规，但良好的 guidance 可以避免不必要的重试
3. **日志级别**：REASONING 步骤的完成记录为 INFO 级别，违规记录为 WARNING 级别
