"""
Progent Pipeline - 即插即用的安全防御 Pipeline

这个模块提供了一个完整的 Progent 防御 pipeline，可以直接传入 AgentDojo 的
benchmark_suite_with_injections 函数，无需修改 AgentDojo 核心代码。

核心设计：
1. 继承 AgentDojo 的标准 pipeline elements
2. 自动包装工具调用
3. 支持策略自动生成和动态更新
4. 提供配置化的安全策略

使用示例:
    ```python
    from secagent.progent_pipeline import create_progent_pipeline
    from agentdojo.benchmark import benchmark_suite_with_injections
    
    # 创建 Progent pipeline
    pipeline = create_progent_pipeline(
        llm="gpt-4o",
        suite_name="banking",
        auto_generate_policy=True,
        enable_dynamic_update=True
    )
    
    # 直接传入 benchmark
    results = benchmark_suite_with_injections(
        agent_pipeline=pipeline,
        suite=suite,
        attack=attack,
        logdir="./runs"
    )
    ```
"""

import os
from typing import List, Dict, Optional, Callable, TYPE_CHECKING
from pathlib import Path
import openai
import time

# 使用 TYPE_CHECKING 来避免运行时导入
if TYPE_CHECKING:
    from agentdojo.agent_pipeline import AgentPipeline
    from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
    from agentdojo.agent_pipeline.basic_elements import SystemMessage
    from agentdojo.functions_runtime import FunctionsRuntime, EmptyEnv, Env
    from agentdojo.types import ChatMessage

# Secagent imports
from .tool import (
    generate_security_policy,
    generate_update_security_policy,
    reset_security_policy,
    update_available_tools,
    update_always_allowed_tools,
    update_always_blocked_tools,
    apply_secure_tool_wrapper,
    get_security_policy
)

# 日志格式化导入
from .log_formatter import (
    log_info, log_success, log_warning, log_error, log_debug,
    log_policy_generation, log_policy_details, log_policy_update,
    log_tool_call, log_task_start, log_task_end
)


class ProgentInitQuery:
    """
    Progent 初始化元素 - 负责：
    1. 添加用户查询到消息列表
    2. 根据用户查询自动生成安全策略（如果启用）
    """
    
    def __init__(self, auto_generate: bool = True):
        self.auto_generate = auto_generate
        
    def query(
        self,
        query: str,
        runtime,  # FunctionsRuntime
        env=None,  # Env
        messages: List = [],
        extra_args: dict = {},
    ) -> tuple:
        from agentdojo.types import ChatUserMessage
        from agentdojo.functions_runtime import EmptyEnv
        
        if env is None:
            env = EmptyEnv()
        
        # 添加用户查询
        query_message = ChatUserMessage(role="user", content=query)
        
        # 自动生成安全策略
        if self.auto_generate:
            try:
                start_time = time.time()
                generate_security_policy(query)
                elapsed = time.time() - start_time
                log_policy_generation(query, success=True)
                log_debug(f"策略生成耗时: {elapsed:.2f}秒")

                # 显示生成的策略详情
                policy = get_security_policy()
                if policy:
                    log_policy_details(policy)
            except Exception as e:
                log_policy_generation(query, success=False)
                log_error(f"策略生成异常: {str(e)}")

        messages = [*messages, query_message]
        return query, runtime, env, messages, extra_args


class ProgentToolsExecutor:
    """
    Progent 工具执行器 - 负责：
    1. 执行工具调用（继承自标准 ToolsExecutor）
    2. 根据执行结果动态更新安全策略（如果启用）
    """
    
    def __init__(
        self,
        base_executor,  # BasePipelineElement
        enable_dynamic_update: bool = True,
        ignore_update_error: bool = True
    ):
        self.base_executor = base_executor
        self.enable_dynamic_update = enable_dynamic_update
        self.ignore_update_error = ignore_update_error
        
    def query(
        self,
        query: str,
        runtime,  # FunctionsRuntime
        env=None,  # Env
        messages: List = [],
        extra_args: dict = {},
    ) -> tuple:
        from agentdojo.functions_runtime import EmptyEnv
        
        if env is None:
            env = EmptyEnv()
            
        # 执行工具调用（使用原始 executor）
        result = self.base_executor.query(query, runtime, env, messages, extra_args)
        query, runtime, env, messages, extra_args = result
        
        # 动态更新策略
        if self.enable_dynamic_update and len(messages) > 0:
            last_message = messages[-1]
            if last_message.get("role") == "tool":
                # 提取工具调用和结果
                try:
                    # 收集最近的工具调用
                    intermediate_calls = []
                    intermediate_results = []
                    
                    # 从倒数第二条消息获取工具调用
                    if len(messages) >= 2 and messages[-2].get("tool_calls"):
                        for tool_call in messages[-2]["tool_calls"]:
                            intermediate_calls.append({
                                "name": tool_call.function,
                                "args": tool_call.args
                            })
                    
                    # 从最后一条消息获取结果
                    if isinstance(last_message.get("content"), list):
                        intermediate_results = [
                            item.get("content", "") for item in last_message["content"]
                        ]
                    elif "content" in last_message:
                        intermediate_results = [last_message["content"]]
                    
                    # 更新策略
                    if intermediate_calls:
                        log_debug(f"准备更新策略，基于 {len(intermediate_calls)} 个工具调用")
                        start_time = time.time()
                        generate_update_security_policy(
                            intermediate_calls,
                            str(intermediate_results),
                            manual_check=False
                        )
                        elapsed = time.time() - start_time
                        log_success(f"策略已根据执行结果更新 (耗时: {elapsed:.2f}秒)")

                        # 显示更新后的策略
                        updated_policy = get_security_policy()
                        if updated_policy:
                            log_policy_details(updated_policy)

                except Exception as e:
                    if not self.ignore_update_error:
                        raise
                    log_warning(f"策略更新失败（已忽略）: {str(e)}")
        
        return query, runtime, env, messages, extra_args


