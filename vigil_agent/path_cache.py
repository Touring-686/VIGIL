"""路径缓存 (Path Cache)

这是 VIGIL 框架的学习机制，负责缓存已验证的成功执行路径。

设计原则：
1. Learning from Experience: 从成功的执行中学习
2. Fast Retrieval: 快速检索（简单字典查找）
3. Safety Preservation: 只缓存经过安全验证的路径

核心机制：
- 简单的字典存储: {abstract_step_description: tool_name}
- add_verified_path: 字典写入操作 dict[key] = value
- retrieve_paths_by_abstract_step: 字典读取操作 dict.get(key)

Benefits:
1. 效率提升：跳过 Hypothesis-Verification 循环
2. 简单高效：O(1) 查找复杂度
3. 学习能力：从成功执行中学习
"""

import logging
from typing import Any

from vigil_agent.config import VIGILConfig

logger = logging.getLogger(__name__)


class VerifiedPath:
    """已验证的执行路径 - 简化版本

    只保留必要的字段：工具名称和执行次数
    """

    def __init__(self, tool_name: str, execution_count: int = 1):
        self.tool_name = tool_name
        self.execution_count = execution_count


class PathCache:
    """路径缓存 - 简化版本

    核心存储: {abstract_step_description: tool_name}
    简单的字典读写操作
    """

    def __init__(
        self,
        config: VIGILConfig,
        openai_client=None,
        token_tracker=None,
    ):
        """初始化路径缓存

        Args:
            config: VIGIL配置
            openai_client: OpenAI客户端（保留参数兼容性，但不使用）
            token_tracker: Token 统计追踪器（保留参数兼容性，但不使用）
        """
        self.config = config
        # 核心存储：{abstract_step_description: tool_name}
        self._cache: dict[str, str] = {}
        # 统计信息：{abstract_step_description: execution_count}
        self._execution_counts: dict[str, int] = {}

    def add_verified_path(
        self,
        user_query: str,
        tool_name: str,
        arguments: dict[str, Any],
        outcome: str,
        step_index: int | None = None,
        abstract_step: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加已验证的路径到缓存 - 简化版本（字典写入操作）

        Args:
            user_query: 用户查询（保留参数兼容性，但不使用）
            tool_name: 工具名称
            arguments: 工具参数（保留参数兼容性，但不使用）
            outcome: 执行结果 ("success" or "failure")
            step_index: 步骤索引（保留参数兼容性，但不使用）
            abstract_step_description: 抽象步骤描述（作为字典的 key）
            metadata: 额外元数据（保留参数兼容性，但不使用）
        """
        # 只缓存成功的执行，且必须有 abstract_step_description
        if outcome != "success" or not abstract_step:
            return

        # 规范化 abstract step description
        normalized_key = self._normalize_key(abstract_step)

        # 简单的字典写入操作: dict[key] = value
        self._cache[normalized_key] = tool_name

        # 更新执行计数
        if normalized_key in self._execution_counts:
            self._execution_counts[normalized_key] += 1
        else:
            self._execution_counts[normalized_key] = 1

        logger.info(
            f"[PathCache] Cached: '{abstract_step}' -> '{tool_name}' "
            f"(count: {self._execution_counts[normalized_key]})"
        )

    def retrieve_paths_by_abstract_step(
        self, abstract_step_step_type: str, top_k: int = 3
    ) -> list[VerifiedPath]:
        """基于 abstract step description 检索路径 - 简化版本（字典读取操作）

        Args:
            abstract_step_description: 抽象步骤描述
            top_k: 返回前 K 个（保留参数兼容性，简化版本只返回1个）

        Returns:
            匹配的路径列表（简化版本：要么返回1个，要么返回空列表）
        """
        # 规范化 key
        normalized_key = self._normalize_key(abstract_step_step_type)

        # 简单的字典读取操作: dict.get(key)
        tool_name = self._cache.get(normalized_key)

        if tool_name:
            # 找到缓存，返回 VerifiedPath 对象
            execution_count = self._execution_counts.get(normalized_key, 1)
            verified_path = VerifiedPath(tool_name, execution_count)

            logger.info(
                f"[PathCache] ✓ Cache HIT: '{abstract_step_step_type}...' -> '{tool_name}' "
                f"(used {execution_count} times)"
            )
            return [verified_path]
        else:
            # 未找到缓存
            logger.debug(
                f"[PathCache] ✗ Cache MISS: No cached tool for '{abstract_step_step_type}...'"
            )
            return []

    def select_tool_with_llm(
        self,
        abstract_step_description: str,
        candidate_paths: list[VerifiedPath],
    ) -> tuple[str | None, str | None]:
        """从候选路径中选择工具 - 简化版本（不使用 LLM）

        简化版本：直接返回第一个候选工具（因为 retrieve 只返回一个）

        Args:
            abstract_step_description: 当前抽象步骤描述（保留参数兼容性）
            candidate_paths: 候选路径列表

        Returns:
            (选中的工具名称, 选择理由)
        """
        if not candidate_paths:
            return None, None

        # 简化版本：直接返回第一个（也是唯一的）候选工具
        selected_path = candidate_paths[0]
        tool_name = selected_path.tool_name
        rationale = f"Cached tool from previous successful execution (used {selected_path.execution_count} times)"

        return tool_name, rationale

    def _normalize_key(self, abstract_step: str) -> str:
        """规范化 abstract step description 作为字典的 key

        Args:
            abstract_step_description: 抽象步骤描述

        Returns:
            规范化后的 key（转小写、去除多余空格）
        """
        return " ".join(abstract_step.lower().split())

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total_paths = len(self._cache)
        total_executions = sum(self._execution_counts.values())

        return {
            "total_cached_paths": total_paths,
            "successful_paths": total_paths,  # 简化版本只缓存成功的
            "failed_paths": 0,  # 简化版本不缓存失败的
            "total_executions": total_executions,
            "unique_queries": total_paths,
        }

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._execution_counts.clear()
        logger.info("[PathCache] Cache cleared")

    def export_cache(self) -> dict[str, Any]:
        """导出缓存数据

        Returns:
            缓存数据的字典表示
        """
        return {
            "cache": self._cache,
            "execution_counts": self._execution_counts,
            "stats": self.get_stats(),
        }

    def import_cache(self, cache_data: dict[str, Any]) -> None:
        """导入缓存数据

        Args:
            cache_data: 缓存数据
        """
        self.clear()

        self._cache = cache_data.get("cache", {})
        self._execution_counts = cache_data.get("execution_counts", {})

        logger.info(f"[PathCache] Imported {len(self._cache)} paths from cache data")

    # ===== 向后兼容的方法 =====
    # 这些方法保留是为了不破坏现有代码的调用

    def retrieve_paths(
        self, user_query: str, step_index: int | None = None
    ) -> list[VerifiedPath]:
        """向后兼容方法 - 转发到 retrieve_paths_by_abstract_step"""
        # 简化版本：将 user_query 当作 abstract_step_description
        return self.retrieve_paths_by_abstract_step(user_query, top_k=1)

    def get_recommended_tool(
        self, user_query: str, step_index: int | None = None
    ) -> str | None:
        """向后兼容方法 - 获取推荐的工具"""
        paths = self.retrieve_paths_by_abstract_step(user_query, top_k=1)
        if paths:
            return paths[0].tool_name
        return None
