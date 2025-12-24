import json
import logging
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path

from cohere.core.api_error import ApiError
from google.genai.errors import ServerError
from openai import BadRequestError, UnprocessableEntityError
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from typing_extensions import Self, TypedDict

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.attacks.base_attacks import BaseAttack
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask
from agentdojo.functions_runtime import Env, Function
from agentdojo.logging import Logger, TraceLogger
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.task_suite.task_suite import TaskSuite
from agentdojo.types import ChatMessage


def print_malicious_tool_info(fn: Function, goal: str | None = None) -> None:
    """Print complete malicious tool information before execution.

    Prints:
    - Function name
    - Function signature (parameters with types and defaults)
    - Full docstring
    - Parameter descriptions
    """
    print("\n" + "=" * 80)
    print("[DEBUG] MALICIOUS TOOL INFO (BEFORE EXECUTION)")
    print("=" * 80)

    # 1. Function name
    print(f"\n[Function Name]: {fn.name}")

    # 2. Full docstring (with injection vector replaced if applicable)
    docstring = fn.full_docstring or fn.description or ""
    if goal is not None and "{injection_vector}" in docstring:
        docstring = docstring.replace("{injection_vector}", str(goal))
    print(f"\n[Full Docstring]:\n{docstring}")

    # 3. Parameters info from the Pydantic model
    print(f"\n[Parameters Schema]:")
    if fn.parameters:
        try:
            schema = fn.parameters.model_json_schema()
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "unknown")
                param_desc = param_info.get("description", "No description")
                param_default = param_info.get("default", "REQUIRED" if param_name in required else "None")
                is_required = "REQUIRED" if param_name in required else "optional"
                print(f"  - {param_name}: {param_type} ({is_required})")
                print(f"      Description: {param_desc}")
                if param_default != "REQUIRED":
                    print(f"      Default: {param_default}")
        except Exception as e:
            print(f"  Error extracting parameters: {e}")

    # 4. Return type
    print(f"\n[Return Type]: {fn.return_type}")

    # 5. Dependencies (if any)
    if fn.dependencies:
        print(f"\n[Dependencies]:")
        for dep_name, dep in fn.dependencies.items():
            print(f"  - {dep_name}: {dep}")

    print("\n" + "=" * 80 + "\n")

processed_count: int = 0
utility_true_count: int = 0
security_true_count: int = 0

class SuiteResults(TypedDict):
    """The results of running a suite of tasks with a given pipeline."""

    utility_results: dict[tuple[str, str], bool]
    """The utility results for each injection task and user task couple. The
    key is a tuple of the user task ID and the injection task ID."""
    security_results: dict[tuple[str, str], bool]
    """The security results for each injection task and user task couple. The
    key is a tuple of the user task ID and the injection task ID."""
    injection_tasks_utility_results: dict[str, bool]
    """The utility results for each injection task. The key is the injection task ID."""
    successful_injection_details: list[dict]
    """Details of successful injection attacks, including injection_task_id, user_task_id, 
    malicious_tool_name, and malicious_tool_docstring"""


def aggregate_results(results: list[dict[tuple[str, str], bool]]) -> float:
    all_results = [result for results in results for result in results.values()]
    return sum(all_results) / len(all_results)


