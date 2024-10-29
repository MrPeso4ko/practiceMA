import dbm
import threading
from secrets import token_urlsafe
from urllib.parse import urlparse, parse_qs
from time import time, sleep

import uvicorn

PORT = 8000
BASE_URL = f"localhost:{PORT}/"  # replace to your URL shortener domain if needed

RPM = 10  # allowed number of requests per minute for user


class Storage:
    def __init__(self):
        self._dbm = dbm.open("dbm", "c")
        self._cache = {}

    def store(self, key, value):
        self._dbm[key] = value
        self._cache[key] = value

    def get(self, key):
        value = self._cache.get(key)
        if not value:
            value = self._dbm.get(key)
        return value

    def close(self):
        self._dbm.close()


class RequestCounter:
    def __init__(self):
        self.request_count = {}
        self._lock = threading.Lock()
        threading.Thread(target=self._cleaner, daemon=True).start()

    def _cleaner(self):
        while True:  # thread that cleans old requests
            sleep(60)
            self._clean()

    def _clean(self):
        cur_minute = int(time()) // 60

        with self._lock:
            keys = self.request_count.keys()

        for minute, user in keys:
            if minute + 1 < cur_minute:
                with self._lock:
                    self.request_count.pop((minute, user), None)

    def check_limits(self, client_id):
        cur_minute = int(time()) // 60
        with self._lock:
            if (cur_minute, client_id) in self.request_count:
                if self.request_count[(cur_minute, client_id)] >= RPM:
                    return False
                self.request_count[(cur_minute, client_id)] += 1
            else:
                self.request_count[(cur_minute, client_id)] = 1
        return True


class App:
    def __init__(self):
        self.storage = Storage()
        self.request_counter = RequestCounter()

    async def _return(self, scope, recieve, send, code, body, headers=None):
        if not headers:
            headers = []
        await send({
            "type": "http.response.start",
            "status": code,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            raise TypeError("Only http scope is supported")

        if scope["method"] != "GET":
            await self._return(scope, receive, send, code=405, body=b"Method not allowed\n")
            return

        client_id = scope["client"][0]
        if not self.request_counter.check_limits(client_id):
            await self._return(scope, receive, send, code=429, body=b"Too many requests\n")
            return

        path = scope.get("path", "/")
        if path.startswith("/shorten"):
            await self.shorten_link(scope, receive, send)
            return

        full_url = self.storage.get(path[1:])

        if not full_url:
            await self._return(scope, receive, send, code=404, body=b"Not Found\n")
            return

        await self._return(scope, receive, send, code=301, body=b"Moved permanently\n",
                           headers=[[b"Location", full_url.encode("utf-8")]])

    def _gen_short_link(self):
        token = token_urlsafe(6)
        # если будут коллизии то можно будет раскомментировать
        # while self.storage.get(token):
        #     token = token_urlsafe(6)
        return token

    async def shorten_link(self, scope, receive, send):
        params = parse_qs(scope.get("query_string", ""))
        if b'url' not in params:
            await self._return(scope, receive, send, code=400, body=b"Url not provided\n")
            return

        url = params[b'url'][0].decode("utf-8")

        # Проверка на валидный URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                await self._return(scope, receive, send, code=400, body=b"Url is not valid\n")
                return
        except AttributeError:
            await self._return(scope, receive, send, code=400, body=b"Url is not valid\n")
            return

        short_link = self._gen_short_link()

        self.storage.store(short_link, url)
        full_short_link = f'{BASE_URL}{short_link}'

        await self._return(scope, receive, send, code=200, body=full_short_link.encode("utf-8"))

    def close_resources(self):
        self.storage.close()


app = App()

if __name__ == '__main__':
    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    finally:
        app.close_resources()
