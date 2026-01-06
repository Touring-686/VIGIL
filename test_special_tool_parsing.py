"""测试特殊工具名的简化解析功能"""

import sys
sys.path.insert(0, '/Users/justin/BDAA/ACL/code/agentdojo/src')

from vigil_agent.hypothesizer import Hypothesizer
from vigil_agent.config import VIGILConfig
import openai

def test_special_tool_parsing():
    """测试 __internal_reasoning__ 等特殊工具名的解析"""

    # 创建配置和 Hypothesizer 实例
    config = VIGILConfig()
    client = openai.OpenAI()
    hypothesizer = Hypothesizer(config=config, openai_client=client)

    # 测试用例 1: __internal_reasoning__
    test_case_1 = """[{"choice_id": "choice1", "tool_name": "__internal_reasoning__", "operation_type": "REASONING", "execution_args": [{"args": {"task": "Identify the French restaurant with the highest rating", "source_data": "restaurants_list"}, "reasoning": "Need to analyze the restaurant ratings to find the best French option", "information_flow": {}}]}]"""

    print("=" * 80)
    print("测试用例 1: __internal_reasoning__")
    print("=" * 80)
    print(f"输入字符串长度: {len(test_case_1)}")
    print(f"输入前100字符: {test_case_1[:100]}...")

    try:
        result = hypothesizer._parse_function_arguments(test_case_1)
        print("\n✅ 解析成功!")
        print(f"返回的 strategies 数量: {len(result)}")
        print(f"第一个 strategy: {result[0]}")

        # 验证结构
        assert len(result) == 1, "应该返回1个strategy"
        assert result[0]["tool_name"] == "__internal_reasoning__", "tool_name 应该是 __internal_reasoning__"
        assert "reasoning" in result[0]["execution_args"][0], "应该包含 reasoning 字段"
        assert result[0]["execution_args"][0]["args"] == {}, "args 应该是空字典"

        print("\n✅ 所有断言通过!")

    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试用例 2: __response__
    test_case_2 = """[{"choice_id": "choice2", "tool_name": "__response__", "operation_type": "RESPONSE", "execution_args": [{"args": {"message": "Here are the results"}, "reasoning": "Ready to send response to user", "information_flow": {}}]}]"""

    print("\n" + "=" * 80)
    print("测试用例 2: __response__")
    print("=" * 80)

    try:
        result = hypothesizer._parse_function_arguments(test_case_2)
        print("✅ 解析成功!")
        print(f"第一个 strategy: {result[0]}")
        assert result[0]["tool_name"] == "__response__", "tool_name 应该是 __response__"
        print("✅ 断言通过!")

    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试用例 3: __step_skip__
    test_case_3 = """[{"choice_id": "choice3", "tool_name": "__step_skip__", "operation_type": "SKIP", "execution_args": [{"args": {}, "reasoning": "This step is not needed", "information_flow": {}}]}]"""

    print("\n" + "=" * 80)
    print("测试用例 3: __step_skip__")
    print("=" * 80)

    try:
        result = hypothesizer._parse_function_arguments(test_case_3)
        print("✅ 解析成功!")
        print(f"第一个 strategy: {result[0]}")
        assert result[0]["tool_name"] == "__step_skip__", "tool_name 应该是 __step_skip__"
        print("✅ 断言通过!")

    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("所有测试完成!")
    print("=" * 80)

if __name__ == "__main__":
    test_special_tool_parsing()
