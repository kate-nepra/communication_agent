import os
from configparser import ConfigParser
from datetime import datetime

import arrow
from dotenv import load_dotenv

load_dotenv()

CONSTANTS_CONFIG_PATH = '/home/rinaen/PycharmProjects/communication_agent/cfg/constants.ini'
DATE_FORMAT = 'YYYY-MM-DD'
DATETIME_FORMAT = 'YYYY-MM-DDTHH:mm:ss'
TODAY = arrow.now().format(DATE_FORMAT)
TOMORROW = arrow.now().shift(days=1).format(DATE_FORMAT)
WEEKDAY = datetime.now().strftime('%A')
MAX_SIZE = 2500

_config = ConfigParser()
_config.read(CONSTANTS_CONFIG_PATH)
_config_csv_paths = _config['API_INFOS']

LLAMA_URL = str(_config_csv_paths['LLAMA_URL'])
LLAMA_KEY = os.getenv('LLAMA_API_KEY')

OPENAI_URL = str(_config_csv_paths['OPENAI_URL'])
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

LOCAL_URL = str(_config_csv_paths['LOCAL_URL'])
LOCAL_KEY = os.getenv('LOCAL_API_KEY')