def run_task_with_injection_tasks(
    suite: TaskSuite,
    agent_pipeline: BasePipelineElement,
    user_task: BaseUserTask,
    attack: BaseAttack,
    logdir: Path | None,
    force_rerun: bool,
    injection_tasks: Sequence[str] | None = None,
    benchmark_version: str | None = None,
) -> tuple[dict[tuple[str, str], bool], dict[tuple[str, str], bool]] | None:
    """Runs the given user task with the given injection tasks (or all tasks if no injection
    task is provided) by injecting the environment by using the given attack.

    Args:
        suite: The task suite to run.
        agent_pipeline: The agent pipeline to use.
        user_task: The user task to run.
        attack: The attack to run.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.
        injection_tasks: The injection tasks to run. If None, all injection tasks in the suite will be run.

    Returns:
        A tuple of two dictionaries. The first dictionary contains the utility results for each injection
            task and user task couple. The second dictionary contains the security results for each
            injection and user task couple.

    """
    global processed_count, utility_true_count, security_true_count
    utility_results: dict[tuple[str, str], bool] = {}
    security_results: dict[tuple[str, str], bool] = {}

    if attack.is_dos_attack:
        # No need to run all injection tasks since we don't care about the injection target!
        injection_tasks_to_run = [next(iter(suite.injection_tasks.keys()))]
    else:
        injection_tasks_to_run = suite.injection_tasks

    if injection_tasks is not None and not attack.is_dos_attack:
        injection_tasks_to_run = injection_tasks
    
    tools_to_use = suite.tools_attack_mode if attack.name == "tool_attack" else suite.tools
    
    if attack.name == "tool_attack":
        # Get attack_vector_type from attack object (set by ToolAttack.__init__)
        attack_vector_type = getattr(attack, "attack_vector_type", None)
        attack_type_filter = getattr(attack, "attack_type", None)
        
        # Combined filtering: support both attack_type and attack_vector_type simultaneously
        if attack_type_filter is not None or attack_vector_type is not None:
            filtered_tasks: list[str] = []
            # Ensure we get the keys from the dict
            if isinstance(injection_tasks_to_run, dict):
                base_iterable = injection_tasks_to_run.keys()
            else:
                base_iterable = injection_tasks_to_run if injection_tasks_to_run is not None else suite.injection_tasks.keys()
            
            for tid in base_iterable:
                try:
                    inj_task = suite.get_injection_task_by_id(tid)
                    
                    # Check ATTACK_TYPE if specified
                    if attack_type_filter is not None:
                        task_attack_type = getattr(inj_task, "ATTACK_TYPE", None) or getattr(inj_task.__class__, "ATTACK_TYPE", None)
                        if task_attack_type != attack_type_filter:
                            continue  # Skip if ATTACK_TYPE doesn't match
                    
                    # Check ATTACK_VECTOR if specified
                    if attack_vector_type is not None:
                        task_attack_vector = getattr(inj_task, "ATTACK_VECTOR", None) or getattr(inj_task.__class__, "ATTACK_VECTOR", None)
                        if task_attack_vector != attack_vector_type:
                            continue  # Skip if ATTACK_VECTOR doesn't match
                    
                    # Both conditions passed (or weren't specified)
                    filtered_tasks.append(tid)
                except Exception as e:
                    logging.debug(f"Error filtering task {tid}: {e}")
                    continue
            
            if filtered_tasks:
                injection_tasks_to_run = filtered_tasks
                filter_desc = []
                if attack_vector_type:
                    filter_desc.append(f"attack_vector='{attack_vector_type}'")
                if attack_type_filter:
                    filter_desc.append(f"attack_type='{attack_type_filter}'")
                logging.info(f"Filtered to {len(filtered_tasks)} injection tasks matching {' and '.join(filter_desc)}")
            else:
                filter_desc = []
                if attack_vector_type:
                    filter_desc.append(f"attack_vector='{attack_vector_type}'")
                if attack_type_filter:
                    filter_desc.append(f"attack_type='{attack_type_filter}'")
                logging.warning(f"No injection tasks found matching {' and '.join(filter_desc)}")
        else:
            # No attack_type or attack_vector_type filter specified - fall back to shadow tasks filtering
            try:
                # Only execute shadow injection tasks (module contains 'injection_tasks_shadow'),
                # but respect any user-provided subset.
                shadow_tasks: list[str] = []
                # Ensure we get the keys from the dict
                if isinstance(injection_tasks_to_run, dict):
                    base_iterable = injection_tasks_to_run.keys()
                else:
                    base_iterable = injection_tasks_to_run if injection_tasks_to_run is not None else suite.injection_tasks.keys()
                
                for tid in base_iterable:
                    try:
                        inj_task = suite.get_injection_task_by_id(tid)
                        if "injection_tasks_shadow" in inj_task.__class__.__module__:
                            shadow_tasks.append(tid)
                    except Exception:
                        continue
                if shadow_tasks:
                    injection_tasks_to_run = shadow_tasks
            except Exception:
                ...

    injection_task_ids = list(injection_tasks_to_run)
    total_injection_tasks = len(injection_task_ids)

    for idx, injection_task_id in enumerate(injection_task_ids, 1):
        injection_task = suite.get_injection_task_by_id(injection_task_id)
        task_injections = attack.attack(user_task, injection_task)

        # Always log initial GOAL/malicious tool (first entry) before running
        goal_pre = getattr(injection_task, "GOAL", None)
        malicious_pre: tuple[str, str] | None = None
        try:
            malicious_list = [m for m in getattr(injection_task, "MALICIOUS_TOOLS", []) if isinstance(m, dict)]
            malicious_names = [malicious_list[0].get("name")] if malicious_list else []
            for fn in tools_to_use:
                if fn.name in malicious_names:
                    doc = fn.full_docstring or fn.description or ""
                    if goal_pre is not None and "{injection_vector}" in doc:
                        doc = doc.replace("{injection_vector}", str(goal_pre))
                    malicious_pre = (fn.name, doc)
                    break
        except Exception:
            malicious_pre = None
        if logdir is not None and agent_pipeline.name is not None:
            # 在这里注册恶意tool的injection vector
            try:
                task_result = load_task_results(
                    agent_pipeline.name,
                    suite.name,
                    user_task.ID,
                    attack_name=attack.name,
                    injection_task=injection_task.ID,
                    logdir=logdir,
                )
            except (ValidationError, FileNotFoundError):
                task_result = None
        else:
            task_result = None

        if task_result is not None and not force_rerun:
            logging.info(f"Skipping task '{user_task.ID}' with '{injection_task.ID}' because it was already run.")
            utility, security = task_result.utility, task_result.security
            logger = None  # No logger since we're skipping
        else:
            # a trace logger captures logs and saves them, but also passes them to the delegate logger
            with TraceLogger(
                delegate=Logger.get(),
                suite_name=suite.name,
                user_task_id=user_task.ID,
                injection_task_id=injection_task_id,
                injections=task_injections,
                attack_type=getattr(attack, "attack_type", None) or attack.name,
                pipeline_name=agent_pipeline.name,
                benchmark_version=benchmark_version,
            ) as logger:
                try:
                    result = suite.run_task_with_pipeline(
                        agent_pipeline,
                        user_task,
                        injection_task,
                        task_injections,
                        tools=tools_to_use,
                        attack_vector_type=getattr(attack, "attack_vector_type", None),
                    )
                    if result is None or result == (None, None):
                        # Not applicable; mark as such and continue to logging
                        utility, security = None, None
                        continue
                    else:
                        utility, security = result
                except BadRequestError as e:
                    if (
                        e.code == "context_length_exceeded"
                        or e.param == "max_tokens"
                        or "reduce the length of the messages." in repr(e)
                    ):
                        logger.log_error(
                            f"Skipping task '{user_task.ID}' with '{injection_task.ID}' due to context_length_exceeded: {e}"
                        )
                        utility = False
                        security = True
                    else:
                        raise e
                except ApiError as e:
                    if "internal server error" in str(e):
                        logger.log_error(
                            f"Skipping task '{user_task.ID}' with '{injection_task.ID}' because of internal server error: {e}"
                        )
                        utility = False
                        security = True
                    else:
                        raise e
                except ServerError as e:
                    logger.log_error(
                        f"Skipping task '{user_task.ID}' with '{injection_task.ID}' because of internal server error: {e}"
                    )
                    utility = False
                    security = True

                if attack.is_dos_attack:
                    security = not utility

                logger.set_contextarg("utility", utility)
                logger.set_contextarg("security", security)
                
                # Extract and record malicious tool info for successful attacks
                try:
                    # 按当前语义：security == True 表示攻击成功（防御失败）；security == False 表示攻击失败（防御成功）
                    attack_succeeded = security is True
                    goal = getattr(injection_task, "GOAL", None)
                    malicious_tool_name = None
                    malicious_tool_docstring = None
                    
                    malicious_list = [
                        m for m in getattr(injection_task, "MALICIOUS_TOOLS", []) if isinstance(m, dict)
                    ]
                    malicious_names = [malicious_list[0].get("name")] if malicious_list else []
                    for fn in tools_to_use:
                        if fn.name in malicious_names:
                            doc = fn.full_docstring or fn.description or ""
                            if goal is not None and "{injection_vector}" in doc:
                                doc = doc.replace("{injection_vector}", str(goal))
                            malicious_tool_name = fn.name
                            malicious_tool_docstring = doc
                            break
                    
                    # Record malicious tool info in logger for successful attacks
                    if attack_succeeded and malicious_tool_name:
                        logger.set_contextarg("malicious_tool_name", malicious_tool_name)
                        logger.set_contextarg("malicious_tool_docstring", malicious_tool_docstring)
                except Exception:
                    pass  # Don't crash on malicious tool extraction errors

        try:
            # 按当前语义：security == True 表示攻击成功（防御失败）；security == False 表示攻击失败（防御成功）
            attack_succeeded = security is True
            goal = getattr(injection_task, "GOAL", None)
            malicious_tool_entry = None
            try:
                malicious_list = [
                    m for m in getattr(injection_task, "MALICIOUS_TOOLS", []) if isinstance(m, dict)
                ]
                malicious_names = [malicious_list[0].get("name")] if malicious_list else []
                for fn in tools_to_use:
                    if fn.name in malicious_names:
                        doc = fn.full_docstring or fn.description or ""
                        if goal is not None and "{injection_vector}" in doc:
                            doc = doc.replace("{injection_vector}", str(goal))
                        malicious_tool_entry = (fn.name, doc)
                        break
            except Exception:
                malicious_tool_entry = getattr(injection_task, "MALICIOUS_TOOLS", None)

            processed_count += 1
            if utility is True:
                utility_true_count += 1
            if security is True:
                security_true_count += 1
            util_ratio = utility_true_count / processed_count if processed_count else 0.0
            sec_ratio = security_true_count / processed_count if processed_count else 0.0

            logging.info(
                f"malicious_tool={malicious_tool_entry!r}\n"
                f"[injection result] utility={utility}\tsecurity={security}\tattack_succeeded={attack_succeeded}\n"
                f"utility_true_count=({utility_true_count}/{processed_count}={util_ratio})\tsecurity_true_ratio=({security_true_count}/{processed_count}={sec_ratio})"
                f"({idx}/{total_injection_tasks})"
            )
        except Exception:
            # Logging should never crash benchmark execution.
            ...
        if utility is not None:
            utility_results[(user_task.ID, injection_task_id)] = utility
        if security is not None:
            security_results[(user_task.ID, injection_task_id)] = security
    return utility_results, security_results


