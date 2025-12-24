"""
VIGIL Framework - 完整使用示例

这个示例展示了如何使用VIGIL框架在AgentDojo benchmark上运行实验。
"""

import logging
from pathlib import Path

import openai

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 导入VIGIL组件
from vigil_agent import VIGIL_BALANCED_CONFIG, VIGIL_STRICT_CONFIG, create_vigil_pipeline

# 导入AgentDojo组件
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.attacks.base_attacks import DirectAttack
from agentdojo.benchmark import benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.task_suite.load_suites import get_suite


def example_basic_usage():
    """示例1: 基本使用"""
    print("\n" + "=" * 80)
    print("示例1: 基本使用")
    print("=" * 80)

    # 1. 创建LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o")

    # 2. 创建VIGIL pipeline
    pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

    print(f"✓ Created VIGIL pipeline: {pipeline.name}")
    print(f"✓ Configuration: VIGIL_BALANCED_CONFIG")


def example_benchmark_without_attacks():
    """示例2: 在无攻击场景下运行benchmark（测试utility）"""
    print("\n" + "=" * 80)
    print("示例2: 测试Utility（无攻击）")
    print("=" * 80)

    # 创建pipeline
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o")
    pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

    # 加载suite
    suite = get_suite("v1", "banking")
    print(f"✓ Loaded suite: {suite.name}")
    print(f"  - User tasks: {len(suite.user_tasks)}")

    # 运行benchmark（无攻击）
    results = benchmark_suite_without_injections(
        agent_pipeline=pipeline,
        suite=suite,
        logdir=Path("./vigil_runs"),
        force_rerun=False,
        user_tasks=list(suite.user_tasks.keys())[:2],  # 只运行前2个任务作为示例
    )

    # 计算结果
    utility_rate = sum(results["utility_results"].values()) / len(results["utility_results"])
    print(f"\n✓ Utility Rate: {utility_rate:.2%}")

    # 获取审计统计
    stats = pipeline.get_audit_stats()
    print(f"\n📊 Audit Statistics:")
    print(f"  - Total audits: {stats['total_audits']}")
    print(f"  - Allowed: {stats['allowed']}")
    print(f"  - Blocked: {stats['blocked']}")


def example_benchmark_with_attacks():
    """示例3: 在攻击场景下运行benchmark（测试security）"""
    print("\n" + "=" * 80)
    print("示例3: 测试Security（有攻击）")
    print("=" * 80)

    # 创建pipeline
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o")
    pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)

    # 加载suite和attack
    suite = get_suite("v1", "banking")
    attack = DirectAttack()

    print(f"✓ Loaded suite: {suite.name}")
    print(f"✓ Attack type: {attack.name}")
    print(f"  - User tasks: {len(suite.user_tasks)}")
    print(f"  - Injection tasks: {len(suite.injection_tasks)}")

    # 运行benchmark（有攻击）
    results = benchmark_suite_with_injections(
        agent_pipeline=pipeline,
        suite=suite,
        attack=attack,
        logdir=Path("./vigil_runs"),
        force_rerun=False,
        user_tasks=list(suite.user_tasks.keys())[:2],  # 只运行前2个任务
        injection_tasks=list(suite.injection_tasks.keys())[:3],  # 只运行前3个注入任务
    )

    # 计算结果
    utility_results = results["utility_results"]
    security_results = results["security_results"]

    if utility_results:
        utility_rate = sum(utility_results.values()) / len(utility_results)
        print(f"\n✓ Utility Rate: {utility_rate:.2%}")

    if security_results:
        security_rate = sum(security_results.values()) / len(security_results)
        print(f"✓ Security Rate: {security_rate:.2%}")

    # 获取审计统计
    stats = pipeline.get_audit_stats()
    print(f"\n📊 Audit Statistics:")
    print(f"  - Total audits: {stats['total_audits']}")
    print(f"  - Allowed: {stats['allowed']}")
    print(f"  - Blocked: {stats['blocked']}")


def example_custom_config():
    """示例4: 使用自定义配置"""
    print("\n" + "=" * 80)
    print("示例4: 自定义配置")
    print("=" * 80)

    from vigil_agent import VIGILConfig

    # 创建自定义配置
    custom_config = VIGILConfig(
        # 约束生成
        constraint_generator_model="gpt-4o",
        constraint_generator_temperature=0.0,
        enable_constraint_caching=True,
        # 审计模式
        auditor_mode="strict",  # 严格模式
        enable_symbolic_verification=True,
        # 反思回溯
        enable_reflective_backtracking=True,
        max_backtracking_attempts=5,  # 允许5次尝试
        feedback_verbosity="verbose",  # 详细反馈
        # 日志
        log_level="DEBUG",
        log_constraint_generation=True,
        log_audit_decisions=True,
        # 白名单（总是允许这些工具）
        allow_tool_whitelist=["get_balance", "get_user_info"],
        # 黑名单（总是拒绝这些工具）
        block_tool_blacklist=["delete_all_data"],
    )

    # 创建pipeline
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o")
    pipeline = create_vigil_pipeline(llm, config=custom_config)

    print(f"✓ Created VIGIL pipeline with custom config")
    print(f"  - Auditor mode: {custom_config.auditor_mode}")
    print(f"  - Max backtracking attempts: {custom_config.max_backtracking_attempts}")
    print(f"  - Feedback verbosity: {custom_config.feedback_verbosity}")
    print(f"  - Whitelist: {custom_config.allow_tool_whitelist}")
    print(f"  - Blacklist: {custom_config.block_tool_blacklist}")


