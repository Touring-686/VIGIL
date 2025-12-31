import json
from collections.abc import Sequence
from typing import overload

import openai
from openai._types import NOT_GIVEN
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionReasoningEffort,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import FunctionDefinition
from pydantic import BaseModel
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_random_exponential

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, Function, FunctionCall, FunctionsRuntime
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    ChatSystemMessage,
    ChatToolResultMessage,
    ChatUserMessage,
    MessageContentBlock,
    get_text_content_as_str,
    text_content_block_from_string,
)


def _tool_call_to_openai(tool_call: FunctionCall) -> ChatCompletionMessageToolCallParam:
    if tool_call.id is None:
        raise ValueError("`tool_call.id` is required for OpenAI")
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        type="function",
        function={
            "name": tool_call.function,
            "arguments": json.dumps(tool_call.args),
        },
    )


_REASONING_MODELS = {"o1", "o3"}


def _is_reasoning_model(model_name: str) -> bool:
    return any(model in model_name for model in _REASONING_MODELS)


@overload
def _content_blocks_to_openai_content_blocks(
    message: ChatUserMessage | ChatSystemMessage,
) -> list[ChatCompletionContentPartTextParam]: ...


@overload
def _content_blocks_to_openai_content_blocks(
    message: ChatAssistantMessage | ChatToolResultMessage,
) -> list[ChatCompletionContentPartTextParam] | None: ...


def _content_blocks_to_openai_content_blocks(
    message: ChatUserMessage | ChatAssistantMessage | ChatSystemMessage | ChatToolResultMessage,
) -> list[ChatCompletionContentPartTextParam] | None:
    if message["content"] is None:
        return None

    # Handle case where content is a string (from some defense mechanisms like pi_detector)
    if isinstance(message["content"], str):
        return [ChatCompletionContentPartTextParam(type="text", text=message["content"])]

    # Handle normal case where content is a list of content blocks
    return [ChatCompletionContentPartTextParam(type="text", text=el["content"] or "") for el in message["content"]]


def _message_to_openai(message: ChatMessage, model_name: str) -> ChatCompletionMessageParam:
    match message["role"]:
        case "system":
            # Use "system" role for compatibility with most models
            # "developer" role is only supported in o1-series models
            return ChatCompletionSystemMessageParam(
                role="system", content=_content_blocks_to_openai_content_blocks(message)
            )
        case "user":
            return ChatCompletionUserMessageParam(
                role="user", content=_content_blocks_to_openai_content_blocks(message)
            )
        case "assistant":
            if message["tool_calls"] is not None and len(message["tool_calls"]) > 0:
                tool_calls = [_tool_call_to_openai(tool_call) for tool_call in message["tool_calls"]]
                return ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=_content_blocks_to_openai_content_blocks(message),
                    tool_calls=tool_calls,
                )
            return ChatCompletionAssistantMessageParam(
                role="assistant",
                content=_content_blocks_to_openai_content_blocks(message),
            )
        case "tool":
            if message["tool_call_id"] is None:
                raise ValueError("`tool_call_id` should be specified for OpenAI.")
            return ChatCompletionToolMessageParam(
                content=message["error"] or _content_blocks_to_openai_content_blocks(message),
                tool_call_id=message["tool_call_id"],
                role="tool",
                name=message["tool_call"].function,  # type: ignore -- this is actually used, and is important!
            )
        case _:
            raise ValueError(f"Invalid message type: {message}")


def _openai_to_tool_call(tool_call: ChatCompletionMessageToolCall) -> FunctionCall:
    # Handle empty or missing arguments
    args_str = tool_call.function.arguments
    if not args_str or args_str.strip() == "":
        args = {}
    else:
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            # If parsing fails, use empty dict
            args = {}

    return FunctionCall(
        function=tool_call.function.name,
        args=args,
        id=tool_call.id,
    )


def _assistant_message_to_content(message: ChatCompletionMessage) -> list[MessageContentBlock] | None:
    if message.content is None:
        return None
    return [text_content_block_from_string(message.content)]


def _openai_to_assistant_message(message: ChatCompletionMessage) -> ChatAssistantMessage:
    if message.tool_calls is not None:
        tool_calls = [_openai_to_tool_call(tool_call) for tool_call in message.tool_calls]
    else:
        tool_calls = None
    return ChatAssistantMessage(role="assistant", content=_assistant_message_to_content(message), tool_calls=tool_calls)