def benchmark_suite_with_injections(
    agent_pipeline: BasePipelineElement,
    suite: TaskSuite[Env],
    attack: BaseAttack,
    logdir: Path | None,
    force_rerun: bool,
    user_tasks: Sequence[str] | None = None,
    injection_tasks: Sequence[str] | None = None,
    verbose: bool = True,
    benchmark_version: str | None = None,
    defense: str | None = None,
) -> SuiteResults:
    """Benchmark a suite with injections.

    Args:
        agent_pipeline: The agent pipeline to use.
        suite: The suite to benchmark.\
        attack: The attack to use.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.
        user_tasks: A subset of user tasks to run. If None, all user tasks are run.
        injection_tasks: A subset of injection tasks to run. If None, all injection tasks are run.
        verbose: Whether to print the results.
    """
    suite_utility_results: dict[tuple[str, str], bool] = {}
    suite_security_results: dict[tuple[str, str], bool] = {}

    if user_tasks is not None:
        user_tasks_to_run = [suite.get_user_task_by_id(user_task_id) for user_task_id in user_tasks]
    else:
        user_tasks_to_run = suite.user_tasks.values()

    if injection_tasks is not None:
        injection_tasks_to_run = {
            injection_task_id: suite.get_injection_task_by_id(injection_task_id)
            for injection_task_id in injection_tasks
        }
    else:
        injection_tasks_to_run = suite.injection_tasks

    injection_tasks_utility_results = {}
    successful_injection_details = []
    # if not attack.is_dos_attack:
    #     tools_to_use = suite.tools
    #     for injection_task_id, injection_task in injection_tasks_to_run.items():
    #         successful, _ = run_task_without_injection_tasks(
    #             suite, agent_pipeline, injection_task, logdir, force_rerun, tools=tools_to_use
    #         )
    #         injection_tasks_utility_results[injection_task_id] = successful
        
    #     # 先保证所有的injection task都可以被解决，保证攻击成功
    #     if not all(injection_tasks_utility_results.values()):
    #         warnings.warn("Not all injection tasks were solved as user tasks.")
    tools_to_use = suite.tools_attack_mode if attack.name == "tool_attack" else suite.tools

    for user_task in user_tasks_to_run:
        import os
        if os.getenv('USE_SECAGENT', "False") == "True":
            # Add progent to path for importing reset_security_policy
            from secagent.tool import reset_security_policy
            reset_security_policy()
        result = run_task_with_injection_tasks(
            suite,
            agent_pipeline,
            user_task,
            attack,
            logdir,
            force_rerun,
            injection_tasks,
            benchmark_version,
        )
        if result is None:
            continue
        utility, security = result
        suite_utility_results.update(utility)
        suite_security_results.update(security)

    # Collect successful injection details from saved logs
    if logdir is not None and agent_pipeline.name is not None:
        for (user_task_id, injection_task_id), security_result in suite_security_results.items():
            if security_result is True:  # Attack succeeded (defense failed)
                try:
                    task_result = load_task_results(
                        agent_pipeline.name,
                        suite.name,
                        user_task_id,
                        attack_name=getattr(attack, "attack_type", None) or attack.name,
                        injection_task=injection_task_id,
                        logdir=logdir,
                    )
                    malicious_tool_name = getattr(task_result, "malicious_tool_name", None)
                    malicious_tool_docstring = getattr(task_result, "malicious_tool_docstring", None)
                    if malicious_tool_name:
                        successful_injection_details.append({
                            "injection_task_id": injection_task_id,
                            "user_task_id": user_task_id,
                            "malicious_tool_name": malicious_tool_name,
                            "malicious_tool_docstring": malicious_tool_docstring,
                        })
                except Exception as e:
                    logging.debug(f"Failed to load malicious tool info for {user_task_id}/{injection_task_id}: {e}")

    # Log summary of successful injections
    if successful_injection_details:
        logging.info(f"\n{'='*80}")
        logging.info(f"SUCCESSFUL INJECTION ATTACKS SUMMARY ({len(successful_injection_details)} total):")
        logging.info(f"{'='*80}")
        for detail in successful_injection_details:
            logging.info(
                f"  - InjectionTask: {detail['injection_task_id']}\n"
                f"    UserTask: {detail['user_task_id']}\n"
                f"    MaliciousTool: {detail['malicious_tool_name']}\n"
            )
        logging.info(f"{'='*80}\n")

    return SuiteResults(
        utility_results=suite_utility_results,
        security_results=suite_security_results,
        injection_tasks_utility_results=injection_tasks_utility_results,
        successful_injection_details=successful_injection_details,
    )


