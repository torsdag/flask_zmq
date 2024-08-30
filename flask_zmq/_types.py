import typing

import flask
import pydantic


class Request(pydantic.BaseModel):
    url: str
    method: str

    params: dict[str, str]
    headers: dict[str, str]

    data: typing.Any


class Response(pydantic.BaseModel):
    status_code: int
    headers: dict[str, str]
    data: typing.Any

    @classmethod
    def from_flask_response(cls, response: flask.Response) -> "Response":
        return cls(
            status_code=response.status_code,
            headers=dict(response.headers),
            data=response.data,
        )
