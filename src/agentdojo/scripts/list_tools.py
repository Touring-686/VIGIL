"""
List all tools (functions) available in task suites, with their descriptions.

Usage:
  # List tools for default version v1.2.2
  PYTHONPATH=src python -m agentdojo.scripts.list_tools

  # Specify version and save to file
  PYTHONPATH=src python -m agentdojo.scripts.list_tools -v v1.2.2 -o tools.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suites
from agentdojo.task_suite.task_suite import TaskSuite


def escape_md(text: str) -> str:
    # Escape pipe to avoid breaking markdown tables
    return text.replace("|", "\\|")


def list_suite_tools(suite: TaskSuite) -> list[str]:
    lines: list[str] = []
    lines.append(f"## Suite: {suite.name}")
    lines.append(f"- 工具数量: {len(suite.tools)}")
    lines.append("")
    lines.append("| 工具名 | 描述 |")
    lines.append("| --- | --- |")
    for tool in suite.tools:
        name = escape_md(tool.name)
        desc = escape_md(tool.description or "")
        lines.append(f"| {name} | {desc} |")
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="List all tools (name + description) for a benchmark version.")
    parser.add_argument("-v", "--version", default="v1.2.2", help="Benchmark version (default: v1.2.2).")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional path to save output markdown.",
    )
    args = parser.parse_args()

    suites = get_suites(args.version)
    lines: list[str] = [f"# 工具清单（version {args.version})", ""]
    for suite in suites.values():
        lines.extend(list_suite_tools(suite))

    text = "\n".join(lines)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
