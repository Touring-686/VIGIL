# VIGIL调试配置 - 完整说明

## ✅ 已完成的配置

我已经为你在 `.vscode/launch.json` 中添加了**11个**专门的VIGIL调试配置！

## 🚀 立即开始

### 最快的方式（3步）：

1. **设置API key**:
   ```bash
   export OPENAI_API_KEY='your-key-here'
   ```

2. **在VSCode中按 F5** 或点击左侧的"Run and Debug"图标

3. **选择配置**:
   - 新手推荐: `VIGIL | Test Script` (不需要API key)
   - 完整测试: `VIGIL | Quick Run Script (Banking)`
   - 组件调试: `VIGIL | Debug Constraint Generator`

## 📋 11个可用的调试配置

### 🧪 基础测试 (3个)

1. **VIGIL | Test Script**
   - 运行基础测试脚本
   - 不需要API key也能运行部分测试
   - 适合验证安装

2. **VIGIL | Quick Run Script (Banking)**
   - 在Banking suite上快速测试
   - 完整的端到端测试
   - 需要API key

3. **VIGIL | Complete Examples**
   - 运行所有6个示例
   - 展示VIGIL的各种用法
   - 需要API key

### 🎯 Suite测试 (5个)

4. **VIGIL | Banking | No Attack (Utility Test)**
   - 测试utility（无攻击场景）
   - 验证任务完成能力

5. **VIGIL | Banking | With Attacks (Security Test)**
   - 测试security（有攻击场景）
   - 验证防御能力

6. **VIGIL | Travel | With Attacks**
   - Travel suite测试

7. **VIGIL | Slack | With Attacks**
   - Slack suite测试

8. **VIGIL | Workspace | With Attacks**
   - Workspace suite测试

### 🔧 组件调试 (3个)

9. **VIGIL | Debug Constraint Generator**
   - 单独调试约束生成器
   - 适合调试约束生成逻辑

10. **VIGIL | Debug Runtime Auditor**
    - 单独调试审计器
    - 适合调试审计逻辑

11. **VIGIL | Custom Debug Script**
    - 调试当前打开的Python文件
    - 最灵活的调试方式

## 🎯 推荐的断点位置

我建议你在以下位置设置断点：

### 约束生成器 (`vigil_agent/constraint_generator.py`)
```python
# 第 97 行 - generate_constraints()
def generate_constraints(self, user_query: str) -> ConstraintSet:
    # 👈 在这里设置断点
    # 查看: user_query, constraint_data, constraints
```

### 运行时审计器 (`vigil_agent/runtime_auditor.py`)
```python
# 第 57 行 - audit_tool_call()
def audit_tool_call(self, tool_call_info: ToolCallInfo) -> AuditResult:
    # 👈 在这里设置断点
    # 查看: tool_call_info, constraint_set, violated_constraints

# 第 107 行 - _verify_against_constraints()
def _verify_against_constraints(self, tool_call_info: ToolCallInfo) -> AuditResult:
    # 👈 在这里设置断点
    # 查看: 详细的验证过程
```

### VIGIL执行器 (`vigil_agent/vigil_executor.py`)
```python
# 第 85 行 - 工具被拦截时
if not audit_result.allowed:
    # 👈 在这里设置断点
    # 查看: audit_result, backtrack_count, feedback_message

# 第 141 行 - 工具被允许执行时
else:
    # 👈 在这里设置断点
    # 查看: 工具正常执行
```

## 🔥 使用示例

### 示例1: 调试端到端流程

1. 选择配置: `VIGIL | Quick Run Script (Banking)`
2. 设置断点:
   - `vigil_pipeline.py` 第48行 (初始化)
   - `constraint_generator.py` 第97行 (生成约束)
   - `runtime_auditor.py` 第57行 (审计)
   - `vigil_executor.py` 第85行 (拦截处理)
3. 按 F5 启动
4. 单步执行 (F10) 或继续 (F5)

### 示例2: 调试为什么工具被拦截

1. 选择配置: `VIGIL | Banking | With Attacks`
2. 在 `runtime_auditor.py` 第57行设置断点
3. 按 F5 启动
4. 查看变量:
   - `tool_call_info["tool_name"]` - 工具名称
   - `violated_constraints` - 违反的约束
   - `audit_result.feedback_message` - 反馈消息

### 示例3: 调试约束生成

1. 选择配置: `VIGIL | Debug Constraint Generator`
2. 在 `constraint_generator.py` 第97行设置断点
3. 按 F5 启动
4. 在Debug Console中执行:
   ```python
   for c in constraints:
       print(f"{c.constraint_type}: {c.description}")
   ```

## 💡 高级调试技巧

