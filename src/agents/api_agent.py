import inspect
import json
import time
from abc import ABC
from dataclasses import asdict
from langchain_core.utils.function_calling import convert_to_openai_tool
from openai import OpenAI
from typing import Callable
from pydantic import BaseModel
from json_repair import repair_json
import logging

from src.agents.constants import FUNC_NAME, JSON_ERR, NO_CALL_ERR, RECURSION_ERR, API_ERR, CONN_ERR
from src.agents.message import Message, AssistantMessage, UserMessage
from src.constants import MAX_SIZE
from src.data_acquisition.constants import ADDRESS, DEFAULT_ADDRESS

logger = logging.getLogger(__name__)


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

    def get_base_response(self, messages: list[dict]):
        """Get the response from the model without function calling"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=False
        )
        logger.info(f"Response: {str(response)}")
        return response

    def get_base_call_response(self, messages: list[dict], functions_schemas: list[dict]):
        """Get the response from the model with function calling
        :param messages: List of messages to be sent to the model
        :param functions_schemas: List of function schemas in OpenAI tool format
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            functions=functions_schemas,
            stream=False
        )
        logger.info(f"Response: {str(response)}")
        return response

    def get_forced_call_response(self, messages: list[dict], function: Callable, function_call: dict):
        """Get the response from the model with forced function call
        :param messages: List of messages to be sent to the model
        :param function: Function to be called
        :param function_call: Function call enforcing the function name
        """
        schema = [self._function_to_openai_function_schema(function)]
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            functions=schema,
            stream=False,
            function_call=function_call,
        )
        logger.info(f"Response: {str(response)}")
        return response

    def get_function_call(self, module: dict, functions: list, max_retries: int = 3,
                          messages: list[Message] = None):
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
        functions_schemas = [self._function_to_openai_function_schema(f) for f in functions]
        response = self.get_base_call_response(con_messages, functions_schemas)
        self._add_message(AssistantMessage(str(response.choices[0].message)))
        return self._handle_response_function_call_errors(module, response, max_retries,
                                                          lambda: self.get_function_call(module, functions,
                                                                                         max_retries - 1))

    def get_custom_descr_function_call(self, module: dict, functions: list[tuple[Callable, str]],
                                       max_retries: int = 3,
                                       messages: list[Message] = None):
        """
        Instruct the model to call a function and get the result of the function call
        :param module: Module containing the functions
        :param functions: List of functions to chosen from with custom descriptions
        :param messages: List of messages to be sent to the model
        :param max_retries:
        :return: result of called function
        """
        if messages:
            self._add_messages_initially(messages)
        con_messages = [asdict(m) for m in self.messages_storage]
        functions_schemas = self._get_function_schemas_with_custom_description(functions)
        response = self.get_base_call_response(con_messages, functions_schemas)
        self._add_message(AssistantMessage(str(response.choices[0].message)))
        return self._handle_response_function_call_errors(module, response, max_retries,
                                                          lambda: self.get_custom_descr_function_call(module,
                                                                                                      functions,
                                                                                                      max_retries - 1))

    def get_forced_function_call(self, module: dict, function: Callable, max_retries: int = 3,
                                 messages: list[Message] = None):
        """ Get the response with forced function call
        :param module: Module containing the function
        :param function: Function to be called
        :param max_retries: Number of retries
        :param messages: List of messages to be sent to the model
        :return:
        """
        if messages:
            self._add_messages_initially(messages)
        con_messages = [asdict(m) for m in self.messages_storage]
        response = self.get_forced_call_response(con_messages, function, function.__name__)
        self._add_message(AssistantMessage(str(response.choices[0].message)))
        return self._handle_response_function_call_errors(module, response, max_retries,
                                                          lambda: self.get_forced_function_call(module, function,
                                                                                                max_retries - 1))

    def get_json_format_response(self, response_model: BaseModel, messages: list[Message] = None,
                                 max_retries=3) -> dict:
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
        schema = self._function_to_openai_function_schema(response_model)
        response = self.get_forced_call_response(messages, response_model, dict({"name": schema["name"]}))
        self._add_message(AssistantMessage(str(response)))
        try:

            parsed = self._repair_output_json(response.choices[0].message.function_call.arguments)
            return self._match_parameters(parsed, schema["name"], schema["parameters"]["required"])
        except Exception as e:
            return self._handle_call_exception(e, JSON_ERR, max_retries,
                                               lambda: self.get_json_format_response(response_model,
                                                                                     max_retries=max_retries - 1))

    def _get_function_schemas_with_custom_description(self, functions):
        functions_schemas = []
        for f, desc in functions:
            functions_schema = self._function_to_openai_function_schema(f)
            functions_schema["description"] = desc
            functions_schemas.append(functions_schema)
        return functions_schemas

    def _handle_response_function_call_errors(self, module, response, max_retries, handling_function):
        """ Handle the errors in the function call part of the response
        :param max_retries: Number of retries
        :param module: Module containing the functions
        :param response: Model response in API format
        :return:
        """
        if response.choices[0].message.function_call is None:
            return self._handle_call_exception("", NO_CALL_ERR, max_retries, handling_function)
        if max_retries > 0:
            return self._handle_function_call_return(handling_function, max_retries, module, response)
        logger.error(f"Max retries reached. Skipping.")
        return None

    def _handle_call_exception(self, e, error_text, max_retries, handling_function: Callable):
        if RECURSION_ERR in str(e):
            logger.error(f"Recursion error: {e}")
            return {}
        if API_ERR in str(e) or CONN_ERR in str(e):
            time.sleep(10)
            max_retries += 1
        if max_retries > 0:
            logger.error(f"{error_text}{e}. Retrying")
            self._add_message(UserMessage(f"{error_text}{e}. Retry."))
            return handling_function()
        logger.error(f"{error_text}{e}. Max retries reached. Skipping.")
        return {}

    def _handle_function_call_return(self, handling_function, max_retries, module, response):
        """
        Handle the return of the function call
        :param max_retries: Number of retries
        :param module: Module containing the functions
        :param response: Model response in API format
        :return:
        """
        name = None
        try:
            name, arguments = self._parse_function_call(module, response)
            if not name:
                self._add_message(UserMessage("Function name not found. Retry."))
                return self._handle_function_call_return_errors(handling_function, max_retries)
            if arguments:
                return module[name](**arguments)
            return module[name]()
        except RecursionError as e:
            logger.error(f"{e}")
            return
        except Exception as e:
            logger.error(f"Error calling function {name}: {e}")
            self._add_message(UserMessage(f"Error calling function {name}: {e}. Retry."))
            return self._handle_function_call_return_errors(handling_function, max_retries)

    @staticmethod
    def _handle_function_call_return_errors(handling_function, max_retries):
        if max_retries > 0:
            logger.error("Could not make function call, retrying.")
            return handling_function()
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

        function_arguments = self._repair_output_json(function_arguments)
        if "description" not in str(function_arguments):
            return self._fix_encoding(function_arguments)
        result = {}
        for key in function_arguments:
            result[key] = function_arguments[key].get("description", "")
        return self._fix_encoding(result)

    def _add_message(self, message: Message):
        """
        Add a message to the message storage
        :param message: Message to be added
        :return:
        """
        if len(self.messages_storage) > 10 or len(str(self.messages_storage)) > MAX_SIZE:
            self.messages_storage = self.messages_storage[:3]
        self.messages_storage.append(message)

    def _add_messages_initially(self, messages: list[Message]):
        """
        Add a list of messages to the message storage
        :param messages: List of messages to be added
        """
        self.messages_storage = []
        for m in messages:
            if isinstance(m, Message):
                self._add_message(m)

    @staticmethod
    def _repair_output_json(function_arguments) -> dict:
        try:
            function_arguments = dict(function_arguments)
        except Exception as e:
            logger.info("Error parsing function arguments to dictionary: %s. Handling.", e)
            a = function_arguments.replace('\n', ' ')
            a = a.replace('\"https\"', 'https')
            a = a.replace('None', '""')
            a = repair_json(a)
            function_arguments = dict(json.loads(a))
        return function_arguments

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
                    UserMessage(
                        f"Error: Parameter {arg} required but not found in call for function {function_name}. Retry."))
                return {}
            matched_args[arg] = received_arguments[arg] if received_arguments[arg] not in ["None", "null"] else ""
        redundant_args = [arg for arg in received_arguments if arg not in function_params]
        if redundant_args:
            self._add_message(UserMessage(f"Redundant arguments provided: {redundant_args}."))
        return matched_args

    @staticmethod
    def _does_function_exist(function_name: str, module: dict) -> bool:
        if function_name not in module:
            logger.error(f"Function {function_name} not found in the module.")
            return False
        return True

    @staticmethod
    def _get_func_name_and_descr_dict(function: Callable) -> dict:
        """
        Get the name and description of the function
        :param function: Function to be converted
        :return: dictionary containing the function name and description
        """
        try:
            return {FUNC_NAME: function.__name__, "description": function.__doc__}
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
            if m.is_user():
                return m
        return None

    @staticmethod
    def _get_function_params_dict(function: Callable) -> dict:
        sig = inspect.signature(function)
        params = {param.name: param.annotation.__name__ for param in sig.parameters.values()}
        return params