class ProgentPipeline:
    """
    Progent 完整 Pipeline - 封装了所有防御机制
    
    特性：
    - 自动工具包装（secure_tool_wrapper）
    - 策略自动生成
    - 动态策略更新
    - 任务间策略隔离
    """
    
    def __init__(
        self,
        *pipeline_elements,
        name: str = "Progent",
        auto_generate_policy: bool = True,
        enable_dynamic_update: bool = True,
        always_allowed_tools: List[str] = None,
        always_blocked_tools: List[str] = None,
        allow_all_no_arg_tools: bool = False,
    ):
        # 在运行时导入 AgentPipeline（使用 importlib 避免 vertexai）
        import importlib
        ap_module = importlib.import_module("agentdojo.agent_pipeline.agent_pipeline")

        # 使用组合而不是继承
        self._base_pipeline = ap_module.AgentPipeline(pipeline_elements)
        self._base_pipeline.name = name
        self.name = name
        self.pipeline_elements = list(pipeline_elements)
        self.auto_generate_policy = auto_generate_policy
        self.enable_dynamic_update = enable_dynamic_update
        self.always_allowed_tools = always_allowed_tools or []
        self.always_blocked_tools = always_blocked_tools or []
        self.allow_all_no_arg_tools = allow_all_no_arg_tools
        
    def query(
        self,
        query: str,
        runtime,  # FunctionsRuntime
        env=None,  # Env
        messages: List = [],
        extra_args: dict = {},
    ) -> tuple:
        from agentdojo.functions_runtime import EmptyEnv
        
        if env is None:
            env = EmptyEnv()
        
        """
        覆盖 query 方法，在每次查询前重置策略
        """
        # 重置策略（确保任务间隔离）
        reset_security_policy()
        log_info("新任务开始，策略已重置")

        # 更新工具列表
        if runtime.functions:
            tools_info = []
            for func_name, func in runtime.functions.items():
                # 提取工具信息 - 使用 Pydantic model_json_schema 以支持 JSON 序列化
                if hasattr(func, 'parameters'):
                    # AgentDojo Function 对象
                    # Rebuild the model to ensure all type references are resolved
                    # We need to provide the namespace containing all types used in the model
                    try:
                        # Import all types that might be used in the workspace suite
                        from agentdojo.default_suites.v1.tools.types import (
                            SharingPermission, CloudDriveFileID, CloudDriveFile,
                            EvenStatus, CalendarEventID, CalendarEvent,
                            EmailStatus, EmailContact, EmailID, Email
                        )
                        types_namespace = {
                            'SharingPermission': SharingPermission,
                            'CloudDriveFileID': CloudDriveFileID,
                            'CloudDriveFile': CloudDriveFile,
                            'EvenStatus': EvenStatus,
                            'CalendarEventID': CalendarEventID,
                            'CalendarEvent': CalendarEvent,
                            'EmailStatus': EmailStatus,
                            'EmailContact': EmailContact,
                            'EmailID': EmailID,
                            'Email': Email,
                        }
                        func.parameters.model_rebuild(_types_namespace=types_namespace, raise_errors=False)
                        log_debug(f"Successfully rebuilt model for {func_name}")
                    except Exception as e:
                        log_debug(f"Could not rebuild model for {func_name}: {e}")
                        # Continue anyway - the model might work without rebuild

                    args_schema = func.parameters.model_json_schema()
                    args = args_schema.get("properties", {})
                    description = func.description if hasattr(func, 'description') else ""
                else:
                    # 普通函数（fallback）
                    args = {}
                    description = getattr(func, "__doc__", "") or ""

                tools_info.append({
                    "name": func_name,
                    "description": description,
                    "args": args
                })
            update_available_tools(tools_info)
            log_debug(f"可用工具已更新: {len(tools_info)} 个工具")

        # 设置 always_allowed/blocked 工具
        if self.always_allowed_tools:
            update_always_allowed_tools(
                self.always_allowed_tools,
                self.allow_all_no_arg_tools
            )
            log_debug(f"始终允许的工具: {len(self.always_allowed_tools)} 个")
        if self.always_blocked_tools:
            update_always_blocked_tools(self.always_blocked_tools)
            log_debug(f"始终阻止的工具: {len(self.always_blocked_tools)} 个")
        
        # 调用基础 pipeline 的 query
        return self._base_pipeline.query(query, runtime, env, messages, extra_args)


