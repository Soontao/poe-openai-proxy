from threading import Lock, Condition
from poe import Client
import os


class ResourcePool:
    def __init__(self):
        self.pool = []
        self.lock = Lock()
        self.cond = Condition()

    def make_resource(self, token):
        """make new resource into pool"""
        with self.cond:
            if len(list(filter(lambda c: c.token == token, self.pool))) > 0:
                return
            self.pool.append(_get_client(token))
            self.cond.notify()

    def get_resource(self):
        with self.cond:
            if len(self.pool) == 0:
                # wait return at least one resource
                self.cond.wait()
            return self.pool.pop()

    def release_resource(self, resource):
        with self.cond:
            self.pool.append(resource)
            self.cond.notify()


class Resource:
    def __init__(self, pool: ResourcePool):
        self.pool = pool

    def __enter__(self) -> Client:
        self.resource = self.pool.get_resource()
        return self.resource

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.resource != None:
            self.pool.release_resource(self.resource)


global_pool = ResourcePool()


def _get_client(token: str) -> Client:
    proxy = os.environ.get("PROXY", None)
    c = Client(token, proxy=proxy)
    c.token = token
    return c


def _register_token(token: str):
    global_pool.make_resource(token)


def poe_client():
    return Resource(global_pool)


if "POE_KEYS" in os.environ.keys():
    import json
    import threading

    for token in json.loads(os.environ.get("POE_KEYS")):
        threading.Thread(target=lambda: global_pool.make_resource(token)).start()
