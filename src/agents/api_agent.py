import inspect
import json
from abc import ABC
from dataclasses import dataclass, asdict
import instructor
from langchain_core.utils.function_calling import convert_to_openai_tool
from openai import OpenAI
from typing import Type, Callable
from pydantic import BaseModel, create_model, Field
from json_repair import repair_json
import logging

from src.data_acquisition.constants import SYSTEM, ASSISTANT, USER, ADDRESS, DEFAULT_ADDRESS

logger = logging.getLogger(__name__)

FUNC_ERR = "Error getting function call response: "
JSON_ERR = "Error getting JSON format response: "
NO_CALL_ERR = "No function call found in the response."


@dataclass
class Message:
    role: str
    content: str


class ApiAgent(ABC):
    """Base class for function calling API agents that interact through the OpenAI API."""

    def __init__(self, url, api_key, model_name):
        """
        Initialize the API agent
        :param url: API url
        :param api_key: API key for the service
        :param model_name: Name of the model to be used
        """
        self.client = OpenAI(api_key=api_key, base_url=url)
        self.model_name = model_name
        self.messages_storage = []

    def _add_message(self, message: Message):
        """
        Add a message to the message storage
        :param message: Message to be added
        :return:
        """
        if len(self.messages_storage) > 10:  # todo limit by tokens and do sum ups
            self.messages_storage = self.messages_storage[:3]
        self.messages_storage.append(message)

    def _add_messages_initially(self, messages: list[Message]):
        """
        Add a list of messages to the message storage
        :param messages: List of messages to be added
        :return:
        """
        self.messages_storage = []
        for m in messages:
            self._add_message(m)

    def get_function_call_response(self, module: dict, functions: list, messages: list[Message] = None,
                                   max_retries: int = 2):
        """
        Instruct the model to call a function and get the result of the function call
        :param module: Module containing the functions
        :param functions: List of functions to chosen from
        :param messages: List of messages to be sent to the model
        :param max_retries:
        :return: result of called function
        """
        if messages:
            self._add_messages_initially(messages)
        con_messages = [asdict(m) for m in self.messages_storage]
        openai_functions = [self._function_to_openai_function_schema(f) for f in functions]
        if not openai_functions:
            return None
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=con_messages,
            functions=openai_functions,
            stream=False
        )
        self._add_message(Message(ASSISTANT, str(response.choices[0].message)))
        return self._handle_response_function_call_errors(functions, max_retries, module, response)

    def _handle_response_function_call_errors(self, functions, max_retries, module, response):
        """ Handle the errors in the function call part of the response
        :param functions: Functions that were chosen from
        :param max_retries: Number of retries
        :param module: Module containing the functions
        :param response: Model response in API format
        :return:
        """
        if response.choices[0].message.function_call is None:
            self._handle_call_exception("", NO_CALL_ERR, max_retries,
                                        lambda: self.get_function_call_response(module, functions,
                                                                                max_retries=max_retries - 1))
        return self._handle_function_call_return(functions, max_retries, module, response)

    def _handle_call_exception(self, e, error_text, max_retries, handling_function: Callable):
        if max_retries > 0:
            logger.error(f"{error_text}{e}. Retrying")
            self._add_message(Message(USER, f"{error_text}{e}. Retry."))
            return handling_function()
        logger.error(f"{error_text}{e}. Max retries reached. Skipping.")
        return {}

    def _handle_function_call_return(self, functions, max_retries, module, response):
        """
        Handle the return of the function call
        :param functions: Functions that were chosen from
        :param max_retries: Number of retries
        :param module: Module containing the functions
        :param response: Model response in API format
        :return:
        """
        name = None
        try:
            name, arguments = self._parse_function_call(module, response)
            if not name:
                self._add_message(Message(USER, "Function name not found. Retry."))
                return self._handle_function_call_return_errors(functions, max_retries, module)
            if arguments:
                return module[name](**arguments)
            return module[name]()
        except Exception as e:
            logger.error(f"Error calling function {name}: {e}")
            self._add_message(Message(USER, f"Error calling function {name}: {e}. Retry."))
            return self._handle_function_call_return_errors(functions, max_retries, module)

    def _handle_function_call_return_errors(self, functions, max_retries, module):
        """
        Handle the errors in the function call return
        :param functions: Functions that were chosen from
        :param max_retries: Number of retries
        :param module: Module containing the functions
        :return:
        """
        if max_retries > 0:
            logger.error("Could not make function call, retrying.")
            return self.get_function_call_response(module, functions, max_retries=max_retries - 1)
        logger.error("Could not make function call, max retries reached. Skipping.")
        return None

    def _parse_function_call(self, module: dict, response) -> [str, dict]:
        """
        Parse the response from the model to get the function call
        :param module: Module containing the function
        :param response: Model response in API format
        :return: result of called function
        """
        function_name = response.choices[0].message.function_call.name
        if not self._does_function_exist(function_name, module):
            logger.error(f"Function {function_name} not found in the module.")
            return None, None
        params = self._get_function_parameters(module, function_name)
        if not params:
            return function_name, None
        function_arguments = self._parse_function_arguments(response.choices[0].message.function_call.arguments)
        matched_arguments = self._match_parameters(function_arguments, function_name, params)
        if matched_arguments:
            return function_name, matched_arguments
        return None, None

    def _parse_function_arguments(self, function_arguments: dict) -> dict:
        """
        Parse the individual function arguments from the response
        :param function_arguments: Unparsed function arguments in JSON string format
        :return: dictionary containing the parsed function arguments
        """

        try:
            function_arguments = dict(function_arguments)
        except Exception as e:
            logger.error("Error parsing function arguments to dictionary: %s. Handling.", e)
            a = function_arguments.replace('\n', ' ')
            a = a.replace('\"https\"', 'https')
            a = a.replace('None', '""')
            a = repair_json(a)
            function_arguments = dict(json.loads(a))
        if "description" not in str(function_arguments):
            return self._fix_encoding(function_arguments)
        result = {}
        for key in function_arguments:
            result[key] = function_arguments[key].get("description", "")
        return self._fix_encoding(result)

    @staticmethod
    def _fix_encoding(arguments: dict) -> dict:
        for k, v in arguments.items():
            if isinstance(v, str):
                if "\\" in v:
                    v = v.replace('\n', ' ').replace('\"', '')
                    try:
                        arguments[k] = bytes(v, 'utf-8').decode('unicode_escape')
                    except UnicodeDecodeError as e:
                        logger.error(f"Error decoding string: {e}")
                        arguments[k] = v
        return arguments

    @staticmethod
    def _get_function_parameters(module: dict, func_name) -> list:
        """
        Get the parameters of the function
        :param module: Module containing the function
        :param func_name: Name of the function
        :return:
        """
        if func_name in module:
            function_obj = module[func_name]
            signature = inspect.signature(function_obj)
            parameter_names = list(signature.parameters.keys())
            return parameter_names
        else:
            logger.error(f"Function {func_name} not found in the module.")
            return []

    @staticmethod
    def _function_to_openai_function_schema(function: Callable) -> dict:
        """
        Convert the function to OpenAI function schema
        :param function: Function to be converted
        :return: dictionary containing the function schema
        """
        converted = {}
        try:
            converted = dict(convert_to_openai_tool(function)["function"])
        except Exception as e:
            logger.error(f"Error converting function to OpenAI function schema: {e}")
        return converted

    def get_json_format_response(self, response_model: BaseModel, messages: list[Message] = None,
                                 max_retries=2) -> dict:
        """
        Get the response in desired JSON format
        :param response_model: Desired response model
        :param messages: List of messages to be sent to the model
        :param max_retries: Number of retries
        :return: dictionary containing the formatted response
        """

        messages = [asdict(m) for m in messages]
        client = instructor.patch(
            self.client,
            mode=instructor.Mode.JSON,
        )

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            response_model=response_model,
            max_retries=0
        )
        self._add_message(Message(ASSISTANT, str(response)))
        try:
            return dict(response)
        except Exception as e:
            return self._handle_call_exception(e, JSON_ERR, max_retries,
                                               lambda: self.get_json_format_response(response_model,
                                                                                     max_retries=max_retries - 1))

    def _match_parameters(self, received_arguments: dict, function_name: str, function_params: list) -> dict:
        matched_args = {}
        for arg in function_params:
            if arg not in received_arguments:
                if arg == ADDRESS:
                    matched_args[arg] = DEFAULT_ADDRESS
                    logger.error(
                        f"Parameter {arg} required but not found in call for function {function_name}. Applying default value.")
                    continue
                logger.error(f"Parameter {arg} required but not found in call for function {function_name}.")
                self._add_message(
                    Message(USER,
                            f"Error: Parameter {arg} required but not found in call for function {function_name}. Retry."))
                return {}
            matched_args[arg] = received_arguments[arg]
        redundant_args = [arg for arg in received_arguments if arg not in function_params]
        self._add_message(Message(USER, f"Redundant arguments provided: {redundant_args}."))
        return matched_args

    @staticmethod
    def _does_function_exist(function_name: str, module: dict) -> bool:
        if function_name not in module:
            logger.error(f"Function {function_name} not found in the module.")
            return False
        return True

    @staticmethod
    def _get_function_name_and_description_dict(function: Callable) -> dict:
        """
        Get the name and description of the function
        :param function: Function to be converted
        :return: dictionary containing the function name and description
        """
        try:
            return {"function_name": function.__name__, "description": function.__doc__}
        except Exception as e:
            logger.error(f"Error getting function name and description: {e}")
            return {}

    @staticmethod
    def _get_first_user_message(messages: list[Message]) -> [Message, None]:
        """
        Get the first user message from the list of messages
        :param messages: List of messages
        :return:
        """
        for m in messages:
            if m.role == USER:
                return m
        return None

    @staticmethod
    def _get_function_params_dict(function: Callable) -> dict:
        sig = inspect.signature(function)
        params = {param.name: param.annotation.__name__ for param in sig.parameters.values()}
        return params


