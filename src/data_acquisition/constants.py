import ast
from configparser import ConfigParser

from src.constants import CONSTANTS_CONFIG_PATH

_config = ConfigParser()
_config.read(CONSTANTS_CONFIG_PATH)
CONTENT_SUBSTRINGS = ast.literal_eval(_config['CONTENT_RETRIEVAL']["CONTENT_SUBSTRINGS"])

FORCED_TAGS = ['body', 'main', 'html']

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
DATE_SCRAPED = 'date_scraped'
BANNED = 'banned'
CRAWL_ONLY = 'crawl_only'
PARENT = 'parent'
TYPE = 'record_type'
TYPE_ID = 'type_id'
UPDATE_INTERVAL = 'update_interval'

SYSTEM = "system"
USER = "user"
