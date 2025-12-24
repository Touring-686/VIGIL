#!/usr/bin/env python3
"""
Example script showing how to use the VIGIL defense in agentdojo.

This script demonstrates how to use VIGIL as a standard defense option,
just like other defenses (tool_filter, pi_detector, etc.).
"""

import sys
import os

# Add paths to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.attacks.baseline_attacks import DirectAttack
from agentdojo.benchmark import benchmark_suite_with_injections


def example_1_create_vigil_pipeline():
    """Example 1: Creating a pipeline with VIGIL defense using PipelineConfig"""
    print("\n" + "=" * 60)
    print("Example 1: Create VIGIL pipeline using PipelineConfig")
    print("=" * 60)

    # Create a pipeline config with VIGIL defense
    config = PipelineConfig(
        llm="gpt-4o-2024-05-13",  # Use a valid model from ModelsEnum
        model_id=None,
        defense="vigil",  # Use VIGIL defense
        system_message_name="default",
        system_message=None,
    )

    # Create the pipeline
    pipeline = AgentPipeline.from_config(config)

    print(f"✓ Created pipeline: {pipeline.name}")
    print(f"  Defense: VIGIL (Neuro-Symbolic Dynamic Constraints)")
    print(f"  Components: {len(pipeline.elements)} pipeline elements")

    return pipeline


def example_2_run_benchmark():
    """Example 2: Run benchmark with VIGIL defense"""
    print("\n" + "=" * 60)
    print("Example 2: Run benchmark with VIGIL defense")
    print("=" * 60)

    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠ Skipping benchmark example (no OPENAI_API_KEY)")
        print("  To run this example, set your OPENAI_API_KEY environment variable")
        return

    # Create VIGIL pipeline
    config = PipelineConfig(
        llm="gpt-4o-2024-05-13",
        model_id=None,
        defense="vigil",
        system_message_name="default",
        system_message=None,
    )
    pipeline = AgentPipeline.from_config(config)

    # Load a small test suite
    suite = get_suite("v1", "banking")
    attack = DirectAttack()

    print(f"✓ Pipeline created: {pipeline.name}")
    print(f"  Suite: {suite.name}")
    print(f"  Attack: {attack.__class__.__name__}")
    print("\nTo run full benchmark:")
    print("  results = benchmark_suite_with_injections(")
    print("      pipeline, suite, attack, logdir=None, force_rerun=False")
    print("  )")


def example_3_compare_defenses():
    """Example 3: Show how to use different defenses"""
    print("\n" + "=" * 60)
    print("Example 3: Comparing different defenses")
    print("=" * 60)

    from agentdojo.agent_pipeline.agent_pipeline import DEFENSES

    print(f"Available defenses in agentdojo: {len(DEFENSES)}")
    for defense in DEFENSES:
        print(f"  • {defense}")

    print("\nTo use any defense:")
    print("  config = PipelineConfig(")
    print("      llm='gpt-4o-2024-05-13',  # Or any valid model from ModelsEnum")
    print("      defense='<defense_name>',  # One of the above")
    print("      system_message_name='default',")
    print("      system_message=None,")
    print("  )")
    print("  pipeline = AgentPipeline.from_config(config)")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("VIGIL Defense Integration Examples")
    print("=" * 60)

    try:
        # Example 1: Create pipeline
        pipeline = example_1_create_vigil_pipeline()

        # Example 2: Run benchmark
        example_2_run_benchmark()

        # Example 3: Compare defenses
        example_3_compare_defenses()

        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        print("\nVIGIL is now fully integrated into agentdojo!")
        print("You can use it like any other defense:")
        print("  • Via command line: --defense vigil")
        print("  • Via PipelineConfig: defense='vigil'")
        print("  • Via AgentPipeline.from_config()")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
