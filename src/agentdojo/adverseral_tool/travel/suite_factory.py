"""Helpers to build adversarial Travel task suites and runtimes."""

from importlib import import_module, resources
from typing import Iterable

from pathlib import Path
from agentdojo.default_suites.v1.travel.task_suite import TravelEnvironment
from agentdojo.default_suites.v1.travel.task_suite import task_suite as benign_travel_suite
from agentdojo.functions_runtime import Function, make_function
from agentdojo.task_suite.load_suites import register_suite
from agentdojo.task_suite.task_suite import TaskSuite

from . import injection_tasks

# Mapping of type name to (module path, function names)
_TYPE_TOOLS: dict[str, tuple[str, list[str]]] = {
    "type_i_a": (
        "agentdojo.adverseral_tool.travel.type_i_a",
        ["reserve_hotel", "get_flight_information", "get_all_car_rental_companies_in_city"],
    ),
    "type_i_b": (
        "agentdojo.adverseral_tool.travel.type_i_b",
        ["reserve_hotel", "get_flight_information", "get_all_car_rental_companies_in_city"],
    ),
    "type_ii_a": (
        "agentdojo.adverseral_tool.travel.type_ii_a",
        [
            "booking_com_verified_search",
            "yelp_elite_dining_concierge",
            "hertz_priority_fleet_finder",
            "expedia_global_trip_optimizer",
        ],
    ),
    "type_ii_b": (
        "agentdojo.adverseral_tool.travel.type_ii_b",
        [
            "reserve_hotel",
            "reserve_restaurant",
            "reserve_car_rental",
            "get_all_hotels_in_city",
            "get_flight_information",
        ],
    ),
    "type_iii_a": (
        "agentdojo.adverseral_tool.travel.type_iii_a",
        [
            "fetch_verified_review_data",
            "get_all_hotels_in_city",
            "get_all_restaurants_in_city",
            "get_all_car_rental_companies_in_city",
            "fetch_verified_hotel_reviews",
            "fetch_verified_restaurant_reviews",
        ],
    ),
    "type_iii_b": (
        "agentdojo.adverseral_tool.travel.type_iii_b",
        [
            "audit_spending_limit",
            "validate_contact_format",
            "check_availability_realtime",
        ],
    ),
}

_INJECTION_TASKS = [
]
try:
    from agentdojo.adverseral_tool.travel import injection_tasks_shadow

    _INJECTION_TASKS += [
        injection_tasks_shadow.InjectionTask100,
        injection_tasks_shadow.InjectionTask101,
        injection_tasks_shadow.InjectionTask102,
        injection_tasks_shadow.InjectionTask103,
        injection_tasks_shadow.InjectionTask104,
        injection_tasks_shadow.InjectionTask105,
    ]
except Exception:
    ...

# Import type_i_a_injection_tasks to register InjectionTask1000-1019
try:
    from agentdojo.adverseral_tool.travel import type_i_a_injection_tasks
    # 这些类已经通过 @task_suite.register_injection_task 装饰器自动注册
    # 只需要导入模块即可
except Exception as e:
    import warnings
    warnings.warn(f"Failed to import type_i_a_injection_tasks: {e}")


def load_functions(type_name: str) -> list[Function]:
    """Build Function objects for a given adversarial type."""
    if type_name not in _TYPE_TOOLS:
        raise ValueError(f"Unknown adversarial type '{type_name}'. Valid: {sorted(_TYPE_TOOLS)}")
    module_path, fn_names = _TYPE_TOOLS[type_name]
    module = import_module(module_path)
    functions: list[Function] = []
    for fn_name in fn_names:
        fn = getattr(module, fn_name)
        functions.append(make_function(fn))
    return functions


def _travel_data_path() -> Path:
    pkg = resources.files("agentdojo") / "data" / "suites" / "travel"
    with resources.as_file(pkg) as p:
        return Path(p)


def build_adversarial_travel_suite(type_name: str, benchmark_version=(1, 0, 0)) -> TaskSuite:
    """Create a TaskSuite wired with the adversarial tools and injection tasks."""
    tools = load_functions(type_name)
    suite = TaskSuite[TravelEnvironment](
        f"travel_adversarial_{type_name}",
        TravelEnvironment,
        tools,
        data_path=_travel_data_path(),
        benchmark_version=benchmark_version,
    )

    for inj_cls in _INJECTION_TASKS:
        suite.register_new_injection_task(benchmark_version, inj_cls)
    return suite


def available_types() -> Iterable[str]:
    return _TYPE_TOOLS.keys()


_ADV_VERSION = "adversarial"


def register_all_adversarial_travel_suites(version: str = _ADV_VERSION):
    """Register adversarial travel suites so they can be loaded by benchmark CLI."""
    # Also register the benign travel suite under this version to allow --suite travel.
    register_suite(benign_travel_suite.get_new_version((1, 0, 0)), version)
    for type_name in available_types():
        suite = build_adversarial_travel_suite(type_name)
        register_suite(suite, version)


# Auto-register on import to make them visible when module is loaded via --module-to-load
register_all_adversarial_travel_suites()
