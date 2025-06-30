from typing import Optional
from datetime import datetime


class Message:
    def to_bytes(self) -> bytes:
        raise NotImplementedError()

    @classmethod
    def from_bytes(cls, data: bytes, sent_at: Optional[datetime] = None, received_at: Optional[datetime] = None) -> "Message":
        # Parse data into an Answer (can use timestamps)
        raise NotImplementedError()

