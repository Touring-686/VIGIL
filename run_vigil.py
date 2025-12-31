#!/usr/bin/env python3
"""
VIGIL Agent - 快速运行脚本

使用这个脚本快速在AgentDojo benchmark上测试VIGIL agent。
"""

import logging
import os
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

import openai
from rich.logging import RichHandler

# 配置彩色日志
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
    handlers=[RichHandler(show_path=False, markup=True)],
)

from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.attacks.base_attacks import DirectAttack
from agentdojo.benchmark import benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite
from vigil_agent import create_vigil_pipeline, get_vigil_config


def main():
    """运行VIGIL benchmark"""
    print("=" * 80)
    print("VIGIL Agent - Quick Run Script")
    print("=" * 80)

    # 配置 - 支持环境变量覆盖
    SUITE_NAME = os.getenv("VIGIL_SUITE", "banking")  # 可修改: "banking" | "slack" | "travel" | "workspace"
    MODEL = os.getenv("VIGIL_MODEL", "gpt-4o")  # 可修改为其他OpenAI模型
    LOGDIR = Path(os.getenv("VIGIL_LOGDIR", "./vigil_runs"))
    RUN_ATTACKS = os.getenv("VIGIL_RUN_ATTACKS", "true").lower() == "true"  # 设为False只测试utility

    print(f"\nConfiguration:")
    print(f"  Suite: {SUITE_NAME}")
    print(f"  Model: {MODEL}")
    print(f"  Log directory: {LOGDIR}")
    print(f"  Run with attacks: {RUN_ATTACKS}")

    # 检查API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n⚠️  Warning: OPENAI_API_KEY not set!")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)

    # 创建pipeline
    print("\n🔧 Creating VIGIL pipeline...")
    client = openai.OpenAI()
    llm = OpenAILLM(client, MODEL)
    pipeline = create_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)
    print(f"✓ Pipeline created: {pipeline.name}")

    # 加载suite
    print(f"\n📦 Loading {SUITE_NAME} suite...")
    suite = get_suite("v1", SUITE_NAME)
    print(f"✓ Suite loaded:")
    print(f"  - User tasks: {len(suite.user_tasks)}")
    print(f"  - Injection tasks: {len(suite.injection_tasks)}")

    if RUN_ATTACKS:
        # 运行带攻击的benchmark
        print("\n🔴 Running benchmark WITH attacks...")
        attack = DirectAttack()
        print(f"  Attack type: {attack.name}")

        # 使用 OutputLogger 来显示彩色消息日志
        with OutputLogger(str(LOGDIR)):
            results = benchmark_suite_with_injections(
                agent_pipeline=pipeline,
                suite=suite,
                attack=attack,
                logdir=LOGDIR,
                force_rerun=False,
                # 取消下面的注释来只运行部分任务（用于快速测试）
                # user_tasks=list(suite.user_tasks.keys())[:2],
                # injection_tasks=list(suite.injection_tasks.keys())[:3],
            )

        # 显示结果
        utility = results["utility_results"]
        security = results["security_results"]

        if utility:
            utility_rate = sum(utility.values()) / len(utility)
            print(f"\n📊 Results:")
            print(f"  Utility Rate: {utility_rate:.2%}")

        if security:
            security_rate = sum(security.values()) / len(security)
            print(f"  Security Rate: {security_rate:.2%}")

    else:
        # 只运行utility测试
        print("\n🟢 Running benchmark WITHOUT attacks (utility only)...")

        # 使用 OutputLogger 来显示彩色消息日志
        with OutputLogger(str(LOGDIR)):
            results = benchmark_suite_without_injections(
                agent_pipeline=pipeline,
                suite=suite,
                logdir=LOGDIR,
                force_rerun=False,
            )

        # 显示结果
        utility = results["utility_results"]
        if utility:
            utility_rate = sum(utility.values()) / len(utility)
            print(f"\n📊 Results:")
            print(f"  Utility Rate: {utility_rate:.2%}")

    # 审计统计
    stats = pipeline.get_audit_stats()
    print(f"\n🔍 Audit Statistics:")
    print(f"  Total audits: {stats['total_audits']}")
    print(f"  Allowed: {stats['allowed']}")
    print(f"  Blocked: {stats['blocked']}")
    print(f"  Confirmations: {stats['confirmed']}")

    print("\n" + "=" * 80)
    print("✓ Benchmark completed!")
    print(f"📁 Logs saved to: {LOGDIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
