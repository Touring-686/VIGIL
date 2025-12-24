# VIGIL Agent Framework - 使用总结

## 🎉 已完成的工作

我为你创建了一个完整的基于VIGIL框架的agent脚手架，具有以下特点：

### ✨ 核心特性

1. **低耦合设计**: vigil_agent模块独立于agentdojo，可以轻松修改和扩展
2. **即插即用**: 一行代码即可创建VIGIL pipeline
3. **高度可配置**: 丰富的配置选项，适应不同场景
4. **完整文档**: 详细的代码注释、README、快速启动指南和示例

### 📦 项目结构

```
agentdojo/
├── vigil_agent/                    # VIGIL框架模块（你的agent实现）
│   ├── __init__.py                 # 公共API
│   ├── types.py                    # 类型定义
│   ├── config.py                   # 配置类和预定义配置
│   ├── constraint_generator.py     # 约束生成器
│   ├── runtime_auditor.py          # 运行时审计器
│   ├── vigil_executor.py           # VIGIL执行器
│   ├── vigil_pipeline.py           # Pipeline工厂方法
│   ├── test_vigil.py               # 测试脚本
│   ├── README.md                   # 完整文档
│   └── QUICKSTART.md               # 快速启动指南
│
├── examples/
│   └── vigil_benchmark_example.py  # 完整使用示例
│
└── run_vigil.py                    # 快速运行脚本
```

## 🚀 快速开始

### 1. 最简单的方式（3行代码）

```python
from vigil_agent import create_vigil_pipeline, VIGIL_BALANCED_CONFIG
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
import openai

client = openai.OpenAI()
llm = OpenAILLM(client, "gpt-4o")
pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)
```

### 2. 使用快速运行脚本

```bash
# 设置OpenAI API key
export OPENAI_API_KEY='your-key-here'

# 运行
python run_vigil.py
```

修改 `run_vigil.py` 中的配置来测试不同的suite和模型。

### 3. 完整的benchmark示例

```bash
python examples/vigil_benchmark_example.py
```

## 🏗️ VIGIL架构说明

VIGIL实现了你的设计思想：

```
User Query
    ↓
[1. Constraint Generator] ← 动态生成符号化约束（只信任用户查询）
    ↓
[2. Speculative Planner] ← LLM自由推理和尝试
    ↓
[3. Runtime Auditor] ← 符号化验证（快速、确定性）
    ↓ (如果被拦截)
[4. Reflective Backtracking] ← 返回反馈，允许重试
```

### 核心组件

1. **ConstraintGenerator** (`constraint_generator.py`):
   - 使用LLM分析用户查询
   - 生成结构化的安全约束（JSON格式）
   - 支持缓存以提高性能

2. **RuntimeAuditor** (`runtime_auditor.py`):
   - 基于符号化规则验证工具调用
   - 支持模式匹配、操作类型推断
   - 可插拔的自定义验证器

3. **VIGILToolsExecutor** (`vigil_executor.py`):
   - 在工具执行前进行审计
   - 实现反思回溯机制
   - 跟踪回溯次数，防止无限循环

4. **VIGILAgentPipeline** (`vigil_pipeline.py`):
   - 整合所有组件的完整pipeline
   - 提供工厂方法简化创建
   - 支持从现有pipeline转换

## 🎨 配置和定制

### 预定义配置

```python
# 严格模式 - 最大化安全性
VIGIL_STRICT_CONFIG

# 平衡模式 - 推荐使用
VIGIL_BALANCED_CONFIG

# 快速模式 - 最小开销
VIGIL_FAST_CONFIG
```

### 自定义配置示例

```python
from vigil_agent import VIGILConfig, create_vigil_pipeline

custom_config = VIGILConfig(
    # 约束生成
    constraint_generator_model="gpt-4o",
    enable_constraint_caching=True,

    # 审计模式
    auditor_mode="hybrid",  # "strict" | "permissive" | "hybrid"

    # 反思回溯
    max_backtracking_attempts=5,
    feedback_verbosity="detailed",

    # 白名单/黑名单
    allow_tool_whitelist=["get_balance"],
    block_tool_blacklist=["delete_account"],
)

pipeline = create_vigil_pipeline(llm, config=custom_config)
```

