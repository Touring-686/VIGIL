# VIGIL Launch.json 调试配置说明

## 概述

已清理的 launch.json 只包含 VIGIL 框架的调试配置，所有配置都通过 `agentdojo.scripts.benchmark` 模块运行。

## 配置结构

所有配置都遵循标准的 agentdojo benchmark 格式：

```json
{
  "module": "agentdojo.scripts.benchmark",
  "args": [
    "--suite", "<suite_name>",              // banking, travel, slack, workspace
    "--benchmark-version", "adversarial",
    "--attack", "<attack_name>",            // tool_attack, important_instructions
    "--attack-vector-type", "<type>",       // type_i_a, type_i_b, type_ii_a, type_ii_b, type_iii_a
    "--attack-type", "<subtype>",           // Optional: intent_hijacking, parameter_override, etc.
    "--defense", "vigil",
    "--model", "gpt-4o-2024-08-06",
    "--max-workers", "1",
    "--force-rerun",
    "--logdir", "${workspaceFolder}/runs/vigil/<path>"
  ]
}
```

## 可用的调试配置

### Banking Suite（7个配置）
1. **VIGIL | Banking | Type I-A | Intent Hijacking** - 意图劫持
2. **VIGIL | Banking | Type I-A | Parameter Override** - 参数覆盖
3. **VIGIL | Banking | Type I-B** - 逻辑陷阱
4. **VIGIL | Banking | Type II-A** - 推理扭曲
5. **VIGIL | Banking | Type II-B** - 过度优化
6. **VIGIL | Banking | Type III-A** - SOP注入
7. **VIGIL | Banking | Important Instructions** - 重要指令攻击

### Travel Suite（2个配置）
1. **VIGIL | Travel | Type I-A | Parameter Override**
2. **VIGIL | Travel | Type II-A**

### Slack Suite（2个配置）
1. **VIGIL | Slack | Type I-A | Parameter Override**
2. **VIGIL | Slack | Important Instructions**

### Workspace Suite（2个配置）
1. **VIGIL | Workspace | Type I-A | Parameter Override**
2. **VIGIL | Workspace | Type II-B**

### 通用模板（2个配置）
1. **VIGIL | Custom Suite & Attack (Template)** - 可自定义的模板
2. **VIGIL | All Banking Attacks (Sequential)** - 顺序运行所有banking攻击

## 使用方法

### 方法1: 使用预定义配置

1. 在 VSCode 中按 `F5` 或点击 "Run and Debug"
2. 从下拉菜单选择你想要的配置
3. 点击 "Start Debugging" (绿色播放按钮)

### 方法2: 自定义配置

使用 "VIGIL | Custom Suite & Attack (Template)" 配置：

1. 打开 `.vscode/launch.json`
2. 找到 "VIGIL | Custom Suite & Attack (Template)"
3. 修改参数：
   ```json
   "--suite", "banking",           // 改为你需要的 suite
   "--attack", "tool_attack",      // 改为你需要的 attack
   "--attack-vector-type", "type_i_a",  // 改为你需要的 type
   "--attack-type", "parameter_override",  // 可选的 subtype
   ```
4. 保存并运行

### 方法3: 命令行运行

也可以直接在终端运行：

```bash
# 设置 PYTHONPATH
export PYTHONPATH=/Users/justin/BDAA/ACL/code/agentdojo/src:/Users/justin/BDAA/ACL/code/agentdojo:$PYTHONPATH

# 运行 benchmark
python -m agentdojo.scripts.benchmark \
  --suite banking \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_i_a \
  --attack-type parameter_override \
  --defense vigil \
  --model gpt-4o-2024-08-06 \
  --max-workers 1 \
  --force-rerun \
  --logdir ./runs/vigil/banking/type_i_a_param
```

## 参数说明

