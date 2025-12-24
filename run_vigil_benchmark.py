"""
完整VIGIL框架 - Benchmark测试脚本

这个脚本展示了如何使用完整的VIGIL框架（四层架构）运行AgentDojo benchmark。

VIGIL框架包含：
- Layer 0: Perception Sanitizer (防御Type I-A, I-B, III-A)
- Layer 1: Intent Anchor (Constraints + Abstract Sketch)
- Layer 2: Speculative Reasoner (Hypothesizer)
- Layer 3: Neuro-Symbolic Verifier (Enhanced Auditor with Minimum Necessity)

使用方法：
    python run_vigil_benchmark.py --suite banking --attack direct --output ./vigil_results
"""

import argparse
import logging
import os
from pathlib import Path

import openai
from dotenv import load_dotenv
from agentdojo.attacks.attack_registry import load_attack
# 加载 .env 文件中的环境变量
load_dotenv()

# 模型名称映射（支持自定义模型名称）
MODEL_NAME_MAPPING = {
    # Qwen 模型映射
    "QWEN3_MAX": "qwen-max",
    "QWEN_MAX": "qwen-max",
    "QWEN_PLUS": "qwen-plus",
    "QWEN_TURBO": "qwen-turbo",
    "QWEN_LONG": "qwen-long",
    # 保持 OpenAI 模型名称不变
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4-turbo": "gpt-4-turbo",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
}


def normalize_model_name(model: str) -> str:
    """标准化模型名称

    Args:
        model: 原始模型名称

    Returns:
        标准化后的模型名称
    """
    return MODEL_NAME_MAPPING.get(model, model)

# 导入VIGIL组件
from vigil_agent import (
    create_enhanced_vigil_pipeline,  # 完整VIGIL框架
    create_vigil_pipeline,  # 基础VIGIL
    get_vigil_config,  # 导入配置生成函数
    VIGILConfig,
)

