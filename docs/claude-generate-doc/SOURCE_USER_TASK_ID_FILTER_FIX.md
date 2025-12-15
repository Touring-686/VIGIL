# SOURCE_USER_TASK_ID 过滤逻辑修复

## 问题描述

在运行 Type II-A 攻击测试（`./type_ii_a_attack.sh`）时，发现一个 user task 会对应多个 injection tasks，导致执行效率低下且结果混乱。

**示例：**
- `user_task_0` 原本应该只配对 `injection_task_200` 和 `injection_task_220`
- 但实际上所有 40 个 Type II-A injection tasks 都会尝试与它配对
- 这导致大量不必要的测试运行

## 根本原因

在 `task_suite.py` 的 `run_task_with_pipeline` 方法中，只有 `parameter_override` 类型的 injection tasks 会检查 `SOURCE_USER_TASK` 是否匹配：

```python
# 原代码 - 只对 parameter_override 做检查
if getattr(injection_task, "ATTACK_TYPE", None) == "parameter_override":
    if getattr(injection_task, "SOURCE_USER_TASK", None) != getattr(user_task, "ID", None):
        return None, None  # Skip mismatched pairs
```

而 Type II-A 的 `short_circuit_reasoning` 任务虽然也定义了 `SOURCE_USER_TASK_ID`，但没有被过滤。

## 解决方案

将过滤逻辑从特定攻击类型提升为通用逻辑：**所有有 `SOURCE_USER_TASK_ID` 或 `SOURCE_USER_TASK` 字段的 injection task 都会被检查**。

### 修改位置

**文件：** `/src/agentdojo/task_suite/task_suite.py`  
**方法：** `run_task_with_pipeline`

### 修改内容

```python
# 新代码 - 通用的 SOURCE_USER_TASK_ID 检查
source_user_task_id = getattr(injection_task, "SOURCE_USER_TASK_ID", None) or getattr(injection_task, "SOURCE_USER_TASK", None)
if source_user_task_id is not None:
    user_task_id = getattr(user_task, "ID", None)
    if source_user_task_id != user_task_id:
        # Skip mismatched injection/user task pairs
        return None, None
```

### 关键改进

1. **双字段支持：** 同时支持 `SOURCE_USER_TASK_ID` 和 `SOURCE_USER_TASK`（向后兼容）
2. **通用性：** 不限于特定攻击类型，所有设置了源任务 ID 的 injection tasks 都会被正确过滤
3. **早期返回：** 不匹配的任务直接返回 `(None, None)`，避免不必要的计算

## 影响范围

此修改影响以下攻击类型：

- ✅ **Type I-A (`parameter_override`)**: 原有逻辑保留，继续工作
- ✅ **Type II-A (`short_circuit_reasoning`)**: 新增支持，40 个任务现在会正确过滤
- ✅ **Type II-B (`induced_parameter`)**: 如果设置了 `SOURCE_USER_TASK_ID`，会被正确过滤
- ✅ 其他设置了 `SOURCE_USER_TASK_ID` 的任务类型

## 验证结果

运行测试脚本 `test_source_user_task_id_filter.py`：

```
Testing with: user_task_0

✅ Injection tasks that SHOULD run with user_task_0:
   injection_task_200 (SOURCE_USER_TASK_ID=user_task_0)
   injection_task_220 (SOURCE_USER_TASK_ID=user_task_0)

❌ Injection tasks that should be SKIPPED:
   38 tasks with different SOURCE_USER_TASK_ID

Summary:
  - 2 injection tasks will execute with user_task_0
  - 38 injection tasks will be skipped (SOURCE_USER_TASK_ID mismatch)
```

**结论：** 过滤逻辑正常工作，每个 user task 现在只会与指定的 injection tasks 配对。

## 性能提升

- **修改前：** 每个 user task × 40 个 injection tasks = 800 次配对尝试（20 个 user tasks）
- **修改后：** 每个 user task × 2 个相关 injection tasks = 40 次有效配对
- **效率提升：** 减少了 95% 的无效配对检查

## 相关文件

- `/src/agentdojo/task_suite/task_suite.py` - 主要修改
- `/src/agentdojo/adverseral_tool/travel/type_ii_a_injection_tasks.py` - 定义了 SOURCE_USER_TASK_ID
- `test_source_user_task_id_filter.py` - 验证脚本
