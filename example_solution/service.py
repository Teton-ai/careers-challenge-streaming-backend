"""
Example *stub* solution to show the API contract.

This implementation is deliberately bad: it stores everything in process
memory, has no dedup, no late-event handling, no restart correctness, and
no real backpressure. It exists so you can run the eval end-to-end and
see what the read endpoints should return.

Run:
    python example_solution/service.py
"""

import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.environ.get("PORT", "8080"))


_lock = threading.Lock()
_device_last_heartbeat: dict = {}        # device_id -> ts
_device_heartbeats: dict = defaultdict(lambda: deque(maxlen=300))  # device_id -> [ts]
_room_presence: dict = {}                # room_id -> (in_room, ts)
_room_presence_history: dict = defaultdict(list)  # room_id -> [(ts, in_room)]
_alarms: list = []                       # all fall_warn events (NO DEDUP — bad)


def ingest(event: dict) -> None:
    etype = event.get("type")
    device_id = event.get("device_id")
    room_id = event.get("room_id")
    ts = event.get("ts")
    with _lock:
        if etype == "heartbeat":
            _device_last_heartbeat[device_id] = ts
            _device_heartbeats[device_id].append(time.time())
        elif etype == "presence":
            in_room = bool(event.get("in_room"))
            _room_presence[room_id] = (in_room, ts)
            _room_presence_history[room_id].append((time.time(), in_room))
        elif etype == "fall_warn":
            _alarms.append(event)


def room_occupancy(room_id: str, window_seconds: int) -> dict:
    now = time.time()
    with _lock:
        latest = _room_presence.get(room_id)
        in_room = latest[0] if latest else False
        history = [t for t, val in _room_presence_history.get(room_id, [])
                   if val and t >= now - window_seconds]
    occupied_seconds = len(history)  # super naive
    return {
        "in_room": in_room,
        "occupied_pct": min(occupied_seconds / window_seconds, 1.0),
        "window_seconds": window_seconds,
    }


def device_health(device_id: str) -> dict:
    now = time.time()
    with _lock:
        last_ts = _device_last_heartbeat.get(device_id)
        recent = [t for t in _device_heartbeats.get(device_id, []) if t >= now - 300]
    return {
        "last_heartbeat_ts": last_ts,
        "availability_5m": min(len(recent) / 300, 1.0),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        pass

    def do_POST(self):
        if self.path != "/events":
            self._send(404, {"error": "unknown path"})
            return
        body = self._read_json()
        if not isinstance(body, dict):
            self._send(400, {"error": "invalid json"})
            return
        ingest(body)
        self._send(202, {"ok": True})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        query = self._parse_query()

        if path.startswith("/devices/") and path.endswith("/health"):
            device_id = path.split("/")[2]
            self._send(200, device_health(device_id))
            return

        if path.startswith("/rooms/") and path.endswith("/occupancy"):
            room_id = path.split("/")[2]
            window = self._parse_window(query.get("window", "5m"))
            self._send(200, room_occupancy(room_id, window))
            return

        if path == "/alarms":
            since = float(query.get("since", "0") or "0")
            with _lock:
                items = list(_alarms)
            self._send(200, {"alarms": items, "since": since})
            return

        self._send(404, {"error": "unknown path"})

    def _parse_query(self) -> dict:
        if "?" not in self.path:
            return {}
        from urllib.parse import parse_qs
        raw = self.path.split("?", 1)[1]
        return {k: v[0] for k, v in parse_qs(raw).items()}

    def _parse_window(self, s: str) -> int:
        if s.endswith("m"):
            return int(s[:-1]) * 60
        if s.endswith("h"):
            return int(s[:-1]) * 3600
        return int(s)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            return None

    def _send(self, status: int, body: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, default=str).encode())


def main():
    print(f"Example stub service listening on :{PORT}")
    print("This is a deliberately bad reference implementation. Beat it.")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