def run_task_without_injection_tasks(
    suite: TaskSuite,
    agent_pipeline: BasePipelineElement,
    task: BaseUserTask | BaseInjectionTask,
    logdir: Path | None,
    force_rerun: bool,
    benchmark_version: str | None = None,
    tools: Sequence[Function] | None = None,
    ) -> tuple[bool, bool] | None:
    """Run a task without injections. Useful to benchmark the utility of a pipeline.

    Args:
        suite: The suite to use to run the benchmark.
        agent_pipeline: The agent pipeline to benchmark.
        task: The task to run.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task
        tools: Optional set of tools to expose to the runtime. Defaults to the suite tools.

    Returns:
        A tuple with the utility and security of the task. The security is always True.
    """
    if logdir is not None and agent_pipeline.name is not None:
        try:
            task_result = load_task_results(
                agent_pipeline.name,
                suite.name,
                task.ID,
                attack_name="none",
                injection_task="none",
                logdir=logdir,
            )
        except (ValidationError, FileNotFoundError):
            task_result = None
    else:
        task_result = None

    if task_result is not None and not force_rerun:
        logging.info(f"Skipping task '{task.ID}' with no injections because it was already run.")
        return task_result.utility, task_result.security

    with TraceLogger(
        delegate=Logger.get(),
        suite_name=suite.name,
        user_task_id=task.ID,
        injection_task_id=None,
        injections={},
        attack_type="none",
        pipeline_name=agent_pipeline.name,
        benchmark_version=benchmark_version,
    ) as logger:
        utility: bool = False
        security: bool = True
        try:
            result = suite.run_task_with_pipeline(
                agent_pipeline,
                task,
                injection_task=None,
                injections={},
                tools=tools,
                attack_vector_type=None,
            )
            if result is None or result == (None, None):
                return None
            utility_val, security_val = result
            utility = bool(utility_val)
            security = bool(security_val)
        except BadRequestError as e:
            if (
                e.code == "context_length_exceeded"
                or e.param == "max_tokens"
                or "reduce the length of the messages." in repr(e)
            ):
                logger.log_error(f"Skipping task {task.ID} due to context_length_exceeded: {e}")
                utility = False
                security = True
            else:
                raise e
        except UnprocessableEntityError as e:
            if "max_new_tokens" in str(e):
                logger.log_error(f"Skipping task {task.ID} due to context_length_exceeded: {e}")
                utility = False
                security = True
            else:
                raise e
        except ApiError as e:
            if "internal server error" in str(e):
                logger.log_error(f"Skipping task {task.ID} because of internal server error: {e}")
                utility = False
                security = True
            else:
                raise e
        except ServerError as e:
            logger.log_error(f"Skipping task {task.ID} because of internal server error: {e}")
            utility = False
            security = True
        logger.set_contextarg("utility", utility)
        logger.set_contextarg("security", security)

    return utility, security


