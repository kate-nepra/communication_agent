import inspect
from dataclasses import asdict
import instructor
from typing import Type, Callable
from pydantic import BaseModel, create_model, Field
import logging

from src.agents.api_agent import ApiAgent
from src.agents.constants import JSON_ERR, FUNC_NAME, CANT_CALL_ERR, FUNC_ERR
from src.agents.message import Message, AssistantMessage, UserMessage, SystemMessage

logger = logging.getLogger(__name__)


class LocalApiAgent(ApiAgent):

    def get_json_format_response(self, response_model: BaseModel, messages: list[Message] = None,
                                 max_retries=2) -> dict:
        """
        Get the response in desired JSON format
        :param response_model: Desired response model
        :param messages: List of messages to be sent to the model
        :param max_retries: Number of retries
        :return: dictionary containing the formatted response
        """
        if messages:
            self._add_messages_initially(messages)
        messages = [asdict(m) for m in self.messages_storage]
        client = instructor.patch(
            self.client,
            mode=instructor.Mode.JSON,
        )
        logger.info(f"Messages: {messages}")
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            response_model=response_model,
            max_retries=1
        )
        self._add_message(AssistantMessage(str(response)))
        try:
            return dict(response)
        except Exception as e:
            return self._handle_call_exception(e, JSON_ERR, max_retries - 1,
                                               lambda: self.get_json_format_response(response_model,
                                                                                     max_retries=max_retries - 1))

    def get_function_call(self, module: dict, functions: list, max_retries: int = 2,
                          messages: list[Message] = None):
        """
        Instruct the model to call a function and get the result of the function call
        :param module: Module containing the functions
        :param functions: List of functions to be chosen from
        :param messages: List of messages to be sent to the model
        :param max_retries: Number of retries
        :return: result of the called function
        """
        try:
            names_and_descriptions = [self._get_func_name_and_descr_dict(f) for f in functions]
            name, model = self._get_func_name_and_model(module, functions, names_and_descriptions, max_retries,
                                                        messages)
        except Exception as e:
            logger.error(f"Error choosing function and schema: {e}")
            return
        return self._end_func_call(messages, model, module, name, names_and_descriptions, max_retries)

    def get_custom_descr_function_call(self, module: dict, functions: list[tuple[Callable, str]],
                                       max_retries: int = 2,
                                       messages: list[Message] = None):

        """
        Instruct the model to call a function and get the result of the function call, with providing custom descriptions
        :param module: Module containing the functions
        :param functions: list of [function, description] to be chosen from
        :param max_retries: Number of retries
        :param messages: List of messages to be sent to the model
        :return: result of the called function
        """
        try:
            names_and_descriptions = [{FUNC_NAME: f.__name__, "description": descr} for f, descr in functions]
            name, model = self._get_func_name_and_model(module, [f for f, _ in functions], names_and_descriptions,
                                                        max_retries, messages)
        except Exception as e:
            logger.error(f"Error choosing function and schema: {e}")
            return
        return self._end_func_call(messages, model, module, name, names_and_descriptions, max_retries)

    def _end_func_call(self, messages, model, module, name, names_and_descriptions, max_retries):
        chosen_descr = self._get_chosen_description(names_and_descriptions, name)
        messages = self._get_messages_with_params_config(messages,
                                                         self._get_function_params_dict(module[name]),
                                                         chosen_descr)
        if self._get_function_parameters(module, name):
            return self._call_for_arguments(name, module, model, messages, max_retries)
        return module[name]()

    def get_forced_function_call(self, module: dict, function: Callable, max_retries: int = 2,
                                 messages: list[Message] = None):
        function_name = function.__name__
        function_schema = self._function_to_pydantic_model(function)
        messages = self._get_messages_with_params_config(messages, self._get_function_params_dict(function),
                                                         function.__doc__)
        if self._get_function_parameters(module, function_name):
            return self._call_for_arguments(function_name, module, function_schema, messages, max_retries)
        return module[function_name]()

    def _get_func_name_and_model(self, module, functions, names_and_descriptions, max_retries=1, messages=None):
        if len(functions) > 1:
            self._setup_messages(messages, names_and_descriptions)
            try:
                name = self._choose_from_functions(module, max_retries)
                model = self._function_to_pydantic_model(module[name])
            except Exception as e:
                return self._handle_call_exception(e, FUNC_ERR, max_retries - 1,
                                                   lambda: self._get_func_name_and_model(module, functions,
                                                                                         max_retries - 1))
        else:
            name = functions[0].__name__
            model = self._function_to_pydantic_model(functions[0])
        return name, model

    def _setup_messages(self, messages, names_and_descriptions):
        if messages:
            config_message = SystemMessage(
                f"You are a helpful assistant with access to the following functions, your task is to choose one of the functions according to the descriptions: ```{names_and_descriptions}```."
                f"Return valid JSON only as a response.")
            self._add_messages_initially([config_message] + [self._get_first_user_message(messages)])

    def _choose_from_functions(self, module, max_retires):

        class ChosenFunction(BaseModel):
            """Chosen function to be called"""
            function_name: str = Field(...,
                                       description="Name of one of the provided functions that was chosen to be called")

        try:

            response = self.get_json_format_response(ChosenFunction, self.messages_storage)
            self._add_message(AssistantMessage(str(response)))
            function_name = response[FUNC_NAME]
            if not self._does_function_exist(function_name, module):
                error_msg = f"Got incorrect function name: {function_name}, function not found in the module. Retry."
                return self._handle_call_exception("", error_msg, max_retires - 1,
                                                   lambda: self._choose_from_functions(module, max_retires - 1))
        except RecursionError as e:
            logger.error(f"RecError: {e}")
            return
        except Exception as e:
            logger.error(f"Error: {e}")
            return
        return function_name

    @staticmethod
    def _function_to_pydantic_model(function: Callable) -> Type[BaseModel]:
        """
        Takes a function and returns a Pydantic BaseModel class constructed
        from the function's parameters, assuming all parameters are required
        and of type str if not annotated.
        """

        params = inspect.signature(function).parameters
        fields = {
            name: (
                param.annotation if param.annotation is not inspect.Parameter.empty else 'str', ...)
            for name, param in params.items()
        }
        return create_model(function.__name__, **fields)

    def _call_for_arguments(self, function_name, module, function_schema, messages=None, max_retries=2):
        """Get the arguments for the function call"""

        if messages:
            self._add_messages_initially(messages)
        try:
            response = self.get_json_format_response(function_schema, self.messages_storage, max_retries=max_retries)
            return self._handle_json_call_return(function_name, function_schema, max_retries, module, response)
        except Exception as e:
            return self._handle_call_exception(e, JSON_ERR, max_retries - 1,
                                               lambda: self._call_for_arguments(function_name, module, function_schema,
                                                                                max_retries=max_retries - 1))

    def _handle_json_call_return(self, function_name, function_schema, max_retries, module, response):
        """Handle the return of the response JSON format"""
        try:
            arguments = self._match_parameters(response, function_name,
                                               self._get_function_parameters(module, function_name))
            if arguments:
                return module[function_name](**arguments)
            return module[function_name]()
        except Exception as e:
            logger.error(f"{CANT_CALL_ERR}{function_name}: {e}")
            self._add_message(UserMessage(f"{CANT_CALL_ERR}{function_name}: {e}. Retry."))
            return self._call_for_arguments(function_name, module, function_schema,
                                            max_retries=max_retries - 1)

    @staticmethod
    def _get_messages_with_params_config(messages, parameters, description=None):
        description_text = f" of function with description: ```{description}``` " if description else ""
        config_message = SystemMessage(
            f"You are a smart function calling assistant. Your task is to provide the arguments following this template {parameters} for a function call according to the instructions, and description {description_text}."
            f"Return valid JSON only as a response, no additional text.")
        messages = messages + [config_message] if messages else [config_message]
        return messages

    @staticmethod
    def _get_chosen_description(names_and_descriptions: list[dict], name: str) -> str:
        for item in names_and_descriptions:
            if item[FUNC_NAME] == name:
                return item["description"]
        return ""
