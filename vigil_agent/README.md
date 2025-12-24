# VIGIL Agent Framework

**V**erifiable **I**ntent-**G**uided **I**ntelligent **L**imiter

一个基于Neuro-Symbolic + Dynamic Constraints设计的AI Agent安全框架，专为AgentDojo benchmark设计，但可以轻松应用于其他场景。

## 🎯 核心思想

VIGIL框架基于以下设计原则：

1. **Dynamic vs. Static**: 安全约束不是静态的，而是根据用户查询动态生成
2. **Symbolic vs. Blackbox**: 使用可解释的符号化逻辑验证，而非黑盒LLM判断
3. **Neuro-Symbolic Fusion**: 结合LLM的理解能力和符号系统的可靠性
4. **Reflective Backtracking**: 被拦截时不直接失败，而是提供反馈让agent调整策略

## 🏗️ 架构

```
User Query
    ↓
┌─────────────────────────────────────────────────┐
│  1. Constraint Generator (Neuro-Symbolic)       │
│     - 分析用户意图                                │
│     - 生成符号化安全约束                          │
│     - 只信任用户查询，不信任工具文档               │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  2. Speculative Planner (Reasoning)             │
│     - LLM自由推理                                │
│     - 生成工具调用计划                            │
│     - 允许Trial-and-Error                        │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  3. Runtime Auditor (Verification)              │
│     - 符号化约束验证                              │
│     - 快速且确定性                                │
│     - 可插拔的验证器                              │
└─────────────────────────────────────────────────┘
    ↓ (if blocked)
┌─────────────────────────────────────────────────┐
│  4. Reflective Backtracking (Correction)        │
│     - 返回详细的安全反馈                          │
│     - Agent根据反馈调整策略                       │
│     - 多次尝试机会                                │
└─────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 基本使用

```python
from vigil_agent import create_vigil_pipeline, VIGIL_BALANCED_CONFIG
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

# 1. 创建LLM
client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")

# 2. 创建VIGIL pipeline（一行代码！）
pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

# 3. 在AgentDojo benchmark中使用
from agentdojo.benchmark import benchmark_suite_with_injections
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.attacks.base_attacks import DirectAttack
from pathlib import Path

suite = get_suite("v1", "banking")
attack = DirectAttack()

results = benchmark_suite_with_injections(
    agent_pipeline=pipeline,
    suite=suite,
    attack=attack,
    logdir=Path("./runs"),
    force_rerun=False
)

print(f"Utility: {sum(results['utility_results'].values()) / len(results['utility_results'])}")
print(f"Security: {sum(results['security_results'].values()) / len(results['security_results'])}")
```

### 自定义配置

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

# 创建自定义配置
custom_config = VIGILConfig(
    # 约束生成
    constraint_generator_model="gpt-4o",
    enable_constraint_caching=True,

    # 审计模式
    auditor_mode="strict",  # "strict" | "permissive" | "hybrid"
    enable_symbolic_verification=True,

    # 反思回溯
    enable_reflective_backtracking=True,
    max_backtracking_attempts=3,
    feedback_verbosity="detailed",  # "minimal" | "detailed" | "verbose"

    # 白名单/黑名单
    allow_tool_whitelist=["get_balance", "list_transactions"],
    block_tool_blacklist=["delete_account"],
)

pipeline = create_vigil_pipeline(llm, config=custom_config)
```

### 预定义配置

VIGIL提供三种预定义配置：

```python
from vigil_agent import (
    VIGIL_STRICT_CONFIG,   # 最大化安全性
    VIGIL_BALANCED_CONFIG, # 平衡安全性和性能
    VIGIL_FAST_CONFIG,     # 最小开销
    create_vigil_pipeline
)

# 使用严格模式
strict_pipeline = create_vigil_pipeline(llm, config=VIGIL_STRICT_CONFIG)

# 使用平衡模式（推荐）
balanced_pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

# 使用快速模式
fast_pipeline = create_vigil_pipeline(llm, config=VIGIL_FAST_CONFIG)
```

## 📚 核心组件详解

### 1. Constraint Generator

从用户查询动态生成安全约束：

```python
from vigil_agent import ConstraintGenerator, VIGILConfig

config = VIGILConfig()
generator = ConstraintGenerator(config)

# 生成约束
constraint_set = generator.generate_constraints(
    "Please transfer $100 to Alice"
)

# 查看生成的约束
for constraint in constraint_set.constraints:
    print(f"[{constraint.constraint_type}] {constraint.description}")
```

