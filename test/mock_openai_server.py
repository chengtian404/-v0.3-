"""Small OpenAI-compatible server used by local integration tests."""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if payload.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for text in ("SSE ", "CONNECTED"):
                event = {
                    "choices": [{"delta": {"content": text}, "index": 0}],
                    "usage": None,
                }
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
                self.wfile.flush()
                time.sleep(0.03)
            usage = {
                "choices": [],
                "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
            }
            self.wfile.write(("data: " + json.dumps(usage) + "\n\n").encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return
        body = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": "CONNECTED"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 18080), Handler).serve_forever()
