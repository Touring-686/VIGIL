#!/usr/bin/env python3
"""
Run VIGIL framework on user tasks only (without injection tasks/attacks).

This script tests VIGIL's performance on normal tasks without any adversarial attacks,
allowing you to measure the utility cost of the defense mechanism.

Usage:
    python run_vigil_user_tasks.py --suite banking
    python run_vigil_user_tasks.py --suite slack --model gpt-4o
    python run_vigil_user_tasks.py --suite all --output ./results
"""

import argparse
import subprocess
import sys
from pathlib import Path


SUITES = ["banking", "slack", "travel", "workspace"]


def run_user_tasks(
    suite: str,
    model: str = "QWEN3_MAX",
    output_dir: str = "./runs/vigil",
    max_workers: int = 1,
    force_rerun: bool = True,
    verbose: bool = True,
):
    """Run VIGIL framework on user tasks only for a specific suite."""

    output_path = Path(output_dir) / suite / "user_tasks_only"

    cmd = [
        sys.executable, "-m", "agentdojo.scripts.benchmark",
        "--suite", suite,
        "--benchmark-version", "adversarial",
        "--defense", "vigil",
        "--model", model,
        "--max-workers", str(max_workers),
        "--logdir", str(output_path),
    ]

    if force_rerun:
        cmd.append("--force-rerun")

    if verbose:
        print(f"\n{'='*80}")
        print(f"Running VIGIL on {suite.upper()} suite - User Tasks Only (No Attack)")
        print(f"{'='*80}")
        print(f"Model: {model}")
        print(f"Output: {output_path}")
        print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            env={
                **subprocess.os.environ,
                "PYTHONPATH": f"{Path(__file__).parent}/src:{Path(__file__).parent}",
            }
        )

        if verbose:
            print(f"\n✓ Successfully completed {suite} suite")

        return result.returncode

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running {suite} suite: {e}", file=sys.stderr)
        return e.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run VIGIL framework on user tasks only (no attacks)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on a single suite
  python run_vigil_user_tasks.py --suite banking

  # Run on all suites
  python run_vigil_user_tasks.py --suite all

  # Use different model
  python run_vigil_user_tasks.py --suite banking --model gpt-4o

  # Custom output directory
  python run_vigil_user_tasks.py --suite slack --output ./my_results
        """
    )

    parser.add_argument(
        "--suite",
        choices=SUITES + ["all"],
        required=True,
        help="Suite to run, or 'all' to run all suites"
    )

    parser.add_argument(
        "--model",
        default="QWEN3_MAX",
        help="Model to use (default: QWEN3_MAX)"
    )

    parser.add_argument(
        "--output",
        default="./runs/vigil",
        help="Output directory for results (default: ./runs/vigil)"
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)"
    )

    parser.add_argument(
        "--no-force-rerun",
        action="store_true",
        help="Don't force rerun if results already exist"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    # Determine which suites to run
    if args.suite == "all":
        suites_to_run = SUITES
    else:
        suites_to_run = [args.suite]

    # Run each suite
    results = {}
    for suite in suites_to_run:
        returncode = run_user_tasks(
            suite=suite,
            model=args.model,
            output_dir=args.output,
            max_workers=args.max_workers,
            force_rerun=not args.no_force_rerun,
            verbose=not args.quiet,
        )
        results[suite] = returncode

    # Print summary
    if not args.quiet and len(suites_to_run) > 1:
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        for suite, returncode in results.items():
            status = "✓ SUCCESS" if returncode == 0 else "✗ FAILED"
            print(f"{suite:12} {status}")

    # Exit with error if any suite failed
    if any(code != 0 for code in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
