from agentdojo.default_suites.v1.slack.injection_tasks import SlackInjectionTask  # noqa: F401 - Register tasks
from agentdojo.default_suites.v1.slack.task_suite import task_suite as slack_task_suite
from agentdojo.default_suites.v1.slack.user_tasks import SlackUserTask  # noqa: F401 - Register tasks

# Import Type III-A injection tasks
try:
    import agentdojo.adverseral_tool.slack.type_iii_a_injection_tasks  # noqa: F401
except ImportError:
    pass  # Type III-A tasks not available

__all__ = ["slack_task_suite"]
