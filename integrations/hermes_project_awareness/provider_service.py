"""Dedicated-account provider daemon. It accepts only fixed, typed read requests over AF_UNIX."""

from __future__ import annotations

import json
import os
import socket
import socketserver
import struct
import sys
import uuid
from typing import Any

from .audit import record as audit_record
from .github import GitHubProvider, GitHubSettings
from .inventory import collect


MAX_FRAME = 1_048_576
GITHUB_OPS = frozenset({"repository_summary", "read_document", "branches", "recent_commits", "issues", "pull_requests", "pull_request_reviews", "tree"})
INVENTORY_OPS = frozenset({"host_summary", "model_catalog", "project_directories", "service_inventory"})


class ProviderServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, socket_path: str, provider: str, client_uid: int):
        self.provider = provider
        self.client_uid = client_uid
        if provider == "github":
            self.impl = GitHubProvider(GitHubSettings(
                app_id=os.environ["HERMES_GITHUB_APP_ID"],
                installation_id=os.environ["HERMES_GITHUB_INSTALLATION_ID"],
                private_key_credential=os.environ.get("CREDENTIALS_DIRECTORY", "/run/credentials") + "/github-app-key",
                proxy_socket=os.environ.get("HERMES_GITHUB_PROXY_SOCKET", "/run/hermes-egress/github-connect.sock"),
            ))
        elif provider == "inventory":
            self.impl = None
        else:
            raise ValueError("unknown provider")
        super().__init__(socket_path, _ProviderRequestHandler)


class _ProviderRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server: ProviderServer = self.server  # type: ignore[assignment]
        request_id = uuid.uuid4().hex
        operation = "repository_summary" if server.provider == "github" else "host_summary"
        try:
            _pid, uid, _gid = struct.unpack("3i", self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
            if uid != server.client_uid:
                self._send({"error": "unauthorized local client"})
                return
            raw = self.rfile.readline(MAX_FRAME + 1)
            if not raw or len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
                self._send({"error": "invalid request frame"})
                return
            request = json.loads(raw)
            if not isinstance(request, dict) or set(request) != {"request_id", "operation", "arguments"}:
                self._send({"error": "invalid request shape"})
                return
            request_id = request["request_id"]
            operation, args = request["operation"], request["arguments"]
            if not isinstance(request_id, str) or len(request_id) != 32 or any(ch not in "0123456789abcdef" for ch in request_id) or not isinstance(args, dict):
                self._send({"error": "arguments must be an object"})
                return
            if server.provider == "github" and operation not in GITHUB_OPS:
                self._send({"error": "operation is not available"})
                return
            if server.provider == "inventory" and (operation not in INVENTORY_OPS or args):
                self._send({"error": "operation or arguments are not available"})
                return
            audit_record({"request_id": request_id, "event": "provider_started", "provider": server.provider,
                          "operation": operation})
            if server.provider == "github":
                result = server.impl.call(operation, args)
            else:
                result = collect(operation)
            evidence_ids = [row.get("evidence_id", "") for row in result.get("evidence", []) if isinstance(row, dict)]
            audit_record({"request_id": request_id, "event": "provider_completed", "provider": server.provider,
                          "operation": operation, "evidence_ids": evidence_ids})
            self._send({"result": result})
        except Exception as exc:
            # Do not return exception strings: lower layers may include paths, URLs, or
            # remote response details. A request ID is supplied by the MCP adapter audit log.
            print(f"provider={getattr(self.server, 'provider', 'unknown')} error={type(exc).__name__}", file=sys.stderr, flush=True)
            try:
                audit_record({"request_id": request_id, "event": "failed", "provider": server.provider,
                              "operation": operation, "result": "error"})
            except Exception:
                pass
            self._send({"error": "provider request failed"})

    def _send(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_FRAME:
            body = b'{"error":"provider response exceeds limit"}'
        self.wfile.write(body + b"\n")
        self.wfile.flush()


def serve(provider: str, socket_path: str, client_uid: int) -> None:
    os.umask(0o117)
    if os.path.lexists(socket_path):
        raise RuntimeError("provider socket path already exists")
    server = ProviderServer(socket_path, provider, client_uid)
    try:
        os.chmod(socket_path, 0o660)
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        try:
            os.unlink(socket_path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    # Service units set fixed provider/socket/authorized client values. No MCP or model
    # argument is allowed to control the daemon's identity or filesystem paths.
    service_provider = os.environ.get("HERMES_PROVIDER_ID", "")
    service_socket = os.environ.get("HERMES_PROVIDER_SOCKET", "")
    client_uid = os.environ.get("HERMES_PROVIDER_CLIENT_UID", "")
    if service_provider not in {"github", "inventory"} or not service_socket or not client_uid.isdigit():
        raise SystemExit("provider service configuration is incomplete")
    serve(service_provider, service_socket, int(client_uid))
