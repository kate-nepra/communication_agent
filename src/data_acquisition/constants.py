import ast
from configparser import ConfigParser

from src.constants import CONSTANTS_CONFIG_PATH

_config = ConfigParser()
_config.read(CONSTANTS_CONFIG_PATH)
CONTENT_SUBSTRINGS = ast.literal_eval(_config['CONTENT_RETRIEVAL']["CONTENT_SUBSTRINGS"])

FORCED_TAGS = ['body', 'main', 'html']
BASE_URL = 'gotobrno'
ADDRESS = 'address'
DEFAULT_ADDRESS = 'Brno, Czech Republic'
DATES_EXAMPLE = '[{"start": "2024-01-11"}, {"start": "2024-01-14 15:00"}, {"start": "2024-01-31 15:00", "end": "2024-02-14"}]'
DATES_FORMAT_EXAMPLE = 'dates=[{"start": start_date, "end": end_date}]'

PLACE = 'place'
EVENT = 'event'
ADMINISTRATION = 'administration'
STATIC = 'static'
PDF = 'pdf'
RECORD_TYPE_LABELS = [PLACE, EVENT, ADMINISTRATION, STATIC, PDF]

ROOT = 'root'
ID = 'id'
URL = 'url'
DATE_ADDED = 'date_added'
DATE_PARSED = 'date_parsed'
BANNED = 'banned'
CRAWL_ONLY = 'crawl_only'
PARENT = 'parent'
TYPE = 'record_type'
TYPE_IDS = 'type_ids'
UPDATE_INTERVAL = 'update_interval'
ENCODED_CONTENT = 'encoded_content'

SYSTEM = "system"
USER = "user"
ASSISTANT = "assistant"
