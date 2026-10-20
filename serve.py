#!/usr/bin/env python3
"""
Local HTTP server for the kiosk page, with caching fully disabled.

The default `python3 -m http.server` lets Chromium cache index.html and
the assets based on file mtime, which caused Chromium to keep serving a
stale cached copy of the page across many service restarts during
development - very confusing to debug. This adds explicit no-cache
headers to every response so that never happens again.

Two more things matter for smooth video playback:
- Threaded: each request gets its own thread. With a single-threaded
  server, one video download that Chromium pauses (its buffer is full)
  blocks every other request - the next clip, state.json polling, logs.
- Range requests: Chromium streams video by asking for byte ranges
  ("Range: bytes=..."), which the stock handler ignores.
"""

import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


class NoCacheHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        # index.html posts its console messages here so they show up in
        # the system log: sudo journalctl -u kiosk-server -f
        if self.path != "/log":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        print("[page]", self.rfile.read(length).decode("utf-8", "replace"), flush=True)
        self.send_response(204)
        self.end_headers()

    def send_head(self):
        match = RANGE_RE.match(self.headers.get("Range", "").strip())
        path = self.translate_path(self.path)
        if not match or not os.path.isfile(path):
            return super().send_head()

        size = os.path.getsize(path)
        start, end = match.groups()
        if start == "":  # "bytes=-N" means the last N bytes
            start, end = max(0, size - int(end or 0)), size - 1
        else:
            start, end = int(start), min(int(end) if end else size - 1, size - 1)
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None

        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._range_remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_remaining", None)
        self._range_remaining = None
        try:
            if remaining is None:
                return super().copyfile(source, outputfile)
            while remaining > 0:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Chromium dropped the connection (e.g. clip released)

    def log_request(self, code="-", size="-"):
        pass  # don't log every file request - it drowns out the page messages

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        if self.command == "GET" and not self.headers.get("Range"):
            self.send_header("Accept-Ranges", "bytes")
        super().end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer.daemon_threads = True
    server = ThreadingHTTPServer(("0.0.0.0", 8080), NoCacheHandler)
    print("Serving on :8080 with caching disabled", flush=True)
    server.serve_forever()
