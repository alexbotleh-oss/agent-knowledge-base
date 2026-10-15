#!/usr/bin/env python3
"""Local HTTP adapter for a trusted chat client to record turn lifecycle events.

This service does not inspect ChatGPT pages or infer delivery. A client must call
POST /v1/turns before processing, then publish progress/report/submission events.
The default bind is loopback and a bearer token is mandatory.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from turn_lifecycle_ledger import DEFAULT_LEDGER, EVENTS, digest, inspect, record

MAX_BODY_BYTES = 1024 * 1024
MAX_TEXT_CHARS = 250_000
MAX_ID_CHARS = 256
ALLOWED_EVENT_FIELDS = {"detail", "artifact", "report", "submission", "delivery"}


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def validate_string(value: object, field: str, *, required: bool = True, max_len: int = MAX_ID_CHARS) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > max_len:
        raise ValueError(f"{field} must be a {'non-empty ' if required else ''}string of at most {max_len} characters")
    return value


def make_handler(ledger_path: Path, token: str, allowed_origins: set[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TurnLifecycleAdapter/1.0"
        sys_version = ""

        def log_message(self, fmt, *args):
            # Never log request bodies, authorization headers, or exact user text.
            sys.stderr.write("turn-adapter: " + (fmt % args) + "\n")

        def _send(self, status: int, value: object, *, origin: str | None = None):
            payload = json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if origin and origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(payload)

        def _auth_ok(self) -> bool:
            header = self.headers.get("Authorization", "")
            scheme, _, supplied = header.partition(" ")
            return scheme.lower() == "bearer" and bool(supplied) and hmac.compare_digest(supplied, token)

        def _read_json(self) -> dict:
            length_text = self.headers.get("Content-Length")
            if length_text is None:
                raise ValueError("Content-Length is required")
            try:
                length = int(length_text)
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise OverflowError("request body exceeds size limit")
            raw = self.rfile.read(length)
            try:
                obj = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("body must be valid UTF-8 JSON") from exc
            if not isinstance(obj, dict):
                raise ValueError("JSON body must be an object")
            return obj

        def do_OPTIONS(self):
            origin = self.headers.get("Origin")
            if not origin or origin not in allowed_origins:
                self._send(403, {"status": "ERROR", "error": "origin_not_allowed"})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Max-Age", "300")
            self.end_headers()

        def do_GET(self):
            if not self._auth_ok():
                self._send(401, {"status": "ERROR", "error": "unauthorized"})
                return
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send(200, {"status": "OK", "service": "turn-lifecycle-adapter"})
                return
            if parsed.path == "/v1/turns":
                query = parse_qs(parsed.query)
                result = inspect(ledger_path)
                if query.get("incomplete", ["false"])[0].lower() in {"1", "true", "yes"}:
                    result["turns"] = [t for t in result["turns"] if t["turn_id"] in result["incomplete_turn_ids"]]
                self._send(200, result, origin=self.headers.get("Origin"))
                return
            if parsed.path.startswith("/v1/turns/"):
                turn_id = parsed.path.removeprefix("/v1/turns/")
                if not turn_id or "/" in turn_id:
                    self._send(400, {"status": "ERROR", "error": "invalid_turn_id"})
                    return
                result = inspect(ledger_path, turn_id)
                if not result["turns"]:
                    self._send(404, {"status": "ERROR", "error": "turn_not_found"})
                    return
                self._send(200, result["turns"][0], origin=self.headers.get("Origin"))
                return
            self._send(404, {"status": "ERROR", "error": "not_found"})

        def do_POST(self):
            if not self._auth_ok():
                self._send(401, {"status": "ERROR", "error": "unauthorized"})
                return
            origin = self.headers.get("Origin")
            if origin and origin not in allowed_origins:
                self._send(403, {"status": "ERROR", "error": "origin_not_allowed"})
                return
            try:
                obj = self._read_json()
                parsed = urlparse(self.path)
                if parsed.path == "/v1/turns":
                    extra = set(obj) - {"turn_id", "task_id", "user_text", "previous_checkpoint"}
                    if extra:
                        raise ValueError("unsupported fields: " + ", ".join(sorted(extra)))
                    turn_id = validate_string(obj.get("turn_id"), "turn_id")
                    task_id = validate_string(obj.get("task_id"), "task_id")
                    user_text = validate_string(obj.get("user_text"), "user_text", max_len=MAX_TEXT_CHARS)
                    previous_checkpoint = validate_string(obj.get("previous_checkpoint"), "previous_checkpoint", required=False)
                    result = record(
                        ledger_path, "TURN_RECEIVED", turn_id,
                        task_id=task_id, user_text=user_text,
                        user_text_sha256=digest(user_text),
                        previous_checkpoint=previous_checkpoint,
                    )
                    self._send(201 if result["status"] == "APPENDED" else 200, result, origin=origin)
                    return
                if parsed.path.startswith("/v1/turns/") and parsed.path.endswith("/events"):
                    turn_id = parsed.path.removeprefix("/v1/turns/").removesuffix("/events").strip("/")
                    validate_string(turn_id, "turn_id")
                    event_type = validate_string(obj.get("event_type"), "event_type")
                    if event_type not in EVENTS - {"TURN_RECEIVED"}:
                        raise ValueError("unsupported event_type")
                    extra = set(obj) - {"event_type", "event_id"} - ALLOWED_EVENT_FIELDS
                    if extra:
                        raise ValueError("unsupported fields: " + ", ".join(sorted(extra)))
                    fields = {key: obj[key] for key in ALLOWED_EVENT_FIELDS if key in obj}
                    if "event_id" in obj:
                        fields["event_id"] = validate_string(obj["event_id"], "event_id")
                    if "detail" in fields:
                        fields["detail"] = validate_string(fields["detail"], "detail", required=False, max_len=MAX_TEXT_CHARS) or ""
                    for name in ("artifact", "report", "submission", "delivery"):
                        if name in fields and not isinstance(fields[name], dict):
                            raise ValueError(f"{name} must be a JSON object")
                    result = record(ledger_path, event_type, turn_id, **fields)
                    self._send(201 if result["status"] == "APPENDED" else 200, result, origin=origin)
                    return
                self._send(404, {"status": "ERROR", "error": "not_found"}, origin=origin)
            except OverflowError as exc:
                self._send(413, {"status": "ERROR", "error": str(exc)}, origin=origin)
            except (ValueError, OSError) as exc:
                self._send(400, {"status": "ERROR", "error": str(exc)}, origin=origin)

        def do_HEAD(self):
            self._send(405, {"status": "ERROR", "error": "method_not_allowed"})

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allowed-origin", action="append", default=[], help="exact browser origin allowed for CORS; repeat as needed")
    parser.add_argument("--allow-remote", action="store_true", help="permit non-loopback bind; bearer token still required")
    args = parser.parse_args(argv)
    token = os.environ.get("AGENT_TURN_ADAPTER_TOKEN", "")
    if len(token) < 32:
        print("ERROR: set AGENT_TURN_ADAPTER_TOKEN to a random secret of at least 32 characters", file=sys.stderr)
        return 2
    if args.port < 1 or args.port > 65535:
        print("ERROR: port must be in 1..65535", file=sys.stderr)
        return 2
    import ipaddress
    try:
        address = ipaddress.ip_address(args.bind)
    except ValueError:
        print("ERROR: --bind must be an IP address (use 127.0.0.1 by default)", file=sys.stderr)
        return 2
    if not address.is_loopback and not args.allow_remote:
        print("ERROR: non-loopback bind requires --allow-remote", file=sys.stderr)
        return 2
    if len(set(args.allowed_origin)) != len(args.allowed_origin):
        print("ERROR: duplicate --allowed-origin value", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((args.bind, args.port), make_handler(args.ledger, token, set(args.allowed_origin)))
    server.daemon_threads = True
    print(f"Turn lifecycle adapter listening on {args.bind}:{args.port}; ledger={args.ledger}", file=sys.stderr)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
