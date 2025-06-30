from typing import List, Optional


class Message:
    def to_bytes(self) -> bytes:
        raise NotImplementedError()

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Message':
        raise NotImplementedError()


class Request(Message):
    pass


class Answer(Message):
    pass
