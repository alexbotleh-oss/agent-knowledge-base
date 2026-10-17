#!/usr/bin/env python3
"""Authenticated loopback bridge for importing browser attachments into Rima's private library.

The browser sends raw file bytes only after the user attaches a file. The caller must
supply an explicit project ID and source conversation/message IDs. The bridge never
logs payloads or returns attachment bytes.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from project_attachment_library import register_attachment

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
MAX_ID_CHARS = 256
FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def _required(value: str | None, field: str, limit: int = MAX_ID_CHARS) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    return value.strip()


def _safe_filename(value: str | None) -> str:
    value = _required(value, "X-Rima-Filename", 255).replace("\\", "/").split("/")[-1]
    value = FILENAME_RE.sub("_", value).strip(" .")
    if not value or value in {".", ".."}:
        raise ValueError("invalid attachment filename")
    return value


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def make_handler(library_root: Path, token: str, allowed_origins: set[str], allowed_projects: set[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "RimaAttachmentAdapter/1.0"
        sys_version = ""

        def log_message(self, fmt, *args):
            # Never log file bytes, auth headers, or user text.
            sys.stderr.write("rima-attachment-adapter: " + (fmt % args) + "\n")

        def _send(self, status: int, value: object, *, origin: str | None = None):
            payload = _json_bytes(value)
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

        def _authorized(self) -> bool:
            scheme, _, supplied = self.headers.get("Authorization", "").partition(" ")
            return scheme.lower() == "bearer" and bool(supplied) and hmac.compare_digest(supplied, token)

        def do_OPTIONS(self):
            origin = self.headers.get("Origin")
            if not origin or origin not in allowed_origins:
                self._send(403, {"status": "ERROR", "error": "origin_not_allowed"})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "Authorization, Content-Type, X-Rima-Project-ID, X-Rima-Conversation-ID, "
                             "X-Rima-Source-Message-ID, X-Rima-Filename")
            self.send_header("Access-Control-Max-Age", "300")
            self.end_headers()

        def do_GET(self):
            if not self._authorized():
                self._send(401, {"status": "ERROR", "error": "unauthorized"})
                return
            if urlparse(self.path).path == "/health":
                self._send(200, {"status": "OK", "service": "rima-attachment-adapter"})
                return
            self._send(404, {"status": "ERROR", "error": "not_found"})

        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin and origin not in allowed_origins:
                self._send(403, {"status": "ERROR", "error": "origin_not_allowed"})
                return
            if not self._authorized():
                self._send(401, {"status": "ERROR", "error": "unauthorized"}, origin=origin)
                return
            if urlparse(self.path).path != "/v1/attachments":
                self._send(404, {"status": "ERROR", "error": "not_found"}, origin=origin)
                return
            length_text = self.headers.get("Content-Length")
            try:
                length = int(length_text) if length_text is not None else -1
            except ValueError:
                length = -1
            if length < 0:
                self._send(400, {"status": "ERROR", "error": "valid_content_length_required"}, origin=origin)
                return
            if length > MAX_ATTACHMENT_BYTES:
                self._send(413, {"status": "ERROR", "error": "attachment_too_large"}, origin=origin)
                return
            if length == 0:
                self._send(400, {"status": "ERROR", "error": "empty_attachment"}, origin=origin)
                return
            temp_path: Path | None = None
            try:
                project_id = _required(self.headers.get("X-Rima-Project-ID"), "X-Rima-Project-ID")
                if project_id not in allowed_projects:
                    self._send(403, {"status": "ERROR", "error": "project_not_allowed"}, origin=origin)
                    return
                conversation_id = _required(self.headers.get("X-Rima-Conversation-ID"), "X-Rima-Conversation-ID")
                source_message_id = _required(self.headers.get("X-Rima-Source-Message-ID"), "X-Rima-Source-Message-ID")
                filename = _safe_filename(self.headers.get("X-Rima-Filename"))
                media_type = self.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0].strip()
                if not media_type or len(media_type) > 128:
                    raise ValueError("invalid Content-Type")
                with tempfile.NamedTemporaryFile(prefix=".rima-attachment-", dir=library_root, delete=False) as temp:
                    temp_path = Path(temp.name)
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("request body ended before Content-Length")
                        temp.write(chunk)
                        remaining -= len(chunk)
                    temp.flush()
                    os.fsync(temp.fileno())
                result = register_attachment(
                    temp_path, library_root, project_id=project_id,
                    conversation_id=conversation_id, source_message_id=source_message_id,
                    original_name=filename, media_type=media_type,
                )
                result.pop("storage_locator", None)
                self._send(201 if result["status"] == "REGISTERED" else 200,
                           {"status": result["status"], "attachment": result}, origin=origin)
            except ValueError as exc:
                self._send(400, {"status": "ERROR", "error": str(exc)}, origin=origin)
            except (OSError, OverflowError) as exc:
                self._send(500, {"status": "ERROR", "error": "attachment_storage_failed",
                                 "detail": type(exc).__name__}, origin=origin)
            finally:
                if temp_path is not None:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        sys.stderr.write("rima-attachment-adapter: temporary file cleanup failed\\n")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", default=str(Path.home() / ".local/share/rima/project-library"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--allow-origin", action="append", default=[])
    parser.add_argument("--allow-project", action="append", default=[],
                        help="explicit project ID allowed to receive attachments; repeat per project")
    parser.add_argument("--token-file", required=True, help="file containing a long random bearer token")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("only loopback bind addresses are allowed")
    if not 0 < args.port < 65536:
        parser.error("port must be between 1 and 65535")
    token_path = Path(args.token_file).expanduser()
    try:
        token = token_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        parser.error(f"cannot read token file: {exc}")
    if len(token) < 32:
        parser.error("bearer token must contain at least 32 characters")
    if not args.allow_origin:
        parser.error("at least one exact --allow-origin is required")
    if not args.allow_project:
        parser.error("at least one explicit --allow-project is required")
    library_root = Path(args.library_root).expanduser().resolve()
    library_root.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port),
                                 make_handler(library_root, token, set(args.allow_origin), set(args.allow_project)))
    server.daemon_threads = True
    print(json.dumps({"status": "READY", "host": args.host, "port": args.port,
                      "library_root": str(library_root), "allowed_origins": args.allow_origin,
                      "allowed_projects": args.allow_project}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