def _resolve_schema_refs(cls: type[BaseModel]) -> dict:
    """Resolve $ref and $defs in JSON schema for compatibility with Google API.

    Google's API (when accessed via OpenAI-compatible interface) doesn't support
    $defs and $ref in JSON schemas. This function resolves all references inline.

    Example:
        Input: {'$defs': {'Enum': {'type': 'string'}}, 'properties': {'x': {'$ref': '#/$defs/Enum'}}}
        Output: {'properties': {'x': {'type': 'string'}}}
    """
    schema = cls.model_json_schema()
    if "$defs" not in schema:
        return schema

    defs = schema.pop("$defs")

    def _resolve(node):
        """Recursively resolve all $ref in a schema node."""
        if not isinstance(node, dict):
            return

        # Remove default values (Google API doesn't like them)
        if "default" in node:
            del node["default"]

        # If this node is a $ref, replace it with the referenced definition
        if "$ref" in node:
            ref_key = node.pop("$ref").split("/")[-1]
            if ref_key in defs:
                # Clear the node and replace with the definition
                node.clear()
                node.update(defs[ref_key])
                # Continue resolving in case the definition contains more $refs
                _resolve(node)
            return

        # Recursively process all nested structures
        if "properties" in node and isinstance(node["properties"], dict):
            for prop_value in node["properties"].values():
                _resolve(prop_value)

        if "items" in node:
            _resolve(node["items"])

        if "additionalProperties" in node and isinstance(node["additionalProperties"], dict):
            _resolve(node["additionalProperties"])

        # Handle anyOf, allOf, oneOf
        for key in ["anyOf", "allOf", "oneOf"]:
            if key in node and isinstance(node[key], list):
                for item in node[key]:
                    _resolve(item)

    _resolve(schema)
    return schema


def _remove_additional_properties(schema_node: dict | list) -> dict | list:
    """Remove additionalProperties from schema for Google API compatibility."""
    if isinstance(schema_node, dict):
        if "additionalProperties" in schema_node:
            del schema_node["additionalProperties"]
        for key in list(schema_node.keys()):
            _remove_additional_properties(schema_node[key])
    elif isinstance(schema_node, list):
        for item in schema_node:
            _remove_additional_properties(item)
    return schema_node


def _function_to_openai(f: Function, use_google_format: bool = False) -> ChatCompletionToolParam:
    # Get the base schema
    parameters = f.parameters.model_json_schema()

    if use_google_format:
        # Only process if schema contains $defs (like share_file in workspace suite)
        if "$defs" in parameters:
            import logging
            logging.info(f"Converting schema for tool '{f.name}' (contains $defs)")
            # Resolve $refs and remove additionalProperties for Google API compatibility
            parameters = _resolve_schema_refs(f.parameters)
            parameters = _remove_additional_properties(parameters)

    function_definition = FunctionDefinition(
        name=f.name,
        description=f.description,
        parameters=parameters,
    )
    return ChatCompletionToolParam(type="function", function=function_definition)


@retry(
    wait=wait_random_exponential(multiplier=1, max=40),
    stop=stop_after_attempt(3),
    reraise=True,
    retry=retry_if_not_exception_type((openai.BadRequestError, openai.UnprocessableEntityError)),
)
def chat_completion_request(
    client: openai.OpenAI,
    model: str,
    messages: Sequence[ChatCompletionMessageParam],
    tools: Sequence[ChatCompletionToolParam],
    reasoning_effort: ChatCompletionReasoningEffort | None,
    temperature: float | None = 0.0,
):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools or NOT_GIVEN,
        tool_choice="auto" if tools else NOT_GIVEN,
        temperature=temperature or NOT_GIVEN,
        reasoning_effort=reasoning_effort or NOT_GIVEN,
    )