### 必需参数

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `--suite` | `banking`, `travel`, `slack`, `workspace` | 测试套件 |
| `--benchmark-version` | `adversarial` | Benchmark版本（固定为adversarial） |
| `--attack` | `tool_attack`, `important_instructions` | 攻击类型 |
| `--defense` | `vigil` | 防御方法（固定为vigil） |
| `--model` | `gpt-4o-2024-08-06` | 使用的LLM模型 |

### Tool Attack 专用参数

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `--attack-vector-type` | `type_i_a`, `type_i_b`, `type_ii_a`, `type_ii_b`, `type_iii_a` | 攻击向量类型 |
| `--attack-type` | `intent_hijacking`, `parameter_override`, 等 | 攻击子类型（可选） |

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-workers` | `1` | 并行worker数量 |
| `--force-rerun` | - | 强制重新运行（忽略缓存） |
| `--logdir` | - | 日志输出目录 |

## 攻击类型说明

### Tool Attack (工具攻击)

#### Type I-A: Docstring Injection (文档字符串注入)
- **intent_hijacking**: 意图劫持 - 通过恶意docstring劫持agent目标
- **parameter_override**: 参数覆盖 - 通过docstring覆盖函数参数

#### Type I-B: Logic Trap (逻辑陷阱)
- 在工具实现中植入隐式的恶意逻辑

#### Type II-A: Reasoning Distortion (推理扭曲)
- 通过工具描述误导agent的推理过程

#### Type II-B: Over-Optimization (过度优化)
- 通过提供"更强大"的恶意工具诱导agent选择

#### Type III-A: SOP Injection (SOP注入)
- 通过错误消息注入标准操作程序(SOP)

### Important Instructions Attack

agentdojo原始的攻击方式，直接在用户查询中注入恶意指令。

## 调试技巧

### 设置断点

1. 在VIGIL框架代码中设置断点：
   - `vigil_agent/enhanced_auditor.py` - 审计逻辑
   - `vigil_agent/perception_sanitizer.py` - 输入清洗
   - `vigil_agent/hypothesizer.py` - 假设生成

2. 启动调试（F5）

3. 代码会在断点处暂停

### 查看变量

- 使用 Debug Console 查看变量
- 使用 Variables 面板查看局部变量
- 使用 Watch 面板监视特定表达式

### 查看日志

日志会输出到 `--logdir` 指定的目录：
- `runs/vigil/<suite>/<attack_type>/`

## 常见问题

### Q: 如何测试所有injection tasks？
A: 使用预定义的配置运行不同的suite和attack-type组合，或者使用自定义模板配置。

### Q: 如何更改模型？
A: 修改 `--model` 参数，例如改为 `gpt-4o-mini`

### Q: 如何查看VIGIL的审计统计？
A: 查看运行日志，搜索 "VIGIL" 或 "Audit" 关键词

### Q: 如何添加新的suite配置？
A: 复制现有配置，修改 `--suite` 和 `--logdir` 参数

## 快速测试示例

### 测试 Banking Suite 的 Type I-A Intent Hijacking
1. 选择配置: "VIGIL | Banking | Type I-A | Intent Hijacking"
2. 按 F5 开始调试
3. 查看终端输出和日志文件

### 测试 Travel Suite 的所有攻击
依次运行：
1. "VIGIL | Travel | Type I-A | Parameter Override"
2. "VIGIL | Travel | Type II-A"

### 自定义测试
1. 打开 "VIGIL | Custom Suite & Attack (Template)"
2. 修改参数：
   - Suite: `slack`
   - Attack Vector: `type_ii_b`
3. 运行调试

## 输出结果

运行后会在指定的logdir生成：
- 详细的执行日志
- VIGIL的审计决策记录
- 工具调用历史
- 攻击成功/失败统计

## 相关文件

- `.vscode/launch.json` - 本配置文件
- `vigil_agent/` - VIGIL框架实现
- `src/agentdojo/scripts/benchmark.py` - Benchmark脚本
- `src/agentdojo/attacks/tool_attack.py` - Tool Attack实现
- `src/agentdojo/attacks/important_instructions_attacks.py` - Important Instructions实现
