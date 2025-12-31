# Path Cache 快速参考

## 一行代码启用/禁用

```python
from vigil_agent.config import VIGILConfig

# 启用 Path Cache
config = VIGILConfig(enable_path_cache=True)

# 禁用 Path Cache
config = VIGILConfig(enable_path_cache=False)
```

## 预设配置

```python
from vigil_agent.config import get_vigil_config

# strict: 禁用缓存 (最安全)
strict_config = get_vigil_config("strict", "gpt-4o")

# balanced: 启用缓存 (推荐)
balanced_config = get_vigil_config("balanced", "gpt-4o")

# fast: 启用缓存 (最快)
fast_config = get_vigil_config("fast", "gpt-4o")
```

## 在 Pipeline 中使用

```python
from vigil_agent.enhanced_pipeline import create_enhanced_vigil_pipeline
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

# 创建配置
config = VIGILConfig(enable_path_cache=True)

# 创建 Pipeline
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")
pipeline = create_enhanced_vigil_pipeline(llm, config=config)

# 检查状态
assert pipeline.path_cache is not None  # 已启用

# 获取统计
stats = pipeline.get_path_cache_stats()
print(stats)
```

## 选择指南

| 场景 | 推荐配置 | 说明 |
|------|----------|------|
| 生产环境 - 关键任务 | strict (禁用) | 最大化安全性 |
| 生产环境 - 常规任务 | balanced (启用) | 平衡性能和安全 |
| 开发测试 - 性能测试 | fast (启用) | 最大化速度 |
| 开发测试 - 调试 | strict (禁用) | 观察完整推理 |

## 常见问题

**Q: 默认是启用还是禁用？**
A: 默认禁用 (`enable_path_cache=False`)

**Q: 如何查看缓存是否生效？**
A: 使用 `pipeline.get_path_cache_stats()` 查看统计信息

**Q: 缓存会影响安全性吗？**
A: 不会。只有经过安全验证的路径才会被缓存

**Q: 如何清空缓存？**
A: 调用 `pipeline.reset_for_new_task()` 或 `pipeline.path_cache.clear()`

## 更多信息

- 详细文档: `PATH_CACHE_USAGE.md`
- 实现总结: `PATH_CACHE_IMPLEMENTATION_SUMMARY.md`
- 测试文件: `test_path_cache_config.py`
- 示例代码: `example_path_cache_usage.py`
