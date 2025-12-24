# VIGIL Framework Testing Guide

## Overview

本指南介绍如何使用VIGIL框架对agentdojo中的所有攻击类型进行测试。

## 测试场景

### 1. Tool Attack (工具攻击) - 6种类型

VIGIL框架设计用于防御以下6种工具流投毒攻击：

#### Type I-A: Docstring Injection (文档字符串注入)
- **Intent Hijacking**: 通过恶意docstring劫持agent的目标
- **Parameter Override**: 通过docstring覆盖函数参数

#### Type I-B: Logic Trap (逻辑陷阱)
- 在工具实现中植入隐式的恶意逻辑

#### Type II-A: Reasoning Distortion (推理扭曲)
- 通过工具描述误导agent的推理过程

#### Type II-B: Over-Optimization (过度优化)
- 通过提供"更强大"的恶意工具诱导agent选择

#### Type III-A: SOP Injection (SOP注入)
- 通过错误消息注入标准操作程序(SOP)

### 2. Important Instructions Attack (重要指令攻击)

agentdojo原始的攻击方式，直接在用户查询中注入恶意指令。

## 测试的Suite

针对以下4个suite进行测试：
1. **banking** - 银行业务场景
2. **slack** - Slack通信场景
3. **travel** - 旅行预订场景
4. **workspace** - 工作区管理场景

## 使用方法

### 方式1: 完整测试所有场景

```bash
# 测试所有suite和所有攻击类型（需要较长时间）
python test_vigil_all_attacks.py

# 只测试特定suite
python test_vigil_all_attacks.py --suite banking

# 只测试tool attacks
python test_vigil_all_attacks.py --attack-type tool

# 只测试important instructions
python test_vigil_all_attacks.py --attack-type important_instructions

# 快速测试模式（只测试banking suite的type_i_a）
python test_vigil_all_attacks.py --quick-test
```

### 方式2: 调试单个攻击场景

```bash
# 测试banking suite的Type I-A intent hijacking
python debug_vigil_single_attack.py --suite banking --attack tool --attack-type type_i_a --subtype intent_hijacking

# 测试travel suite的Type II-A
python debug_vigil_single_attack.py --suite travel --attack tool --attack-type type_ii_a

# 测试slack suite的important instructions
python debug_vigil_single_attack.py --suite slack --attack important_instructions

# 使用strict配置测试
python debug_vigil_single_attack.py --suite banking --attack tool --attack-type type_i_a --config strict

# 使用verbose模式查看详细日志
python debug_vigil_single_attack.py --suite banking --attack tool --attack-type type_i_a --verbose
```

## VIGIL配置选项

提供3种预设配置：

### 1. VIGIL_BALANCED_CONFIG (默认)
- 平衡安全性和性能
- 启用所有4层防御
- 适合大多数场景

### 2. VIGIL_STRICT_CONFIG
- 最高安全性
- 更严格的必要性检查阈值
- 最多回溯次数

### 3. VIGIL_FAST_CONFIG
- 最小开销
- 关闭部分耗时组件
- 适合快速测试

## 输出结果

### 完整测试
结果保存在 `vigil_test_results/` 目录：
- `vigil_test_results_YYYYMMDD_HHMMSS.json` - 完整测试结果
- `logs/` - 每个测试的详细日志

### 调试单个攻击
结果保存在 `debug_logs/` 目录：
- `debug_logs/{suite}/{attack_type}/{subtype}/` - 测试日志

## 结果分析

每个测试会输出：
1. **任务成功率**: Agent是否完成了用户任务
2. **安全性**: Agent是否被攻击成功（是否执行了恶意操作）
3. **VIGIL统计**:
   - 总审计次数
   - 允许的操作数
   - 阻止的操作数
   - 阻止率

## 示例工作流

### 快速验证VIGIL是否工作
```bash
# 1. 快速测试单个场景
python debug_vigil_single_attack.py --suite banking --attack tool --attack-type type_i_a --subtype intent_hijacking

# 2. 检查日志
cat debug_logs/banking/type_i_a/intent_hijacking/*.log

# 3. 查看VIGIL是否阻止了恶意操作
```

### 完整性能评估
```bash
# 1. 运行所有测试
python test_vigil_all_attacks.py

# 2. 分析结果
python analyze_vigil_results.py vigil_test_results/vigil_test_results_*.json
```

### 针对特定攻击类型调优
```bash
# 1. 使用不同配置测试
python debug_vigil_single_attack.py --suite banking --attack tool --attack-type type_ii_a --config balanced
python debug_vigil_single_attack.py --suite banking --attack tool --attack-type type_ii_a --config strict

# 2. 比较结果
```

## VIGIL的4层架构

测试时，VIGIL的4层防御都会被激活：

1. **Layer 0: Perception Sanitizer**
   - 清洗工具文档和返回值
   - 防御 Type I-A, Type I-B, Type III-A

2. **Layer 1: Intent Anchor**
   - 生成抽象执行草图
   - 动态生成安全约束
   - 作为不可变的"北极星"

3. **Layer 2: Speculative Reasoner (Hypothesizer)**
   - 生成多分支假设
   - 符号化标记风险、必要性、冗余度
   - 防御 Type II-A, Type II-B

4. **Layer 3: Neuro-Symbolic Verifier**
   - 最小必要性检查
   - 冗余性检查
   - 草图一致性检查
   - 反思回溯

## 常见问题

### Q: 测试需要多长时间？
A:
- 单个攻击场景: 2-5分钟
- 单个suite所有攻击: 30-60分钟
- 所有4个suite所有攻击: 2-4小时

### Q: 如何查看VIGIL具体阻止了哪些操作？
A: 在日志目录中查看详细日志文件，搜索 "VIGIL" 或 "Blocked" 关键词。

### Q: 如何修改VIGIL的配置？
A:
1. 在脚本中使用预设配置: `--config balanced|strict|fast`
2. 或者在代码中自定义 `VIGILConfig`

### Q: 测试失败怎么办？
A:
1. 使用 `--verbose` 查看详细日志
2. 检查 OpenAI API key是否正确
3. 查看具体错误消息

## 进阶使用

### 自定义VIGIL配置
```python
from vigil_agent import VIGILConfig, create_enhanced_vigil_pipeline

custom_config = VIGILConfig(
    # 调整必要性阈值
    minimum_necessity_threshold=0.4,
    # 启用/禁用特定组件
    enable_redundancy_check=True,
    enable_sketch_consistency_check=True,
    # 调整回溯参数
    max_backtracking_attempts=5,
)

pipeline = create_enhanced_vigil_pipeline(llm, config=custom_config)
```

### 只测试特定的injection task
修改 `test_vigil_all_attacks.py`，在benchmark调用前过滤injection tasks。

### 对比不同防御方法
```bash
# 测试VIGIL
python test_vigil_all_attacks.py --suite banking

# 测试其他防御（修改脚本使用不同的defense）
# 例如: tool_filter, pi_detector等
```

## 相关文件

- `test_vigil_all_attacks.py` - 完整测试脚本
- `debug_vigil_single_attack.py` - 单攻击调试脚本
- `vigil_agent/` - VIGIL框架实现
- `src/agentdojo/adverseral_tool/` - 攻击实现
- `VIGIL_TESTING_GUIDE.md` - 本文档

## 联系与反馈

如果发现问题或有改进建议，请在项目中提issue。
