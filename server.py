"""Serves the Orchid web UI and proxies chat requests to Groq.

Usage:
    python server.py        then open http://localhost:8000

The API key stays on the server; the browser only talks to /api/chat.
"""

import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import groq

from llm import MODEL, ROOT, describe_error, make_client

SYSTEM_PROMPT = (
    "You are Orchid, a warm, friendly personal assistant. "
    "Help the user think, plan, write, or get unstuck. Keep answers clear and concise."
)
PORT = int(os.environ.get("PORT", "8000"))
PUBLIC_FILES = {"/", "/index.html", "/app.js", "/style.css"}
LOCAL_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")

client = make_client()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        # Only serve the web UI files - never the key or the source.
        if self.path.split("?")[0] not in PUBLIC_FILES:
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        self.do_GET()

    def end_headers(self):
        # Let the page call the API when opened from disk or another local dev server.
        origin = self.headers.get("Origin", "")
        if origin == "null" or LOCAL_ORIGIN.match(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            history = json.loads(self.rfile.read(length))["messages"]
            history = [
                {"role": m["role"], "content": str(m["content"])}
                for m in history
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]
            if not history or history[-1]["role"] != "user":
                raise ValueError
        except (ValueError, KeyError, TypeError):
            self.send_json(400, {"error": "Invalid request."})
            return

        if client is None:
            self.send_json(500, {"error": "No API key configured on the server. Add GROQ_API_KEY to .env and restart."})
            return

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]
        try:
            stream = client.chat.completions.create(model=MODEL, messages=messages, stream=True)
        except groq.APIError as e:
            self.send_json(502, {"error": describe_error(e)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            finish_reason = None
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.delta.content:
                    self.write_chunk(choice.delta.content)
                finish_reason = choice.finish_reason or finish_reason
            if finish_reason == "length":
                self.write_chunk("\n\n(Response cut off at the length limit.)")
        except groq.APIError as e:
            self.write_chunk(f"\n\n({describe_error(e)})")
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser went away
        finally:
            stream.close()

    def write_chunk(self, text):
        self.wfile.write(text.encode("utf-8"))
        self.wfile.flush()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Orchid running at http://localhost:{PORT}  (model: {MODEL}, Ctrl+C to stop)")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
