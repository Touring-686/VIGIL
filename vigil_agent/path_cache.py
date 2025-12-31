"""路径缓存 (Path Cache)

这是 VIGIL 框架的学习机制，负责缓存已验证的成功执行路径。

设计原则：
1. Learning from Experience: 从成功的执行中学习
2. Fast Retrieval: 快速检索相似的查询
3. Safety Preservation: 只缓存经过安全验证的路径

核心机制：
- 存储 (Abstract Step Description → Tool) 映射
- 对于成功执行的路径，记录 (abstract_step_description, tool_name, arguments, outcome)
- 在后续遇到相似步骤时，使用 LLM 从 top-K 候选中选择最合适的工具

Benefits:
1. 效率提升：跳过 Hypothesis-Verification 循环
2. 一致性：对相似任务使用经过验证的方法
3. 学习能力：系统随使用变得越来越智能

Implementation Note:
当前实现使用简单的内存缓存和 Jaccard 相似度匹配。
使用 LLM 从缓存的候选工具中选择最合适的一个。
"""

import hashlib
import json
import logging
from typing import Any

import openai

from vigil_agent.config import VIGILConfig
from vigil_agent.token_stats_tracker import TokenStatsTracker, get_global_tracker

logger = logging.getLogger(__name__)


class VerifiedPath:
    """已验证的执行路径

    表示一条成功执行并通过安全验证的路径。
    支持基于 abstract step description 的缓存。
    """

    def __init__(
        self,
        user_query: str,
        tool_name: str,
        arguments: dict[str, Any],
        outcome: str,  # "success" or "failure"
        step_index: int | None = None,
        abstract_step_description: str | None = None,  # 新增：抽象步骤描述
        execution_count: int = 1,
        metadata: dict[str, Any] | None = None,
    ):
        """初始化已验证路径

        Args:
            user_query: 用户查询
            tool_name: 工具名称
            arguments: 工具参数
            outcome: 执行结果 ("success" or "failure")
            step_index: 步骤索引（用于多步骤任务）
            abstract_step_description: 抽象步骤描述（来自 Abstract Sketch）
            execution_count: 执行次数
            metadata: 额外元数据
        """
        self.user_query = user_query
        self.tool_name = tool_name
        self.arguments = arguments
        self.outcome = outcome
        self.step_index = step_index
        self.abstract_step_description = abstract_step_description  # 新增
        self.execution_count = execution_count
        self.metadata = metadata or {}
        self.path_id = self._generate_path_id()

    def _generate_path_id(self) -> str:
        """生成路径ID

        优先使用 abstract_step_description，其次使用 user_query + step_index。

        Returns:
            路径ID
        """
        # 优先使用 abstract_step_description 作为 key
        if self.abstract_step_description:
            content = f"{self.abstract_step_description.lower()}:{self.tool_name}"
        else:
            # 向后兼容：使用 query + step_index
            step_str = str(self.step_index) if self.step_index is not None else "none"
            content = f"{self.user_query.lower()}:{step_str}:{self.tool_name}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def increment_count(self) -> None:
        """增加执行计数"""
        self.execution_count += 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            字典表示
        """
        return {
            "path_id": self.path_id,
            "user_query": self.user_query,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "outcome": self.outcome,
            "step_index": self.step_index,
            "abstract_step_description": self.abstract_step_description,  # 新增
            "execution_count": self.execution_count,
            "metadata": self.metadata,
        }


class PathCache:
    """路径缓存

    维护已验证的执行路径，支持快速检索和学习。
    支持基于 abstract step description 的缓存和检索。
    """

    def __init__(
        self,
        config: VIGILConfig,
        openai_client=None,
        token_tracker: TokenStatsTracker | None = None,
    ):
        """初始化路径缓存

        Args:
            config: VIGIL配置
            openai_client: OpenAI客户端（用于LLM选择器）
            token_tracker: Token 统计追踪器
        """
        self.config = config
        self.openai_client = openai_client
        self.token_tracker = token_tracker or get_global_tracker()

        # 如果没有提供 OpenAI client，尝试创建一个
        if self.openai_client is None:
            try:
                self.openai_client = openai.OpenAI()
                logger.info("[PathCache] Initialized OpenAI client for LLM selector")
            except Exception as e:
                logger.warning(f"[PathCache] Failed to initialize OpenAI client: {e}")
                logger.warning("[PathCache] LLM selector will not be available")

        self._cache: dict[str, VerifiedPath] = {}
        self._query_index: dict[str, list[str]] = {}  # query -> [path_ids] (向后兼容)
        self._step_query_index: dict[str, list[str]] = {}  # (query, step_index) -> [path_ids] (向后兼容)
        self._abstract_step_index: dict[str, list[str]] = {}  # abstract_step_description -> [path_ids] (新增)

    def add_verified_path(
        self,
        user_query: str,
        tool_name: str,
        arguments: dict[str, Any],
        outcome: str,
        step_index: int | None = None,
        abstract_step_description: str | None = None,  # 新增：抽象步骤描述
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加已验证的路径到缓存

        Args:
            user_query: 用户查询
            tool_name: 工具名称
            arguments: 工具参数
            outcome: 执行结果 ("success" or "failure")
            step_index: 步骤索引（用于多步骤任务）
            abstract_step_description: 抽象步骤描述（来自 Abstract Sketch）
            metadata: 额外元数据
        """
        # 创建或更新路径
        path = VerifiedPath(
            user_query,
            tool_name,
            arguments,
            outcome,
            step_index=step_index,
            abstract_step_description=abstract_step_description,  # 新增
            metadata=metadata
        )

        if path.path_id in self._cache:
            # 路径已存在，增加计数
            existing_path = self._cache[path.path_id]
            existing_path.increment_count()

            # 如果新的执行结果与缓存不同，更新为最新结果
            if existing_path.outcome != outcome:
                logger.info(
                    f"[PathCache] Updating path outcome from '{existing_path.outcome}' to '{outcome}' "
                    f"for path_id: {path.path_id}"
                )
                existing_path.outcome = outcome
        else:
            # 新路径，添加到缓存
            self._cache[path.path_id] = path

            # 更新查询索引（向后兼容：不考虑步骤索引的索引）
            query_key = self._normalize_query(user_query)
            if query_key not in self._query_index:
                self._query_index[query_key] = []
            self._query_index[query_key].append(path.path_id)

            # 更新步骤级别的查询索引（向后兼容）
            if step_index is not None:
                step_query_key = self._get_step_query_key(user_query, step_index)
                if step_query_key not in self._step_query_index:
                    self._step_query_index[step_query_key] = []
                self._step_query_index[step_query_key].append(path.path_id)

            # 更新 abstract step description 索引（新增）
            if abstract_step_description:
                abstract_key = self._normalize_abstract_step(abstract_step_description)
                if abstract_key not in self._abstract_step_index:
                    self._abstract_step_index[abstract_key] = []
                self._abstract_step_index[abstract_key].append(path.path_id)

            step_info = f" (step {step_index})" if step_index is not None else ""
            abstract_info = f" [abstract: {abstract_step_description[:30]}...]" if abstract_step_description else ""
            logger.info(
                f"[PathCache] Added new verified path{step_info}{abstract_info}: "
                f"'{user_query[:50]}...' -> '{tool_name}' (outcome: {outcome})"
            )

    def retrieve_paths(
        self, user_query: str, step_index: int | None = None
    ) -> list[VerifiedPath]:
        """检索与查询匹配的路径

        Args:
            user_query: 用户查询
            step_index: 步骤索引（可选，如果提供则只返回该步骤的路径）

        Returns:
            匹配的路径列表（按执行次数排序）
        """
        path_ids: list[str] = []

        if step_index is not None:
            # 步骤级别的检索（优先）
            step_query_key = self._get_step_query_key(user_query, step_index)
            path_ids = self._step_query_index.get(step_query_key, [])

            if not path_ids:
                # 没有精确匹配，尝试模糊匹配（步骤级别）
                path_ids = self._fuzzy_match(user_query, step_index=step_index)
        else:
            # 查询级别的检索（向后兼容）
            query_key = self._normalize_query(user_query)
            path_ids = self._query_index.get(query_key, [])

            if not path_ids:
                # 没有精确匹配，尝试模糊匹配
                path_ids = self._fuzzy_match(user_query)

        # 检索路径并按执行次数排序
        paths = [self._cache[pid] for pid in path_ids if pid in self._cache]
        paths.sort(key=lambda p: p.execution_count, reverse=True)

        if paths and logger.isEnabledFor(logging.INFO):
            step_info = f" (step {step_index})" if step_index is not None else ""
            logger.info(
                f"[PathCache] Retrieved {len(paths)} cached paths{step_info} for query: '{user_query[:50]}...'"
            )

        return paths

    def get_recommended_tool(
        self, user_query: str, step_index: int | None = None
    ) -> str | None:
        """获取推荐的工具

        返回最常用且成功的工具。

        Args:
            user_query: 用户查询
            step_index: 步骤索引（可选）

        Returns:
            推荐的工具名称，如果没有缓存则返回 None
        """
        paths = self.retrieve_paths(user_query, step_index=step_index)

        # 过滤出成功的路径
        successful_paths = [p for p in paths if p.outcome == "success"]

        if successful_paths:
            recommended = successful_paths[0]  # 执行次数最多的
            step_info = f" for step {step_index}" if step_index is not None else ""
            logger.info(
                f"[PathCache] Recommending tool '{recommended.tool_name}'{step_info} "
                f"(used {recommended.execution_count} times successfully)"
            )
            return recommended.tool_name

        return None

    def _normalize_query(self, query: str) -> str:
        """规范化查询

        Args:
            query: 用户查询

        Returns:
            规范化后的查询
        """
        # 简单的规范化：转小写、去除多余空格
        return " ".join(query.lower().split())

    def _normalize_abstract_step(self, abstract_step_description: str) -> str:
        """规范化抽象步骤描述

        Args:
            abstract_step_description: 抽象步骤描述

        Returns:
            规范化后的描述
        """
        # 简单的规范化：转小写、去除多余空格
        return " ".join(abstract_step_description.lower().split())

    def _get_step_query_key(self, user_query: str, step_index: int) -> str:
        """生成步骤级别的查询键

        Args:
            user_query: 用户查询
            step_index: 步骤索引

        Returns:
            步骤级别的查询键
        """
        normalized_query = self._normalize_query(user_query)
        return f"{normalized_query}__step_{step_index}"

    def _fuzzy_match(
        self, user_query: str, step_index: int | None = None
    ) -> list[str]:
        """模糊匹配查询

        对于没有精确匹配的查询，尝试找到相似的查询。

        Args:
            user_query: 用户查询
            step_index: 步骤索引（可选）

        Returns:
            匹配的路径ID列表
        """
        query_words = set(user_query.lower().split())
        matches: list[tuple[str, float]] = []  # (path_id, similarity_score)

        # 选择要搜索的索引
        if step_index is not None:
            # 搜索步骤级别的索引
            search_index = self._step_query_index
        else:
            # 搜索查询级别的索引
            search_index = self._query_index

        for cached_query_key, path_ids in search_index.items():
            # 提取查询部分（去掉 __step_N 后缀）
            if step_index is not None:
                # 从 "query__step_N" 中提取 "query"
                cached_query = cached_query_key.rsplit("__step_", 1)[0]
            else:
                cached_query = cached_query_key

            cached_words = set(cached_query.split())

            # 计算 Jaccard 相似度
            intersection = len(query_words & cached_words)
            union = len(query_words | cached_words)

            if union > 0:
                similarity = intersection / union

                # 如果相似度超过阈值（0.5），认为匹配
                if similarity >= 0.5:
                    for path_id in path_ids:
                        matches.append((path_id, similarity))

        # 按相似度排序
        matches.sort(key=lambda x: x[1], reverse=True)

        # 返回前5个最相似的路径
        matched_ids = [path_id for path_id, _ in matches[:5]]

        if matched_ids:
            step_info = f" (step {step_index})" if step_index is not None else ""
            logger.debug(
                f"[PathCache] Fuzzy match found {len(matched_ids)} similar paths{step_info} "
                f"for query: '{user_query[:50]}...'"
            )

        return matched_ids

    def retrieve_paths_by_abstract_step(
        self, abstract_step_description: str, top_k: int = 3
    ) -> list[VerifiedPath]:
        """基于 abstract step description 检索路径（返回 top-K）

        这是新的主要检索接口，用于基于抽象步骤描述的相似度匹配。

        Args:
            abstract_step_description: 抽象步骤描述
            top_k: 返回前 K 个最相似的路径（默认 3）

        Returns:
            匹配的路径列表（按相似度和执行次数排序）
        """
        abstract_key = self._normalize_abstract_step(abstract_step_description)

        # 1. 首先尝试精确匹配
        path_ids = self._abstract_step_index.get(abstract_key, [])

        # 2. 如果没有精确匹配，尝试模糊匹配
        if not path_ids:
            path_ids = self._fuzzy_match_abstract_step(abstract_step_description)

        # 3. 检索路径并过滤成功的路径
        paths = [self._cache[pid] for pid in path_ids if pid in self._cache]
        successful_paths = [p for p in paths if p.outcome == "success"]

        # 4. 按执行次数排序（越多越优先）
        successful_paths.sort(key=lambda p: p.execution_count, reverse=True)

        # 5. 返回 top-K
        result = successful_paths[:top_k]

        if result:
            logger.info(
                f"[PathCache] Retrieved {len(result)} cached paths for abstract step: "
                f"'{abstract_step_description[:50]}...'"
            )
        else:
            logger.debug(
                f"[PathCache] No cached paths found for abstract step: "
                f"'{abstract_step_description[:50]}...'"
            )

        return result

    def select_tool_with_llm(
        self,
        abstract_step_description: str,
        candidate_paths: list[VerifiedPath],
    ) -> tuple[str | None, str | None]:
        """使用 LLM 从候选路径中选择最合适的工具

        Args:
            abstract_step_description: 当前抽象步骤描述
            candidate_paths: 候选路径列表（通常是 top-K）

        Returns:
            (选中的工具名称, 选择理由)，如果无法选择则返回 (None, None)
        """
        if not candidate_paths:
            return None, None

        if not self.openai_client:
            logger.warning("[PathCache] No OpenAI client available, cannot select with LLM")
            # 回退：返回执行次数最多的工具
            best_path = max(candidate_paths, key=lambda p: p.execution_count)
            return best_path.tool_name, f"Fallback: most frequently used tool ({best_path.execution_count} times)"

        # 构造提示
        prompt = self._build_selector_prompt(abstract_step_description, candidate_paths)

        try:
            # 调用 LLM
            response = self.openai_client.chat.completions.create(
                model=self.config.hypothesizer_model,  # 使用 hypothesizer 的模型配置
                messages=[
                    {"role": "system", "content": "You are a tool selector that chooses the most appropriate tool from cached execution history."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )

            # 记录 token 使用
            if response.usage:
                self.token_tracker.record_usage(
                    module=TokenStatsTracker.MODULE_PATH_CACHING,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    model=self.config.hypothesizer_model,
                )

            result_text = response.choices[0].message.content.strip()

            # 解析结果
            selected_tool, rationale = self._parse_selector_result(result_text, candidate_paths)

            if selected_tool:
                logger.info(
                    f"[PathCache] LLM selected tool '{selected_tool}' from {len(candidate_paths)} candidates. "
                    f"Rationale: {rationale[:100]}..."
                )
                return selected_tool, rationale
            else:
                # 解析失败，回退到最常用的
                logger.warning("[PathCache] Failed to parse LLM selection, using fallback")
                best_path = max(candidate_paths, key=lambda p: p.execution_count)
                return best_path.tool_name, f"Fallback after parse failure: {best_path.tool_name}"

        except Exception as e:
            logger.error(f"[PathCache] Error calling LLM selector: {e}")
            # 回退：返回执行次数最多的工具
            best_path = max(candidate_paths, key=lambda p: p.execution_count)
            return best_path.tool_name, f"Fallback after error: {best_path.tool_name}"

    def _build_selector_prompt(
        self,
        abstract_step_description: str,
        candidate_paths: list[VerifiedPath],
    ) -> str:
        """构造 LLM 选择器的提示

        Args:
            abstract_step_description: 当前抽象步骤描述
            candidate_paths: 候选路径列表

        Returns:
            提示文本
        """
        candidates_text = ""
        for i, path in enumerate(candidate_paths, 1):
            candidates_text += f"\n{i}. Tool: {path.tool_name}\n"
            candidates_text += f"   Used {path.execution_count} times successfully\n"
            if path.abstract_step_description:
                candidates_text += f"   Previous step description: \"{path.abstract_step_description}\"\n"

        prompt = f"""You are selecting the most appropriate tool from successful execution history.

Current Step Description:
"{abstract_step_description}"

Available Cached Tools:{candidates_text}

Task:
1. Compare the current step description with each tool's previous usage context
2. Select the tool that best matches the current step's requirements
3. Provide a brief rationale (1-2 sentences)

Response format:
SELECTED_TOOL: <tool_name>
RATIONALE: <your reasoning>

Your response:"""

        return prompt

    def _parse_selector_result(
        self,
        result_text: str,
        candidate_paths: list[VerifiedPath],
    ) -> tuple[str | None, str | None]:
        """解析 LLM 选择器的结果

        Args:
            result_text: LLM 返回的文本
            candidate_paths: 候选路径列表

        Returns:
            (选中的工具名称, 选择理由)
        """
        lines = result_text.strip().split('\n')
        selected_tool = None
        rationale = None

        for line in lines:
            if line.startswith("SELECTED_TOOL:"):
                tool_name = line.replace("SELECTED_TOOL:", "").strip()
                # 验证工具名称是否在候选列表中
                for path in candidate_paths:
                    if path.tool_name == tool_name:
                        selected_tool = tool_name
                        break
            elif line.startswith("RATIONALE:"):
                rationale = line.replace("RATIONALE:", "").strip()

        # 如果没有找到有效的工具，尝试模糊匹配
        if not selected_tool:
            tool_names = [path.tool_name for path in candidate_paths]
            for tool_name in tool_names:
                if tool_name.lower() in result_text.lower():
                    selected_tool = tool_name
                    break

        return selected_tool, rationale or "LLM selection"

    def _fuzzy_match_abstract_step(
        self, abstract_step_description: str
    ) -> list[str]:
        """模糊匹配抽象步骤描述

        使用 Jaccard 相似度匹配相似的抽象步骤。

        Args:
            abstract_step_description: 抽象步骤描述

        Returns:
            匹配的路径ID列表
        """
        step_words = set(abstract_step_description.lower().split())
        matches: list[tuple[str, float]] = []  # (path_id, similarity_score)

        for cached_step_key, path_ids in self._abstract_step_index.items():
            cached_words = set(cached_step_key.split())

            # 计算 Jaccard 相似度
            intersection = len(step_words & cached_words)
            union = len(step_words | cached_words)

            if union > 0:
                similarity = intersection / union

                # 如果相似度超过阈值（0.5），认为匹配
                if similarity >= 0.5:
                    for path_id in path_ids:
                        matches.append((path_id, similarity))

        # 按相似度排序
        matches.sort(key=lambda x: x[1], reverse=True)

        # 返回前10个最相似的路径（后续会再筛选成功的路径并取 top-K）
        matched_ids = [path_id for path_id, _ in matches[:10]]

        if matched_ids:
            logger.debug(
                f"[PathCache] Fuzzy match found {len(matched_ids)} similar paths "
                f"for abstract step: '{abstract_step_description[:50]}...'"
            )

        return matched_ids

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total_paths = len(self._cache)
        successful_paths = sum(1 for p in self._cache.values() if p.outcome == "success")
        total_executions = sum(p.execution_count for p in self._cache.values())

        return {
            "total_cached_paths": total_paths,
            "successful_paths": successful_paths,
            "failed_paths": total_paths - successful_paths,
            "total_executions": total_executions,
            "unique_queries": len(self._query_index),
        }

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._query_index.clear()
        self._step_query_index.clear()
        self._abstract_step_index.clear()  # 新增：清除 abstract step 索引
        logger.info("[PathCache] Cache cleared")

    def export_cache(self) -> dict[str, Any]:
        """导出缓存数据

        Returns:
            缓存数据的字典表示
        """
        return {
            "paths": [path.to_dict() for path in self._cache.values()],
            "stats": self.get_stats(),
        }

    def import_cache(self, cache_data: dict[str, Any]) -> None:
        """导入缓存数据

        Args:
            cache_data: 缓存数据
        """
        self.clear()

        for path_dict in cache_data.get("paths", []):
            path = VerifiedPath(
                user_query=path_dict["user_query"],
                tool_name=path_dict["tool_name"],
                arguments=path_dict["arguments"],
                outcome=path_dict["outcome"],
                step_index=path_dict.get("step_index"),
                abstract_step_description=path_dict.get("abstract_step_description"),  # 新增
                execution_count=path_dict["execution_count"],
                metadata=path_dict.get("metadata"),
            )
            self._cache[path.path_id] = path

            # 重建查询索引（向后兼容）
            query_key = self._normalize_query(path.user_query)
            if query_key not in self._query_index:
                self._query_index[query_key] = []
            self._query_index[query_key].append(path.path_id)

            # 重建步骤级别的查询索引（向后兼容）
            if path.step_index is not None:
                step_query_key = self._get_step_query_key(path.user_query, path.step_index)
                if step_query_key not in self._step_query_index:
                    self._step_query_index[step_query_key] = []
                self._step_query_index[step_query_key].append(path.path_id)

            # 重建 abstract step 索引（新增）
            if path.abstract_step_description:
                abstract_key = self._normalize_abstract_step(path.abstract_step_description)
                if abstract_key not in self._abstract_step_index:
                    self._abstract_step_index[abstract_key] = []
                self._abstract_step_index[abstract_key].append(path.path_id)

        logger.info(f"[PathCache] Imported {len(self._cache)} paths from cache data")