def wrap_tools_with_progent(runtime):  # FunctionsRuntime
    """
    包装 FunctionsRuntime 中的所有工具

    Args:
        runtime: 原始的 FunctionsRuntime

    Returns:
        包装后的 FunctionsRuntime（所有工具都应用了 secure_tool_wrapper）
    """
    from agentdojo.functions_runtime import FunctionsRuntime

    wrapped_functions = {}

    for func_name, func in runtime.functions.items():
        # 应用 secure_tool_wrapper
        wrapped_func = apply_secure_tool_wrapper(func)
        wrapped_functions[func_name] = wrapped_func

    # 创建新的 runtime 并使用 update_functions 方法设置包装后的函数
    wrapped_runtime = FunctionsRuntime(functions=list(wrapped_functions.values()))

    return wrapped_runtime


def create_progent_pipeline(
    llm: str,
    suite_name: str = None,
    system_message: str = None,
    auto_generate_policy: bool = True,
    enable_dynamic_update: bool = True,
    always_allowed_tools: List[str] = None,
    always_blocked_tools: List[str] = None,
    allow_all_no_arg_tools: bool = False,
    policy_model: str = None,
    ignore_update_error: bool = True,
    **llm_kwargs
):  # -> ProgentPipeline
    """
    创建 Progent Pipeline（工厂函数）
    
    Args:
        llm: LLM 模型名称（例如 "gpt-4o", "qwen-turbo"）
        suite_name: 测试套件名称（banking/slack/travel/workspace）
        system_message: 自定义系统消息（如果不提供，将使用 AgentDojo 默认）
        auto_generate_policy: 是否自动生成安全策略
        enable_dynamic_update: 是否启用动态策略更新
        always_allowed_tools: 总是允许的工具列表
        always_blocked_tools: 总是阻止的工具列表
        allow_all_no_arg_tools: 是否允许所有无参数工具
        policy_model: 策略生成使用的 LLM（默认使用 SECAGENT_POLICY_MODEL 环境变量）
        ignore_update_error: 是否忽略策略更新错误
        **llm_kwargs: 传递给 LLM 的额外参数
        
    Returns:
        配置好的 ProgentPipeline 实例
    """
    # 设置策略模型
    if policy_model:
        os.environ["SECAGENT_POLICY_MODEL"] = policy_model
    
    # 设置环境变量（用于 secagent 内部）
    os.environ["SECAGENT_GENERATE"] = str(auto_generate_policy)
    os.environ["SECAGENT_UPDATE"] = str(enable_dynamic_update)
    os.environ["SECAGENT_IGNORE_UPDATE_ERROR"] = str(ignore_update_error)
    if suite_name:
        os.environ["SECAGENT_SUITE"] = suite_name
    
    # 加载套件默认配置
    if suite_name and not always_allowed_tools:
        always_allowed_tools = get_suite_always_allowed_tools(suite_name)
    
    # 构建 pipeline elements
    pipeline_elements = []

    # 1. System Message
    if system_message:
        from agentdojo.agent_pipeline.basic_elements import SystemMessage
        pipeline_elements.append(SystemMessage(system_message))

    # 2. Progent Init Query
    pipeline_elements.append(ProgentInitQuery(auto_generate=auto_generate_policy))

    # 3. LLM Call (根据模型选择)
    llm_call = create_llm_call(llm, **llm_kwargs)
    pipeline_elements.append(llm_call)

    # 4. Tools Executor (包装为 Progent 版本)
    from agentdojo.agent_pipeline.tool_execution import ToolsExecutor, ToolsExecutionLoop
    base_executor = ToolsExecutor()
    progent_executor = ProgentToolsExecutor(
        base_executor=base_executor,
        enable_dynamic_update=enable_dynamic_update,
        ignore_update_error=ignore_update_error
    )

    # 5. Tools Execution Loop (关键：确保工具执行后继续调用 LLM)
    tools_loop = ToolsExecutionLoop([progent_executor, llm_call])
    pipeline_elements.append(tools_loop)

    # 6. 创建 Progent Pipeline
    pipeline = ProgentPipeline(
        *pipeline_elements,
        name=f"Progent-{llm}",
        auto_generate_policy=auto_generate_policy,
        enable_dynamic_update=enable_dynamic_update,
        always_allowed_tools=always_allowed_tools,
        always_blocked_tools=always_blocked_tools,
        allow_all_no_arg_tools=allow_all_no_arg_tools
    )

    log_success(f"Pipeline 创建完成: {pipeline.name}")
    log_info(f"  自动生成策略: {'启用' if auto_generate_policy else '禁用'}")
    log_info(f"  动态策略更新: {'启用' if enable_dynamic_update else '禁用'}")
    if always_allowed_tools:
        log_info(f"  始终允许的工具: {len(always_allowed_tools)} 个")

    return pipeline