## 🔧 如何修改和扩展

### 场景1: 修改约束生成提示

编辑 `constraint_generator.py` 中的 `DEFAULT_CONSTRAINT_GENERATION_PROMPT`，或通过配置传入：

```python
config = VIGILConfig(
    constraint_generation_prompt_template="Your custom prompt here..."
)
```

### 场景2: 添加自定义验证器

```python
def my_verifier(tool_call, constraint):
    # 你的验证逻辑
    return True  # 或 False

config = VIGILConfig(
    custom_constraint_verifiers={
        "my_constraint_id": my_verifier
    }
)
```

### 场景3: 修改审计逻辑

直接编辑 `runtime_auditor.py` 中的 `RuntimeAuditor` 类：
- `_is_constraint_applicable`: 约束适用性判断
- `_infer_operation_from_tool`: 操作类型推断
- `_extract_target_from_arguments`: 目标提取

### 场景4: 调整回溯策略

编辑 `vigil_executor.py` 中的 `VIGILToolsExecutor.query` 方法。

## 📊 运行测试

### 基本测试

```bash
export PYTHONPATH=/Users/justin/BDAA/ACL/code/agentdojo/src:/Users/justin/BDAA/ACL/code/agentdojo:$PYTHONPATH
python vigil_agent/test_vigil.py
```

预期输出：
```
Passed: 3/5  # 另外2个需要OpenAI API key
```

### 完整benchmark测试

```bash
export OPENAI_API_KEY='your-key-here'
python run_vigil.py
```

## 📖 文档索引

1. **README.md** - 完整文档，包含架构说明、API文档
2. **QUICKSTART.md** - 5分钟快速开始指南
3. **examples/vigil_benchmark_example.py** - 6个完整示例
4. **代码注释** - 每个类和方法都有详细的docstring

## 💡 下一步建议

1. **测试基本功能**:
   ```bash
   python vigil_agent/test_vigil.py
   ```

2. **在小规模数据上测试**:
   修改 `run_vigil.py`，添加：
   ```python
   user_tasks=list(suite.user_tasks.keys())[:2],
   injection_tasks=list(suite.injection_tasks.keys())[:3],
   ```

3. **根据结果调整配置**:
   - 如果security太低：使用 `VIGIL_STRICT_CONFIG`
   - 如果utility太低：增加 `max_backtracking_attempts`
   - 如果速度太慢：启用 `enable_constraint_caching`

4. **优化约束生成提示**:
   根据你的具体场景，修改 `DEFAULT_CONSTRAINT_GENERATION_PROMPT`

5. **扩展验证逻辑**:
   在 `RuntimeAuditor` 中添加针对你的攻击类型的特定验证

## 🔑 关键设计决策

1. **低耦合**: vigil_agent完全独立，可以作为单独的包使用
2. **可扩展**: 每个组件都可以单独替换或继承
3. **类型安全**: 完整的类型提示，IDE友好
4. **配置驱动**: 大部分行为可通过配置修改，无需改代码
5. **兼容性**: 实现标准的BasePipelineElement接口，兼容所有agentdojo功能

## 🤝 与benchmark集成

VIGIL pipeline完全兼容agentdojo的所有benchmark功能：

```python
from agentdojo.benchmark import (
    benchmark_suite_with_injections,
    benchmark_suite_without_injections
)

# 有攻击
results = benchmark_suite_with_injections(pipeline, suite, attack, logdir, False)

# 无攻击（测试utility）
results = benchmark_suite_without_injections(pipeline, suite, logdir, False)
```

## 📝 总结

你现在拥有：
- ✅ 完整实现的VIGIL框架
- ✅ 清晰的模块化架构
- ✅ 丰富的配置选项
- ✅ 详细的文档和示例
- ✅ 与benchmark低耦合的设计
- ✅ 即使不熟悉agentdojo也能快速修改

可以直接开始使用和修改！如有任何问题，请查阅文档或代码注释。