def benchmark_suite_without_injections(
    agent_pipeline: BasePipelineElement,
    suite: TaskSuite,
    logdir: Path | None,
    force_rerun: bool,
    user_tasks: Sequence[str] | None = None,
    benchmark_version: str | None = None,
) -> SuiteResults:
    """Benchmark a suite without injections.

    Args:
        agent_pipeline: The agent pipeline to use.
        suite: The suite to benchmark.\
        attack: The attack to use.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.
        user_tasks: A subset of user tasks to run. If None, all user tasks are run.
    """

    suite_utility_results: dict[tuple[str, str], bool] = {}
    suite_security_results: dict[tuple[str, str], bool] = {}

    if user_tasks is not None:
        user_tasks_to_run = [suite.get_user_task_by_id(user_task_id) for user_task_id in user_tasks]
    else:
        user_tasks_to_run = suite.user_tasks.values()

    for user_task in user_tasks_to_run:
        result = run_task_without_injection_tasks(
            suite, agent_pipeline, user_task, logdir, force_rerun, benchmark_version
        )
        if result is None:
            continue
        utility, security = result
        suite_utility_results[(user_task.ID, "")] = utility
        suite_security_results[(user_task.ID, "")] = security

    return SuiteResults(
        utility_results=suite_utility_results,
        security_results=suite_security_results,
        injection_tasks_utility_results={},
        successful_injection_details=[],
    )


