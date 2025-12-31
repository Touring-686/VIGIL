# Path Cache 命令行参数使用指南

## 概述

现在可以通过命令行参数 `--enable-path-cache` 来控制 VIGIL 框架中的 Path Cache 功能。

## 使用方法

### 1. 禁用 Path Cache（默认）

不使用 `--enable-path-cache` 标志，Path Cache 将被禁用：

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --attack direct \
    --framework enhanced \
    --config balanced \
    --model gpt-4o
```

输出将显示：
```
Path Cache: ✗ Disabled
```

### 2. 启用 Path Cache

添加 `--enable-path-cache` 标志来启用 Path Cache：

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --attack direct \
    --framework enhanced \
    --config balanced \
    --model gpt-4o \
    --enable-path-cache
```

输出将显示：
```
Path Cache: ✓ Enabled
[EnhancedVIGIL] Path Cache auto-created from config (learning enabled)
```

## 完整示例

### 示例 1: 在 Banking Suite 上使用 Path Cache

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --attack direct \
    --framework enhanced \
    --config balanced \
    --model gpt-4o \
    --enable-path-cache \
    --output ./results_with_cache
```

### 示例 2: 在 Travel Suite 上不使用 Path Cache

```bash
python run_vigil_benchmark.py \
    --suite travel \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --framework enhanced \
    --config strict \
    --model gpt-4o \
    --output ./results_without_cache
```

### 示例 3: 快速测试（启用 Path Cache）

```bash
python run_vigil_benchmark.py \
    --suite workspace \
    --attack none \
    --framework enhanced \
    --config fast \
    --model gpt-4o-mini \
    --enable-path-cache \
    --max-tasks 5
```

## Path Cache 的作用

当启用 Path Cache 时：

1. **学习成功路径**: 系统会记录所有成功执行的工具调用
2. **智能推荐**: 对于相似的任务步骤，优先使用之前成功的工具
3. **性能提升**: 跳过 Hypothesis-Verification 循环，直接使用缓存的工具
4. **逐步优化**: 随着运行次数增加，系统变得越来越智能

### 何时使用 Path Cache

**推荐使用场景：**
- 重复运行相似任务
- 生产环境部署
- 性能敏感的应用
- 需要快速响应的场景

**不推荐使用场景：**
- 首次测试新环境
- 需要探索所有可能路径
- 调试特定工具调用问题

## 其他相关参数

```bash
# 完整的命令行参数列表
python run_vigil_benchmark.py --help

可用参数：
  --suite              Task suite (banking/travel/slack/workspace)
  --attack             Attack type (direct/tool_attack/none)
  --attack-vector-type Attack vector (type_i_a/type_i_b/etc.)
  --framework          VIGIL framework (basic/enhanced)
  --config             Config preset (strict/balanced/fast)
  --model              OpenAI model (gpt-4o/gpt-4o-mini/etc.)
  --output             Output directory
  --max-tasks          Maximum tasks to run
  --max-injections     Maximum injection tasks
  --force-rerun        Force rerun all tasks
  --verbose            Enable verbose logging
  --enable-path-cache  Enable Path Cache ← 新增！
```

## 验证 Path Cache 是否工作

启用 Path Cache 后，日志中会显示：

```
[HypothesisGuidance] 🔍 Querying Path Cache for abstract step 0: '...'
[HypothesisGuidance] ✓ Path Cache HIT: 'tool_name' (used 3 times successfully)
[HypothesisGuidance] ⚡ Fast path: Using cached tool 'tool_name', skipping hypothesis tree generation
```

如果看到 "Path Cache HIT" 和 "Fast path"，说明 Path Cache 正在工作。

## 与配置文件的关系

命令行参数 `--enable-path-cache` 会覆盖配置文件中的 `enable_path_cache` 设置：

```python
# 配置文件设置会被命令行参数覆盖
config = get_vigil_config(preset, model)
config.enable_path_cache = args.enable_path_cache  # ← 命令行参数优先
```

## 常见问题

### Q: Path Cache 数据存储在哪里？
A: 默认情况下，Path Cache 存储在内存中。如果需要持久化，可以使用 Path Cache 的 `export_cache()` 和 `import_cache()` 方法。

### Q: 如何清除 Path Cache？
A: 重启程序即可，因为 Path Cache 默认存储在内存中。

### Q: Path Cache 会影响安全性吗？
A: 不会。Path Cache 只缓存**已通过安全审计**的成功执行路径。所有缓存的工具调用都已经过 VIGIL 框架的完整验证。

### Q: 不同任务之间的 Path Cache 是共享的吗？
A: 在单次运行中，所有任务共享同一个 Path Cache 实例。这意味着后面的任务可以从前面任务的执行中学习。

## 总结

通过简单添加 `--enable-path-cache` 标志，你就可以启用 VIGIL 框架的学习能力，让系统从成功执行中学习并逐步优化性能！

```bash
# 简单记忆：
# 不加参数 = 不使用 Path Cache
# 加 --enable-path-cache = 使用 Path Cache
```
