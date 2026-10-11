"""Tiny local web server: serves the front end and the /api/anonymize endpoint.

Run: python app/server.py   then open http://127.0.0.1:8000
"""
from __future__ import annotations

import base64
import getpass
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from anonymizer import process_file
import llm

STATIC = Path(__file__).resolve().parent / "static"
MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}
STATIC_TYPES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def do_GET(self) -> None:
        entry = STATIC_TYPES.get(self.path.split("?")[0])
        if not entry:
            self._json(404, {"error": "Not found"})
            return
        self._send(200, (STATIC / entry[0]).read_bytes(), entry[1])

    def do_POST(self) -> None:
        if self.path != "/api/anonymize":
            self._json(404, {"error": "Not found"})
            return
        name = unquote(self.headers.get("X-Filename", ""))
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        length = int(self.headers.get("Content-Length") or 0)
        if ext not in ALLOWED:
            self._json(400, {"error": "Unsupported file type. Use PDF, DOCX, TXT, PNG or JPG."})
            return
        if not 0 < length <= MAX_BYTES:
            self._json(413, {"error": "File is empty or larger than 10 MB."})
            return
        try:
            try:
                keep = json.loads(unquote(self.headers.get("X-Keep", "")) or "{}")
            except ValueError:
                keep = {}
            result = process_file(self.rfile.read(length), ext, keep if isinstance(keep, dict) else {})
        except ValueError as e:
            self._json(422, {"error": str(e)})
            return
        except Exception:
            self._json(422, {"error": "Could not read this file. Is it valid and not encrypted?"})
            return
        stem = re.sub(r"[^\w.-]", "_", name.rsplit(".", 1)[0])[:80] or "document"
        self._json(200, {
            "filename": f"{stem}_censored.{ext}",
            "mime": result["mime"],
            "data": base64.b64encode(result["file"]).decode(),
            "original": result["original"],
            "censored": result["censored"],
            "count": result["count"],
            "engine": result["engine"],
        })

    def log_message(self, format: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    if not llm.is_configured() and sys.stdin.isatty():
        key = getpass.getpass("Enter your Gemini API key (input hidden; not saved): ").strip()
        if key:
            os.environ["GEMINI_API_KEY"] = key
        else:
            print("No key entered; only built-in detection rules will be used.")
    elif not llm.is_configured():
        print("GEMINI_API_KEY is not set; only built-in detection rules will be used.")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Open http://{host}:{port}")
    server.serve_forever()
