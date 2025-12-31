"""条件LLM Wrapper

在direct mode下，如果HypothesisGuidance已经生成了tool call，则跳过LLM调用。
这样可以确保执行的是经过验证的推荐工具，而不是LLM自主决策的工具。
"""

import logging
from collections.abc import Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import ChatMessage

logger = logging.getLogger(__name__)


class ConditionalLLM(BasePipelineElement):
    """条件LLM Wrapper

    根据extra_args中的标志决定是否调用LLM：
    - 如果skip_llm=True，跳过LLM调用（返回原messages）
    - 否则，正常调用LLM

    这用于direct mode，其中HypothesisGuidance直接生成tool call后，
    不需要再调用LLM进行决策。
    """

    def __init__(self, llm: BasePipelineElement):
        """初始化条件LLM

        Args:
            llm: 实际的LLM pipeline element
        """
        self.llm = llm
        # 继承LLM的name属性
        if hasattr(llm, 'name'):
            self.name = llm.name

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        """执行条件LLM调用

        检查extra_args['skip_llm']标志：
        - True: 跳过LLM，直接返回
        - False或不存在: 调用LLM

        Args:
            query: 用户查询
            runtime: 函数运行时
            env: 环境
            messages: 消息历史
            extra_args: 额外参数（包含skip_llm标志）

        Returns:
            更新后的查询、运行时、环境、消息和额外参数
        """
        # 检查是否应该跳过LLM
        skip_llm = extra_args.get('skip_llm', False)

        if skip_llm:
            logger.info(
                "[ConditionalLLM] Skipping LLM call (HypothesisGuidance generated tool call in direct mode)"
            )
            # 清除标志（避免影响下一轮）
            # extra_args = {**extra_args, 'skip_llm': False}
            return query, runtime, env, messages, extra_args

        # 正常调用LLM
        return self.llm.query(query, runtime, env, messages, extra_args)
