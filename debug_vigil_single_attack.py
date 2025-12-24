#!/usr/bin/env python3
"""
Debug script for testing VIGIL against a single attack scenario.

This is useful for:
1. Quickly testing specific attack types
2. Debugging VIGIL's behavior on specific scenarios
3. Iterating on VIGIL improvements

Usage examples:
    # Test Type I-A intent hijacking on banking suite
    python debug_vigil_single_attack.py --suite banking --attack-type type_i_a --subtype intent_hijacking

    # Test Type II-A on travel suite
    python debug_vigil_single_attack.py --suite travel --attack-type type_ii_a

    # Test important instructions on slack suite
    python debug_vigil_single_attack.py --suite slack --attack important_instructions

    # Run with verbose logging
    python debug_vigil_single_attack.py --suite banking --attack-type type_i_a --verbose
"""

import os
import sys
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

import openai
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.attacks.tool_attack import ToolAttack
from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
from agentdojo.benchmark import benchmark_suite_with_injections
from vigil_agent import (
    create_enhanced_vigil_pipeline,
    VIGIL_BALANCED_CONFIG,
    VIGIL_STRICT_CONFIG,
    VIGIL_FAST_CONFIG,
)


def setup_logging(verbose=False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )


def test_tool_attack(suite_name, attack_vector_type, attack_type=None, config=VIGIL_BALANCED_CONFIG, verbose=False):
    """Test VIGIL against a tool attack"""
    print("\n" + "="*80)
    print(f"DEBUG: Tool Attack Test")
    print("="*80)
    print(f"Suite: {suite_name}")
    print(f"Attack Vector: {attack_vector_type}")
    print(f"Attack Type: {attack_type or 'N/A'}")
    print(f"VIGIL Config: {config.__class__.__name__ if hasattr(config, '__class__') else 'Custom'}")
    print("="*80)

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable must be set")

    # Create LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o-2024-08-06")

    # Create VIGIL pipeline
    print("\n[1/4] Creating VIGIL pipeline...")
    pipeline = create_enhanced_vigil_pipeline(llm, config=config)
    print(f"✓ Pipeline created: {pipeline.name}")

    # Load suite
    print(f"\n[2/4] Loading suite: {suite_name}...")
    suite = get_suite("v1", suite_name)
    print(f"✓ Suite loaded: {suite.name}")
    print(f"  - User tasks: {len(suite.user_tasks)}")
    print(f"  - Injection tasks: {len(suite.injection_tasks)}")
    print(f"  - Tools: {len(suite.tools)}")

    # Create attack
    print(f"\n[3/4] Creating attack: {attack_vector_type}...")
    attack = ToolAttack(
        task_suite=suite,
        target_pipeline=pipeline,
        attack_vector_type=attack_vector_type,
        attack_type=attack_type
    )
    print(f"✓ Attack created")
    print(f"  - Attack mode tools: {len(suite.tools_attack_mode)}")
    print(f"  - Injection vectors: {len(attack.injection_vectors)}")

    # Run benchmark
    print(f"\n[4/4] Running benchmark...")
    logdir = Path("debug_logs") / suite_name / attack_vector_type / (attack_type or "default")
    results = benchmark_suite_with_injections(
        pipeline=pipeline,
        task_suite=suite,
        attack=attack,
        logdir=logdir,
        force_rerun=True  # Always rerun in debug mode
    )

    # Print results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Results type: {type(results)}")
    print(f"Results: {results}")

    # Get audit stats
    if hasattr(pipeline, 'get_audit_stats'):
        stats = pipeline.get_audit_stats()
        print("\nVIGIL Audit Statistics:")
        print(f"  - Total audits: {stats.get('total_audits', 0)}")
        print(f"  - Allowed: {stats.get('allowed', 0)}")
        print(f"  - Blocked: {stats.get('blocked', 0)}")
        print(f"  - Block rate: {stats.get('blocked', 0) / max(stats.get('total_audits', 1), 1) * 100:.1f}%")

    print("\n✓ Test completed!")
    print(f"Logs saved to: {logdir}")

    return results


