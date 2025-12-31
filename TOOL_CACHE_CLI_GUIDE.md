# Tool Cache 命令行参数使用指南

## 概述

现在可以通过命令行参数 `--use-tool-cache` 来控制 VIGIL 框架中的 Tool Sanitization 缓存功能。

## 问题背景

VIGIL 框架的 Perception Sanitizer 会清洗所有工具的文档字符串（docstring），以防止 Type I-A 攻击。这个清洗过程：
- 调用 LLM 进行文档清洗
- 需要消耗 token 和时间
- 对于相同的工具集，清洗结果是确定的

## 解决方案

通过 `--use-tool-cache` 参数，可以：
1. **首次运行**：执行工具清洗，并将结果保存到磁盘（`vigil_cache/sanitized_tools/`）
2. **后续运行**：直接从磁盘加载已清洗的工具，跳过清洗过程

## 使用方法

### 方式 1: 不使用缓存（默认）

每次运行都会执行工具清洗：

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --attack direct \
    --framework enhanced \
    --config balanced
```

日志输出：
```
[ToolDocstringSanitizer] Disk cache: ✗ Disabled (will sanitize tools)
Tool Cache: ✗ Disabled (will sanitize tools)
```

### 方式 2: 使用缓存

添加 `--use-tool-cache` 标志来启用缓存：

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --attack direct \
    --framework enhanced \
    --config balanced \
    --use-tool-cache
```

日志输出：
```
[ToolDocstringSanitizer] Disk cache: ✓ Enabled
Tool Cache: ✓ Enabled (loading from disk)
[ToolDocstringSanitizer] ✓ Loaded description cache from vigil_cache/sanitized_tools/banking_description.json
[ToolDocstringSanitizer] ✓ Loaded docstring cache from vigil_cache/sanitized_tools/banking_docstring.json
```

## 工作流程

### 首次运行（生成缓存）

```bash
# 第一次运行，会执行清洗并保存缓存
python run_vigil_benchmark.py \
    --suite banking \
    --framework enhanced \
    --use-tool-cache

# 输出：
# [ToolDocstringSanitizer] Disk cache: ✓ Enabled
# [ToolDocstringSanitizer] Disk cache disabled, will sanitize all tools
# ... 执行清洗 ...
# [ToolDocstringSanitizer] ✓ Sanitized and cached 15 tools
# [ToolDocstringSanitizer] ✓ Saved docstring cache to vigil_cache/sanitized_tools/banking_docstring.json
# [ToolDocstringSanitizer] ✓ Saved description cache to vigil_cache/sanitized_tools/banking_description.json
```

### 后续运行（使用缓存）

```bash
# 第二次及以后运行，直接加载缓存
python run_vigil_benchmark.py \
    --suite banking \
    --framework enhanced \
    --use-tool-cache

# 输出：
# [ToolDocstringSanitizer] Disk cache: ✓ Enabled
# [ToolDocstringSanitizer] ✓ Loaded description cache from vigil_cache/sanitized_tools/banking_description.json
# [ToolDocstringSanitizer] ✓ Loaded docstring cache from vigil_cache/sanitized_tools/banking_docstring.json
# [ToolDocstringSanitizer] ✓ Sanitized and cached 15 tools
```

## 缓存文件位置

缓存文件保存在：
```
vigil_cache/sanitized_tools/
├── banking_docstring.json      # Banking suite 的工具文档字符串
├── banking_description.json    # Banking suite 的工具描述
├── travel_docstring.json       # Travel suite 的工具文档字符串
├── travel_description.json     # Travel suite 的工具描述
├── slack_docstring.json        # Slack suite 的工具文档字符串
├── slack_description.json      # Slack suite 的工具描述
└── ...
```

每个 suite 都有独立的缓存文件。

## 完整示例

### 示例 1: Banking Suite（使用工具缓存）

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --attack direct \
    --framework enhanced \
    --config balanced \
    --model gpt-4o \
    --use-tool-cache \
    --output ./results_with_tool_cache
