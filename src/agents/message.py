from abc import ABC
from dataclasses import dataclass

from src.data_acquisition.constants import USER, ASSISTANT, SYSTEM


def message_from_dict(data):
    role = data.get("role")
    if role == USER:
        return UserMessage(data.get("content"))
    elif role == ASSISTANT:
        return AssistantMessage(data.get("content"))
    elif role == SYSTEM:
        return SystemMessage(data.get("content"))
    else:
        raise ValueError(f"Unknown role: {role}")


@dataclass
class Message(ABC):
    role: str
    content: str

    def as_dict(self):
        return {"role": self.role, "content": self.content}

    def is_user(self):
        return self.role == USER

    def is_assistant(self):
        return self.role == ASSISTANT

    def is_system(self):
        return self.role == SYSTEM


class UserMessage(Message):
    def __init__(self, content: str):
        super().__init__(USER, content)


class AssistantMessage(Message):
    def __init__(self, content: str):
        super().__init__(ASSISTANT, content)


class SystemMessage(Message):
    def __init__(self, content: str):
        super().__init__(SYSTEM, content)