def create_llm_call(llm: str, **kwargs):  # -> BasePipelineElement
    """
    根据 LLM 名称创建对应的 LLM Call element
    
    Args:
        llm: LLM 模型名称
        **kwargs: 额外参数
        
    Returns:
        LLM Call element
    """
    import importlib
    # OpenAI 系列（使用 importlib 直接导入模块，避免触发 __init__.py）
    if llm.startswith("gpt-") or llm.startswith("o1-") or llm.startswith("o3-"):
        openai_llm = importlib.import_module("agentdojo.agent_pipeline.llms.openai_llm")
        return openai_llm.OpenAILLM(model=llm, **kwargs)
    
    # Anthropic Claude
    elif llm.startswith("claude-"):
        anthropic_llm = importlib.import_module("agentdojo.agent_pipeline.llms.anthropic_llm")
        return anthropic_llm.AnthropicLLM(model=llm, **kwargs)
    
    # Qwen 系列（通过 OpenAI 兼容接口）
    elif llm.startswith("qwen"):
        client = openai.OpenAI()
        openai_llm = importlib.import_module("agentdojo.agent_pipeline.llms.openai_llm")
        return openai_llm.OpenAILLM(client, model=llm, **kwargs)
    
    # Google Gemini
    elif llm.startswith("gemini-"):
        google_llm = importlib.import_module("agentdojo.agent_pipeline.llms.google_llm")
        return google_llm.GoogleLLM(model=llm, **kwargs)
    
    # 默认使用 OpenAI
    else:
        openai_llm = importlib.import_module("agentdojo.agent_pipeline.llms.openai_llm")
        client = openai.OpenAI()
        return openai_llm.OpenAILLM(client, model=llm, **kwargs)


def get_suite_always_allowed_tools(suite_name: str) -> List[str]:
    """
    获取每个 suite 的默认 always_allowed_tools
    
    Args:
        suite_name: 套件名称
        
    Returns:
        工具名称列表
    """
    suite_configs = {
        "banking": [
            "get_most_recent_transactions",
            # 所有无参数工具会自动添加（通过 allow_all_no_arg_tools=True）
        ],
        "slack": [
            "get_channels",
            "read_channel_messages",
            "read_inbox",
            "get_users_in_channel",
        ],
        "travel": [
            "get_user_information",
            "get_all_hotels_in_city",
            "get_all_car_rental_companies_in_city",
            "get_all_restaurants_in_city",
            "get_flight_information",
            "get_car_price",
            "get_rating_reviews_for_hotels",
            "get_rating_reviews_for_restaurants",
            "get_hotels_prices",
        ],
        "workspace": [
            "get_all_emails",
            "read_email",
            "get_all_calendar_events",
            "get_calendar_event",
            "search_files",
        ],
    }
    
    return suite_configs.get(suite_name, [])


# 为了向后兼容，提供环境变量控制的入口
def should_enable_progent() -> bool:
    """检查是否应该启用 Progent（基于环境变量）"""
    return os.getenv("ENABLE_PROGENT", "False").lower() == "true"


def get_progent_config() -> Dict:
    """从环境变量读取 Progent 配置"""
    return {
        "auto_generate": os.getenv("SECAGENT_GENERATE", "True").lower() == "true",
        "enable_update": os.getenv("SECAGENT_UPDATE", "True").lower() == "true",
        "suite_name": os.getenv("SECAGENT_SUITE"),
        "policy_model": os.getenv("SECAGENT_POLICY_MODEL", "gpt-4o-2024-08-06"),
        "ignore_update_error": os.getenv("SECAGENT_IGNORE_UPDATE_ERROR", "True").lower() == "true",
    }
