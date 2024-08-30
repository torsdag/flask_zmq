import time
import asyncio

import anyio
import httpx

from flask_zmq.client import ZMQAsyncSession


async def request_zmq(count: int):
    async with ZMQAsyncSession("tcp://localhost:6000") as client:
        for i in range(count):
            response = await client.get("http://localhost:5000/test")

            if response.status_code != 200:
                raise Exception(f"Request failed: {response}")


async def request_httpx(count: int):
    async with httpx.AsyncClient() as client:

        for i in range(count):
            response = await client.get("http://localhost:8000/test")

            if response.status_code != 200:
                raise Exception(f"Request failed: {response}")


async def request_httpx_keep_alive_disabled(count: int):
    async with httpx.AsyncClient() as client:
        client.headers["Connection"] = "close"

        for i in range(count):
            response = await client.get("http://localhost:8000/test")

            if response.status_code != 200:
                raise Exception(f"Request failed: {response}")


async def benchmark(count: int = 1000):
    for concurrency in (
        1,
        2,
        4,
        8,
    ):
        print("Concurrency", concurrency)

        for bench in (
            request_zmq,
            request_httpx,
            request_httpx_keep_alive_disabled,
        ):
            async with anyio.create_task_group() as task_group:
                t = time.time()

                for _ in range(concurrency):
                    task_group.start_soon(bench, count)

            print(
                count * concurrency,
                "\t",
                "requests",
                time.time() - t,
                "\t",
                bench.__name__,
            )


asyncio.run(benchmark())
