from agentdojo.default_suites.v1.banking.injection_tasks import BankingInjectionTask  # noqa: F401 - Register tasks
from agentdojo.default_suites.v1.banking.task_suite import task_suite as banking_task_suite
from agentdojo.default_suites.v1.banking.user_tasks import BankingUserTask  # noqa: F401 - Register tasks

__all__ = ["banking_task_suite"]

# Import adversarial tool modules to register their injection tasks
# Must be after __all__ to avoid circular imports
try:
    import agentdojo.adverseral_tool.banking.type_i_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_i_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_ii_a_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_ii_b_injection_tasks  # noqa: F401
    import agentdojo.adverseral_tool.banking.type_iii_a_injection_tasks  # noqa: F401
except ImportError:
    pass
