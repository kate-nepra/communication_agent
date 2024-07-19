from dataclasses import dataclass


@dataclass
class Duration:
    """ Format for event duration. Field "end" is optional, it is used for period of time (that are two dates from-to). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time."""
    start: str
    end: str = None


@dataclass
class BaseSchema:
    """ Base schema for all entities """
    header: str
    record_type: str
    brief: str
    text: str
    url: str
    date_fetched: str
    address: str = None

    def asdict(self):
        return self.__dict__


@dataclass
class EventSchema(BaseSchema):
    """ Event schema for events """
    dates: list = None
