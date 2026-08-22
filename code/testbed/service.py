"""Universal microservice for the Fulcrum real-deployment testbed (stdlib only).

Each instance is configured by env vars to be either a healthy boundary (does local work,
little or no downstream fan-out) or a distributed-monolith boundary (tiny local work, many
synchronous downstream hops). It measures its OWN Kinetic Efficiency from real request timing:
  t_total  = wall-clock time in the request handler
  t_useful = time doing local CPU work (NOT waiting on downstream HTTP)
  E        = sum(t_useful) / sum(t_total)  over all requests   (Section 7.1)
Exposes GET /work (do the work) and GET /stats (cumulative useful, total, count).

Env: SERVICE_NAME, USEFUL_MS (local work per request), HOPS (synchronous downstream calls),
     DOWNSTREAM (url to call), PORT.
No third-party dependencies. Author: Viquar Khan. Copyright 2026 Viquar Khan.
"""
import os, time, json, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NAME = os.environ.get("SERVICE_NAME", "svc")
USEFUL_MS = float(os.environ.get("USEFUL_MS", "20"))
HOPS = int(os.environ.get("HOPS", "0"))
DOWNSTREAM = os.environ.get("DOWNSTREAM", "")
PORT = int(os.environ.get("PORT", "8080"))
# Bind to loopback by default (this testbed is driven from localhost). Set BIND_HOST=0.0.0.0
# only for an intentional cloud/container deployment where the port is otherwise protected.
HOST = os.environ.get("BIND_HOST", "127.0.0.1")

_lock = threading.Lock()
_stat = {"useful": 0.0, "total": 0.0, "count": 0}


def burn_cpu(ms):
    """Do real local CPU work for approximately ms milliseconds."""
    end = time.perf_counter() + ms / 1000.0
    x = 0
    while time.perf_counter() < end:
        x += 1  # busy work
    return x


def call_downstream():
    if not DOWNSTREAM:
        return
    try:
        urllib.request.urlopen(DOWNSTREAM + "/work", timeout=10).read()
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/stats"):
            with _lock:
                s = dict(_stat)
            s["E"] = (s["useful"] / s["total"]) if s["total"] > 0 else None
            s["service"] = NAME
            body = json.dumps(s).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body)
            return
        # /work: measure this request
        t0 = time.perf_counter()
        useful = 0.0
        # local useful work
        u0 = time.perf_counter(); burn_cpu(USEFUL_MS); useful += time.perf_counter() - u0
        # synchronous downstream hops (this time is overhead: waiting on remote)
        for _ in range(HOPS):
            call_downstream()
        total = time.perf_counter() - t0
        with _lock:
            _stat["useful"] += useful; _stat["total"] += total; _stat["count"] += 1
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers()
        self.wfile.write(b"ok")


if __name__ == "__main__":
    print(f"{NAME} on :{PORT} useful={USEFUL_MS}ms hops={HOPS} downstream={DOWNSTREAM or 'none'}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
