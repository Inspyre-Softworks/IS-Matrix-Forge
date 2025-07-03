from typing import Optional, Type
from .message import Message


class Request(Message):
    answer_type: Optional[Type["Answer"]] = None
    response_size: Optional[int] = None    # default size; can override per-request

