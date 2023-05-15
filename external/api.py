import poe
import os
import sys
import uuid
import json
import time
from werkzeug.exceptions import HTTPException
from flask import Flask, request, stream_with_context, Response
from poe import Client


proxy = os.environ.get("PROXY", None)
default_bot = os.environ.get("DEFAULT_BOT", "a2")
timeout = int(os.environ.get("TIMEOUT", '30'), 10)
app = Flask(__name__)

clients = {}


def _get_client(token: str) -> Client:
  app.logger.info("Connecting to poe...")
  return poe.Client(token, proxy=proxy)


def _register_token(token: str) -> Client:
  if token not in clients.keys():
    c = _get_client(token)
    clients[token] = c
    app.logger.info(
        "register client for token xxxx{}xxxx successful".format(token[4:-4]))
    return c
  else:
    return clients.get(token)


def _get_req_config():
  bot = request.values.get('bot', default_bot)
  token = request.values.get('token')
  content = request.values.get("content")
  return token, bot, content


@app.route('/', methods=['GET'])
def index():
  return {'service': 'poe-api', 'status': 'alive'}


@app.route('/register_token', methods=['GET', 'POST'])
def register_token():
  token = request.values.get('token')
  status = 304
  if token not in clients.keys():
    status = 201
    _register_token(token)
  return Response({'status': 'successful'}, status=status)


@app.route('/ask', methods=['GET', 'POST'])
def ask():
  token, bot, content = _get_req_config()
  client = _register_token(token)
  for chunk in client.send_message(bot, content, with_chat_break=True, timeout=timeout):
    pass
  return Response(chunk["text"].strip(), content_type="text/plain")


@app.route('/ask_stream', methods=['GET', 'POST'])
def ask_stream():
  token, bot, content = _get_req_config()
  client = _register_token(token)

  @stream_with_context
  def generate_response():
    for chunk in client.send_message(bot, content, with_chat_break=True, timeout=timeout):
      yield chunk["text_new"]

  return Response(generate_response(), content_type="text/plain")


@app.post('/chat/completions')
def chat_completion():
  token = request.headers.get("authorization").removeprefix("Bearer ")
  client = _register_token(token)
  body = request.get_json()
  messages = body.get('messages')
  stream = body.get("stream", False)
  content = "\n".join(
      map(lambda m: "{}: {}".format(m.get("role"), m.get("content")), messages))

  if stream:
    def stream():
      for chunk in client.send_message(default_bot, content, with_chat_break=True, timeout=timeout):
        yield chunk["text_new"]
    return Response(stream(), mimetype='text/event-stream')

  else:
    for chunk in client.send_message(default_bot, content, with_chat_break=True, timeout=timeout):
      pass
    return {
        "id": uuid.uuid4(),
        "object": "chat.completion",
        "created": int(time.time_ns()),
        "model": default_bot,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": chunk['text'].strip()
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }


@app.errorhandler(HTTPException)
def handle_exception(e):
  """Return JSON instead of HTML for HTTP errors."""
  # start with the correct headers and status code from the error
  response = e.get_response()
  # replace the body with JSON
  response.data = json.dumps({
      "code": e.code,
      "name": e.name,
      "description": e.description,
  })
  response.content_type = "application/json"
  return response


if __name__ == '__main__':
  app.run(host="0.0.0.0")
