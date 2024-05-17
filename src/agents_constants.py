import os
from configparser import ConfigParser

from src.agents.llama_api_agent import LlamaApiAgent
from src.agents.local_api_agent import LocalApiAgent
from src.agents.openai_api_agent import OpenAIApiAgent
from src.constants import CONSTANTS_CONFIG_PATH

_config = ConfigParser()
_config.read(CONSTANTS_CONFIG_PATH)
_config_apis = _config['API_INFOS']

LLAMA_URL = str(_config_apis['LLAMA_URL'])
LLAMA_KEY = os.getenv('LLAMA_API_KEY')

OPENAI_URL = str(_config_apis['OPENAI_URL'])
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

LOCAL_URL = str(_config_apis['LOCAL_URL'])
LOCAL_KEY = os.getenv('LOCAL_API_KEY')

LLAMA3_70 = "llama3:70b"
LLAMA3_8 = "llama3"
MIXTRAL = "mixtral"
GPT_3 = "gpt-3.5-turbo-1106"  # "gpt-3.5-turbo-0125" seems to have issues lately
LLAMA3_70_API = "llama3-70b"

LLAMA3_70_AGENT = LocalApiAgent(LOCAL_URL, LOCAL_KEY, LLAMA3_70)
LLAMA3_8_AGENT = LocalApiAgent(LOCAL_URL, LOCAL_KEY, LLAMA3_8)
MIXTRAL_AGENT = LocalApiAgent(LOCAL_URL, LOCAL_KEY, MIXTRAL)
GPT_3_AGENT = OpenAIApiAgent(OPENAI_URL, OPENAI_KEY, GPT_3)
LLAMA3_70_API_AGENT = LlamaApiAgent(LLAMA_URL, LLAMA_KEY, LLAMA3_70)