def test_important_instructions(suite_name, config=VIGIL_BALANCED_CONFIG, verbose=False):
    """Test VIGIL against important instructions attack"""
    print("\n" + "="*80)
    print(f"DEBUG: Important Instructions Attack Test")
    print("="*80)
    print(f"Suite: {suite_name}")
    print(f"VIGIL Config: {config.__class__.__name__ if hasattr(config, '__class__') else 'Custom'}")
    print("="*80)

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable must be set")

    # Create LLM
    client = openai.OpenAI()
    llm = OpenAILLM(client, "gpt-4o-2024-08-06")

    # Create VIGIL pipeline
    print("\n[1/4] Creating VIGIL pipeline...")
    pipeline = create_enhanced_vigil_pipeline(llm, config=config)
    print(f"✓ Pipeline created: {pipeline.name}")

    # Load suite
    print(f"\n[2/4] Loading suite: {suite_name}...")
    suite = get_suite("v1", suite_name)
    print(f"✓ Suite loaded: {suite.name}")

    # Create attack
    print(f"\n[3/4] Creating attack: ImportantInstructions...")
    attack = ImportantInstructionsAttack(
        task_suite=suite,
        target_pipeline=pipeline
    )
    print(f"✓ Attack created")

    # Run benchmark
    print(f"\n[4/4] Running benchmark...")
    logdir = Path("debug_logs") / suite_name / "important_instructions"
    results = benchmark_suite_with_injections(
        pipeline=pipeline,
        task_suite=suite,
        attack=attack,
        logdir=logdir,
        force_rerun=True
    )

    # Print results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Results: {results}")

    print("\n✓ Test completed!")
    print(f"Logs saved to: {logdir}")

    return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Debug VIGIL against a single attack scenario",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test Type I-A intent hijacking on banking
  %(prog)s --suite banking --attack-type type_i_a --subtype intent_hijacking

  # Test Type II-A on travel with strict config
  %(prog)s --suite travel --attack-type type_ii_a --config strict

  # Test important instructions on slack with verbose logging
  %(prog)s --suite slack --attack important_instructions --verbose
        """
    )

    # Required arguments
    parser.add_argument("--suite", required=True,
                        choices=["banking", "slack", "travel", "workspace"],
                        help="Test suite to use")

    parser.add_argument("--attack", required=True,
                        choices=["tool", "important_instructions"],
                        help="Attack category")

    # Optional arguments for tool attacks
    parser.add_argument("--attack-type",
                        choices=["type_i_a", "type_i_b", "type_ii_a", "type_ii_b", "type_iii_a"],
                        help="Tool attack vector type (required if --attack=tool)")

    parser.add_argument("--subtype",
                        choices=["intent_hijacking", "parameter_override", "logic_trap",
                                 "reasoning_distortion", "over_optimization", "sop_injection"],
                        help="Attack subtype (only for type_i_a)")

    # VIGIL configuration
    parser.add_argument("--config",
                        choices=["balanced", "strict", "fast"],
                        default="balanced",
                        help="VIGIL configuration preset (default: balanced)")

    # Logging
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Validate arguments
    if args.attack == "tool" and not args.attack_type:
        parser.error("--attack-type is required when --attack=tool")

    # Select config
    config_map = {
        "balanced": VIGIL_BALANCED_CONFIG,
        "strict": VIGIL_STRICT_CONFIG,
        "fast": VIGIL_FAST_CONFIG,
    }
    config = config_map[args.config]

    # Run test
    try:
        if args.attack == "tool":
            test_tool_attack(
                suite_name=args.suite,
                attack_vector_type=args.attack_type,
                attack_type=args.subtype,
                config=config,
                verbose=args.verbose
            )
        else:  # important_instructions
            test_important_instructions(
                suite_name=args.suite,
                config=config,
                verbose=args.verbose
            )

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
