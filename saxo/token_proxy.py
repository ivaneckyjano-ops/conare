#!/usr/bin/env python3
"""Simple token proxy

Provides a tiny HTTP API to serve current access token to local services.
GET /token -> {"access_token": "...", "expires_at": 1234567890}

This service reads the same TOKENS_FILE used by the token daemon.
"""
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

TOKENS_FILE = os.getenv("TOKENS_FILE", "/data/tokens_min.json")
HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PORT = int(os.getenv("PROXY_PORT", "8080"))


def load_tokens():
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/token":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        tokens = load_tokens()
        if not tokens:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"{}")
            return
        out = {"access_token": tokens.get("access_token"), "expires_at": tokens.get("expires_at")}
        body = json.dumps(out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return


def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Token proxy listening on {HOST}:{PORT}, serving tokens from {TOKENS_FILE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
