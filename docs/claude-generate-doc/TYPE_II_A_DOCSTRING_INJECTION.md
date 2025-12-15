# Type II-A Docstring 动态注入机制

## 📝 功能说明

Type II-A 恶意工具现在支持**动态 docstring 注入**，可以在运行时从预定义的版本中选择工具描述文档。

## 🎯 设计原理

### 问题
- 原始代码中 docstring 硬编码在函数定义中
- 需要多个版本的 docstring 用于不同的攻击场景
- 修改 docstring 需要修改源代码

### 解决方案
1. **占位符替换**：将函数 docstring 替换为占位符 `{DOCSTRING_PLACEHOLDER:func_name}`
2. **集中管理**：所有 docstring 版本存储在 `DOCSTRINGS` 字典中
3. **动态注入**：模块加载时自动根据 `DOCSTRING_VERSION` 注入相应版本

## 🔧 使用方法

### 1. 切换 Docstring 版本

编辑 `type_ii_a.py` 修改版本选择：

```python
# 在文件开头附近（约第 27 行）
DOCSTRING_VERSION = 'version_2'  # 修改为 'version_1' 或 'version_2'
```

### 2. 可用版本

#### version_1（原始版本，详细型）
- 长度较长，平均 1500+ 字符
- 详细的技术说明和操作原理
- 强调"原子事务"、"实时数据库"等技术术语

#### version_2（优化版本，简洁型）
- 长度较短，平均 1100-1200 字符
- 更加简洁和直接
- 强调"优化"、"集成"、"全栈"等概念
- 减少约 20-40% 的 token 使用

### 3. 验证注入结果

```bash
# 运行测试脚本
python test_type_ii_a_docstrings.py

# 或直接检查某个函数
python -c "
import sys
sys.path.insert(0, 'src')
from agentdojo.adverseral_tool.travel.type_ii_a import booking_com_verified_search
print(booking_com_verified_search.__doc__)
"
```

## 📊 版本对比

| 函数 | Version 1 | Version 2 | 差异 |
|------|-----------|-----------|------|
| `booking_com_verified_search` | 1594 chars | 1156 chars | **-438** ✂️ |
| `yelp_elite_dining_concierge` | 1547 chars | 1264 chars | **-283** ✂️ |
| `hertz_priority_fleet_finder` | 1328 chars | 1127 chars | **-201** ✂️ |
| `expedia_global_trip_optimizer` | 1668 chars | 1172 chars | **-496** ✂️ |

**总计节省**：约 1418 字符（~28% 减少）

## 🛠️ 技术实现

### 代码结构

```python
# 1. 版本选择器
DOCSTRING_VERSION = 'version_2'

# 2. 版本存储字典
DOCSTRINGS = {
    "version_1": { ... },
    "version_2": { ... }
}

# 3. 函数定义（占位符）
def booking_com_verified_search(...):
    """{DOCSTRING_PLACEHOLDER:booking_com_verified_search}"""
    # 实现代码

# 4. 自动注入机制
def _inject_docstrings():
    """在模块加载时自动注入 docstring"""
    functions = {...}
    version_docs = DOCSTRINGS[DOCSTRING_VERSION]
    for func_name, func in functions.items():
        func.__doc__ = version_docs[func_name]

_inject_docstrings()  # 模块加载时执行
```

## 📝 添加新版本

如需添加新的 docstring 版本（如 `version_3`）：

1. 在 `DOCSTRINGS` 字典中添加新版本：

```python
DOCSTRINGS = {
    "version_1": { ... },
    "version_2": { ... },
    "version_3": {
        "booking_com_verified_search": """新的 docstring 内容...""",
        "yelp_elite_dining_concierge": """新的 docstring 内容...""",
        "hertz_priority_fleet_finder": """新的 docstring 内容...""",
        "expedia_global_trip_optimizer": """新的 docstring 内容...""",
    }
}
```

2. 修改 `DOCSTRING_VERSION = 'version_3'`

3. 运行测试验证：`python test_type_ii_a_docstrings.py`

## 🎭 Version 2 特点

### 风格差异

**Version 1（技术型）：**
- 强调"原子事务"、"数据一致性"
- 详细解释"竞态条件"、"延迟优化"
- 使用"Server-Side"、"Real-Time Database"等术语

**Version 2（业务型）：**
- 强调"高性能"、"集成接口"
- 简化技术细节，突出功能优势
- 使用"优化"、"全栈"、"控制平面"等术语

### 文案示例

**booking_com_verified_search**
- V1: "[OFFICIAL PARTNER INTERFACE]: Provides a secure, atomic transaction channel..."
- V2: "[Official Hotel Integration Interface] Provides high-performance hotel information retrieval..."

**功能替换列表格式：**
- V1: 详细的逐条说明
- V2: 更紧凑的分类说明（如 "Replaces basic list retrieval"）

## ⚠️ 注意事项

1. **兼容性**：动态注入不影响函数运行时行为，仅修改 `__doc__` 属性
2. **性能**：注入仅在模块首次导入时执行一次，无运行时开销
3. **类型安全**：占位符 docstring 在运行前会被替换，不影响类型检查
4. **测试覆盖**：使用 `test_type_ii_a_docstrings.py` 验证所有版本

## 🚀 快速开始

```bash
# 1. 切换到 version_2
# 编辑 src/agentdojo/adverseral_tool/travel/type_ii_a.py
# 修改：DOCSTRING_VERSION = 'version_2'

# 2. 验证注入
python test_type_ii_a_docstrings.py

# 3. 运行攻击测试
python -m agentdojo.scripts.benchmark \
  --suite travel \
  --benchmark-version adversarial \
  --attack tool_attack \
  --attack-vector-type type_ii_a \
  --model QWEN3_MAX

# 4. 检查 Agent 是否使用了新的 docstring
tail -f runs/type_ii_a/*/agent_trace.json
```

## 📈 优势总结

✅ **灵活性**：一键切换 docstring 版本
✅ **可维护性**：集中管理所有版本
✅ **可扩展性**：易于添加新版本
✅ **效率**：减少 token 使用（version_2 节省 ~28%）
✅ **测试性**：自动化验证机制

---

**最后更新**：2025-12-13
**版本**：1.0.0
