from collections import defaultdict

import agentdojo.default_suites.v1_1  # Register new tasks
import agentdojo.default_suites.v1_1_1  # Register new tasks
import agentdojo.default_suites.v1_2  # Register new tasks
import agentdojo.default_suites.v1_2_1  # Register new tasks
import agentdojo.default_suites.v1_2_2  # noqa: F401 # Register new tasks
from agentdojo.default_suites.v1.banking import banking_task_suite
from agentdojo.default_suites.v1.slack import slack_task_suite
from agentdojo.default_suites.v1.travel import travel_task_suite
from agentdojo.default_suites.v1.workspace import workspace_task_suite
from agentdojo.task_suite.task_suite import TaskSuite
import agentdojo.adverseral_tool.travel.injection_tasks_shadow  # Direct module import to avoid circular import
from agentdojo.adverseral_tool.travel import type_i_b
from agentdojo.adverseral_tool.travel import type_ii_a
from agentdojo.adverseral_tool.travel import type_ii_b
from agentdojo.adverseral_tool.travel import type_iii_a

# Import injection task modules to register them
# Note: Must be imported AFTER travel_task_suite to avoid circular imports
try:
    import agentdojo.adverseral_tool.travel.type_i_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_i_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_ii_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_ii_b_injection_tasks  # noqa: F401
    
    
    import agentdojo.adverseral_tool.slack.type_i_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.slack.type_i_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.slack.type_ii_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.slack.type_ii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.slack.type_iii_a_injection_tasks  # noqa: F401
    
    import agentdojo.adverseral_tool.banking.type_i_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_i_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_ii_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_ii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_iii_a_injection_tasks  # noqa: F401
    
    import agentdojo.adverseral_tool.workspace.type_i_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.workspace.type_i_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.workspace.type_ii_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.workspace.type_ii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.workspace.type_iii_a_injection_tasks  # noqa: F401
    
    # Type III-B imports
    import agentdojo.adverseral_tool.banking.type_iii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.workspace.type_iii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_iii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.slack.type_iii_b_injection_tasks  # noqa: F401
    
    # import agentdojo.adverseral_tool.travel.type_iii_a_injection_tasks  # noqa: F401
except ImportError as e:
    print(f"Adversarial tool module import failed: {e}")
    pass  # Adversarial tool modules may not be available

_V1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite,
    "travel": travel_task_suite,
    "banking": banking_task_suite,
    "slack": slack_task_suite,
}

_V1_1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite,
    "travel": travel_task_suite.get_new_version((1, 1, 0)),
    "banking": banking_task_suite,
    "slack": slack_task_suite,
}

_V1_1_1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 1, 1)),
    "travel": travel_task_suite.get_new_version((1, 1, 1)),
    "banking": banking_task_suite.get_new_version((1, 1, 1)),
    "slack": slack_task_suite.get_new_version((1, 1, 1)),
}

_V1_1_2_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 1, 2)),
    "travel": travel_task_suite.get_new_version((1, 1, 2)),
    "banking": banking_task_suite.get_new_version((1, 1, 1)),
    "slack": slack_task_suite.get_new_version((1, 1, 1)),
}

_V1_2_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 0)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 0)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
}

_V1_2_1_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 1)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 0)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
}

_V1_2_2_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 2)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 2)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
}

_ADVERSARIAL_SUITES: dict[str, TaskSuite] = {
    "workspace": workspace_task_suite.get_new_version((1, 2, 0)),
    "travel": travel_task_suite.get_new_version((1, 2, 0)),
    "banking": banking_task_suite.get_new_version((1, 2, 0)),
    "slack": slack_task_suite.get_new_version((1, 2, 0)),
}


_SUITES: defaultdict[str, dict[str, TaskSuite]] = defaultdict(
    dict,
    {
        "v1": _V1_SUITES,
        "v1.1": _V1_1_SUITES,
        "v1.1.1": _V1_1_1_SUITES,
        "v1.1.2": _V1_1_2_SUITES,
        "v1.2": _V1_2_SUITES,
        "v1.2.1": _V1_2_1_SUITES,
        "v1.2.2": _V1_2_2_SUITES,
        "adversarial": _ADVERSARIAL_SUITES,
    },
)


def register_suite(suite: TaskSuite, version: str) -> None:
    _SUITES[version][suite.name] = suite


def get_suites(benchmark_version: str) -> dict[str, TaskSuite]:
    return _SUITES[benchmark_version]


def get_suite(benchmark_version: str, suite_name: str) -> TaskSuite:
    return _SUITES[benchmark_version][suite_name]