class TaskResults(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    suite_name: str
    pipeline_name: str
    user_task_id: str
    injection_task_id: str | None
    attack_type: str | None
    injections: dict[str, str]
    messages: list[ChatMessage]
    error: str | None
    utility: bool
    security: bool
    duration: float
    malicious_tool_name: str | None = None
    malicious_tool_docstring: str | None = None

    @model_validator(mode="after")
    def check_messages(self) -> Self:
        if len(self.messages) < 2 and "claude-3-opus" not in self.pipeline_name:
            raise ValueError("TaskResults must have at least two messages.")
        return self


def convert_old_messages_format(messages: list[dict]) -> list[dict]:
    """Convert messages from old format (string content) to new format (content blocks).

    The new format was introduced with commit d67f9d141305e599ca2056f430f703d4021fd82a.
    """
    converted_messages = []
    for message in messages:
        message_copy = message.copy()
        if message_copy["role"] == "assistant" and message_copy["content"] is not None:
            message_copy["content"] = [{"type": "text", "content": message_copy["content"]}]
        elif message_copy["role"] in ["user", "system"]:
            message_copy["content"] = [{"type": "text", "content": message_copy["content"]}]
        elif message_copy["role"] == "tool":
            message_copy["content"] = [{"type": "text", "content": message_copy["content"]}]
        converted_messages.append(message_copy)
    return converted_messages


def load_task_results(
    pipeline_name: str,
    suite_name: str,
    user_task: str,
    attack_name: str,
    injection_task: str,
    logdir: Path,
) -> TaskResults:
    path = logdir / pipeline_name / suite_name / user_task / attack_name / f"{injection_task}.json"
    with path.open() as f:
        res_dict = json.load(f)

    # Check if the result is in the old format (without content blocks)
    # Old format didn't have agentdojo_package_version field
    if "agentdojo_package_version" not in res_dict:
        # Convert messages to the new format with content blocks
        res_dict["messages"] = convert_old_messages_format(res_dict["messages"])

    return TaskResults(**res_dict)


def load_suite_results(
    suite_name: str,
    pipeline_name: str,
    attack_name: str,
    logdir=Path("../runs"),
    benchmark_version: str = "v1.2.2",
) -> tuple[dict[tuple[str, str], TaskResults], dict[tuple[str, str], TaskResults]]:
    suite = get_suite(benchmark_version, suite_name)
    results_without_injections = {}
    results_with_injections = {}

    for user_task_id in suite.user_tasks.keys():
        results_without_injections[(user_task_id, None)] = load_task_results(
            pipeline_name, suite_name, user_task_id, "none", "none", logdir
        )
        if "dos" in attack_name:
            injection_task_id = next(iter(suite.injection_tasks.keys()))
            results_with_injections[(user_task_id, injection_task_id)] = load_task_results(
                pipeline_name, suite_name, user_task_id, attack_name, injection_task_id, logdir
            )
        elif attack_name != "none":
            for injection_task_id in suite.injection_tasks.keys():
                results_with_injections[(user_task_id, injection_task_id)] = load_task_results(
                    pipeline_name, suite_name, user_task_id, attack_name, injection_task_id, logdir
                )
    return results_without_injections, results_with_injections
