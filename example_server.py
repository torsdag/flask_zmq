import time
import logging

import flask

import flask_zmq.server


def get_test_flask_app() -> flask.Flask:
    app = flask.Flask(__name__)

    @app.route("/test")
    def test():
        return "YO!"

    @app.route("/sleep")
    def sleep():
        time.sleep(1)
        return "OK"

    return app


app: flask.Flask = flask_zmq.server.wrap(get_test_flask_app())

if __name__ == "__main__":
    logging.warning(
        "please run with `gunicorn --workers 4 --worker-class gthread example_server:app` to enable keep-alive connections"
    )
    app.run(port=8000)
