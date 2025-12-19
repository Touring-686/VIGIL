# Benchmark Execution Guide

这个目录包含用于运行AgentDojo benchmark的脚本和配置。

## 文件说明

- `run_all_benchmarks.sh` - 并行运行所有24个benchmark任务
- `run_single_task.sh` - 运行单个benchmark任务
- `ALL_COMMANDS.md` - 所有24条独立命令的完整列表

## 快速开始

### 1. 运行所有24个任务（并行）

```bash
./run_all_benchmarks.sh
```

这将启动所有24个任务作为后台进程。每个任务的输出和日志将保存到不同的文件中。

### 2. 运行单个任务

```bash
./run_single_task.sh <suite> <attack_vector> [attack_type]
```

**参数说明：**
- `suite`: 选择suite（travel, workspace, banking, slack）
- `attack_vector`: 攻击向量类型
- `attack_type`: 攻击类型（某些向量需要）

**示例：**
```bash
# Type I-A
./run_single_task.sh travel type_i_a parameter_override

# Type II-A (不需要attack_type)
./run_single_task.sh workspace type_ii_a

# Type III-A
./run_single_task.sh banking type_iii_a sop_exfiltration
```

## 任务组合说明

总共有 **4个suites × 6种攻击组合 = 24个任务**

### Suites (4个)
- `travel`
- `workspace`
- `banking`
- `slack`

### Attack组合 (6种)

| Attack Vector | Attack Type | 数量 |
|--------------|-------------|------|
| `type_i_a` | `parameter_override` | 4 |
| `type_i_b` | `prerequisite_dependency` | 4 |
| `type_i_b` | `postaction_dependency` | 4 |
| `type_ii_a` | (无) | 4 |
| `type_ii_b` | (无) | 4 |
| `type_iii_a` | `sop_exfiltration` | 4 |

## 输出文件位置

运行脚本后，文件将保存在以下位置：

```
.
├── outputs/              # 标准输出
│   ├── travel_type_i_a_parameter_override.out
│   ├── workspace_type_i_a_parameter_override.out
│   └── ...
├── logs/                 # 错误日志
│   ├── travel_type_i_a_parameter_override.log
│   ├── workspace_type_i_a_parameter_override.log
│   └── ...
└── runs/                 # Benchmark结果 (JSON)
    └── QWEN3_MAX/
        └── ...
```

## 监控和管理

### 实时查看日志
```bash
# 查看特定任务的日志
tail -f logs/travel_type_i_a_parameter_override.log

# 查看所有错误
tail -f logs/*.log
```

### 检查运行状态
```bash
# 查看所有运行中的benchmark任务
ps aux | grep benchmark

# 统计运行中的任务数
ps aux | grep benchmark | wc -l
```

### 终止任务
```bash
# 终止所有benchmark任务
pkill -f 'agentdojo.scripts.benchmark'

# 终止特定任务（使用PID）
kill <PID>
```

## 使用注意事项

1. **并行运行限制**：虽然脚本会并行启动所有任务，但实际并发数取决于你的系统资源（CPU、内存、API限制）。

2. **API限制**：如果使用的模型API有速率限制，可能需要分批运行任务。

3. **磁盘空间**：确保有足够的磁盘空间存储输出文件和日志。

4. **运行时间**：根据你的描述，每个任务可能需要较长时间。24个任务并行运行可能需要数小时。

## 调试技巧

### 查找失败的任务
```bash
# 在日志中查找错误
grep -r "Error\|error\|failed" logs/

# 查看非零退出码的任务
for log in logs/*.log; do
    if grep -q "exit code" "$log"; then
        echo "Failed: $log"
    fi
done
```

### 重新运行失败的任务
```bash
# 使用run_single_task.sh重新运行特定任务
./run_single_task.sh travel type_i_a parameter_override
```

## 高级用法

### 分批运行
如果不想一次运行所有24个任务，可以编辑`run_all_benchmarks.sh`，注释掉不需要立即运行的部分。

### 自定义参数
编辑脚本中的`BASE_ARGS`变量来修改默认参数：
```bash
BASE_ARGS="--benchmark-version adversarial --attack tool_attack --defense melon --model QWEN3_MAX --max-workers 1 --force-rerun --logdir ./runs"
```

## 完整命令列表

如果你需要手动运行或在其他环境中复制命令，请参考`ALL_COMMANDS.md`文件，其中包含所有24条完整的命令。

## 问题排查

### 权限错误
```bash
chmod +x run_all_benchmarks.sh run_single_task.sh
```

### Python模块未找到
确保你在正确的环境中，并且agentdojo已安装：
```bash
pip install -e .
```

### 日志文件过大
定期清理旧的日志文件：
```bash
# 清理输出和日志
rm -rf outputs/* logs/*

# 但保留runs目录中的结果
```
