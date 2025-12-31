# Path Cache 配置使用指南

## 概述

Path Cache（路径缓存）是 VIGIL 框架的学习机制，能够从成功的执行中学习并优化后续相似任务的性能。

## 功能特性

- **学习能力**: 缓存已验证的成功执行路径
- **快速检索**: 对相似查询快速推荐已验证的工具
- **安全保证**: 只缓存经过安全验证的路径
- **步骤级缓存**: 支持多步骤任务的细粒度缓存

## 配置选项

### 1. 通过 VIGILConfig 配置

```python
from vigil_agent.config import VIGILConfig

# 启用 path cache
config = VIGILConfig(enable_path_cache=True)

# 禁用 path cache
config = VIGILConfig(enable_path_cache=False)
```

### 2. 使用预设配置

```python
from vigil_agent.config import get_vigil_config

# strict 模式 - 默认禁用 path cache（最大化安全性）
strict_config = get_vigil_config("strict", "gpt-4o")

# balanced 模式 - 默认启用 path cache（平衡性能和安全）
balanced_config = get_vigil_config("balanced", "gpt-4o")

# fast 模式 - 默认启用 path cache（最大化速度）
fast_config = get_vigil_config("fast", "gpt-4o")
```

### 预设配置默认值

| 模式 | enable_path_cache | 说明 |
|------|-------------------|------|
| strict | False | 最大化安全性，每次都重新验证 |
| balanced | True | 平衡性能和安全，启用学习机制 |
| fast | True | 最大化速度，充分利用缓存 |

## 使用示例

### 基本使用

```python
from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

# 创建配置（启用 path cache）
config = VIGILConfig(enable_path_cache=True)

# 创建 LLM
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")

# 创建 Pipeline
pipeline = EnhancedVIGILPipeline(config=config, llm=llm)

# Path cache 会在执行过程中自动学习和优化
```

### 在 Benchmark 中使用

```python
from vigil_agent.config import get_vigil_config
from vigil_agent.enhanced_pipeline import create_enhanced_vigil_pipeline
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.benchmark import benchmark_suite_with_injections
import openai

# 使用 balanced 配置（默认启用 path cache）
config = get_vigil_config("balanced", "gpt-4o")

# 创建 LLM 和 Pipeline
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")
pipeline = create_enhanced_vigil_pipeline(llm, config=config)

# 运行 benchmark
results = benchmark_suite_with_injections(
    pipeline,
    suite,
    attack,
    logdir="./logs",
    force_rerun=False
)

# 查看缓存统计
cache_stats = pipeline.get_path_cache_stats()
print(f"缓存统计: {cache_stats}")
```

### 动态控制 Path Cache

```python
# 方式 1: 通过配置创建时决定
config_with_cache = VIGILConfig(enable_path_cache=True)
pipeline_with_cache = EnhancedVIGILPipeline(config=config_with_cache, llm=llm)

config_without_cache = VIGILConfig(enable_path_cache=False)
pipeline_without_cache = EnhancedVIGILPipeline(config=config_without_cache, llm=llm)

# 方式 2: 根据任务类型选择不同配置
def create_pipeline_for_task(task_type: str):
    if task_type == "critical":
        # 关键任务：使用 strict 模式（禁用缓存）
        config = get_vigil_config("strict", "gpt-4o")
    elif task_type == "routine":
        # 常规任务：使用 fast 模式（启用缓存）
        config = get_vigil_config("fast", "gpt-4o")
    else:
        # 默认：使用 balanced 模式
        config = get_vigil_config("balanced", "gpt-4o")

    return create_enhanced_vigil_pipeline(llm, config=config)
```

## 获取统计信息

```python
# 获取 path cache 统计信息
stats = pipeline.get_path_cache_stats()

print(f"总缓存路径数: {stats['total_cached_paths']}")
print(f"成功路径数: {stats['successful_paths']}")
print(f"失败路径数: {stats['failed_paths']}")
print(f"总执行次数: {stats['total_executions']}")
print(f"唯一查询数: {stats['unique_queries']}")
```

## 何时启用 Path Cache

### 适合启用的场景

1. **重复性任务**: 需要执行相似操作的场景
2. **高频查询**: 频繁执行的常规任务
3. **性能敏感**: 对响应时间有要求的场景
4. **稳定环境**: 工具集和环境相对稳定

### 适合禁用的场景

1. **关键任务**: 安全性优先，需要每次都重新验证
2. **动态环境**: 工具集或环境频繁变化
3. **首次测试**: 初次测试新的工具或场景
4. **调试阶段**: 需要观察完整的推理过程

## 实现原理

Path Cache 的工作流程：

1. **学习阶段**:
   - Agent 执行工具调用
   - 审计器验证操作安全性
   - 成功的操作被添加到缓存

2. **检索阶段**:
   - 接收到新查询
   - 在缓存中查找相似的已验证路径
   - 推荐最常用且成功的工具

3. **优化效果**:
   - 跳过 Hypothesis-Verification 循环
   - 减少 LLM 推理时间
   - 提高任务执行一致性

## 注意事项

1. Path Cache 是可选功能，默认禁用（`enable_path_cache=False`）
2. 启用后会在内存中维护缓存，长期运行可能占用一定内存
3. 缓存的路径仅包含经过安全验证的操作
4. 不同任务之间的 pipeline 实例不共享缓存（每个实例独立）
5. 可以通过 `pipeline.reset_for_new_task()` 重置缓存状态

## 相关配置项

Path Cache 的行为还受以下配置影响：

- `enable_hypothesis_generation`: 是否启用假设生成（与 path cache 协同工作）
- `enable_direct_tool_execution`: 是否直接执行推荐的工具
- `auditor_mode`: 审计模式（影响路径是否被缓存）

## 参考资料

- `vigil_agent/path_cache.py` - Path Cache 实现
- `vigil_agent/config.py` - 配置选项定义
- `vigil_agent/enhanced_pipeline.py` - Pipeline 集成
- `test_path_cache_config.py` - 测试示例
