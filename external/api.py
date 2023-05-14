import poe
import envtoml as toml
import os
import sys
from flask import Flask, request, stream_with_context, Response
from flask_sock import Sock
from poe import Client

poe.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 "
                  "Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": "\"Chromium\";v=\"112\", \"Google Chrome\";v=\"112\", \"Not:A-Brand\";v=\"99\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Upgrade-Insecure-Requests": "1"
}

file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)
config_path = os.path.join(file_dir, "..", "config.toml")
config = toml.load(config_path)
proxy = config["proxy"]
timeout = config["timeout"]

def get_client(token) -> Client:
    print("Connecting to poe...")
    client_poe = poe.Client(token, proxy=None if proxy == "" else proxy)
    return client_poe

app = Flask(__name__)
sock = Sock(app)
sock.init_app(app)
client_dict = {}

def _register_token(token): 
    if token not in client_dict.keys():
        try:
            c = get_client(token)
            client_dict[token] = c
            return "ok"
        except Exception as exception:
            print("Failed to connect to poe due to " + str(exception))
            return "failed: " + str(exception)
    else:
        return "exist"

@app.route('/add_token', methods=['GET', 'POST'])
def add_token():
    token = request.values['token']
    return _register_token(token)


@app.route('/ask', methods=['GET', 'POST'])
def ask():
    token = request.values['token']
    bot = request.values['bot']
    content = request.values['content']
    _register_token(token)
    client = client_dict[token]
    for chunk in client.send_message(bot, content, with_chat_break=True, timeout=timeout):
        pass
    return Response(chunk["text"].strip(), content_type="text/plain")

@app.route('/ask_stream', methods=['GET', 'POST'])
def ask_stream():
    token = request.values['token']
    bot = request.values['bot']
    content = request.values['content']
    _register_token(token)
    client = client_dict[token]

    @stream_with_context
    def generate():
        for chunk in client.send_message(bot, content, with_chat_break=True, timeout=timeout):
            yield chunk["text_new"]

    return Response(generate(), content_type="text/plain")


@sock.route('/stream')
def stream(ws):
    token = ws.receive()
    bot = ws.receive()
    content = ws.receive()
    _register_token(token)
    client = client_dict[token]
    for chunk in client.send_message(bot, content, with_chat_break=True, timeout=timeout):
        ws.send(chunk["text_new"])
    ws.close()


if __name__ == '__main__':
    app.run(host="0.0.0.0")