class LlamaApiAgent(ApiAgent):

    def get_json_format_response(self, response_model: BaseModel, messages: list[Message] = None,
                                 max_retries=2) -> dict:
        """
        Get the response in desired JSON format
        :param response_model: Desired response model
        :param messages: List of messages to be sent to the model
        :param max_retries: Number of retries
        :return: dictionary containing the formatted response
        """
        messages = [asdict(m) for m in messages]
        schema = self._function_to_openai_function_schema(response_model)
        if not schema:
            return {}
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            functions=[schema],
            function_call=dict({"name": schema["name"]}),
            stream=False,
        )
        self._add_message(Message(ASSISTANT, str(response)))
        try:
            return dict(response.choices[0].message.function_call.arguments)
        except Exception as e:
            return self._handle_json_format_errors(e, max_retries, response_model)


class OpenAIApiAgent(ApiAgent):
    pass


class LocalApiAgent(ApiAgent):

    def get_function_call_response(self, module: dict, functions: list, messages: list[Message] = None,
                                   max_retries: int = 5):
        """
        Instruct the model to call a function and get the result of the function call
        :param module: Module containing the functions
        :param functions: List of functions to be chosen from
        :param messages: List of messages to be sent to the model
        :param max_retries: Number of retries
        :return: result of the called function
        """

        function_name, function_schema = self._choose_function_and_schema(module, functions, max_retries, messages)

        config_message = Message(SYSTEM, f"You are a smart function calling assistant. Your task is to provide "
                                         f"the arguments {self._get_function_params_dict(module[function_name])} for a "
                                         f"function call. Return valid JSON only as a response, no additional text.")
        messages = [config_message] + messages
        return self._call_for_arguments(function_name, module, function_schema, messages)

    def _choose_function_and_schema(self, module, functions, max_retries, messages=None):
        if len(functions) > 1:
            names_and_descriptions = [self._get_function_name_and_description_dict(f) for f in functions]
            if messages:
                config_message = Message(SYSTEM, f"You are a helpful assistant with access to the following functions, "
                                                 f"your task is to choose one of the functions"
                                                 f" according to the descriptions - {names_and_descriptions}."
                                                 f"Return valid JSON only as a response.")
                self._add_messages_initially([config_message] + [self._get_first_user_message(messages)])
            try:
                name = self._choose_from_functions(module, max_retries)
                schema = self._function_to_pydantic_model(module[name])
            except Exception as e:
                return self._handle_call_exception(e, FUNC_ERR, max_retries,
                                                   lambda: self._choose_function_and_schema(module, functions,
                                                                                            max_retries=max_retries - 1))
        else:
            name = functions[0].__name__
            schema = self._function_to_pydantic_model(functions[0])
        return name, schema

    def _choose_from_functions(self, module, max_retires):

        class ChosenFunction(BaseModel):
            """Chosen function to be called"""
            function_name: str = Field(...,
                                       description="Name of one of the provided functions that was chosen to be called")

        response = self.get_json_format_response(ChosenFunction, self.messages_storage)
        self._add_message(Message(ASSISTANT, str(response)))
        function_name = response["function_name"]
        if not self._does_function_exist(function_name, module):
            error_msg = f"Got incorrect function name: {function_name}, function not found in the module. Retry."
            self._handle_call_exception("", error_msg, max_retires,
                                        lambda: self._choose_from_functions(module, max_retires - 1))
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
            response = self.get_json_format_response(function_schema, self.messages_storage, max_retries=10)
            return self._handle_json_call_return(function_name, function_schema, max_retries, module, response)
        except Exception as e:
            return self._handle_call_exception(e, JSON_ERR, max_retries,
                                               lambda: self._call_for_arguments(function_name, module, function_schema,
                                                                                max_retries=max_retries - 1))

    def _handle_json_call_return(self, function_name, function_schema, max_retries, module, response):
        """Handle the return of the response JSON format"""
        try:
            arguments = self._match_parameters(response, function_name,
                                               self._get_function_parameters(module, function_name))
            print(f"Function name: {function_name}, arguments: {arguments}")
            if arguments:
                return module[function_name](**arguments)
            return module[function_name]()
        except Exception as e:
            logger.error(f"Error calling function {function_name}: {e}")
            self._add_message(Message(USER, f"Error calling function {function_name}: {e}. Retry."))
            return self._call_for_arguments(function_name, module, function_schema,
                                            max_retries=max_retries - 1)
