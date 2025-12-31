# Import Fix: UnboundLocalError

## 问题

```python
UnboundLocalError: cannot access local variable 'text_content_block_from_string'
where it is not associated with a value
```

**错误位置**: `vigil_agent/hypothesis_guidance.py:401`

## 原因

`text_content_block_from_string` 在某些地方被局部导入（在if块内部），导致Python认为它是局部变量，但在使用时还未绑定值。

### 问题代码模式

```python
# 文件顶部
from agentdojo.types import text_content_block_from_string  # 全局导入

# 某个函数中
if condition:
    from agentdojo.types import text_content_block_from_string  # 局部导入
    # 使用...

# 稍后在同一函数中
content=[text_content_block_from_string(msg)]  # ❌ UnboundLocalError!
```

Python看到局部导入后，会认为 `text_content_block_from_string` 是局部变量，即使全局有导入。如果执行路径没有进入那个if块，变量就未绑定。

## 解决方案

### 统一为全局导入

将所有常用类型在文件顶部导入，移除内部重复导入：

**1. `vigil_agent/hypothesis_guidance.py`**

```python
# 第22行 - 全局导入（保留）
from agentdojo.types import ChatMessage, ChatSystemMessage, text_content_block_from_string

# 第212行 - 移除重复导入
# 修改前:
from agentdojo.types import ChatAssistantMessage, text_content_block_from_string

# 修改后:
from agentdojo.types import ChatAssistantMessage  # 只导入新需要的
```

**2. `vigil_agent/enhanced_tools_loop.py`**

```python
# 第14行 - 全局导入（扩充）
# 修改前:
from agentdojo.types import ChatMessage

# 修改后:
from agentdojo.types import ChatMessage, ChatAssistantMessage, text_content_block_from_string

# 第94行、137行 - 移除局部导入
# 修改前:
from agentdojo.types import ChatAssistantMessage, text_content_block_from_string

# 修改后:
# （移除，直接使用全局导入）
```

## 修复后的导入策略

### 全局导入（文件顶部）
- 常用的、在多处使用的类型
- `text_content_block_from_string` - 在整个文件中使用
- `ChatMessage` - 类型标注
- `ChatAssistantMessage` - 创建assistant消息
- `ChatSystemMessage` - 创建system消息

### 局部导入（函数内部）
- 只在特定函数使用的类型
- 可选，但必须确保不与全局导入冲突
- 示例：`FunctionCall` 只在生成tool call的函数中使用

## 测试

```bash
$ python test_import_fixes.py
✓ All imports successful
✓ text_content_block_from_string works correctly
✓ ChatAssistantMessage creation works correctly
✅ All import tests passed!
```

## 相关修复

这个修复是系列修复的一部分：

1. **执行历史追踪** (`EXECUTION_HISTORY_FIX.md`)
2. **List Index Out of Range** (`LIST_INDEX_OUT_OF_RANGE_FIX.md`)
3. **Final Assistant Message** (同上)
4. **Import UnboundLocalError** (本文档)

所有修复协同工作，确保系统在任务完成时能够：
- ✅ 正确追踪执行历史
- ✅ 不访问越界的步骤
- ✅ 添加最终的assistant message
- ✅ 所有导入正常工作，没有UnboundLocalError