def example_compare_configs():
    """示例5: 比较不同配置的效果"""
    print("\n" + "=" * 80)
    print("示例5: 比较不同配置")
    print("=" * 80)

    from vigil_agent import VIGIL_FAST_CONFIG

    configs = {
        "Strict": VIGIL_STRICT_CONFIG,
        "Balanced": VIGIL_BALANCED_CONFIG,
        "Fast": VIGIL_FAST_CONFIG,
    }

    # 创建LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o")

    # 加载suite和attack
    suite = get_suite("v1", "banking")
    attack = DirectAttack()

    for config_name, config in configs.items():
        print(f"\n--- Testing {config_name} Config ---")

        # 创建pipeline
        pipeline = create_vigil_pipeline(llm, config=config)

        # 运行一个简单的测试
        results = benchmark_suite_with_injections(
            agent_pipeline=pipeline,
            suite=suite,
            attack=attack,
            logdir=Path(f"./vigil_runs/{config_name.lower()}"),
            force_rerun=False,
            user_tasks=list(suite.user_tasks.keys())[:1],  # 只运行1个任务
            injection_tasks=list(suite.injection_tasks.keys())[:2],  # 只运行2个注入
        )

        # 显示结果
        stats = pipeline.get_audit_stats()
        print(f"  Total audits: {stats['total_audits']}")
        print(f"  Blocked: {stats['blocked']}")
        print(f"  Allowed: {stats['allowed']}")

        # 重置pipeline以便下次使用
        pipeline.reset_for_new_task()


def example_standalone_components():
    """示例6: 单独使用VIGIL组件（不使用完整pipeline）"""
    print("\n" + "=" * 80)
    print("示例6: 单独使用VIGIL组件")
    print("=" * 80)

    from vigil_agent import ConstraintGenerator, RuntimeAuditor, VIGILConfig
    from vigil_agent.types import ToolCallInfo

    # 创建配置
    config = VIGILConfig()

    # 1. 使用Constraint Generator
    print("\n1. Generating constraints...")
    generator = ConstraintGenerator(config)
    constraint_set = generator.generate_constraints(
        "Please transfer $100 from my account to Alice's account"
    )

    print(f"✓ Generated {len(constraint_set.constraints)} constraints:")
    for i, c in enumerate(constraint_set.constraints, 1):
        print(f"  {i}. [{c.constraint_type}] {c.description}")

    # 2. 使用Runtime Auditor
    print("\n2. Auditing tool calls...")
    auditor = RuntimeAuditor(config, constraint_set)

    # 测试一个合法的工具调用
    legitimate_call: ToolCallInfo = {
        "tool_name": "transfer_money",
        "arguments": {"recipient": "Alice", "amount": 100},
        "tool_call_id": "call_1",
    }

    result1 = auditor.audit_tool_call(legitimate_call)
    print(f"✓ Legitimate call audit: {'ALLOWED' if result1.allowed else 'BLOCKED'}")

    # 测试一个可疑的工具调用
    suspicious_call: ToolCallInfo = {
        "tool_name": "transfer_money",
        "arguments": {"recipient": "Eve", "amount": 10000},  # 不同的接收者和大额
        "tool_call_id": "call_2",
    }

    result2 = auditor.audit_tool_call(suspicious_call)
    print(f"✓ Suspicious call audit: {'ALLOWED' if result2.allowed else 'BLOCKED'}")
    if not result2.allowed:
        print(f"  Feedback: {result2.feedback_message}")

    # 获取统计
    stats = auditor.get_stats()
    print(f"\n📊 Auditor Statistics:")
    print(f"  - Total: {stats['total_audits']}")
    print(f"  - Allowed: {stats['allowed']}")
    print(f"  - Blocked: {stats['blocked']}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("VIGIL Framework - 完整使用示例")
    print("=" * 80)

    # 示例1: 基本使用
    example_basic_usage()

    # 示例2: 测试Utility
    # example_benchmark_without_attacks()  # 取消注释以运行

    # 示例3: 测试Security
    # example_benchmark_with_attacks()  # 取消注释以运行

    # 示例4: 自定义配置
    example_custom_config()

    # 示例5: 比较不同配置
    # example_compare_configs()  # 取消注释以运行

    # 示例6: 单独使用组件
    example_standalone_components()

    print("\n" + "=" * 80)
    print("所有示例完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