# 导入AgentDojo组件
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.attacks.baseline_attacks import DirectAttack
from agentdojo.attacks.tool_attack import ToolAttack
from agentdojo.benchmark import benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.task_suite.load_suites import get_suite

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Run VIGIL Framework Benchmark")

    parser.add_argument(
        "--suite",
        type=str,
        default="banking",
        choices=["banking", "travel", "slack", "workspace"],
        help="Task suite to test (default: banking)"
    )

    parser.add_argument(
        "--attack",
        type=str,
        default="direct",
        choices=["direct", "tool_attack", "important_instructions", "none"],
        help="Attack type (default: direct, use 'none' for utility-only test)"
    )

    parser.add_argument(
        "--attack-vector-type",
        type=str,
        default="type_i_a",
        choices=["type_i_a", "type_i_b", "type_ii_a", "type_ii_b", "type_iii_a", "type_iii_b"],
        help="Attack vector type for tool attacks (default: type_i_a)"
    )
    
    parser.add_argument(
        "--attack-type",
        type=str,
        choices=["parameter_override", "postaction_dependency", "prerequisite_dependency", "short_circuit_reasoning", "induced_parameter", "sop_exfiltration"],
        help="Attack vector type for tool attacks (default: type_i_a)"
    )
    

    parser.add_argument(
        "--framework",
        type=str,
        default="enhanced",
        choices=["basic", "enhanced"],
        help="VIGIL framework version (default: enhanced = 4-layer, basic = 2-layer)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="balanced",
        choices=["strict", "balanced", "fast"],
        help="VIGIL configuration preset (default: balanced)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./vigil_benchmark_results",
        help="Output directory for results (default: ./vigil_benchmark_results)"
    )

    parser.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="Maximum number of tasks to run (for quick testing)"
    )

    parser.add_argument(
        "--max-injections",
        type=int,
        default=None,
        help="Maximum number of injection tasks to run"
    )

    parser.add_argument(
        "--force-rerun",
        action="store_true",
        help="Force rerun all tasks even if results exist"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def create_pipeline(framework: str, model: str, preset: str):
    """创建VIGIL pipeline

    Args:
        framework: 框架版本 ("basic" or "enhanced")
        model: LLM模型名称
        preset: 配置预设名称 ("strict", "balanced", "fast")

    Returns:
        VIGIL pipeline
    """
    # 标准化模型名称
    normalized_model = normalize_model_name(model)

    # 显示 API 配置信息
    api_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key_prefix = os.getenv("OPENAI_API_KEY", "")[:8] + "..." if os.getenv("OPENAI_API_KEY") else "Not set"

    logger.info(f"\nAPI Configuration:")
    logger.info(f"  Base URL: {api_base}")
    logger.info(f"  API Key: {api_key_prefix}")
    logger.info(f"  Model (original): {model}")
    if normalized_model != model:
        logger.info(f"  Model (normalized): {normalized_model}")

    # 创建LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, normalized_model)

    # 获取配置（根据模型和预设）
    config = get_vigil_config(preset, normalized_model)

    # 创建pipeline
    if framework == "enhanced":
        logger.info("Creating Enhanced VIGIL Pipeline (4-layer architecture)")
        pipeline = create_enhanced_vigil_pipeline(llm, config=config)
    else:
        logger.info("Creating Basic VIGIL Pipeline (2-layer architecture)")
        pipeline = create_vigil_pipeline(llm, config=config)

    return pipeline


def run_benchmark_without_attacks(args, pipeline, suite):
    """运行无攻击的benchmark（测试utility）

    Args:
        args: 命令行参数
        pipeline: VIGIL pipeline
        suite: 任务套件

    Returns:
        测试结果
    """
    logger.info("\n" + "=" * 80)
    logger.info("Running UTILITY TEST (No Attacks)")
    logger.info("=" * 80)

    # 确定要测试的任务
    user_tasks = list(suite.user_tasks.keys())
    if args.max_tasks:
        user_tasks = user_tasks[:args.max_tasks]

    logger.info(f"Testing {len(user_tasks)} user tasks")

    # 运行benchmark
    results = benchmark_suite_without_injections(
        agent_pipeline=pipeline,
        suite=suite,
        logdir=Path(args.output) / "utility",
        force_rerun=args.force_rerun,
        user_tasks=user_tasks,
    )

    # 计算结果
    utility_rate = sum(results["utility_results"].values()) / len(results["utility_results"])

    logger.info("\n" + "=" * 80)
    logger.info("UTILITY TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Utility Rate: {utility_rate:.2%} ({sum(results['utility_results'].values())}/{len(results['utility_results'])})")

    # 获取审计统计
    if hasattr(pipeline, 'get_audit_stats'):
        stats = pipeline.get_audit_stats()
        logger.info("\nAudit Statistics:")
        logger.info(f"  Total audits: {stats['total_audits']}")
        logger.info(f"  Allowed: {stats['allowed']}")
        logger.info(f"  Blocked: {stats['blocked']}")

    return results


def run_benchmark_with_attacks(args, pipeline, suite, attack):
    """运行有攻击的benchmark（测试security）

    Args:
        args: 命令行参数
        pipeline: VIGIL pipeline
        suite: 任务套件
        attack: 攻击实例

    Returns:
        测试结果
    """
    logger.info("\n" + "=" * 80)
    logger.info(f"Running SECURITY TEST (Attack: {attack.name})")
    logger.info("=" * 80)

    # 确定要测试的任务
    user_tasks = list(suite.user_tasks.keys())
    injection_tasks = list(suite.injection_tasks.keys())

    if args.max_tasks:
        user_tasks = user_tasks[:args.max_tasks]
    if args.max_injections:
        injection_tasks = injection_tasks[:args.max_injections]

    logger.info(f"Testing {len(user_tasks)} user tasks")
    logger.info(f"Testing {len(injection_tasks)} injection tasks")

    # 运行benchmark
    results = benchmark_suite_with_injections(
        agent_pipeline=pipeline,
        suite=suite,
        attack=attack,
        logdir=Path(args.output) / f"security_{attack.name}",
        force_rerun=args.force_rerun,
        user_tasks=user_tasks,
        injection_tasks=injection_tasks,
    )

    # 计算结果
    utility_results = results["utility_results"]
    security_results = results["security_results"]

    utility_rate = sum(utility_results.values()) / len(utility_results) if utility_results else 0.0
    security_rate = sum(security_results.values()) / len(security_results) if security_results else 0.0

    logger.info("\n" + "=" * 80)
    logger.info("SECURITY TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Utility Rate: {utility_rate:.2%} ({sum(utility_results.values())}/{len(utility_results)})")
    logger.info(f"Security Rate: {security_rate:.2%} ({sum(security_results.values())}/{len(security_results)})")

    # 获取审计统计
    if hasattr(pipeline, 'get_audit_stats'):
        stats = pipeline.get_audit_stats()
        logger.info("\nAudit Statistics:")
        logger.info(f"  Total audits: {stats['total_audits']}")
        logger.info(f"  Allowed: {stats['allowed']}")
        logger.info(f"  Blocked: {stats['blocked']}")

    return results


def main():
    """主函数"""
    args = parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("\n" + "=" * 80)
    logger.info("VIGIL Framework - Benchmark Test")
    logger.info("=" * 80)
    logger.info(f"Framework: {args.framework.upper()}")
    logger.info(f"Suite: {args.suite}")
    logger.info(f"Attack: {args.attack}")
    if args.attack == "tool":
        logger.info(f"Attack Vector: {args.attack_vector_type}")
        logger.info(f"Attack Type: {args.attack_type}")
    logger.info(f"Config: {args.config}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Output: {args.output}")

    # 创建输出目录
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # 创建pipeline（传入model和config预设）
    pipeline = create_pipeline(args.framework, args.model, args.config)

    # 加载suite
    suite = get_suite("adversarial", args.suite)
    logger.info(f"\nLoaded suite: {suite.name}")
    logger.info(f"  User tasks: {len(suite.user_tasks)}")
    logger.info(f"  Injection tasks: {len(suite.injection_tasks)}")

    # 运行benchmark
    if args.attack == "none":
        # 只测试utility
        results = run_benchmark_without_attacks(args, pipeline, suite)
    else:
        # 测试security
        if args.attack == "direct":
            attacker_ = DirectAttack(suite, pipeline)
        elif args.attack == "tool_attack":
            attacker_ = load_attack(
                args.attack, 
                suite,
                pipeline,
                attack_vector_type=args.attack_vector_type, 
                attack_type=args.attack_type
            )
            # attack = ToolAttack(suite, pipeline, args.attack_vector)
        else:
            raise ValueError(f"Unknown attack type: {args.attack}")

        results = run_benchmark_with_attacks(
                    args, 
                    pipeline, 
                    suite, 
                    attacker_
                )

    logger.info("\n" + "=" * 80)
    logger.info("Benchmark Complete!")
    logger.info("=" * 80)
    logger.info(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