```

### 示例 2: Travel Suite（不使用工具缓存，但使用 Path Cache）

```bash
python run_vigil_benchmark.py \
    --suite travel \
    --attack tool_attack \
    --attack-vector-type type_iii_a \
    --framework enhanced \
    --config strict \
    --model gpt-4o \
    --enable-path-cache \
    --output ./results_with_path_cache_only
```

### 示例 3: 同时使用 Path Cache 和 Tool Cache

```bash
python run_vigil_benchmark.py \
    --suite workspace \
    --attack none \
    --framework enhanced \
    --config fast \
    --model gpt-4o-mini \
    --enable-path-cache \
    --use-tool-cache \
    --max-tasks 10
```

## 优势

### 使用 Tool Cache 的好处

✅ **节省时间**: 跳过工具清洗步骤，加快启动速度
✅ **节省 Token**: 不需要重复调用 LLM 清洗相同的工具
✅ **一致性**: 确保每次运行使用相同的清洗结果
✅ **调试友好**: 快速迭代测试，无需等待工具清洗

### 何时使用 Tool Cache

**推荐使用场景：**
- 重复测试相同的 suite
- 工具集没有变化
- 需要快速迭代调试
- 生产环境部署

**不推荐使用场景：**
- 工具集发生了变化（需要重新清洗）
- 第一次运行新的 suite
- 怀疑缓存数据有问题

## 清除缓存

如果需要重新生成缓存（例如工具集更新了），删除缓存文件即可：

```bash
# 删除所有缓存
rm -rf vigil_cache/sanitized_tools/

# 或者只删除特定 suite 的缓存
rm vigil_cache/sanitized_tools/banking_*
```

下次运行时会自动重新生成。

## 与 Path Cache 的区别

| 特性 | Tool Cache (`--use-tool-cache`) | Path Cache (`--enable-path-cache`) |
|------|--------------------------------|-----------------------------------|
| **作用** | 缓存清洗后的工具文档 | 缓存成功的执行路径 |
| **目的** | 跳过工具清洗步骤 | 跳过 Hypothesis-Verification 循环 |
| **存储** | 磁盘文件 | 内存 + 磁盘（可选） |
| **适用** | 重复运行相同工具集 | 重复执行相似任务 |
| **清除** | 删除缓存文件 | 重启程序 |

## 组合使用

可以同时使用两个缓存来最大化性能：

```bash
python run_vigil_benchmark.py \
    --suite banking \
    --framework enhanced \
    --enable-path-cache \    # 启用 Path Cache
    --use-tool-cache \       # 启用 Tool Cache
    --output ./results
```

这样可以：
1. **Tool Cache**: 快速加载已清洗的工具（节省启动时间）
2. **Path Cache**: 快速选择已验证的工具调用（节省执行时间）

## 常见问题

### Q: 什么时候会保存缓存到磁盘？
A: 只有当 `--use-tool-cache` 启用时，才会保存缓存到磁盘。否则即使清洗了工具，也不会保存。

### Q: 缓存文件有多大？
A: 通常每个 suite 的缓存文件在几 KB 到几十 KB 之间，非常小。

### Q: 如何知道缓存是否被使用？
A: 查看日志输出：
- `✓ Loaded ... cache from ...` - 表示加载了缓存
- `will sanitize all tools` - 表示没有缓存，将执行清洗

### Q: 修改了工具代码后需要重新生成缓存吗？
A: 是的。如果工具的文档字符串发生了变化，需要删除缓存文件并重新运行。

### Q: Tool Cache 和 enable_perception_sanitizer 配置的关系？
A:
- 如果 `enable_perception_sanitizer=False`，清洗器完全禁用，Tool Cache 无效
- 如果 `enable_perception_sanitizer=True`：
  - `--use-tool-cache` 未设置：每次都清洗
  - `--use-tool-cache` 设置：从缓存加载

## 总结

通过 `--use-tool-cache` 参数，你可以：
- ✅ 跳过工具清洗步骤，加快启动速度
- ✅ 节省 LLM token 消耗
- ✅ 确保清洗结果的一致性
- ✅ 加速调试和测试流程

```bash
# 简单记忆：
# 不加参数 = 每次都清洗工具
# 加 --use-tool-cache = 使用缓存的清洗结果
```
