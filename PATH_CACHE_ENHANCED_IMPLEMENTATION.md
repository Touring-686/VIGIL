# Path Cache 增强实现总结

## 已完成的工作

### 1. ✅ HypothesisBranch 添加 source 字段
- **文件**: `vigil_agent/hypothesizer.py`
- **修改**: 添加 `source: str = "hypothesis_generation"` 字段
- **作用**: 标记分支来源（hypothesis_generation 或 path_cache）

### 2. ✅ PathCache 支持 abstract step description
- **文件**: `vigil_agent/path_cache.py`
- **主要修改**:
  - `VerifiedPath` 添加 `abstract_step_description` 字段
  - 修改 path_id 生成逻辑，优先使用 abstract_step_description
  - 添加 `_abstract_step_index` 索引
  - 更新 `add_verified_path()`、`to_dict()`、`import_cache()` 方法

### 3. ✅ 实现 top-K 检索
- **文件**: `vigil_agent/path_cache.py`
- **新方法**:
  - `retrieve_paths_by_abstract_step(abstract_step_description, top_k=3)` - 主要检索接口
  - `_fuzzy_match_abstract_step()` - 基于 Jaccard 相似度的模糊匹配

### 4. ✅ 实现 LLM 选择器
- **文件**: `vigil_agent/path_cache.py`
- **新方法**:
  - `select_tool_with_llm(abstract_step_description, candidate_paths)` - 主接口
  - `_build_selector_prompt()` - 构造提示
  - `_parse_selector_result()` - 解析 LLM 响应
- **特性**:
  - 使用 LLM 从 top-K 候选中选择最合适的工具
  - 有回退机制（无 LLM client 时选择执行次数最多的）
  - 记录 token 使用统计

### 5. ✅ 更新 EnhancedPipeline
- **文件**: `vigil_agent/enhanced_pipeline.py`
- **修改**: PathCache 初始化时传递 `openai_client` 和 `token_tracker`

## 待完成的工作

### 6. ⏳ 修改 HypothesisGuidanceElement（进行中）
需要在生成 hypothesis tree 之前：
1. 检查当前步骤的 abstract step description
2. 调用 `path_cache.retrieve_paths_by_abstract_step()` 获取 top-3
3. 如果有缓存，调用 `path_cache.select_tool_with_llm()` 选择最佳工具
4. 构造 HypothesisBranch，标记 `source='path_cache'`
5. 跳过正常的 hypothesis generation 流程
6. 如果没有缓存，走正常流程

### 7. ⏳ 修改 CommitmentManager（待开始）
需要检查 branch 的 source 字段：
- 如果 `source == 'path_cache'`，跳过 verification，直接接受
- 如果 `source == 'hypothesis_generation'`，进行正常的 verification

### 8. ⏳ 测试完整流程（待开始）
- 创建测试脚本验证整个流程
- 测试缓存命中和未命中的情况
- 验证 LLM 选择器的工作情况
- 验证 verification 跳过逻辑

## 关键流程图

```
┌─────────────────────────────────────────────────────────────┐
│ HypothesisGuidanceElement.query()                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
         ┌──────────────────────────────────┐
         │ 获取当前 abstract step description│
         └──────────────────────────────────┘
                           │
                           ▼
      ┌──────────────────────────────────────────┐
      │ path_cache.retrieve_paths_by_abstract_step│
      │        (返回 top-3 候选)                   │
      └──────────────────────────────────────────┘
                           │
               ┌───────────┴───────────┐
               │                       │
           有缓存                    无缓存
               │                       │
               ▼                       ▼
  ┌────────────────────────┐   ┌──────────────────┐
  │ path_cache.           │   │ 正常生成          │
  │ select_tool_with_llm  │   │ hypothesis tree  │
  │  (LLM 选择最佳工具)     │   └──────────────────┘
  └────────────────────────┘            │
               │                        ▼
               │              ┌──────────────────┐
               │              │ CommitmentManager│
               │              │   (完整验证)      │
               │              └──────────────────┘
               ▼
  ┌────────────────────────┐
  │ 构造 HypothesisBranch  │
  │ source='path_cache'   │
  └────────────────────────┘
               │
               ▼
  ┌────────────────────────┐
  │ CommitmentManager      │
  │ (跳过验证，直接接受)     │
  └────────────────────────┘
               │
               ▼
  ┌────────────────────────┐
  │ 直接执行工具            │
  └────────────────────────┘
```

## 技术细节

### Path Cache Key 设计
- **Old**: `(user_query, step_index, tool_name)` → 粒度太粗
- **New**: `(abstract_step_description, tool_name)` → 更精确的语义匹配

### 相似度匹配
- 使用 Jaccard 相似度：`similarity = |A ∩ B| / |A ∪ B|`
- 阈值：0.5（可配置）
- 支持模糊匹配，提高召回率

### LLM 选择器
- **输入**: 当前 abstract step + top-K 候选工具
- **输出**: 最佳工具 + 选择理由
- **模型**: 使用 `config.hypothesizer_model`（默认 gpt-4o-mini）
- **温度**: 0.0（确定性选择）

### 验证跳过逻辑
- Path cache 中的工具都是已经验证过的成功路径
- 标记 `source='path_cache'` 允许 CommitmentManager 识别并跳过验证
- 节省时间和 token 消耗

## 向后兼容性
- ✅ 所有修改都保持向后兼容
- ✅ 默认配置 `enable_path_cache=False` 不影响现有行为
- ✅ 旧的缓存数据仍可导入（optional 字段）
- ✅ 支持三种索引方式（query、step_query、abstract_step）

## 下一步操作
继续实现：
1. HypothesisGuidanceElement 的 Path Cache 集成
2. CommitmentManager 的验证跳过逻辑
3. 完整的端到端测试
