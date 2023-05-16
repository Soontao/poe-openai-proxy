import os
import sys
import uuid
import json
import time
import tiktoken
from openai_data import build_chunk_data, build_chat_comp_data
from werkzeug.exceptions import HTTPException
from flask import Flask, request, stream_with_context, Response
from poe_utils import _get_client, _register_token, poe_client

tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
default_bot = os.environ.get("DEFAULT_BOT", "a2")
timeout = int(os.environ.get("TIMEOUT", "30"), 10)
app = Flask(__name__)


def _uuid():
    return "poe_{}".format(str(uuid.uuid4()))


def _now():
    return int(time.time() * 1000)


def _get_req_config():
    bot = request.values.get("bot", default_bot)
    content = request.values.get("content")
    return bot, content


@app.route("/", methods=["GET"])
def index():
    return {"service": "poe-api", "status": "alive"}


@app.route("/register_token", methods=["GET", "POST"])
def register_token():
    token = request.values.get("token")
    status = 304
    if token not in clients.keys():
        status = 201
        _register_token(token)
    return Response({"status": "successful"}, status=status)


@app.route("/ask", methods=["GET", "POST"])
def ask():
    bot, content = _get_req_config()
    with poe_client() as client:
        for chunk in client.send_message(
            bot, content, with_chat_break=True, timeout=timeout
        ):
            pass
        return Response(chunk["text"].strip(), content_type="text/plain")


@app.route("/ask_stream", methods=["GET", "POST"])
def ask_stream():
    bot, content = _get_req_config()

    with poe_client() as client:

        @stream_with_context
        def generate_response():
            for chunk in client.send_message(
                bot, content, with_chat_break=True, timeout=timeout
            ):
                yield chunk["text_new"]

        return Response(generate_response(), content_type="text/plain")


@app.post("/v1/completions")
def completion():
    token = request.headers.get("authorization").removeprefix("Bearer ")
    client = _register_token(token)
    body = request.get_json()
    prompt = body.get("prompt")
    stream = body.get("stream", False)
    model = body.get("model", default_bot)
    id = _uuid()
    created = _now()
    with poe_client() as client:
        if stream:

            def stream():
                for chunk in client.send_message(
                    default_bot, content, with_chat_break=True, timeout=timeout
                ):
                    delta_content = json.dumps(
                        build_chunk_data(id, created, model, chunk["text_new"])
                    )
                    yield "data: {}\r\n\r\n".format(delta_content)
                yield "data: [DONE]\r\n\r\n"

            return Response(stream(), mimetype="text/event-stream")

        else:
            for chunk in client.send_message("capybara", message):
                pass
            text = chunk["text"].strip()
            prop_len = len(tiktoken_encoding.encode(prompt))
            comp_len = len(tiktoken_encoding.encode(text))
            total_tokens = comp_len + prop_len

            return build_comp_data(
                id, created, model, text, prop_len, comp_len, total_tokens
            )


@app.post("/v1/chat/completions")
def chat_completion():
    body = request.get_json()
    messages = body.get("messages")
    model = body.get("model", default_bot)
    stream = body.get("stream", False)
    content = "\n".join(
        map(lambda m: "{}: {}".format(m.get("role"), m.get("content")), messages)
    )
    id = _uuid()
    created = _now()

    with poe_client() as client:
        if stream:

            def stream():
                for chunk in client.send_message(
                    default_bot, content, with_chat_break=True, timeout=timeout
                ):
                    delta_content = json.dumps(
                        build_chunk_data(id, created, model, chunk["text_new"])
                    )
                    yield "data: {}\r\n\r\n".format(delta_content)
                yield "data: [DONE]\r\n\r\n"

            return Response(stream(), mimetype="text/event-stream")

        else:
            for chunk in client.send_message(
                default_bot, content, with_chat_break=True, timeout=timeout
            ):
                pass
            resp_content = chunk["text"].strip()
            prompt_tokens = len(tiktoken_encoding.encode(content))
            completion_tokens = len(tiktoken_encoding.encode(resp_content))

            return build_chat_comp_data(
                id, created, model, resp_content, prompt_tokens, completion_tokens
            )


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps(
        {
            "code": e.code,
            "name": e.name,
            "description": e.description,
        }
    )
    response.content_type = "application/json"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0")