class OpenAILLM(BasePipelineElement):
    """LLM pipeline element that uses OpenAI's API.

    Args:
        client: The OpenAI client.
        model: The model name.
        temperature: The temperature to use for generation.
        use_google_format: If True, format tool schemas for Google API compatibility.
            Set this when using Google models via OpenAI-compatible proxies.
    """

    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        reasoning_effort: ChatCompletionReasoningEffort | None = None,
        temperature: float | None = 0.0,
        use_google_format: bool = False,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.reasoning_effort: ChatCompletionReasoningEffort | None = reasoning_effort
        self.use_google_format = use_google_format

    def _validate_message_sequence(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Validate and fix message sequence to ensure OpenAI API compatibility.

        OpenAI API (and compatible APIs like Qwen) require that any assistant message
        with tool_calls must be immediately followed by tool messages responding to
        each tool_call_id.

        If we find an assistant message with tool_calls that's not followed by tool
        messages, we remove the tool_calls to avoid API errors.

        Args:
            messages: The message sequence to validate

        Returns:
            Fixed message sequence
        """
        if not messages:
            return messages

        import logging
        logger = logging.getLogger(__name__)

        fixed_messages = []
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                # Check if this is the last message or if the next message is not a tool message
                is_last = (i == len(messages) - 1)
                next_is_not_tool = (not is_last and messages[i + 1]["role"] != "tool")

                if is_last or next_is_not_tool:
                    # This assistant message has tool_calls but no tool responses
                    # Remove the tool_calls to avoid API error
                    logger.warning(
                        f"[OpenAI LLM] Detected incomplete tool call sequence at message {i}. "
                        f"Tool: {msg['tool_calls'][0].function if msg['tool_calls'] else 'unknown'}. "
                        f"Removing tool_calls to avoid API error."
                    )

                    # Create a copy without tool_calls
                    fixed_msg = ChatAssistantMessage(
                        role="assistant",
                        content=msg["content"] if msg["content"] else [{"type": "text", "content": ""}],
                        tool_calls=None,
                    )
                    fixed_messages.append(fixed_msg)
                else:
                    fixed_messages.append(msg)
            else:
                fixed_messages.append(msg)

        return fixed_messages

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        # === CRITICAL FIX: Validate message sequence before sending to API ===
        # OpenAI API requires that assistant messages with tool_calls must be
        # immediately followed by tool messages. If not, we get a 400 error.
        # This can happen in VIGIL framework when HypothesisGuidance generates
        # an assistant message with tool_calls but ConditionalLLM is called before
        # the tool is executed.
        validated_messages = self._validate_message_sequence(list(messages))

        openai_messages = [_message_to_openai(message, self.model) for message in validated_messages]
        openai_tools = [_function_to_openai(tool, use_google_format=self.use_google_format) for tool in runtime.functions.values()]

        # Debug: Log tool count and check for issues
        if self.use_google_format:
            import logging
            logging.info(f"Using Google format with {len(openai_tools)} tools")
            # Check if any tool still has $defs or $ref
            for i, tool in enumerate(openai_tools):
                tool_str = json.dumps(tool)
                if "$defs" in tool_str or "$ref" in tool_str:
                    logging.warning(f"Tool {i} ({tool.get('function', {}).get('name', 'unknown')}) still contains $defs or $ref!")
                    logging.warning(f"Tool schema: {json.dumps(tool, indent=2)}")

        completion = chat_completion_request(
            self.client, self.model, openai_messages, openai_tools, self.reasoning_effort, self.temperature
        )

        # Check if the completion has choices
        if not completion.choices or len(completion.choices) == 0:
            import logging
            logging.error(f"API returned no choices. Tool count: {len(openai_tools)}")
            logging.error(f"Full response: {completion}")
            if openai_tools and self.use_google_format:
                logging.error("Sample tool schema (first tool):")
                logging.error(json.dumps(openai_tools[0], indent=2))
            error_msg = f"API returned no choices. Model: {self.model}, Response: {completion}"
            raise ValueError(error_msg)

        output = _openai_to_assistant_message(completion.choices[0].message)
        messages = [*messages, output]
        return query, runtime, env, messages, extra_args


class OpenAILLMToolFilter(BasePipelineElement):
    def __init__(
        self,
        prompt: str,
        client: openai.OpenAI,
        model: str,
        temperature: float | None = 0.0,
        use_google_format: bool = False,
    ) -> None:
        self.prompt = prompt
        self.client = client
        self.model = model
        self.temperature = temperature
        self.use_google_format = use_google_format

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        messages = [*messages, ChatUserMessage(role="user", content=[text_content_block_from_string(self.prompt)])]
        openai_messages = [_message_to_openai(message, self.model) for message in messages]
        openai_tools = [_function_to_openai(tool, use_google_format=self.use_google_format) for tool in runtime.functions.values()]

        # Pass tools but don't specify tool_choice
        # Some Google API proxies don't support tool_choice="none"
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=openai_tools or NOT_GIVEN,
                # Don't use tool_choice="none" - it's not supported by all proxies
                temperature=self.temperature,
            )
        except Exception as e:
            # If it still fails, try without tools
            import logging
            logging.warning(f"Tool filter failed with tools, retrying without: {e}")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=self.temperature,
            )

        # Check if the completion has choices
        if not completion.choices or len(completion.choices) == 0:
            error_msg = f"Tool filter API returned no choices. Model: {self.model}, Response: {completion}"
            raise ValueError(error_msg)

        output = _openai_to_assistant_message(completion.choices[0].message)

        new_tools = {}
        for tool_name, tool in runtime.functions.items():
            if output["content"] is not None and tool_name in get_text_content_as_str(output["content"]):
                new_tools[tool_name] = tool

        runtime.update_functions(new_tools)

        messages = [*messages, output]
        return query, runtime, env, messages, extra_args
