import inspect
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
import instructor
from langchain_core.utils.function_calling import convert_to_openai_tool
from openai import OpenAI
from pydantic import BaseModel


@dataclass
class Message:
    role: str
    content: str


class ApiAgent(ABC):
    """Base class for API agents that interact through the OpenAI API."""

    def __init__(self, url, api_key, model_name):
        """
        Initialize the API agent
        :param url: API url
        :param api_key: API key for the service
        :param model_name: Name of the model to be used
        """
        self.client = OpenAI(api_key=api_key, base_url=url)
        self.model_name = model_name

    def get_function_call_response(self, module: dict, functions: list, messages: list[Message]):
        """
        Instruct the model to call a function and get the result of the function call
        :param module: Module containing the functions
        :param functions: List of functions to chosen from
        :param messages: List of messages to be sent to the model
        :return: result of called function
        """
        messages = [asdict(m) for m in messages]
        openai_functions = [self._transfer_function_to_openai_function_schema(f) for f in functions]
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            functions=openai_functions,
            stream=False
        )
        return self._parse_function_call(module, response)

    @abstractmethod
    def _parse_function_call(self, module: dict, response):
        """
        Parse the response from the model to get the function call
        :param module: Module containing the function
        :param response: Model response in API format
        :return: result of called function
        """
        pass

    @staticmethod
    def _get_function_parameters(module: dict, func_name):
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
            return []

    @abstractmethod
    def get_json_format_response(self, response_model: BaseModel, messages: list[Message]) -> dict:
        """
        Get the response in desired JSON format
        :param response_model: Desired response model
        :param messages: List of messages to be sent to the model
        :return: dictionary containing the formatted response
        """
        pass

    @staticmethod
    def _transfer_function_to_openai_function_schema(function) -> dict:
        """
        Convert the function to OpenAI function schema
        :param function: Function to be converted
        :return: dictionary containing the function schema
        """
        return dict(convert_to_openai_tool(function)["function"])


class LlamaApiAgent(ApiAgent):

    def _parse_function_call(self, module: dict, response):
        """
        Parse the response from the model to get the function call
        :param module: Module containing the function
        :param response: Model response in API format
        :return: result of called function
        """
        function_name = response.choices[0].message.function_call.name
        if not self._get_function_parameters(module, function_name):
            return module[function_name]()
        function_arguments = self._parse_function_arguments(response.choices[0].message.function_call.arguments)
        return module[function_name](**function_arguments)

    @staticmethod
    def _parse_function_arguments(function_arguments: dict) -> dict:
        """
        Parse the individual function arguments from the response
        :param function_arguments: Unparsed function arguments in JSON string format
        :return: dictionary containing the parsed function arguments
        """
        # a = str(function_arguments)
        # a = a.replace('\"https\"', 'https')
        # a = a.replace('None', '""')
        # data = json.loads(a)
        function_arguments = dict(function_arguments)
        result = {}
        for key in function_arguments:
            result[key] = function_arguments[key].get("description", "")
        return result

    def get_json_format_response(self, response_model: BaseModel, messages: list[Message]) -> dict:
        """
        Get the response in desired JSON format
        :param response_model: Desired response model
        :param messages: List of messages to be sent to the model
        :return: dictionary containing the formatted response
        """
        messages = [asdict(m) for m in messages]
        schema = self._transfer_function_to_openai_function_schema(response_model)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            functions=[schema],
            function_call=dict({"name": schema["name"]}),
            stream=False
        )
        return dict(response.choices[0].message.function_call.arguments)


class OpenAIApiAgent(ApiAgent):

    def _parse_function_call(self, module: dict, response):
        """
        Parse the response from the model to get the function call
        :param module: Module containing the function
        :param response: Model response in API format
        :return: result of called function
        """
        function_name = response.choices[0].message.function_call.name
        if not self._get_function_parameters(module, function_name):
            return module[function_name]()
        function_arguments = response.choices[0].message.function_call.arguments
        return module[function_name](**function_arguments)

    def get_json_format_response(self, response_model: BaseModel, messages: list[Message]) -> dict:
        """
        Get the response in desired JSON format
        :param response_model: Desired response model
        :param messages: List of messages to be sent to the model
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
            max_retries=10
        )
        return dict(response)
