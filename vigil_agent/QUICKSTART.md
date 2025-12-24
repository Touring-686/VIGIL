# VIGIL Framework - 快速启动指南

## 5分钟快速开始

### 1. 最简单的使用方式

```python
from vigil_agent import create_vigil_pipeline, VIGIL_BALANCED_CONFIG
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.benchmark import benchmark_suite_with_injections
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.attacks.base_attacks import DirectAttack
from pathlib import Path
import openai

# 三行代码创建VIGIL agent
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")
pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

# 在benchmark上运行
suite = get_suite("v1", "banking")
attack = DirectAttack()
results = benchmark_suite_with_injections(
    pipeline, suite, attack, Path("./runs"), force_rerun=False
)

print(f"Utility: {sum(results['utility_results'].values()) / len(results['utility_results']):.2%}")
print(f"Security: {sum(results['security_results'].values()) / len(results['security_results']):.2%}")
```

### 2. 运行测试

```bash
cd vigil_agent
python test_vigil.py
```

### 3. 运行完整示例

```bash
cd examples
python vigil_benchmark_example.py
```

## 配置选择指南

### VIGIL_STRICT_CONFIG - 严格模式
- **适用场景**: 高安全性要求，宁可误杀不可放过
- **特点**: 任何违反约束的操作都会被拦截
- **性能**: 较慢，但最安全

```python
from vigil_agent import VIGIL_STRICT_CONFIG, create_vigil_pipeline
pipeline = create_vigil_pipeline(llm, config=VIGIL_STRICT_CONFIG)
```

### VIGIL_BALANCED_CONFIG - 平衡模式 (推荐)
- **适用场景**: 大部分场景，安全性和实用性的平衡
- **特点**: 根据约束优先级决定是否拦截
- **性能**: 适中，推荐用于benchmark

```python
from vigil_agent import VIGIL_BALANCED_CONFIG, create_vigil_pipeline
pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)
```

### VIGIL_FAST_CONFIG - 快速模式
- **适用场景**: 快速原型开发，性能优先
- **特点**: 只记录违规但不拦截
- **性能**: 最快，最小开销

```python
from vigil_agent import VIGIL_FAST_CONFIG, create_vigil_pipeline
pipeline = create_vigil_pipeline(llm, config=VIGIL_FAST_CONFIG)
```

## 常见自定义场景

### 场景1: 我想要更详细的反馈

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

config = VIGILConfig(
    feedback_verbosity="verbose",  # "minimal" | "detailed" | "verbose"
    log_level="DEBUG",
    log_constraint_generation=True,
    log_audit_decisions=True,
)

pipeline = create_vigil_pipeline(llm, config=config)
```

### 场景2: 我想要更多的回溯尝试次数

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

config = VIGILConfig(
    enable_reflective_backtracking=True,
    max_backtracking_attempts=10,  # 默认是3
)

pipeline = create_vigil_pipeline(llm, config=config)
```

### 场景3: 我想要设置工具白名单/黑名单

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

config = VIGILConfig(
    # 这些工具始终允许
    allow_tool_whitelist=["get_balance", "list_transactions", "get_user_info"],
    # 这些工具始终拒绝
    block_tool_blacklist=["delete_account", "transfer_all_money"],
)

pipeline = create_vigil_pipeline(llm, config=config)
```

### 场景4: 我想要使用不同的LLM生成约束

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

config = VIGILConfig(
    constraint_generator_model="gpt-4o",  # 用于生成约束
    constraint_generator_temperature=0.0,
)

# 执行agent使用另一个模型
llm = OpenAILLM(client, "gpt-4o-mini")  # 用于agent推理

pipeline = create_vigil_pipeline(llm, config=config)
```

## 与AgentDojo Benchmark集成

### 完整的Benchmark脚本模板

```python
#!/usr/bin/env python3
"""VIGIL Agent Benchmark Script"""

from pathlib import Path
import openai
from vigil_agent import create_vigil_pipeline, VIGIL_BALANCED_CONFIG
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.benchmark import benchmark_suite_with_injections
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.attacks.base_attacks import DirectAttack

def main():
    # 配置
    SUITE_NAME = "banking"  # "banking" | "slack" | "travel" | "workspace"
    MODEL = "gpt-4o"
    LOGDIR = Path("./vigil_runs")

    # 创建pipeline
    client = openai.OpenAI()
    llm = OpenAILLM(client, MODEL)
    pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

    # 加载suite和attack
    suite = get_suite("v1", SUITE_NAME)
    attack = DirectAttack()

    # 运行benchmark
    print(f"Running VIGIL benchmark on {SUITE_NAME} suite...")
    results = benchmark_suite_with_injections(
        agent_pipeline=pipeline,
        suite=suite,
        attack=attack,
        logdir=LOGDIR,
        force_rerun=False,
    )

    # 显示结果
    utility = results["utility_results"]
    security = results["security_results"]

    utility_rate = sum(utility.values()) / len(utility) if utility else 0
    security_rate = sum(security.values()) / len(security) if security else 0

    print(f"\nResults:")
    print(f"  Utility Rate: {utility_rate:.2%}")
    print(f"  Security Rate: {security_rate:.2%}")

    # 审计统计
    stats = pipeline.get_audit_stats()
    print(f"\nAudit Statistics:")
    print(f"  Total: {stats['total_audits']}")
    print(f"  Allowed: {stats['allowed']}")
    print(f"  Blocked: {stats['blocked']}")

if __name__ == "__main__":
    main()
```

保存为 `run_vigil_benchmark.py` 并运行：

```bash
python run_vigil_benchmark.py
```

## 调试技巧

### 查看生成的约束

```python
# 在运行后检查
constraint_set = pipeline.vigil_init_query.constraint_generator._constraint_cache
for query, cset in constraint_set.items():
    print(f"Query: {query}")
    for c in cset.constraints:
        print(f"  - [{c.constraint_type}] {c.description}")
```

### 查看审计决策

设置详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config = VIGILConfig(
    log_level="DEBUG",
    log_constraint_generation=True,
    log_audit_decisions=True,
)
```

### 单独测试组件

```python
from vigil_agent import ConstraintGenerator, RuntimeAuditor, VIGILConfig
from vigil_agent.types import ToolCallInfo

# 测试约束生成
config = VIGILConfig()
generator = ConstraintGenerator(config)
constraints = generator.generate_constraints("Your test query")

# 测试审计
auditor = RuntimeAuditor(config, constraints)
result = auditor.audit_tool_call({
    "tool_name": "test_tool",
    "arguments": {"arg": "value"},
    "tool_call_id": "123"
})

print(f"Allowed: {result.allowed}")
print(f"Feedback: {result.feedback_message}")
```

## 下一步

1. 阅读完整文档: `README.md`
2. 查看代码示例: `examples/vigil_benchmark_example.py`
3. 修改配置以适应你的需求
4. 在你的benchmark上运行测试
5. 根据结果调整配置和约束生成提示

## 常见问题

**Q: 如何修改约束生成的提示？**

A: 在VIGILConfig中设置 `constraint_generation_prompt_template`

**Q: 如何完全禁用某个工具？**

A: 使用 `block_tool_blacklist` 配置

**Q: 约束生成太慢怎么办？**

A: 启用缓存 `enable_constraint_caching=True` 或使用更快的模型

**Q: 如何与现有的defense机制结合？**

A: VIGIL可以单独使用，也可以与其他defense叠加。建议先单独测试VIGIL的效果。

**Q: 能否在运行时动态修改约束？**

A: 可以，调用 `pipeline.auditor.update_constraints(new_constraint_set)`
