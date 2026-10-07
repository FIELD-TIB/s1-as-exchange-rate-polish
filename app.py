"""Local web interface and JSON API for the KES/TZS rate tracker."""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from rate_service import RatePoller
from rate_store import RateStore


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DATABASE_PATH = Path(os.environ.get("RATE_DB_PATH", APP_DIR / "data" / "rates.sqlite3"))


class RateRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, store, poller, **kwargs):
        self.store = store
        self.poller = poller
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/api/status":
            self._send_json(
                {
                    "poller": self.poller.status(),
                    "latest": self.store.get_latest(),
                }
            )
            return
        if parsed_url.path == "/api/rates":
            query = parse_qs(parsed_url.query)
            try:
                limit = int(query.get("limit", ["100"])[0])
            except ValueError:
                self.send_error(400, "limit must be an integer")
                return
            if not 1 <= limit <= 500:
                self.send_error(400, "limit must be between 1 and 500")
                return
            self._send_json({"rates": self.store.get_samples(limit)})
            return
        if parsed_url.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def _send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        print(f"[web] {self.address_string()} - {format_string % args}")


def main():
    store = RateStore(DATABASE_PATH)
    poller = RatePoller(store)
    poller.start()

    def handler(*args, **kwargs):
        return RateRequestHandler(*args, store=store, poller=poller, **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    print("KES/TZS Rate Tracker is running at http://127.0.0.1:8000")
    print(f"Local rate history: {DATABASE_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        poller.stop()
        server.server_close()


if __name__ == "__main__":
    main()