### 1. 条件断点

右键断点 → "Edit Breakpoint" → 添加条件:

```python
# 只在特定工具时暂停
tool_call_info["tool_name"] == "send_money"

# 只在有违规时暂停
len(violated_constraints) > 0

# 只在特定suite时暂停
suite.name == "banking"
```

### 2. 日志断点

右键断点 → "Edit Breakpoint" → "Logpoint":

```
Tool: {tool_call_info["tool_name"]}, Allowed: {audit_result.allowed}
```

### 3. Watch表达式

在调试面板的"Watch"中添加:

```python
len(self.constraint_set.constraints) if self.constraint_set else 0
self._backtracking_counts
self.auditor.stats
```

### 4. Debug Console技巧

按 `Ctrl+Shift+Y` 打开Debug Console:

```python
# 查看所有约束
for c in constraint_set.constraints:
    print(f"[{c.priority}] {c.constraint_type}: {c.description}")

# 手动测试审计
test_call = {
    "tool_name": "test_tool",
    "arguments": {"arg": "value"},
    "tool_call_id": "123"
}
result = auditor.audit_tool_call(test_call)
```

## 🎓 学习路径

### 第一次使用VIGIL调试:

1. **运行测试**: `VIGIL | Test Script`
   - 验证环境配置
   - 不需要API key

2. **端到端体验**: `VIGIL | Quick Run Script (Banking)`
   - 完整流程体验
   - 在关键位置设置断点观察

3. **组件深入**: `VIGIL | Debug Constraint Generator`
   - 理解约束生成机制

### 开发新功能:

1. 先单独测试组件
2. 使用 `VIGIL | Custom Debug Script` 测试集成
3. 使用完整配置验证

### 调试问题:

1. 复现问题（选择对应suite配置）
2. 设置断点
3. 使用Watch和Debug Console检查状态
4. 单步执行找到根因

## 📚 文档索引

- **VIGIL_DEBUG_QUICKREF.txt** - 快速参考卡片（打印或放在旁边）
- **VIGIL_DEBUG_GUIDE.md** - 完整调试指南（详细说明）
- **VIGIL_SUMMARY.md** - VIGIL框架使用总结
- **vigil_agent/README.md** - VIGIL框架完整文档
- **vigil_agent/QUICKSTART.md** - 5分钟快速开始

## 🐛 故障排除

### 问题1: 断点没有触发

**解决**:
- 确保选择了正确的调试配置
- 检查 `justMyCode` 已设置为 `false`（已配置）
- 确保代码路径会被执行

### 问题2: 找不到模块

**解决**:
- 检查 PYTHONPATH 环境变量（已在配置中设置）
- 重启VSCode

### 问题3: OpenAI API错误

**解决**:
```bash
# 设置API key
export OPENAI_API_KEY='your-key-here'

# 或者在 ~/.bashrc 中添加
echo "export OPENAI_API_KEY='your-key'" >> ~/.bashrc
source ~/.bashrc
```

### 问题4: 想调试特定的task

**解决**: 修改 `run_vigil.py`:
```python
results = benchmark_suite_with_injections(
    pipeline, suite, attack, logdir, False,
    user_tasks=["task_1"],  # 👈 添加这行
    injection_tasks=["inj_1", "inj_2"],  # 👈 添加这行
)
```

## 🎯 快捷键

- `F5` - 开始/继续调试
- `F9` - 设置/取消断点
- `F10` - 单步跳过
- `F11` - 单步进入
- `Shift+F11` - 单步跳出
- `Ctrl+Shift+D` - 打开调试面板
- `Ctrl+Shift+Y` - 打开Debug Console

## ✨ 特色功能

### 支持环境变量配置

所有配置都支持通过环境变量自定义:

```bash
export VIGIL_SUITE="travel"        # 切换suite
export VIGIL_MODEL="gpt-4o-mini"   # 切换模型
export VIGIL_RUN_ATTACKS="false"   # 只测试utility
```

### 完整的PYTHONPATH配置

所有配置都已正确设置PYTHONPATH，无需手动配置。

### 灵活的自定义脚本调试

使用 `VIGIL | Custom Debug Script` 可以调试任何Python文件。

## 🎉 开始使用

现在你可以：

1. 按 `F5` 打开调试菜单
2. 选择 `VIGIL | Test Script` 开始
3. 查看 `VIGIL_DEBUG_QUICKREF.txt` 作为参考

祝调试顺利！🚀

---

**需要帮助？** 查看详细文档:
- 详细调试指南: `VIGIL_DEBUG_GUIDE.md`
- 快速参考: `VIGIL_DEBUG_QUICKREF.txt`
- 框架文档: `vigil_agent/README.md`
