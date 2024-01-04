from dataclasses import dataclass
from typing import Any, Callable
from openai_functions import FunctionWrapper
import autogen
import logging
import openai_functions

logger = logging.getLogger(__name__)


class Handler:
    def __init__(self, function_wrapper: FunctionWrapper, assistant: "Agent") -> None:
        self._function_wrapper = function_wrapper
        self._assistant = assistant

    def unregister(self) -> None:
        self._assistant._functions_wrappers.remove(self._function_wrapper)


class Agent:
    CONSTANTS = {
        "max_consecutive_auto_reply": 5,
        "system_message": """You are a helpful AI assistant.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses function calling and which step uses your language skill.
The user cannot provide any other feedback or perform any other action beyond the original task. All the interaction must be done through function calling. So do not ask for user input, unless there is a function specified for that.
If the result indicates there is an error, fix the error and call the function again. If the error can't be fixed or if the task is not solved even after the several tries, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply "TERMINATE" at the end of the message when everything is done."""
    }

    def __init__(self, api_base: str = "", api_key: str = "", model: str = "",
                 system_message: str = CONSTANTS["system_message"]) -> None:
        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._functions_wrappers: list[FunctionWrapper] = []
        self._system_message = system_message

    def add_function(self, function: Callable[..., Any]) -> Handler:
        wrapper = openai_functions.FunctionWrapper(function)
        self._functions_wrappers.append(wrapper)
        return Handler(wrapper, self)

    def do_conversation(self, user_message: str,
                        max_consecutive_auto_reply: int = CONSTANTS["max_consecutive_auto_reply"]) -> None:
        config_list = [
            {
                "model": self._model,
                "api_key": self._api_key,
                "api_base": self._api_base
            },
        ]

        # create an AssistantAgent named "assistant"
        assistant = autogen.AssistantAgent(
            name="assistant",
            system_message=self._system_message,
            llm_config={
                "seed": 42,  # seed for caching and reproducibility
                "request_timeout": 580,
                "config_list": config_list,  # a list of OpenAI API configurations
                "temperature": 0,  # temperature for sampling
                "functions": [f.schema for f in self._functions_wrappers]
            },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
        )

        # create a UserProxyAgent instance named "user_proxy"
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            default_auto_reply=".",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            is_termination_msg=lambda x: False if x.get("content", "") == None else x.get("content",
                                                                                          "").rstrip().endswith(
                "TERMINATE") or x.get("content", "").rstrip().startswith("TERMINATE"),
            code_execution_config=False,
            function_map={f.name: f.func for f in self._functions_wrappers}
        )

        user_proxy.initiate_chat(
            assistant,
            message=user_message,
        )
