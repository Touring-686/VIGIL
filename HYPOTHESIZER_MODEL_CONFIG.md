# Hypothesizer 模型配置指南

## 问题说明

如果你看到以下错误：
```
ERROR [Hypothesizer] LLM reasoning failed: Error code: 404 - {'error': {'message': 'The model `gpt-4o-mini` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}
```

这是因为你的 OpenAI client 配置指向了阿里云的 DashScope API，但使用了 `gpt-4o-mini` 这个模型名称。

---

## 解决方案

### 方法 1：通过 `get_vigil_config` 函数指定模型

```python
from vigil_agent import get_vigil_config

# 为大部分组件使用 qwen-plus，为 hypothesizer 使用 qwen-turbo（更快速）
config = get_vigil_config(
    preset="balanced",
    model="qwen-plus",           # 用于其他组件（Sketch, Constraint, Sanitizer）
    hypothesizer_model="qwen-turbo"  # 专门为 Hypothesizer 指定模型
)
```

### 方法 2：直接创建 VIGILConfig

```python
from vigil_agent.config import VIGILConfig

config = VIGILConfig(
    # 其他组件使用的模型
    constraint_generator_model="qwen-plus",
    sketch_generator_model="qwen-plus",
    sanitizer_model="qwen-max",

    # Hypothesizer 使用的模型
    hypothesizer_model="qwen-turbo",  # 阿里云支持的模型
    hypothesizer_temperature=0.0,
    max_hypothesis_branches=10,

    # 其他配置...
    enable_hypothesis_generation=True,
    enable_abstract_sketch=True,
)
```

---

## 阿里云 DashScope 支持的模型

如果你使用阿里云 DashScope API，推荐使用以下模型：

| 模型名称 | 特点 | 适用场景 |
|---------|------|---------|
| `qwen-turbo` | 快速、成本低 | Hypothesizer（需要多次调用） |
| `qwen-plus` | 平衡性能和成本 | 大部分组件 |
| `qwen-max` | 最强性能 | Sanitizer（需要高质量清洗） |
| `qwen3-max` | Qwen 3.0 最强版本 | 复杂推理任务 |

---

## 完整示例

```python
from vigil_agent import create_enhanced_vigil_pipeline, get_vigil_config
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

# 创建 OpenAI client（配置为阿里云 DashScope）
client = openai.OpenAI(
    api_key="your-dashscope-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 创建 LLM（用于主 agent）
llm = OpenAILLM(client, "qwen-plus")

# 创建 VIGIL 配置（为 hypothesizer 指定不同的模型）
config = get_vigil_config(
    preset="balanced",
    model="qwen-plus",              # 其他组件使用 qwen-plus
    hypothesizer_model="qwen-turbo" # Hypothesizer 使用 qwen-turbo（更快）
)

# 创建 VIGIL pipeline
pipeline = create_enhanced_vigil_pipeline(llm, config=config)

# 运行 benchmark
from agentdojo.benchmark import benchmark_suite_with_injections
results = benchmark_suite_with_injections(
    pipeline,
    suite,
    attack,
    logdir,
    force_rerun=False
)
```

---

## 环境变量方式（可选）

你也可以通过环境变量设置默认模型：

```bash
export VIGIL_LLM_MODEL="qwen-plus"
export VIGIL_HYPOTHESIZER_MODEL="qwen-turbo"
```

然后在代码中：

```python
import os
from vigil_agent import get_vigil_config

model = os.getenv("VIGIL_LLM_MODEL", "qwen-plus")
hypothesizer_model = os.getenv("VIGIL_HYPOTHESIZER_MODEL", "qwen-turbo")

config = get_vigil_config("balanced", model, hypothesizer_model)
```

---

## 为什么 Hypothesizer 可以使用不同的模型？

1. **调用频率高**：Hypothesizer 在每个决策点都会被调用，使用更快/便宜的模型可以降低成本
2. **任务相对简单**：只需要从候选工具中筛选相关的工具，不需要最强的推理能力
3. **温度为 0**：不需要创造性，只需要准确性，较小的模型也能胜任

推荐配置：
- **Hypothesizer**: `qwen-turbo` (快速 + 低成本)
- **Sketch Generator**: `qwen-plus` (需要理解任务结构)
- **Sanitizer**: `qwen-max` (需要高质量的清洗)
- **Constraint Generator**: `qwen-plus` (需要生成精确的约束)

---

## 故障排查

如果仍然遇到模型错误：

1. **检查 API Key**：确保你的 API key 有权限访问该模型
2. **检查 base_url**：确保指向正确的 API endpoint
3. **查看日志**：检查 `[Hypothesizer]` 的日志输出，确认使用的模型名称
4. **测试连接**：
   ```python
   response = client.chat.completions.create(
       model="qwen-turbo",
       messages=[{"role": "user", "content": "test"}],
       max_tokens=10
   )
   print(response.choices[0].message.content)
   ```
