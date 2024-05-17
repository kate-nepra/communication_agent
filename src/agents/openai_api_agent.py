from dataclasses import asdict
from typing import Callable

from src.agents.api_agent import ApiAgent
from src.agents.message import Message, AssistantMessage


class OpenAIApiAgent(ApiAgent):
    def get_forced_function_call(self, module: dict, function: Callable, max_retries: int = 2,
                                 messages: list[Message] = None):
        if messages:
            self._add_messages_initially(messages)
        con_messages = [asdict(m) for m in self.messages_storage]
        response = self.get_forced_call_response(con_messages, function, dict({"name": function.__name__}))
        self._add_message(AssistantMessage(str(response.choices[0].message)))
        return self._handle_response_function_call_errors(module, response, max_retries - 1,
                                                          lambda: self.get_forced_function_call(module, function,
                                                                                                max_retries - 1))
