from datetime import datetime
from typing import ByteString, Optional
from .message import Message


class Answer(Message):
    __slots__ = (
        '__raw_data',
        '__received_at',
        '__sent_at',
        '__rtt'
    )
