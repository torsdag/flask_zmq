import sys
import threading
import asyncio
import logging

import uvloop
import anyio
import flask
import zmq.asyncio

from flask_zmq._types import Request, Response


ctx: zmq.asyncio.Context = zmq.asyncio.Context()
logger: logging.Logger = logging.getLogger(__name__)


def handle_request(app: flask.Flask, request: Request) -> Response:
    with app.test_request_context(
        request.url,
        method=request.method,
        headers=request.headers,
    ):
        return Response.from_flask_response(app.full_dispatch_request())


async def worker(
    queue_: asyncio.Queue, socket: zmq.asyncio.Socket, app: flask.Flask
) -> None:
    while True:
        message: list[bytes] = await queue_.get()
        request: Request = Request.model_validate_json(message[-1])
        response: Response = await anyio.to_thread.run_sync(
            handle_request, app, request
        )

        queue_.task_done()

        await socket.send_multipart(
            message[:-1] + [response.model_dump_json().encode()]
        )


async def serve_flask_app(
    app: flask.Flask, port: int = 5005, concurrency: int = 10
) -> None:
    logger.info(f"Starting zmq app on port {port} with concurrency {concurrency}")

    socket: zmq.asyncio.Socket = ctx.socket(zmq.ROUTER)
    poller: zmq.asyncio.Poller = zmq.asyncio.Poller()

    try:
        socket.bind(f"tcp://*:{port}")
        poller.register(socket, zmq.POLLIN)

    except zmq.error.ZMQError as e:

        return

    logger.info(f"ZMQ app started on port {port}")

    async with anyio.create_task_group() as task_group:

        queue: asyncio.Queue = asyncio.Queue()

        for _ in range(concurrency):
            task_group.start_soon(worker, queue, socket, app)

        while True:
            events = await poller.poll()
            for active_socket, event in events:
                if event == zmq.POLLIN:
                    await queue.put(
                        await active_socket.recv_multipart(),
                    )


def wrap(
    app: flask.Flask,
    port: int = 6000,
    concurrency: int = 10,
    loop: asyncio.AbstractEventLoop | None = None,
) -> asyncio.AbstractEventLoop:
    if loop is None:
        loop = uvloop.new_event_loop()

    if not loop.is_running():

        def start_loop(loop_: asyncio.AbstractEventLoop):
            asyncio.set_event_loop(loop_)
            loop_.run_forever()

        threading.Thread(target=start_loop, args=(loop,), daemon=True).start()

    asyncio.run_coroutine_threadsafe(serve_flask_app(app, port, concurrency), loop)

    return app
