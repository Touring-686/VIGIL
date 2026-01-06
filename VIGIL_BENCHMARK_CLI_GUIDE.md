# VIGIL Defense 命令行参数使用指南

## 使用 AgentDojo Benchmark 脚本

当使用 `python -m agentdojo.scripts.benchmark` 运行 VIGIL 防御时，现在可以通过命令行参数控制 Tool Cache 和 Path Cache。

## 使用方法

### 基本用法（不使用任何缓存）

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite slack \
    --attack tool_attack \
    --attack-vector-type type_iii_b
```

### 启用 Tool Cache

使用 `--use-tool-cache` 标志来从磁盘加载已清洗的工具：

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite slack \
    --attack tool_attack \
    --attack-vector-type type_iii_b \
    --use-tool-cache
```

### 启用 Path Cache

使用 `--enable-path-cache` 标志来启用执行路径学习：

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite slack \
    --attack tool_attack \
    --attack-vector-type type_iii_b \
    --enable-path-cache
```

### 同时启用两个缓存

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite slack \
    --attack tool_attack \
    --attack-vector-type type_iii_b \
    --use-tool-cache \
    --enable-path-cache
```

## 完整示例

### 示例 1: Slack Suite + Type III-B Attack（使用所有优化）

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite slack \
    --attack tool_attack \
    --attack-vector-type type_iii_b \
    --use-tool-cache \
    --enable-path-cache \
    --logdir ./results/slack_vigil_optimized
```

### 示例 2: Banking Suite（仅 Tool Cache）

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite banking \
    --attack direct \
    --use-tool-cache \
    --logdir ./results/banking_vigil_tool_cache
```

### 示例 3: 多 Suite 测试

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite banking slack travel workspace \
    --attack tool_attack \
    --attack-vector-type type_iii_b \
    --use-tool-cache \
    --enable-path-cache
```

### 示例 4: 单个任务调试

```bash
python -m agentdojo.scripts.benchmark \
    --model gpt-4o \
    --defense vigil \
    --suite slack \
    --attack tool_attack \
    --attack-vector-type type_iii_b \
    --injection-task-id injection_task_301 \
    --use-tool-cache \
    --force-rerun
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--use-tool-cache` | Flag | False | 使用磁盘缓存的已清洗工具（跳过工具清洗） |
| `--enable-path-cache` | Flag | False | 启用 Path Cache（从成功执行中学习） |
| `--defense` | String | None | 必须设置为 `vigil` 才能使用 VIGIL 框架 |
| `--model` | String | gpt-4o-2024-05-13 | LLM 模型名称 |
| `--suite` | String(s) | All | 要测试的任务套件 |
| `--attack` | String | None | 攻击类型（tool_attack, direct, etc.） |
| `--attack-vector-type` | String | None | 攻击向量类型（type_i_a 到 type_iii_b） |
| `--logdir` | Path | ./runs | 日志输出目录 |
| `--force-rerun` | Flag | False | 强制重新运行所有任务 |

## 注意事项

### 仅对 VIGIL Defense 有效

`--use-tool-cache` 和 `--enable-path-cache` **仅在使用 `--defense vigil` 时有效**。对于其他 defense 策略，这些参数会被忽略。

### Tool Cache 的工作流程

1. **首次运行（生成缓存）**:
   ```bash
   python -m agentdojo.scripts.benchmark \
       --defense vigil \
       --suite slack \
       --use-tool-cache
   ```
   - 执行工具清洗
   - 保存到 `vigil_cache/sanitized_tools/slack_*.json`

2. **后续运行（使用缓存）**:
   ```bash
   python -m agentdojo.scripts.benchmark \
       --defense vigil \
       --suite slack \
       --use-tool-cache
   ```
   - 直接从缓存加载
   - 跳过工具清洗步骤
   - 节省时间和 token

### Path Cache 的工作流程

- Path Cache 在内存中维护
- 随着任务执行逐步学习
- 在单次运行中，后面的任务可以利用前面任务的学习结果

## 性能对比

| 配置 | 启动时间 | Token 消耗 | 执行时间 |
|------|---------|-----------|----------|
| 无缓存 | 慢 | 高 | 正常 |
| Tool Cache | 快 | 中 | 正常 |
| Path Cache | 慢 | 高 | 快 |
| 两者都启用 | 快 | 中 | 快 |

## 查看帮助

```bash
python -m agentdojo.scripts.benchmark --help
```

## 常见问题

### Q: 如何清除 Tool Cache？
A: 删除 `vigil_cache/sanitized_tools/` 目录下的缓存文件。

### Q: Tool Cache 对所有 suite 通用吗？
A: 不是，每个 suite 有独立的缓存文件（如 `slack_docstring.json`、`banking_docstring.json`）。

### Q: 可以在多进程运行中使用缓存吗？
A: 可以。使用 `--max-workers N` 时，缓存参数会传递给所有并行进程。

### Q: 如何验证缓存是否生效？
A: 查看日志输出：
- Tool Cache: `[ToolDocstringSanitizer] ✓ Loaded ... cache from ...`
- Path Cache: `[HypothesisGuidance] ✓ Path Cache HIT: ...`

## 总结

通过命令行参数控制缓存，你可以：
- ✅ 在不修改代码的情况下启用/禁用缓存
- ✅ 灵活控制每次运行的行为
- ✅ 快速迭代测试和调试
- ✅ 节省时间和 token 消耗

```bash
# 简单记忆：
python -m agentdojo.scripts.benchmark \
    --defense vigil \              # 使用 VIGIL 防御
    --use-tool-cache \             # 使用工具缓存
    --enable-path-cache \          # 启用路径缓存
    --suite slack \                # 测试 suite
    --attack tool_attack           # 攻击类型
```
