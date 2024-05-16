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
