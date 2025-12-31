"""测试VIGIL Pipeline的执行顺序

验证第一轮是否正确生成Hypothesis Tree
"""

import logging
import sys
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.task_suite.task_suite import TaskSuite
from vigil_agent.config import VIGILConfig
from vigil_agent.enhanced_pipeline import create_enhanced_vigil_pipeline
import openai


def test_execution_order():
    """测试执行顺序"""
    print("=" * 80)
    print("测试VIGIL Pipeline执行顺序")
    print("=" * 80)

    # 创建配置
    config = VIGILConfig(
        enable_abstract_sketch=True,
        enable_hypothesis_generation=True,
        log_sketch_generation=True,
        log_hypothesis_generation=True,
        log_audit_decisions=True,
    )

    # 创建LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o-mini")

    # 创建pipeline
    pipeline = create_enhanced_vigil_pipeline(llm, config=config)

    print(f"\n创建的Pipeline: {pipeline.name}")
    print(f"Pipeline Elements数量: {len(pipeline.elements)}")

    print("\nPipeline Elements:")
    for i, element in enumerate(pipeline.elements):
        element_name = element.__class__.__name__
        print(f"  {i+1}. {element_name}")

        # 如果是ToolsExecutionLoop，显示其内部元素
        if element_name == "ToolsExecutionLoop":
            print(f"     ToolsExecutionLoop内部元素:")
            for j, inner_elem in enumerate(element.elements):
                inner_name = inner_elem.__class__.__name__
                print(f"       {j+1}. {inner_name}")

    print("\n" + "=" * 80)
    print("测试第一轮执行（模拟）")
    print("=" * 80)

    # 加载一个简单的task suite来测试
    try:
        from agentdojo.task_suite.task_suite import load_suite_from_registry
        suite = load_suite_from_registry("user_task", "banking")

        # 获取第一个任务
        task = suite.tasks[0]
        print(f"\n测试任务: {task.ID}")
        print(f"任务指令: {task.PROMPT[:100]}...")

        # 重置pipeline
        pipeline.reset_for_new_task()

        # 执行任务
        print("\n开始执行...")
        print("观察日志中的执行顺序:\n")

        result = pipeline.query(
            task.PROMPT,
            runtime=suite.runtime,
            env=task.INIT_ENV,
        )

        print("\n执行完成")

    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_execution_order()