### 2. Runtime Auditor

验证工具调用是否符合约束：

```python
from vigil_agent import RuntimeAuditor, VIGILConfig
from vigil_agent.types import ToolCallInfo

config = VIGILConfig()
auditor = RuntimeAuditor(config, constraint_set)

# 审计工具调用
tool_call = ToolCallInfo(
    tool_name="transfer_money",
    arguments={"recipient": "Bob", "amount": 1000},
    tool_call_id="call_123"
)

result = auditor.audit_tool_call(tool_call)

if result.allowed:
    print("Tool call allowed")
else:
    print(f"Blocked: {result.feedback_message}")
```

### 3. VIGIL Tools Executor

整合了审计和回溯的工具执行器，直接集成到pipeline中。

### 4. VIGIL Pipeline

完整的agent pipeline，开箱即用。

## 🔧 高级用法

### 自定义约束生成提示

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

custom_prompt = """Your custom constraint generation prompt here...

USER QUERY: {user_query}

Generate constraints in JSON format..."""

config = VIGILConfig(
    constraint_generation_prompt_template=custom_prompt
)

pipeline = create_vigil_pipeline(llm, config=config)
```

### 自定义约束验证器

```python
from vigil_agent import VIGILConfig
from vigil_agent.types import ToolCallInfo, SecurityConstraint

def my_custom_verifier(tool_call: ToolCallInfo, constraint: SecurityConstraint) -> bool:
    """自定义验证逻辑"""
    # 实现你的验证逻辑
    return True  # 或 False

config = VIGILConfig(
    custom_constraint_verifiers={
        "my_constraint_id": my_custom_verifier
    }
)
```

### 从现有Pipeline转换

```python
from agentdojo.agent_pipeline.agent_pipeline import PipelineConfig, AgentPipeline
from vigil_agent import create_vigil_pipeline_from_base_pipeline

# 创建基础pipeline
base_config = PipelineConfig(
    llm="gpt-4o",
    defense=None,
    system_message_name="default"
)
base_pipeline = AgentPipeline.from_config(base_config)

# 转换为VIGIL pipeline
vigil_pipeline = create_vigil_pipeline_from_base_pipeline(base_pipeline)
```

### 监控和统计

```python
# 运行benchmark
results = benchmark_suite_with_injections(pipeline, suite, attack, logdir, False)

# 获取审计统计
stats = pipeline.get_audit_stats()
print(f"Total audits: {stats['total_audits']}")
print(f"Allowed: {stats['allowed']}")
print(f"Blocked: {stats['blocked']}")
print(f"Confirmed: {stats['confirmed']}")

# 为新任务重置状态
pipeline.reset_for_new_task()
```

## 🎨 设计特点

### 低耦合设计

VIGIL框架与AgentDojo benchmark低耦合：

- **独立模块**: vigil_agent可以作为独立包使用
- **标准接口**: 实现BasePipelineElement接口，兼容任何pipeline
- **易于扩展**: 每个组件都可以单独替换或扩展

### 易于修改

即使不熟悉AgentDojo，也可以轻松修改：

1. **配置驱动**: 大部分行为可通过VIGILConfig配置
2. **清晰的组件边界**: 每个组件职责单一
3. **丰富的文档**: 每个类和方法都有详细注释
4. **类型提示**: 完整的类型标注，IDE友好

### 可解释性

- **符号化约束**: 约束是结构化的，可以被检查和理解
- **详细日志**: 完整的审计日志和决策过程
- **透明验证**: 验证逻辑是确定性的，不是黑盒

## 📖 完整示例

见 `examples/vigil_benchmark_example.py`

## 🔍 架构图

```
vigil_agent/
├── __init__.py              # 公共API导出
├── types.py                 # 类型定义
├── config.py                # 配置类
├── constraint_generator.py  # 约束生成器
├── runtime_auditor.py       # 运行时审计器
├── vigil_executor.py        # VIGIL执行器
└── vigil_pipeline.py        # Pipeline工厂
```

## 🤝 贡献

欢迎贡献！你可以：

1. 实现新的约束验证器
2. 优化约束生成提示
3. 添加新的配置选项
4. 改进文档和示例

## 📝 许可证

MIT License

## 🙏 致谢

基于AgentDojo benchmark框架开发。
