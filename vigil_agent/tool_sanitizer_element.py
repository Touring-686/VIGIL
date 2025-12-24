"""Tool Sanitizer Pipeline Element

这个pipeline元素在工具传递给LLM之前清洗工具文档，防止Type I-A攻击。
"""

import logging
from collections.abc import Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime, Function
from agentdojo.types import ChatMessage

from vigil_agent.config import VIGILConfig
from vigil_agent.perception_sanitizer import PerceptionSanitizer

logger = logging.getLogger(__name__)


class ToolDocstringSanitizer(BasePipelineElement):
    """工具文档清洗器Pipeline元素

    在FunctionsRuntime传递给LLM之前，清洗所有工具的文档字符串。
    这防止了Type I-A (Goal Hijacking via Docstring)攻击。

    使用方式：将此元素放在pipeline的开头，VIGILInitQuery之前。
    """

    def __init__(self, config: VIGILConfig, sanitizer: PerceptionSanitizer):
        """初始化工具文档清洗器

        Args:
            config: VIGIL配置
            sanitizer: 感知层清洗器
        """
        self.config = config
        self.sanitizer = sanitizer
        self._sanitized_runtimes: dict[int, FunctionsRuntime] = {}  # 缓存已清洗的runtime

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """清洗FunctionsRuntime中的工具文档

        Args:
            query: 用户查询
            runtime: 函数运行时
            env: 环境
            messages: 消息历史
            extra_args: 额外参数

        Returns:
            更新后的查询、运行时（已清洗）、环境、消息和额外参数
        """
        if not self.config.enable_perception_sanitizer:
            # 如果未启用清洗器，直接返回
            return query, runtime, env, messages, extra_args

        # 检查缓存
        runtime_id = id(runtime)
        if runtime_id in self._sanitized_runtimes:
            # 已经清洗过这个runtime
            logger.debug("[ToolDocstringSanitizer] Using cached sanitized runtime")
            return query, self._sanitized_runtimes[runtime_id], env, messages, extra_args

        # 创建新的清洗后的runtime
        sanitized_functions = {}

        for func_id, func in runtime.functions.items():
            # 清洗工具描述
            sanitized_description = self.sanitizer.sanitize_tool_docstring(
                func.name, func.description
            )

            # 清洗完整文档字符串
            sanitized_full_docstring = self.sanitizer.sanitize_tool_docstring(
                func.name, func.full_docstring
            )

            # 创建新的Function对象（只修改描述字段）
            sanitized_func = Function(
                name=func.name,
                description=sanitized_description,
                parameters=func.parameters,
                dependencies=func.dependencies,
                run=func.run,
                full_docstring=sanitized_full_docstring,
                return_type=func.return_type,
            )

            sanitized_functions[func_id] = sanitized_func

            if self.config.log_sanitizer_actions:
                if sanitized_description != func.description:
                    logger.warning(
                        f"[ToolDocstringSanitizer] Sanitized docstring for tool '{func.name}'"
                    )
                    logger.debug(f"  Original: {func.description}...")
                    logger.debug(f"  Sanitized: {sanitized_description}...")

        # 创建新的FunctionsRuntime（传递Function对象列表）
        sanitized_runtime = FunctionsRuntime(functions=list(sanitized_functions.values()))

        # 缓存
        self._sanitized_runtimes[runtime_id] = sanitized_runtime

        logger.info(f"[ToolDocstringSanitizer] Sanitized {len(sanitized_functions)} tool docstrings")

        return query, sanitized_runtime, env, messages, extra_args

    def clear_cache(self) -> None:
        """清空缓存"""
        self._sanitized_runtimes.clear()
        logger.info("[ToolDocstringSanitizer] Cache cleared")
