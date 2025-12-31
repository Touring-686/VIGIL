# Path Cache 使用指南

## 概述

Path Cache 现在可以通过参数控制，提供了更灵活的使用方式。

## 使用方式

### 方式 1: 不使用 Path Cache (默认)

```python
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
from vigil_agent.config import VIGILConfig

# 创建配置，关闭 Path Cache
config = VIGILConfig(
    enable_path_cache=False,  # 关闭自动创建
    # ... 其他配置
)

# 创建 Pipeline（不传入 path_cache 参数）
pipeline = EnhancedVIGILPipeline(
    config=config,
    llm=your_llm,
)

# Path Cache 将被禁用
```

### 方式 2: 使用自动创建的 Path Cache

```python
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
from vigil_agent.config import VIGILConfig

# 创建配置，启用 Path Cache
config = VIGILConfig(
    enable_path_cache=True,  # 启用自动创建
    # ... 其他配置
)

# 创建 Pipeline（不传入 path_cache 参数）
pipeline = EnhancedVIGILPipeline(
    config=config,
    llm=your_llm,
)

# Path Cache 将自动创建并使用
```

### 方式 3: 使用自定义 Path Cache（推荐）

```python
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
from vigil_agent.config import VIGILConfig
from vigil_agent.path_cache import PathCache
import openai

# 创建配置
config = VIGILConfig(
    enable_path_cache=False,  # 关闭自动创建
    # ... 其他配置
)

# 手动创建 Path Cache 实例
openai_client = openai.OpenAI()
my_path_cache = PathCache(
    config=config,
    openai_client=openai_client,
)

# 创建 Pipeline 并传入 Path Cache
pipeline = EnhancedVIGILPipeline(
    config=config,
    llm=your_llm,
    path_cache=my_path_cache,  # 显式传入
)

# 使用自定义的 Path Cache
```

### 方式 4: 在多个 Pipeline 间共享 Path Cache

```python
from vigil_agent.enhanced_pipeline import EnhancedVIGILPipeline
from vigil_agent.config import VIGILConfig
from vigil_agent.path_cache import PathCache
import openai

# 创建共享的 Path Cache
config = VIGILConfig(enable_path_cache=False)
openai_client = openai.OpenAI()
shared_cache = PathCache(config=config, openai_client=openai_client)

# 创建多个 Pipeline，共享同一个 Path Cache
pipeline1 = EnhancedVIGILPipeline(
    config=config,
    llm=your_llm1,
    path_cache=shared_cache,
)

pipeline2 = EnhancedVIGILPipeline(
    config=config,
    llm=your_llm2,
    path_cache=shared_cache,
)

# 两个 Pipeline 将共享学习的执行路径
```

## 优先级

Path Cache 的启用优先级如下：

1. **显式传入的 `path_cache` 参数** - 最高优先级
   - 如果传入了 `path_cache`，则使用传入的实例

2. **配置中的 `enable_path_cache`** - 次优先级
   - 如果没有传入 `path_cache`，但 `config.enable_path_cache=True`，则自动创建

3. **默认禁用** - 最低优先级
   - 如果既没有传入 `path_cache`，也没有设置 `enable_path_cache=True`，则禁用

## 日志输出

根据使用方式，你会看到不同的日志：

- 传入 Path Cache:
  ```
  [EnhancedVIGIL] Path Cache provided via parameter (learning enabled)
  ```

- 自动创建:
  ```
  [EnhancedVIGIL] Path Cache auto-created from config (learning enabled)
  ```

- 禁用:
  ```
  [EnhancedVIGIL] Path Cache disabled (not provided and config.enable_path_cache=False)
  ```

## 优势

### 控制粒度更细
- 可以选择性地为某些任务启用 Path Cache
- 可以在运行时决定是否使用缓存

### 共享学习
- 多个 Pipeline 可以共享同一个 Path Cache
- 加速整体学习过程

### 持久化支持
- 可以先创建 Path Cache，加载历史数据
- 然后传入多个 Pipeline 使用

```python
# 加载历史缓存
cache = PathCache(config=config, openai_client=client)
with open('cache.json', 'r') as f:
    cache_data = json.load(f)
    cache.import_cache(cache_data)

# 使用加载了历史的缓存
pipeline = EnhancedVIGILPipeline(
    config=config,
    llm=your_llm,
    path_cache=cache,
)
```

## 总结

通过参数控制 Path Cache，你可以：
- ✅ 完全禁用 Path Cache（不传参数，config.enable_path_cache=False）
- ✅ 使用自动创建的 Path Cache（config.enable_path_cache=True）
- ✅ 使用自定义的 Path Cache（传入 path_cache 参数）
- ✅ 在多个 Pipeline 间共享 Path Cache
- ✅ 加载和持久化 Path Cache
