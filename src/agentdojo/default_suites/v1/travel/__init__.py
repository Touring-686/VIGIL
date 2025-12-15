from agentdojo.default_suites.v1.travel.injection_tasks import TravelInjectionTask  # noqa: F401 - Register tasks
from agentdojo.default_suites.v1.travel.task_suite import task_suite as travel_task_suite
from agentdojo.default_suites.v1.travel.user_tasks import TravelUserTask  # noqa: F401 - Register tasks

# Register adversarial tool injection tasks
try:
    import agentdojo.adverseral_tool.travel.type_i_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_ii_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_ii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.travel.type_iii_a  # noqa: F401
except ImportError:
    pass  # Adversarial tools not available

__all__ = ["travel_task_suite"]
