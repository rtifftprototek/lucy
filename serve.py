#!/usr/bin/env python3
"""
Local HTTP server for the kiosk page, with caching fully disabled.

The default `python3 -m http.server` lets Chromium cache index.html and
the assets based on file mtime, which caused Chromium to keep serving a
stale cached copy of the page across many service restarts during
development - very confusing to debug. This adds explicit no-cache
headers to every response so that never happens again.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), NoCacheHandler)
    print("Serving on :8080 with caching disabled")
    server.serve_forever()
