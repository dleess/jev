#!/usr/bin/env python3
"""TypeSafe key pool: local proxy that rotates API keys on 429.
Clients set TYPESAFE_BASE_URL=http://127.0.0.1:8790; the key a client sends is tried first, then the rest."""
import sys, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = "https://api.typesafe.ai"
KEYS = [k.strip() for k in (Path.home() / ".config/typesafe/keys").read_text().splitlines() if k.strip()]
HOP = {"host", "authorization", "content-length", "connection", "transfer-encoding", "accept-encoding"}


def forward(method, path, headers, body, key):
    h = {k: v for k, v in headers.items() if k.lower() not in HOP}
    h["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(UPSTREAM + path, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


class H(BaseHTTPRequestHandler):
    def _proxy(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        sent = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        order = ([sent] if sent in KEYS else []) + [k for k in KEYS if k != sent]
        for i, key in enumerate(order):
            status, hdrs, data = forward(self.command, self.path, self.headers, body, key)
            if status != 429 or i == len(order) - 1:
                break
            print(f"429 on key #{KEYS.index(key)+1}, trying next", file=sys.stderr)
        self.send_response(status)
        for k, v in hdrs.items():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = _proxy
    log_message = lambda self, *a: None


def selftest():
    import json, threading, http.client
    global forward, KEYS
    KEYS = ["A", "B"]
    calls = []
    def fake(method, path, headers, body, key):
        calls.append(key)
        return (429 if key == "A" else 200), {"Content-Type": "application/json"}, json.dumps({"key": key}).encode()
    forward = fake
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = http.client.HTTPConnection("127.0.0.1", srv.server_port)
    c.request("POST", "/v1/systemone", body=b"{}", headers={"Authorization": "Bearer A", "Content-Type": "application/json"})
    r = c.getresponse(); out = json.loads(r.read())
    assert r.status == 200 and out == {"key": "B"} and calls == ["A", "B"], (r.status, out, calls)
    print("selftest ok: A→429→B")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit()
    ThreadingHTTPServer(("127.0.0.1", 8790), H).serve_forever()
