from __future__ import annotations
import serial
from serial.serialutil import SerialTimeoutError
from typing import Optional
from datetime import datetime


class SerialExchange:
    def __init__(
            self,
            port:            str,
            baudrate:        int = 115200,
            default_timeout: float = 1.0
    ):
        self.port:     str = port
        self.baudrate: int = baudrate
        self.default_timeout = default_timeout

    def send(
            self,
            request: Request,
            timeout: Optional[float] = None
    ) -> Optional[Answer]:
        answer_cls = getattr(request, 'answer_type', None)
        resp_size = getattr(request, 'response_size', 32)

        timeout = timeout if timeout is not None else self.default_timeout

        cmd_bytes = request.to_bytes()
        print(f"[SerialExchange] Sending: {list(cmd_bytes)} ({[f'0x{b:02X}' for b in cmd_bytes]})")

        sent_at = datetime.now()
        with serial.Serial(self.port, self.baudrate, timeout=timeout) as s:
            s.write(cmd_bytes)

            if answer_cls is not None:
                s.flush()
                s.timeout   = timeout
                response    = s.read(resp_size)
                received_at = datetime.now()

                if not response:
                    raise SerialTimeoutError(f"No response received for {request.__class__.__name__} within {timeout} seconds.')

                return answer_cls.from_bytes(response, sent_at, received_at)

        return None
