from configparser import ConfigParser

from src.constants import CONSTANTS_CONFIG_PATH

_config = ConfigParser()
_config.read(CONSTANTS_CONFIG_PATH)
_config_csv_paths = _config['CSV_PATHS']

RECORD_TYPES_CSV = _config_csv_paths['RECORD_TYPES_CSV']
CONTENT_TYPES_CSV = _config_csv_paths['CONTENT_TYPES_CSV']
SOURCES_CSV = _config_csv_paths['SOURCES_CSV']
BANNED_SOURCES_CSV = _config_csv_paths['BANNED_SOURCES_CSV']
PARSED_SOURCES_CSV = _config_csv_paths['PARSED_SOURCES_CSV']
