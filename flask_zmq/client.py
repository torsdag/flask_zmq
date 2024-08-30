import logging
import typing

import zmq
import zmq.asyncio

from flask_zmq._types import Request, Response

ctx: zmq.asyncio.Context = zmq.asyncio.Context()
logger: logging.Logger = logging.getLogger(__name__)


class ZMQAsyncSession:
    def __init__(self, endpoint: str, timeout_ms: int = 5000, retry_count: int = 3):
        self.endpoint: str = endpoint
        self.timeout_ms: int = timeout_ms
        self.retry_count: int = retry_count

        self.socket: zmq.asyncio.Socket = self._connect()

    def _connect(self) -> zmq.asyncio.Socket:
        socket: zmq.asyncio.Socket = ctx.socket(zmq.REQ)
        socket.connect(self.endpoint)

        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)

        return socket

    def _reconnect(self) -> zmq.asyncio.Socket:
        self.socket.close()
        return self._connect()

    async def request(self, request: Request) -> Response:
        for _ in range(self.retry_count):
            try:
                self.socket.send(request.model_dump_json().encode())

                return Response.model_validate_json((await self.socket.recv()).decode())

            except zmq.error.Again as e:
                logger.error(
                    f"Timeout on request {request}, retrying. Attempt {_ + 1} of {self.retry_count}: {e}"
                )

                self.socket = self._reconnect()

        return Response(status_code=500, headers={}, data="")

    async def get(
        self,
        url: str,
        headers: dict[str, str] = None,
        params: dict[str, str] = None,
        data: str = None,
    ) -> Response:
        return await self.request(
            Request(
                url=url,
                method="GET",
                headers=headers or {},
                params=params or {},
                data=data or "",
            )
        )

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: typing.Any | None = None,
    ) -> None:
        self.socket.close()
