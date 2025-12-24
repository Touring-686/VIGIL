"""
Third-Party Agent Adapter for AgentDojo Framework

This module provides a simple interface for integrating third-party agents
into the AgentDojo framework without requiring detailed knowledge of the
pipeline architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall, Function
from agentdojo.types import ChatMessage, ChatAssistantMessage, ChatToolResultMessage
from agentdojo.agent_pipeline.tool_execution import tool_result_to_str


class SimpleAgentInterface(ABC):
    """
    Minimal interface that third-party agents need to implement.

    Third-party developers only need to inherit this class and implement
    the single method: execute_query()
    """

    @abstractmethod
    def execute_query(
        self,
        query: str,
        available_tools: dict[str, dict[str, Any]],
        conversation_history: list[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Execute a query using the agent's own logic.

        Args:
            query: The user's query/task prompt
            available_tools: Dictionary of available tools with their schemas
                Format: {
                    "tool_name": {
                        "description": "Tool description",
                        "parameters": {
                            "param1": {"type": "string", "description": "..."},
                            "param2": {"type": "number", "description": "..."},
                        }
                    }
                }
            conversation_history: Optional list of previous conversation turns
                Format: [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "...", "tool_calls": [...]},
                    {"role": "tool", "content": "...", "tool_name": "..."},
                ]

        Returns:
            Dictionary with agent's response:
            {
                "content": "Agent's text response (optional)",
                "tool_calls": [  # Optional list of tool calls
                    {
                        "tool_name": "send_email",
                        "arguments": {
                            "address": "user@example.com",
                            "subject": "Hello",
                            "body": "World"
                        }
                    }
                ],
                "finish": True/False  # Whether the agent is done (optional, default False)
            }
        """
        pass


