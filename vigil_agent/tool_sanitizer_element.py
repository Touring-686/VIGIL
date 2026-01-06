"""Tool Sanitizer Pipeline Element

这个pipeline元素在工具传递给LLM之前清洗工具文档，防止Type I-A攻击。
支持持久化缓存，避免重复清洗。
"""

import hashlib
import json
import logging
import pickle
from pathlib import Path
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

    支持持久化缓存：
    - 首次清洗后保存到磁盘
    - 后续调试直接加载缓存，无需重新清洗

    使用方式：将此元素放在pipeline的开头，VIGILInitQuery之前。
    """

    def __init__(
        self,
        config: VIGILConfig,
        sanitizer: PerceptionSanitizer,
        cache_dir: str | Path | None = None,
        use_disk_cache: bool = False,
    ):
        """初始化工具文档清洗器

        Args:
            config: VIGIL配置
            sanitizer: 感知层清洗器
            cache_dir: 缓存目录路径（默认：./vigil_cache/sanitized_tools）
            use_disk_cache: 是否使用磁盘缓存（默认：False，只有显式启用才从缓存加载）
        """
        self.config = config
        self.sanitizer = sanitizer
        self.use_disk_cache = use_disk_cache
        self._sanitized_runtimes: dict[int, FunctionsRuntime] = {}  # 内存缓存

        # 持久化缓存目录
        if cache_dir is None:
            cache_dir = Path("./vigil_cache/sanitized_tools")
        self.cache_dir = Path(cache_dir)
        # 确保目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[ToolDocstringSanitizer] Persistent cache directory: {self.cache_dir}")
        logger.info(f"[ToolDocstringSanitizer] Disk cache: {'✓ Enabled' if use_disk_cache else '✗ Disabled (will sanitize tools)'}")
    def clear_cache(self):
        self.sanitizer.clear()
        logger.info("[ToolDocstringSanitizer] Cache cleared")
    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """清洗FunctionsRuntime中的工具文档

        流程：
        1. 检查内存缓存
        2. 检查磁盘缓存（持久化）
        3. 如果都没有，执行清洗并保存

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

        # ===== Step 1: 检查内存缓存 =====
        runtime_id = id(runtime)
        if runtime_id in self._sanitized_runtimes:
            logger.debug("[ToolDocstringSanitizer] ✓ Using cached sanitized runtime (memory)")
            return query, self._sanitized_runtimes[runtime_id], env, messages, extra_args


        # ===== Step 2: 尝试从磁盘加载缓存（只有启用了 disk cache 才加载）=====
        import os
        save_path_desp = f"{self.cache_dir}/{extra_args.get('suite', 'default')}_description.json"
        save_path_docstring = f"{self.cache_dir}/{extra_args.get('suite', 'default')}_docstring.json"

        sanitized_function_description = {}
        sanitized_function_dostrings = {}

        # 只有启用了 disk cache 才从磁盘加载
        if self.use_disk_cache:
            if os.path.exists(save_path_desp):
                with open(save_path_desp, "r") as f:
                    sanitized_function_description = json.load(f)
                logger.debug(f"[ToolDocstringSanitizer] ✓ Loaded description cache from {save_path_desp}")

            if os.path.exists(save_path_docstring):
                with open(save_path_docstring, "r") as f:
                    sanitized_function_dostrings = json.load(f)
                logger.debug(f"[ToolDocstringSanitizer] ✓ Loaded docstring cache from {save_path_docstring}")
        else:
            logger.debug("[ToolDocstringSanitizer] Disk cache disabled, will sanitize all tools")

        # ===== Step 3: 没有缓存，执行清洗 =====
        # logger.info(f"[ToolDocstringSanitizer] No cache found, sanitizing {len(runtime.functions)} tools...")

        sanitized_functions = {}
        for func_id, func in runtime.functions.items():
            # 清洗工具doc string
            if func.name not in sanitized_function_dostrings:
                sanitized_full_docstring = self.sanitizer.sanitize_tool_docstring(
                    func.name, func.full_docstring
                )
                sanitized_function_dostrings[func.name] = sanitized_full_docstring
            else:
                sanitized_full_docstring = sanitized_function_dostrings[func.name]
            
            # 清洗工具doc description
            if func.name not in sanitized_function_description:
                sanitized_full_description = self.sanitizer.sanitize_tool_docstring(
                    func.name, func.description
                )
                sanitized_function_description[func.name] = sanitized_full_description
            else:
                sanitized_full_description = sanitized_function_description[func.name]
            

            # 创建新的Function对象（只修改描述字段）
            sanitized_func = Function(
                name=func.name,
                description=sanitized_full_description,
                parameters=func.parameters,
                dependencies=func.dependencies,
                run=func.run,
                full_docstring=sanitized_full_docstring,
                return_type=func.return_type,
            )

            sanitized_functions[func_id] = sanitized_func

            if self.config.log_sanitizer_actions:
                if sanitized_full_docstring != func.full_docstring:
                    logger.debug(
                        f"[ToolDocstringSanitizer] Sanitized docstring for tool '{func.name}'"
                    )
                    logger.debug(f"  Original: {func.full_docstring}...")
                    logger.debug(f"  Sanitized: {sanitized_full_docstring}...")

#         # 输出并且比较清洗前后的tool的doc string
#         for func_id, func in runtime.functions.items():
#             sanitized_func = sanitized_functions[func_id]
#             if func.full_docstring != sanitized_func.full_docstring:
#                 logger.info(f"""\n========================================================
# [ToolDocstringSanitizer] Tool '{func.name}' docstring changed:
# [Before][{func.name}]: {func.full_docstring}
# [After][{func.name}]: {sanitized_func.full_docstring}
# ========================================================""")

        # 创建新的FunctionsRuntime
        sanitized_runtime = FunctionsRuntime(functions=list(sanitized_functions.values()))

        # ===== Step 4: 保存到磁盘缓存（只有启用了 disk cache 才保存）=====
        if self.use_disk_cache:
            # 确保目录存在
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            with open(save_path_docstring, "w") as f:
                json.dump(sanitized_function_dostrings, f, indent=2, ensure_ascii=False)
            logger.debug(f"[ToolDocstringSanitizer] ✓ Saved docstring cache to {save_path_docstring}")

            with open(save_path_desp, "w") as f:
                json.dump(sanitized_function_description, f, indent=2, ensure_ascii=False)
            logger.debug(f"[ToolDocstringSanitizer] ✓ Saved description cache to {save_path_desp}")

        # ===== Step 5: 保存到内存缓存 =====
        self._sanitized_runtimes[runtime_id] = sanitized_runtime

        logger.info(f"[ToolDocstringSanitizer] ✓ Sanitized and cached {len(sanitized_functions)} tools")

        return query, sanitized_runtime, env, messages, extra_args
