"""测试直接工具执行模式

验证：
1. HypothesisGuidanceElement 可以直接生成 tool call（跳过 LLM）
2. 任务完成后，最后一条消息是 assistant message
"""

import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from agentdojo.types import ChatMessage, ChatToolResultMessage, text_content_block_from_string
from vigil_agent.config import VIGILConfig
from vigil_agent.hypothesis_guidance import HypothesisGuidanceElement
from vigil_agent.hypothesizer import Hypothesizer
from vigil_agent.commitment_manager import CommitmentManager
from vigil_agent.enhanced_auditor import EnhancedRuntimeAuditor
from vigil_agent.path_cache import PathCache
from agentdojo.functions_runtime import FunctionsRuntime, Function, Env, EmptyEnv


def test_direct_tool_execution():
    """测试直接工具执行模式"""

    logger.info("=" * 80)
    logger.info("测试直接工具执行模式")
    logger.info("=" * 80)

    # 创建配置（启用直接执行模式）
    config = VIGILConfig(
        enable_direct_tool_execution=True,
        enable_hypothesis_generation=True,
        log_hypothesis_generation=True,
    )

    # 创建必要的组件
    auditor = EnhancedRuntimeAuditor(config)
    path_cache = PathCache(config)

    # 创建 OpenAI client
    import openai
    openai_client = openai.OpenAI()

    hypothesizer = Hypothesizer(config, openai_client)
    commitment_manager = CommitmentManager(config, auditor)

    # 创建 HypothesisGuidanceElement
    guidance_element = HypothesisGuidanceElement(
        config=config,
        hypothesizer=hypothesizer,
        commitment_manager=commitment_manager,
        auditor=auditor,
        path_cache=path_cache,
    )

    # 创建简单的函数运行时
    def dummy_get_balance(env: Env) -> str:
        return "Your balance is $1000"

    def dummy_get_transactions(env: Env, limit: int = 10) -> str:
        return f"Last {limit} transactions: ..."

    runtime = FunctionsRuntime(
        functions={
            "get_balance": Function(
                name="get_balance",
                description="Get account balance",
                parameters={},
                function=dummy_get_balance,
            ),
            "get_transactions": Function(
                name="get_transactions",
                description="Get recent transactions",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of transactions"}
                    },
                    "required": [],
                },
                function=dummy_get_transactions,
            ),
        }
    )

    env = EmptyEnv()

    # ===== 测试场景 1: 第一次调用（应该生成 tool call）=====
    logger.info("\n[Test 1] 第一次调用 - 应该生成 tool call")

    user_query = "Show me my account balance"
    messages: list[ChatMessage] = []

    # 调用 HypothesisGuidanceElement
    query_out, runtime_out, env_out, messages_out, extra_args_out = guidance_element.query(
        query=user_query,
        runtime=runtime,
        env=env,
        messages=messages,
        extra_args={},
    )

    # 验证最后一条消息是 assistant message（包含 tool call）
    assert len(messages_out) > 0, "Should have generated at least one message"
    last_message = messages_out[-1]
    assert last_message["role"] == "assistant", f"Last message should be assistant, got {last_message['role']}"
    assert last_message.get("tool_calls") is not None, "Should have tool calls"

    logger.info(f"✅ Generated assistant message with tool call: {last_message['tool_calls'][0].function}")

    # ===== 测试场景 2: 添加 tool result 后调用（应该生成最终 assistant message）=====
    logger.info("\n[Test 2] 添加 tool result 后调用 - 应该生成最终 assistant message")

    # 模拟添加 tool result
    tool_result_message = ChatToolResultMessage(
        role="tool",
        content=[text_content_block_from_string("Your balance is $1000")],
        tool_call_id=last_message["tool_calls"][0].id,
        tool_call=last_message["tool_calls"][0],
        error=None,
    )

    messages_with_result = [*messages_out, tool_result_message]

    # 再次调用 HypothesisGuidanceElement
    query_out2, runtime_out2, env_out2, messages_out2, extra_args_out2 = guidance_element.query(
        query=user_query,
        runtime=runtime,
        env=env,
        messages=messages_with_result,
        extra_args={},
    )

    # 验证最后一条消息是 assistant message（任务完成）
    assert len(messages_out2) > len(messages_with_result), "Should have added a final assistant message"
    final_message = messages_out2[-1]
    assert final_message["role"] == "assistant", f"Final message should be assistant, got {final_message['role']}"
    assert final_message.get("tool_calls") is None, "Final message should not have tool calls"

    logger.info("✅ Generated final assistant message (task completion)")
    logger.info(f"   Content: {final_message['content'][0]['text'][:100]}...")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 所有测试通过！直接工具执行模式工作正常")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_direct_tool_execution()
