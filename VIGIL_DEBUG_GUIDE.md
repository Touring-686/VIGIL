# VIGIL Framework - VSCode 调试配置指南

## 📋 可用的调试配置

我已经为你在 `.vscode/launch.json` 中添加了以下VIGIL调试配置：

### 1. 基础测试和示例

#### `VIGIL | Test Script`
- **用途**: 运行VIGIL的基础测试脚本
- **文件**: `vigil_agent/test_vigil.py`
- **适用场景**: 验证VIGIL框架是否正确安装和配置
- **注意**: 不需要OpenAI API key也能运行部分测试

#### `VIGIL | Quick Run Script (Banking)`
- **用途**: 快速运行VIGIL在Banking suite上的完整测试
- **文件**: `run_vigil.py`
- **适用场景**: 快速验证VIGIL agent的整体功能
- **需要**: OpenAI API key

#### `VIGIL | Complete Examples`
- **用途**: 运行完整的示例代码（包含6个示例）
- **文件**: `examples/vigil_benchmark_example.py`
- **适用场景**: 学习VIGIL的各种使用方式

### 2. 不同Suite的调试配置

#### `VIGIL | Banking | No Attack (Utility Test)`
- **用途**: 在Banking suite上测试utility（无攻击）
- **适用场景**: 验证agent在正常情况下的任务完成能力

#### `VIGIL | Banking | With Attacks (Security Test)`
- **用途**: 在Banking suite上测试security（有攻击）
- **适用场景**: 验证agent的安全防护能力

#### `VIGIL | Travel | With Attacks`
- **用途**: 在Travel suite上测试
- **套用**: 可以切换不同的suite进行测试

#### `VIGIL | Slack | With Attacks`
- **用途**: 在Slack suite上测试

#### `VIGIL | Workspace | With Attacks`
- **用途**: 在Workspace suite上测试

### 3. 组件级调试

#### `VIGIL | Debug Constraint Generator`
- **用途**: 单独调试约束生成器
- **文件**: `vigil_agent/constraint_generator.py`
- **适用场景**: 调试约束生成逻辑

#### `VIGIL | Debug Runtime Auditor`
- **用途**: 单独调试运行时审计器
- **文件**: `vigil_agent/runtime_auditor.py`
- **适用场景**: 调试审计逻辑

#### `VIGIL | Custom Debug Script`
- **用途**: 调试当前打开的Python文件
- **使用**: 打开你想调试的.py文件，然后选择这个配置
- **适用场景**: 调试自己编写的测试脚本

## 🚀 使用步骤

### 1. 基础设置

首先设置OpenAI API key：

```bash
export OPENAI_API_KEY='your-api-key-here'
```

或者在 VSCode 中设置环境变量：
1. 打开 `~/.bashrc` 或 `~/.zshrc`
2. 添加: `export OPENAI_API_KEY='your-key'`
3. 重启VSCode

### 2. 开始调试

#### 方式1: 使用VSCode界面

1. 按 `F5` 或点击左侧的"Run and Debug"图标
2. 在顶部下拉菜单中选择一个VIGIL配置
3. 点击绿色播放按钮开始调试

#### 方式2: 使用快捷键

1. 按 `Ctrl+Shift+D` (Mac: `Cmd+Shift+D`) 打开调试面板
2. 选择配置
3. 按 `F5` 开始调试

### 3. 设置断点

在代码中你想暂停的地方点击行号左侧，设置断点：

**推荐的调试点**:

#### 约束生成器 (`vigil_agent/constraint_generator.py`)
```python
# 第97行 - 查看生成的约束
def generate_constraints(self, user_query: str) -> ConstraintSet:
    # 在这里设置断点
    ...
```

#### 运行时审计器 (`vigil_agent/runtime_auditor.py`)
```python
# 第57行 - 查看审计决策
def audit_tool_call(self, tool_call_info: ToolCallInfo) -> AuditResult:
    # 在这里设置断点
    ...
```

#### VIGIL执行器 (`vigil_agent/vigil_executor.py`)
```python
# 第85行 - 查看工具调用被拦截的情况
if not audit_result.allowed:
    # 在这里设置断点
    ...
```

## 🎯 常见调试场景

### 场景1: 调试为什么某个约束没有被生成

1. 选择配置: `VIGIL | Debug Constraint Generator`
2. 在 `constraint_generator.py` 的第97行设置断点
3. F5启动调试
4. 查看变量:
   - `user_query`: 用户查询
   - `constraint_data`: LLM返回的原始JSON
   - `constraints`: 解析后的约束列表

### 场景2: 调试为什么某个工具调用被拦截/放行

1. 选择配置: `VIGIL | Banking | With Attacks`
2. 在 `runtime_auditor.py` 的第57行设置断点
3. F5启动调试
4. 查看变量:
   - `tool_call_info`: 工具调用信息
   - `constraint_set`: 当前的约束集
   - `violated_constraints`: 违反的约束
   - `result`: 最终的审计结果

### 场景3: 调试反思回溯机制

