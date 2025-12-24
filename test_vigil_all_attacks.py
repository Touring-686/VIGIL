#!/usr/bin/env python3
"""
Comprehensive test script for VIGIL framework against all attack types in agentdojo.

This script tests VIGIL defense against:
1. Tool Attack (6 types): type_i_a (intent_hijacking + parameter_override), type_i_b, type_ii_a, type_ii_b, type_iii_a
2. Important Instructions Attack: Original agentdojo attack

For each of the 4 suites (banking, slack, travel, workspace).
"""

import os
import sys
import json
from datetime import datetime
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
from vigil_agent import create_enhanced_vigil_pipeline, VIGIL_BALANCED_CONFIG, VIGIL_STRICT_CONFIG

# Test Configuration
SUITES = ["banking", "slack", "travel", "workspace"]

# Tool Attack Types with descriptions
TOOL_ATTACK_TYPES = {
    "type_i_a": {
        "name": "Type I-A: Docstring Injection",
        "subtypes": {
            "intent_hijacking": "Goal Hijacking via Docstring",
            "parameter_override": "Parameter Override via Docstring"
        }
    },
    "type_i_b": {
        "name": "Type I-B: Logic Trap",
        "subtypes": {
            "logic_trap": "Implicit Logic Trap in Tool Implementation"
        }
    },
    "type_ii_a": {
        "name": "Type II-A: Reasoning Distortion",
        "subtypes": {
            "reasoning_distortion": "Reasoning Distortion via Tool Description"
        }
    },
    "type_ii_b": {
        "name": "Type II-B: Over-Optimization",
        "subtypes": {
            "over_optimization": "Over-Optimization Attack via More Powerful Tools"
        }
    },
    "type_iii_a": {
        "name": "Type III-A: SOP Injection",
        "subtypes": {
            "sop_injection": "SOP Injection via Error Messages"
        }
    }
}

# Important Instructions Attack
IMPORTANT_INSTRUCTIONS_ATTACK = {
    "name": "Important Instructions Attack",
    "description": "Original agentdojo attack - inject instructions in user query"
}


