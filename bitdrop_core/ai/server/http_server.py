# syntheticmind/server/http_server.py

import json
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

from ..metamodel.runtime import MetaModelRuntime
from ..context.packet import Packet


runtime = MetaModelRuntime()


# -------------------------------------------------------------
# HTTP HANDLER
# -------------------------------------------------------------
class MetaModelHandler(BaseHTTPRequestHandler):

    # ---------------------------------------------------------
    # UTIL: JSON RESPONSE
    # ---------------------------------------------------------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # ---------------------------------------------------------
    # UTIL: ERROR RESPONSE
    # ---------------------------------------------------------
    def _error(self, message, status=400, tb=None):
        return self._send_json(
            {
                "ok": False,
                "error": message,
                "traceback": tb,
            },
            status=status,
        )

    # ---------------------------------------------------------
    # GET HANDLER
    # ---------------------------------------------------------
    def do_GET(self):
        try:
            if self.path == "/health":
                return self._send_json({"ok": True, "status": "healthy"})

            if self.path == "/version":
                return self._send_json(
                    {
                        "ok": True,
                        "version": "1.0.0",
                        "engine": "BitDrop MetaModel",
                    }
                )

            return self._error("unknown endpoint", status=404)

        except Exception as e:
            return self._error(str(e), status=500, tb=traceback.format_exc())

    # ---------------------------------------------------------
    # POST HANDLER
    # ---------------------------------------------------------
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)

            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                return self._error("invalid JSON", status=400)

            # -------------------------------------------------
            # /generate endpoint
            # -------------------------------------------------
            if self.path == "/generate":
                return self._handle_generate(payload)

            # -------------------------------------------------
            # /ask endpoint
            # -------------------------------------------------
            if self.path == "/ask":
                return self._handle_ask(payload)

            return self._error("unknown endpoint", status=404)

        except Exception as e:
            return self._error(str(e), status=500, tb=traceback.format_exc())

    # ---------------------------------------------------------
    # HANDLER: /generate
    # ---------------------------------------------------------
    def _handle_generate(self, payload):
        start = time.time()

        text = payload.get("text", "")
        data = payload.get("data")
        intent = payload.get("intent", "small_reasoning")
        compressed = payload.get("compressed", False)
        return_compressed = payload.get("return_compressed", False)
        metadata = payload.get("metadata", {})
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")

        # Build packet
        packet = Packet(
            text=text,
            data=data,
            metadata=metadata,
            intent=intent,
            compressed=compressed,
            return_compressed=return_compressed,
            user_id=user_id,
            session_id=session_id,
        )

        result = runtime.generate_packet(packet)

        result["latency_ms"] = int((time.time() - start) * 1000)
        return self._send_json(result)

    # ---------------------------------------------------------
    # HANDLER: /ask
    # ---------------------------------------------------------
    def _handle_ask(self, payload):
        text = payload.get("text", "")
        result = runtime.ask(text)
        return self._send_json({"ok": True, "output": result})


# -------------------------------------------------------------
# SERVER STARTUP
# -------------------------------------------------------------
def start_server(host="127.0.0.1", port=8080):
    server = HTTPServer((host, port), MetaModelHandler)
    print(f"[BitDrop MetaModel] Server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BitDrop MetaModel] Shutting down gracefully...")
        server.server_close()


if __name__ == "__main__":
    start_server()


