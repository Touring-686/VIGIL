# 环境文件加载逻辑更新

## 概述
更新了环境文件加载逻辑，根据 `attack_type` 参数自动选择加载不同的环境文件。

## 修改内容

### 1. 修改 `load_and_inject_default_environment()` 方法

**文件**: `src/agentdojo/task_suite/task_suite.py`
**行数**: 146-153

**变更**:
- 增加了 `environment_file` 参数，默认值为 `"environment.yaml"`
- 支持指定自定义的环境文件名

```python
def load_and_inject_default_environment(self, injections: dict[str, str], environment_file: str = "environment.yaml") -> Env:
    environment_text = read_suite_file(self.name, environment_file, self.data_path)
    # ... 其余代码保持不变
```

### 2. 修改 `run_task_with_pipeline()` 方法

**文件**: `src/agentdojo/task_suite/task_suite.py`
**行数**: 758-771

**变更**:
- 增加了基于 `attack_type` 的环境文件选择逻辑
- 当 `attack_type` 为 `None` 或不是 `"tool_attack"` 时，加载 `"environment-bu.yaml"`
- 当 `attack_type` 为 `"tool_attack"` 时，加载 `"environment.yaml"`

```python
# Determine which environment file to use based on attack_type
if attack_type is None or attack_type != "tool_attack":
    # Use -bu.yaml suffix when attack is not tool_attack or no attack specified
    environment_file = "environment-bu.yaml"
else:
    # Use default environment.yaml for tool_attack
    environment_file = "environment.yaml"

if getattr(injection_task, "ATTACK_TYPE", None) == "parameter_override":
    environment = self.load_and_inject_default_environment(injections, environment_file)

if environment is None:
    environment = self.load_and_inject_default_environment(injections, environment_file)
```

## 环境文件选择逻辑表

| attack_type     | 加载的环境文件          | 说明                           |
|-----------------|-------------------------|--------------------------------|
| `None`          | `environment-bu.yaml`   | 没有指定攻击类型               |
| `"tool_attack"` | `environment.yaml`      | 使用 tool_attack 攻击          |
| 其他值          | `environment-bu.yaml`   | 使用其他类型的攻击（如 prompt_injection） |

## 影响范围

### 直接影响
- `run_task_with_pipeline()` - 在运行任务时根据攻击类型加载不同的环境文件
- `benchmark_suite_with_injections()` - 通过 `run_task_with_pipeline()` 间接影响

### 不受影响
- `check()` 方法 - 继续使用默认的 `environment.yaml` 进行验证
- 其他显式提供 `environment` 对象的调用

## 可用的环境文件

以下 suite 已经包含 `-bu.yaml` 环境文件：

```
src/agentdojo/data/suites/
├── travel/
│   ├── environment.yaml
│   └── environment-bu.yaml
├── slack/
│   ├── environment.yaml
│   └── environment-bu.yaml
├── banking/
│   ├── environment.yaml
│   └── environment-bu.yaml
└── workspace/
    ├── include/
    │   ├── calendar-bu.yaml
    │   ├── cloud_drive-bu.yaml
    │   └── inbox-bu.yaml
```

## 测试验证

运行测试脚本验证逻辑：
```bash
python test_environment_loading.py
```

所有测试场景均通过：
- ✓ attack_type 为 None 时选择 environment-bu.yaml
- ✓ attack_type 为 "tool_attack" 时选择 environment.yaml
- ✓ attack_type 为其他值时选择 environment-bu.yaml
- ✓ 两个环境文件均可成功加载

## 使用示例

### 在 benchmark.py 中使用

```bash
# 不指定 attack（使用 environment-bu.yaml）
python -m agentdojo.scripts.benchmark --suite travel --model gpt-4o

# 使用 tool_attack（使用 environment.yaml）
python -m agentdojo.scripts.benchmark --suite travel --model gpt-4o --attack tool_attack

# 使用其他攻击（使用 environment-bu.yaml）
python -m agentdojo.scripts.benchmark --suite travel --model gpt-4o --attack prompt_injection
```

### 在代码中直接调用

```python
from agentdojo.task_suite.load_suites import get_suite

suite = get_suite("v1.2.2", "travel")

# 加载默认环境文件
env_default = suite.load_and_inject_default_environment({})

# 加载 -bu.yaml 环境文件
env_bu = suite.load_and_inject_default_environment({}, "environment-bu.yaml")

# 在 run_task_with_pipeline 中，会根据 attack_type 自动选择
suite.run_task_with_pipeline(
    agent_pipeline,
    user_task,
    injection_task,
    injections={},
    attack_type="tool_attack",  # 使用 environment.yaml
)
```

## 向后兼容性

- ✅ 所有现有代码保持兼容
- ✅ 默认行为未改变（默认使用 environment.yaml）
- ✅ 只有在指定非 tool_attack 的 attack_type 时才会使用 -bu.yaml 文件
- ✅ check() 方法等内部验证功能不受影响

## 注意事项

1. 确保每个 suite 都有对应的 `-bu.yaml` 环境文件，否则在使用非 tool_attack 类型时会报错
2. `-bu.yaml` 文件的结构应与 `environment.yaml` 保持一致
3. 如果需要为特定任务指定环境，可以在调用 `run_task_with_pipeline()` 时直接传递 `environment` 参数