1. 选择配置: `VIGIL | Banking | With Attacks`
2. 在 `vigil_executor.py` 的第85行设置断点
3. F5启动调试
4. 查看变量:
   - `audit_result.allowed`: 是否允许
   - `backtrack_count`: 当前回溯次数
   - `feedback_message`: 反馈消息

### 场景4: 端到端调试整个流程

1. 选择配置: `VIGIL | Quick Run Script (Banking)`
2. 在以下位置设置断点:
   - `vigil_pipeline.py` 第48行 (pipeline初始化)
   - `constraint_generator.py` 第97行 (生成约束)
   - `runtime_auditor.py` 第57行 (审计工具调用)
   - `vigil_executor.py` 第85行 (处理拦截)
3. F5启动调试
4. 单步执行，观察整个流程

## 🔧 自定义调试配置

如果你想创建自己的调试配置，可以参考这个模板：

```json
{
  "name": "VIGIL | My Custom Test",
  "type": "debugpy",
  "request": "launch",
  "program": "${workspaceFolder}/my_test_script.py",
  "console": "integratedTerminal",
  "cwd": "${workspaceFolder}",
  "env": {
    "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}",
    "OPENAI_API_KEY": "${env:OPENAI_API_KEY}",
    // 自定义环境变量
    "VIGIL_SUITE": "banking",
    "VIGIL_RUN_ATTACKS": "true"
  },
  "justMyCode": false  // 允许调试库代码
}
```

## 📝 调试技巧

### 1. 条件断点

在断点上右键 -> "Edit Breakpoint" -> 添加条件:

```python
# 只在特定工具被调用时暂停
tool_call_info["tool_name"] == "send_money"

# 只在约束被违反时暂停
len(violated_constraints) > 0
```

### 2. 日志断点

在断点上右键 -> "Edit Breakpoint" -> 选择"Logpoint":

```python
# 记录工具调用
Tool: {tool_call_info["tool_name"]}, Args: {tool_call_info["arguments"]}

# 记录审计结果
Audit: {audit_result.allowed}, Violations: {len(violated_constraints) if violated_constraints else 0}
```

### 3. 监视表达式

在调试面板的"Watch"中添加：

```python
# 监视约束集大小
len(self.constraint_set.constraints) if self.constraint_set else 0

# 监视回溯次数
self._backtracking_counts

# 监视审计统计
self.auditor.stats
```

### 4. 调试控制台

在调试时按 `Ctrl+Shift+Y` 打开调试控制台，可以执行Python代码：

```python
# 查看当前约束
for c in constraint_set.constraints:
    print(f"{c.constraint_type}: {c.description}")

# 查看工具调用信息
print(f"Tool: {tool_call_info['tool_name']}")
print(f"Args: {tool_call_info['arguments']}")

# 手动测试审计
test_call = {"tool_name": "test", "arguments": {}, "tool_call_id": "1"}
result = auditor.audit_tool_call(test_call)
print(f"Result: {result.allowed}")
```

## 🐛 常见问题

### Q1: 为什么断点没有被触发？

**A**: 检查以下几点：
1. 确保选择了正确的调试配置
2. 确保`justMyCode`设置为`false`（已在配置中设置）
3. 确保断点设置在会被执行的代码路径上
4. 检查是否有条件断点的条件不满足

### Q2: 为什么提示找不到模块？

**A**: 检查PYTHONPATH设置：
```json
"env": {
  "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}"
}
```

### Q3: 如何调试特定的injection task？

**A**: 修改`run_vigil.py`，添加task过滤：

```python
results = benchmark_suite_with_injections(
    pipeline, suite, attack, logdir, False,
    user_tasks=["task_1"],  # 指定user task
    injection_tasks=["injection_1", "injection_2"],  # 指定injection task
)
```

然后使用相应的调试配置。

## 🎓 推荐的调试流程

### 初次使用：

1. `VIGIL | Test Script` - 验证基础功能
2. `VIGIL | Quick Run Script (Banking)` - 端到端测试
3. 在关键位置设置断点，重新运行

### 开发新功能：

1. `VIGIL | Debug Constraint Generator` - 测试约束生成
2. `VIGIL | Debug Runtime Auditor` - 测试审计逻辑
3. `VIGIL | Custom Debug Script` - 测试你的脚本

### 调试问题：

1. 复现问题（使用对应的suite配置）
2. 设置断点在怀疑的位置
3. 使用Watch和Debug Console检查状态
4. 单步执行找到根因

## 📚 更多资源

- VSCode Python调试文档: https://code.visualstudio.com/docs/python/debugging
- VIGIL框架文档: `vigil_agent/README.md`
- 快速启动指南: `vigil_agent/QUICKSTART.md`
- 使用示例: `examples/vigil_benchmark_example.py`

## 💡 提示

- 使用`justMyCode: false`可以调试库代码
- 使用条件断点减少不必要的暂停
- 使用日志断点代替print语句
- 使用Watch监视关键变量
- 善用Debug Console进行实验
