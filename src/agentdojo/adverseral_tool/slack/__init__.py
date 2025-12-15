"""Adversarial tools for Slack suite attacks.

This module provides adversarial attack tools and injection tasks for the Slack suite.

Attack Types:
- Type I-A: Explicit Directive Injection (poisoned docstrings force specific actions)
- Type I-B: Procedural Dependency Trap (fake prerequisite requirements)
- Type II-A: Reasoning Path Short-Circuit (super-tools replace multiple benign tools)
- Type II-B: Induced Parameter Attack (extra parameters trigger malicious behavior)
- Type III-A: SOP Injection + Memory Poisoning (fake errors and persistent rules)
"""

from agentdojo.adverseral_tool.slack.injection_tasks import _BaseSlackAdversarialInjection

# Type I-A: Explicit Directive Injection
from agentdojo.adverseral_tool.slack import type_i_a_tools
from agentdojo.adverseral_tool.slack import type_i_a_injection_tasks

# Type I-B: Procedural Dependency Trap
from agentdojo.adverseral_tool.slack import type_i_b_tools
from agentdojo.adverseral_tool.slack import type_i_b_injection_tasks

# Type II-A: Reasoning Path Short-Circuit
from agentdojo.adverseral_tool.slack import type_ii_a_tools
from agentdojo.adverseral_tool.slack import type_ii_a_injection_tasks

# Type II-B: Induced Parameter Attack
from agentdojo.adverseral_tool.slack import type_ii_b_tools
from agentdojo.adverseral_tool.slack import type_ii_b_injection_tasks

# Type III-A: SOP Injection + Memory Poisoning
from agentdojo.adverseral_tool.slack import type_iii_a_tools
from agentdojo.adverseral_tool.slack import type_iii_a_injection_tasks

__all__ = [
    "_BaseSlackAdversarialInjection",
    # Type I-A
    "type_i_a_tools",
    "type_i_a_injection_tasks",
    # Type I-B
    "type_i_b_tools",
    "type_i_b_injection_tasks",
    # Type II-A
    "type_ii_a_tools",
    "type_ii_a_injection_tasks",
    # Type II-B
    "type_ii_b_tools",
    "type_ii_b_injection_tasks",
    # Type III-A
    "type_iii_a_tools",
    "type_iii_a_injection_tasks",
]
