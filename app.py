"""Meeting-room booking server. Run: python app.py  ->  http://127.0.0.1:8000"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from booking import Bookings, BookingError, parse_slot

STORE = Bookings()
PAGE = (Path(__file__).parent / "index.html").read_bytes()
MAX_BODY = 1000  # bytes accepted in a POST body


def out(booking):
    """Booking -> JSON-safe dict."""
    return dict(booking, start=booking["start"].isoformat(), end=booking["end"].isoformat())


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        if ctype.startswith("application/json"):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            return self.send(200, PAGE, "text/html; charset=utf-8")
        if url.path == "/api/rooms":  # rooms that fit this time + group size
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                slot = parse_slot(query.get("start"), query.get("end"),
                                  query.get("attendees"))
            except BookingError as error:
                return self.send(400, {"error": str(error)})
            return self.send(200, {"rooms": STORE.available(*slot)})
        if url.path == "/api/bookings":
            return self.send(200, [out(b) for b in STORE.all()])
        return self.send(404, {"error": "Not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/bookings":
            return self.send(404, {"error": "Not found"})
        # Check the declared size before reading, so a huge or lying Content-Length
        # cannot make us allocate a buffer for it. A real booking is about 200 bytes.
        length = self.headers.get("Content-Length", "0")
        if not length.isdigit():
            return self.send(400, {"error": "Content-Length header is missing or invalid"})
        if int(length) > MAX_BODY:
            return self.send(413, {"error": f"Booking must be under {MAX_BODY} bytes"})
        raw = self.rfile.read(int(length))
        try:
            data = json.loads(raw or b"{}")
            booking = STORE.add(data.get("name"), data.get("room"), data.get("start"),
                                data.get("end"), data.get("attendees"))
        except (json.JSONDecodeError, AttributeError):
            return self.send(400, {"error": "Body must be a JSON object"})
        except BookingError as error:
            return self.send(400, {"error": str(error)})
        return self.send(201, out(booking))

    def log_message(self, *_):
        pass  # keep the terminal readable


if __name__ == "__main__":
    print("Meeting rooms: http://127.0.0.1:8000  (Ctrl+C to stop)")
    # Threading, not plain HTTPServer: browsers open speculative connections and send
    # nothing on them, which would block a single-threaded server for every real request.
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
