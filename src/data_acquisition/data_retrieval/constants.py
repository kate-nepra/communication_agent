import ast
from configparser import ConfigParser

from src.constants import CONSTANTS_CONFIG_PATH

EXCLUDE_TAGS_BASE = [
    'img', 'style', 'script', 'svg', 'canvas', 'video', 'audio', 'iframe', 'embed', 'object', 'param', 'source',
    'track', 'map', 'area', 'math', 'use', 'noscript', 'del', 'ins', 'picture', 'figure', 'footer', 'aside', 'form',
    'input', 'button', 'select', 'textarea', 'label', 'fieldset', 'legend', 'datalist', 'optgroup', 'option', 'output',
    'progress', 'meter', 'details', 'summary', 'caption', 'colgroup', 'col', 'meta', 'head', 'cite', 'abbr', 'acronym',
]

DECOMPOSE_PATTERNS_BASE = [".*accessibility.*", ".*cookie.*", ".*social.*", ".*share.*", ".*footer.*", ".*search.*",
                           ".*intro__scroll.*", ".*vhide.*", ".*icon.*", ".*logo.*", ".*btn.*", ".*img.*", ".*image.*",
                           ".*f-std.*", ".*screen-reader.*", ".*lang.*", ".*login.*", ".*register.*", ".*noprint.*",
                           ".*hidden.*", ".*accordion.*", ".*actions.*", ".*jump.*", ".*shop.*", ".*cart.*",
                           ".*citation.*", ".*privacy.*"]

WIKI_SPECIFIC = [".*ib-settlement-caption.*", ".*wikitable.*", ".*Gallery.*", ".*toccolours.*", ".*References.*",
                 ".*Notes.*", ".*Further reading.*", ".*External links.*", ".*See_also.*", ".*Coordinates.*",
                 ".*Authority control.*", ".*Bibliography.*"]

_config = ConfigParser()
_config.read(CONSTANTS_CONFIG_PATH)
BANNED_SUBSTRINGS = ast.literal_eval(_config['CONTENT_RETRIEVAL']["BANNED_SUBSTRINGS"])
PDF_FOLDER = _config['PDF_FOLDER']['PDF_FOLDER']