class VIGILTester:
    """Comprehensive tester for VIGIL framework"""

    def __init__(self, output_dir="vigil_test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Check API key
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        # Create LLM
        self.client = openai.OpenAI()
        self.llm_model = "gpt-4o-2024-08-06"

        # Results storage
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "llm_model": self.llm_model,
            "vigil_config": "VIGIL_BALANCED_CONFIG",
            "suites": {}
        }

    def create_vigil_pipeline(self):
        """Create VIGIL pipeline"""
        llm = OpenAILLM(self.client, self.llm_model)
        pipeline = create_enhanced_vigil_pipeline(llm, config=VIGIL_BALANCED_CONFIG)
        return pipeline

    def test_tool_attack(self, suite_name, attack_vector_type, attack_type=None):
        """Test a specific tool attack type on a suite"""
        print(f"\n{'='*80}")
        print(f"Testing: {suite_name} - {attack_vector_type}" +
              (f" ({attack_type})" if attack_type else ""))
        print(f"{'='*80}")

        # Load suite
        suite = get_suite("v1", suite_name)

        # Create pipeline
        pipeline = self.create_vigil_pipeline()

        # Create attack
        attack = ToolAttack(
            task_suite=suite,
            target_pipeline=pipeline,
            attack_vector_type=attack_vector_type,
            attack_type=attack_type
        )

        # Run benchmark
        print(f"Running benchmark...")
        results = benchmark_suite_with_injections(
            pipeline=pipeline,
            task_suite=suite,
            attack=attack,
            logdir=self.output_dir / "logs" / suite_name / attack_vector_type / (attack_type or "default"),
            force_rerun=False
        )

        print(f"✓ Completed: {suite_name} - {attack_vector_type}" +
              (f" ({attack_type})" if attack_type else ""))

        return results

    def test_important_instructions_attack(self, suite_name):
        """Test important instructions attack on a suite"""
        print(f"\n{'='*80}")
        print(f"Testing: {suite_name} - Important Instructions Attack")
        print(f"{'='*80}")

        # Load suite
        suite = get_suite("v1", suite_name)

        # Create pipeline
        pipeline = self.create_vigil_pipeline()

        # Create attack
        attack = ImportantInstructionsAttack(
            task_suite=suite,
            target_pipeline=pipeline
        )

        # Run benchmark
        print(f"Running benchmark...")
        results = benchmark_suite_with_injections(
            pipeline=pipeline,
            task_suite=suite,
            attack=attack,
            logdir=self.output_dir / "logs" / suite_name / "important_instructions",
            force_rerun=False
        )

        print(f"✓ Completed: {suite_name} - Important Instructions Attack")

        return results

    def run_all_tests(self, suites=None, tool_attack_types=None, test_tool_attacks=True, test_important_instructions=True):
        """Run all test scenarios"""
        # Use provided suites or default
        suites_to_test = suites if suites is not None else SUITES
        attack_types_to_test = tool_attack_types if tool_attack_types is not None else TOOL_ATTACK_TYPES

        print("\n" + "="*80)
        print("VIGIL Framework - Comprehensive Attack Testing")
        print("="*80)
        print(f"LLM Model: {self.llm_model}")
        print(f"VIGIL Config: VIGIL_BALANCED_CONFIG")
        print(f"Output Directory: {self.output_dir}")
        print(f"Suites to test: {', '.join(suites_to_test)}")
        print("="*80)

        for suite_name in suites_to_test:
            print(f"\n{'#'*80}")
            print(f"# Suite: {suite_name.upper()}")
            print(f"{'#'*80}")

            self.results["suites"][suite_name] = {
                "tool_attacks": {},
                "important_instructions": None
            }

            # Test tool attacks
            if test_tool_attacks:
                print(f"\n[{suite_name}] Testing Tool Attacks...")

                for attack_vector_type, attack_info in attack_types_to_test.items():
                    print(f"\n--- {attack_info['name']} ---")

                    for subtype_key, subtype_desc in attack_info['subtypes'].items():
                        try:
                            # For type_i_a, we need to specify attack_type
                            if attack_vector_type == "type_i_a":
                                results = self.test_tool_attack(
                                    suite_name,
                                    attack_vector_type,
                                    attack_type=subtype_key
                                )
                            else:
                                # For other types, attack_type is optional
                                results = self.test_tool_attack(
                                    suite_name,
                                    attack_vector_type
                                )

                            # Store results
                            key = f"{attack_vector_type}_{subtype_key}"
                            self.results["suites"][suite_name]["tool_attacks"][key] = {
                                "attack_type": attack_vector_type,
                                "subtype": subtype_key,
                                "description": subtype_desc,
                                "results": results
                            }

                            # Only test one subtype for non-type_i_a attacks
                            if attack_vector_type != "type_i_a":
                                break

                        except Exception as e:
                            print(f"✗ Error testing {suite_name} - {attack_vector_type} ({subtype_key}): {e}")
                            import traceback
                            traceback.print_exc()

            # Test important instructions attack
            if test_important_instructions:
                print(f"\n[{suite_name}] Testing Important Instructions Attack...")
                try:
                    results = self.test_important_instructions_attack(suite_name)
                    self.results["suites"][suite_name]["important_instructions"] = results
                except Exception as e:
                    print(f"✗ Error testing {suite_name} - Important Instructions: {e}")
                    import traceback
                    traceback.print_exc()

        # Save results
        self.save_results()

        # Print summary
        self.print_summary()

    def save_results(self):
        """Save results to JSON file"""
        output_file = self.output_dir / f"vigil_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n✓ Results saved to: {output_file}")

    def print_summary(self):
        """Print summary of results"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        for suite_name, suite_results in self.results["suites"].items():
            print(f"\n{suite_name.upper()}:")

            # Tool attacks
            if suite_results["tool_attacks"]:
                print(f"  Tool Attacks: {len(suite_results['tool_attacks'])} tests")
                for attack_key, attack_data in suite_results["tool_attacks"].items():
                    print(f"    - {attack_data['description']}: ✓")

            # Important instructions
            if suite_results["important_instructions"]:
                print(f"  Important Instructions Attack: ✓")

        print("\n" + "="*80)
        print("All tests completed!")
        print("="*80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test VIGIL framework against all attacks")
    parser.add_argument("--suite", choices=SUITES + ["all"], default="all",
                        help="Suite to test (default: all)")
    parser.add_argument("--attack-type", choices=["tool", "important_instructions", "all"],
                        default="all", help="Attack type to test (default: all)")
    parser.add_argument("--output-dir", default="vigil_test_results",
                        help="Output directory for results")
    parser.add_argument("--quick-test", action="store_true",
                        help="Quick test mode: only test one suite with one attack type")

    args = parser.parse_args()

    # Create tester
    tester = VIGILTester(output_dir=args.output_dir)

    # Quick test mode
    if args.quick_test:
        print("\n⚡ Quick Test Mode: Testing banking suite with type_i_a attack only")
        tester.run_all_tests(
            suites=["banking"],
            tool_attack_types={"type_i_a": TOOL_ATTACK_TYPES["type_i_a"]},
            test_tool_attacks=True,
            test_important_instructions=False
        )
        return

    # Normal test mode
    # Filter suites
    suites_to_test = SUITES if args.suite == "all" else [args.suite]

    # Run tests
    tester.run_all_tests(
        suites=suites_to_test,
        test_tool_attacks=(args.attack_type in ["tool", "all"]),
        test_important_instructions=(args.attack_type in ["important_instructions", "all"])
    )


if __name__ == "__main__":
    main()
