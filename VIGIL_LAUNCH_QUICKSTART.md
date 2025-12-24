# VIGIL Launch.json 配置说明

## 📁 文件状态

✅ **原文件已备份**: `.vscode/launch.json.backup` (965行)
✅ **新文件已更新**: `.vscode/launch.json` (1153行，新增188行VIGIL配置)

---

## 🎯 新增的VIGIL调试配置

所有VIGIL配置都通过 `agentdojo.scripts.benchmark` 运行，完全集成到agentdojo框架中。

### Banking Suite（7个配置）
1. ✅ **VIGIL | Banking | Type I-A | Intent Hijacking**
2. ✅ **VIGIL | Banking | Type I-A | Parameter Override**
3. ✅ **VIGIL | Banking | Type I-B**
4. ✅ **VIGIL | Banking | Type II-A**
5. ✅ **VIGIL | Banking | Type II-B**
6. ✅ **VIGIL | Banking | Type III-A**
7. ✅ **VIGIL | Banking | Important Instructions**

### 通用模板
8. ✅ **VIGIL | Custom Suite & Attack (Template)** - 可自定义任何组合

---

## 🚀 使用方法

### 方法1: VSCode调试界面
1. 按 `F5` 或点击左侧"Run and Debug"图标
2. 从下拉菜单选择VIGIL配置（例如：`VIGIL | Banking | Type I-A | Intent Hijacking`）
3. 点击绿色播放按钮开始调试

### 方法2: 自定义模板
1. 选择 `VIGIL | Custom Suite & Attack (Template)`
2. 在launch.json中修改参数：
   ```json
   "--suite", "banking",              // 改为: banking, travel, slack, workspace
   "--attack", "tool_attack",         // 改为: tool_attack, important_instructions
   "--attack-vector-type", "type_i_a", // 改为: type_i_a, type_i_b, type_ii_a, type_ii_b, type_iii_a
   "--attack-type", "parameter_override", // 可选
   ```

### 方法3: 命令行运行
```bash
export PYTHONPATH=/Users/justin/BDAA/ACL/code/agentdojo/src:$PYTHONPATH

python -m agentdojo.scripts.benchmark \
  --suite banking \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_i_a \
  --attack-type intent_hijacking \
  --defense vigil \
  --model gpt-4o-2024-08-06 \
  --max-workers 1 \
  --force-rerun \
  --logdir ./runs/vigil/banking/type_i_a_intent
```

---

## 🔧 配置详解

### 关键参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `--suite` | 测试套件 | `banking`, `travel`, `slack`, `workspace` |
| `--attack` | 攻击类型 | `tool_attack`, `important_instructions` |
| `--attack-vector-type` | 工具攻击向量 | `type_i_a`, `type_i_b`, `type_ii_a`, `type_ii_b`, `type_iii_a` |
| `--attack-type` | 攻击子类型（可选） | `intent_hijacking`, `parameter_override`, 等 |
| `--defense` | 防御方法 | **固定为 `vigil`** |
| `--model` | LLM模型 | `gpt-4o-2024-08-06`, `gpt-4o-mini`, 等 |
| `--max-workers` | 并行数 | 通常设为 `1` 用于调试 |
| `--force-rerun` | 强制重跑 | 忽略缓存 |
| `--logdir` | 日志目录 | 输出路径 |

### PYTHONPATH设置
所有配置都包含：
```json
"env": {
  "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}"
}
```
这确保可以同时导入：
- `agentdojo` 包（从 `src/`）
- `vigil_agent` 模块（从项目根目录）

---

## 📋 攻击类型说明

### Tool Attack（工具攻击）

| 类型 | 说明 | 对应配置 |
|------|------|----------|
| **Type I-A** | Docstring Injection（文档字符串注入） | Intent Hijacking / Parameter Override |
| **Type I-B** | Logic Trap（逻辑陷阱） | 隐式恶意逻辑 |
| **Type II-A** | Reasoning Distortion（推理扭曲） | 误导推理过程 |
| **Type II-B** | Over-Optimization（过度优化） | 诱导选择更强工具 |
| **Type III-A** | SOP Injection（SOP注入） | 错误消息注入指令 |

### Important Instructions Attack
直接在用户查询中注入恶意指令（agentdojo原始攻击）。

---

## 🐛 调试技巧

### 设置断点
在以下文件中设置断点：
- `vigil_agent/enhanced_auditor.py:audit_tool_call()` - 查看审计决策
- `vigil_agent/perception_sanitizer.py:sanitize_*()` - 查看输入清洗
- `vigil_agent/hypothesizer.py:generate_hypotheses()` - 查看假设生成
- `vigil_agent/enhanced_pipeline.py` - 查看完整流程

### 查看日志
日志保存在 `--logdir` 指定的目录：
```
runs/vigil/banking/type_i_a_intent/
├── task_user_001_injection_002.log
├── task_user_001_injection_003.log
└── ...
```

### 监视变量
在 Debug Console 中查看：
- `constraint_set` - 当前约束集
- `hypothesis_tree` - 生成的假设树
- `audit_result` - 审计结果
- `audit_stats` - 统计信息

---

## 💡 快速开始示例

### 测试Banking的Type I-A Intent Hijacking
1. 在VSCode中按 `F5`
2. 选择：`VIGIL | Banking | Type I-A | Intent Hijacking`
3. 观察VIGIL如何阻止意图劫持攻击

### 添加新的Suite配置
复制现有配置并修改：
```json
{
  "name": "VIGIL | Travel | Type I-B",
  "module": "agentdojo.scripts.benchmark",
  "args": [
    "--suite", "travel",           // 修改suite
    "--attack-vector-type", "type_i_b",  // 修改attack type
    "--defense", "vigil",
    "--logdir", "${workspaceFolder}/runs/vigil/travel/type_i_b"  // 修改logdir
  ]
}
```

---

## 📊 运行结果

成功运行后会输出：
- ✅ 每个injection task的执行结果
- ✅ VIGIL的审计统计（允许/阻止/总数）
- ✅ 攻击成功率
- ✅ 任务完成率
- ✅ 详细的执行日志

---

## 🔄 恢复原配置

如果需要恢复原始配置：
```bash
cp .vscode/launch.json.backup .vscode/launch.json
```

---

## 📚 相关文档

- `VIGIL_LAUNCH_CONFIG_GUIDE.md` - 完整使用指南
- `vigil_agent/README.md` - VIGIL框架说明
- `VIGIL_TESTING_GUIDE.md` - 测试指南

---

## ✅ 总结

现在你可以：
1. ✅ 通过VSCode调试界面运行VIGIL
2. ✅ 测试所有suite和attack组合
3. ✅ 在VIGIL代码中设置断点
4. ✅ 查看完整的攻击流程和防御效果
5. ✅ 保留原有的所有配置（已备份）

**原始配置完全保留，VIGIL配置作为新增部分添加！**