class ThirdPartyAgentAdapter(BasePipelineElement):
    """
    Adapter that wraps a SimpleAgentInterface implementation and integrates
    it into the AgentDojo pipeline framework.

    Usage:
        # Step 1: Implement your agent
        class MyAgent(SimpleAgentInterface):
            def execute_query(self, query, available_tools, conversation_history):
                # Your agent logic here
                return {
                    "content": "I will send an email",
                    "tool_calls": [{
                        "tool_name": "send_email",
                        "arguments": {"address": "test@example.com", ...}
                    }]
                }

        # Step 2: Wrap it with adapter
        my_agent = MyAgent()
        adapter = ThirdPartyAgentAdapter(my_agent, max_iterations=10)

        # Step 3: Use in pipeline
        pipeline = AgentPipeline([
            SystemMessage("You are a helpful assistant."),
            InitQuery(),
            adapter
        ])
    """

    def __init__(
        self,
        agent: SimpleAgentInterface,
        max_iterations: int = 15,
        tool_output_formatter=tool_result_to_str,
        verbose: bool = False
    ):
        """
        Initialize the adapter.

        Args:
            agent: Instance of a class implementing SimpleAgentInterface
            max_iterations: Maximum number of agent-tool interaction rounds
            tool_output_formatter: Function to format tool outputs (default: YAML)
            verbose: Whether to print debug information
        """
        self.agent = agent
        self.max_iterations = max_iterations
        self.tool_output_formatter = tool_output_formatter
        self.verbose = verbose
        self.name = f"ThirdPartyAgent({agent.__class__.__name__})"

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env=None,
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {}
    ):
        """
        Execute the third-party agent within the AgentDojo pipeline.

        This method handles:
        1. Converting AgentDojo data structures to simple formats
        2. Calling the third-party agent
        3. Executing tool calls using the runtime
        4. Converting results back to AgentDojo format
        """
        # Convert runtime functions to simple tool format
        available_tools = self._convert_runtime_to_tools(runtime)

        # Convert message history to simple format
        conversation_history = self._convert_messages_to_history(messages)

        # Execute agent-tool loop
        current_messages = list(messages)

        for iteration in range(self.max_iterations):
            if self.verbose:
                print(f"\n=== Iteration {iteration + 1}/{self.max_iterations} ===")

            # Call the third-party agent
            agent_response = self.agent.execute_query(
                query=query,
                available_tools=available_tools,
                conversation_history=conversation_history
            )

            # Convert agent response to AgentDojo message format
            assistant_message = self._create_assistant_message(agent_response)
            current_messages = [*current_messages, assistant_message]

            if self.verbose:
                print(f"Agent response: {agent_response}")

            # Check if agent wants to finish or has no tool calls
            if agent_response.get("finish", False) or not agent_response.get("tool_calls"):
                break

            # Execute tool calls
            tool_results = self._execute_tool_calls(
                agent_response.get("tool_calls", []),
                runtime,
                env
            )

            # Add tool results to messages
            current_messages = [*current_messages, *tool_results]

            # Update conversation history for next iteration
            conversation_history = self._convert_messages_to_history(current_messages)

        return query, runtime, env, current_messages, extra_args

    def _convert_runtime_to_tools(self, runtime: FunctionsRuntime) -> dict[str, dict[str, Any]]:
        """Convert FunctionsRuntime to simple tool dictionary format."""
        tools = {}
        for name, func in runtime.functions.items():
            # Extract parameters from Pydantic model
            parameters = {}
            if func.parameters:
                schema = func.parameters.model_json_schema()
                parameters = schema.get("properties", {})

            tools[name] = {
                "description": func.description,
                "parameters": parameters
            }

        return tools

    def _convert_messages_to_history(self, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        """Convert AgentDojo ChatMessage format to simple dictionary format."""
        history = []

        for msg in messages:
            role = msg.get("role")

            if role == "system":
                # Extract text content
                content = self._extract_text_content(msg.get("content", []))
                history.append({"role": "system", "content": content})

            elif role == "user":
                content = self._extract_text_content(msg.get("content", []))
                history.append({"role": "user", "content": content})

            elif role == "assistant":
                content = self._extract_text_content(msg.get("content", []))
                entry = {"role": "assistant", "content": content}

                # Add tool calls if present
                if msg.get("tool_calls"):
                    entry["tool_calls"] = [
                        {
                            "tool_name": tc.function,
                            "arguments": tc.args,
                            "id": tc.id
                        }
                        for tc in msg["tool_calls"]
                    ]

                history.append(entry)

            elif role == "tool":
                content = self._extract_text_content(msg.get("content", []))
                history.append({
                    "role": "tool",
                    "content": content,
                    "tool_name": msg.get("tool_call", {}).function if msg.get("tool_call") else None,
                    "tool_call_id": msg.get("tool_call_id"),
                    "error": msg.get("error")
                })

        return history

    def _extract_text_content(self, content_blocks: list) -> str:
        """Extract text from content blocks."""
        if not content_blocks:
            return ""

        text_parts = []
        for block in content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)

        return "\n".join(text_parts)

    def _create_assistant_message(self, agent_response: dict[str, Any]) -> ChatAssistantMessage:
        """Create ChatAssistantMessage from agent response."""
        from agentdojo.types import text_content_block_from_string

        # Create content blocks
        content_blocks = []
        if agent_response.get("content"):
            content_blocks.append(
                text_content_block_from_string(agent_response["content"])
            )

        # Create tool calls
        tool_calls = None
        if agent_response.get("tool_calls"):
            tool_calls = []
            for idx, tc in enumerate(agent_response["tool_calls"]):
                # Generate a unique ID if not provided
                tool_call_id = tc.get("id", f"call_{idx}")

                tool_calls.append(
                    FunctionCall(
                        function=tc["tool_name"],
                        args=tc["arguments"],
                        id=tool_call_id
                    )
                )

        return ChatAssistantMessage(
            role="assistant",
            content=content_blocks if content_blocks else None,
            tool_calls=tool_calls
        )

    def _execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        runtime: FunctionsRuntime,
        env
    ) -> list[ChatToolResultMessage]:
        """Execute tool calls and return results as ChatToolResultMessages."""
        from agentdojo.types import text_content_block_from_string

        results = []

        for idx, tool_call in enumerate(tool_calls):
            tool_name = tool_call["tool_name"]
            arguments = tool_call["arguments"]
            tool_call_id = tool_call.get("id", f"call_{idx}")

            # Check if tool exists
            if tool_name not in runtime.functions:
                error_msg = f"Tool '{tool_name}' not found in available functions"
                results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string(error_msg)],
                        tool_call=FunctionCall(
                            function=tool_name,
                            args=arguments,
                            id=tool_call_id
                        ),
                        tool_call_id=tool_call_id,
                        error=error_msg
                    )
                )
                continue

            # Execute the tool
            tool_result, error = runtime.run_function(
                env,
                tool_name,
                arguments,
                raise_on_error=False
            )

            # Format the result
            if error:
                formatted_result = f"Error: {error}"
            else:
                formatted_result = self.tool_output_formatter(tool_result)

            if self.verbose:
                print(f"Tool {tool_name} result: {formatted_result}")

            # Create tool result message
            results.append(
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(formatted_result)],
                    tool_call=FunctionCall(
                        function=tool_name,
                        args=arguments,
                        id=tool_call_id
                    ),
                    tool_call_id=tool_call_id,
                    error=error
                )
            )

        return results


# Utility function for quick integration
def create_simple_pipeline_from_agent(
    agent: SimpleAgentInterface,
    system_message: str = "You are a helpful assistant.",
    max_iterations: int = 15,
    verbose: bool = False
):
    """
    Convenience function to create a complete pipeline from a SimpleAgentInterface.

    Args:
        agent: Instance implementing SimpleAgentInterface
        system_message: System prompt for the agent
        max_iterations: Maximum agent-tool interaction rounds
        verbose: Whether to print debug info

    Returns:
        AgentPipeline ready to use with TaskSuite

    Example:
        my_agent = MyCustomAgent()
        pipeline = create_simple_pipeline_from_agent(my_agent)

        # Now use with TaskSuite
        task_suite = TaskSuite(...)
        utility, security = task_suite.run_task_with_pipeline(pipeline, ...)
    """
    from agentdojo.agent_pipeline import AgentPipeline, SystemMessage, InitQuery

    adapter = ThirdPartyAgentAdapter(
        agent=agent,
        max_iterations=max_iterations,
        verbose=verbose
    )

    pipeline = AgentPipeline([
        SystemMessage(system_message),
        InitQuery(),
        adapter
    ])

    return pipeline
