BANNED_SUBSTRS = ['facebook', 'jobs', 'goout', 'mailto', 'twitter', 'instagram', 'linkedin', 'google', 'shop',
                  '/partners', 'cat=', 'view=', 'search=', 'youtu', 'obchod', 'flickr', 'brno-phenomenon', 'apple',
                  'phaenomen-bruenn', 'fenomen-brno', 'weblist-mzm', 'netscout', '/careers', '/kariera', 'gle', '/de/',
                  'newsletter', 'blog/page', 'kamera']

ROOT = 'root'

DATE_FORMAT = 'YYYY-MM-DD'

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

RECORD_TYPE_LABELS = ['place', 'event', 'administration', 'static']

BRNO_SUBSTRS = ['Brno', 'brno', 'BRNO', 'Brně', 'Brnu', 'Brnem']
FORCED_TAGS = ['body', 'main', 'html']

MAX_SIZE = 2500

PDF_FOLDER = "./../pdfs"
RECORD_TYPES_CSV = './../data/record_types.csv'
CONTENT_TYPES_CSV = './../data/content_types.csv'
SOURCES_CSV = './../data/sources.csv'
BANNED_SOURCES_CSV = './../data/banned_sources.csv'
PARSED_SOURCES_CSV = './../data/parsed_sources.csv'
