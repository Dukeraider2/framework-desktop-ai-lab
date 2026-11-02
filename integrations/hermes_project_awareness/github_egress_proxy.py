"""Single-destination HTTPS CONNECT proxy for the isolated GitHub provider."""

from __future__ import annotations

import ipaddress
import os
import select
import socket
import socketserver
import struct
import sys
import time

from .github import API_HOST


MAX_HEADER_BYTES = 8192
TUNNEL_IDLE_SECONDS = 30
MAX_TUNNEL_SECONDS = 120


class FixedDestinationProxy(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False


class _ConnectHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        client: socket.socket = self.request
        client.settimeout(5)
        try:
            header = bytearray()
            while b"\r\n\r\n" not in header and len(header) <= MAX_HEADER_BYTES:
                chunk = client.recv(1024)
                if not chunk:
                    return
                header.extend(chunk)
            if len(header) > MAX_HEADER_BYTES:
                return self._reject(client, 431, "request headers too large")
            first_line = bytes(header).split(b"\r\n", 1)[0]
            if first_line != f"CONNECT {API_HOST}:443 HTTP/1.1".encode("ascii"):
                return self._reject(client, 403, "destination denied")
            upstream = self._connect_github()
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self._relay(client, upstream)
        except (OSError, ValueError) as exc:
            print(f"github-egress error={type(exc).__name__}", file=sys.stderr, flush=True)

    @staticmethod
    def _reject(client: socket.socket, status: int, reason: str) -> None:
        client.sendall(f"HTTP/1.1 {status} {reason}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".encode("ascii"))

    @staticmethod
    def _connect_github() -> socket.socket:
        candidates = socket.getaddrinfo(API_HOST, 443, type=socket.SOCK_STREAM)
        for family, socktype, proto, _canonname, address in candidates:
            ip = ipaddress.ip_address(address[0])
            if not ip.is_global:
                continue
            upstream = socket.socket(family, socktype, proto)
            upstream.settimeout(8)
            try:
                upstream.connect(address)
                return upstream
            except OSError:
                upstream.close()
        raise OSError("fixed GitHub API host could not be reached")

    @staticmethod
    def _relay(client: socket.socket, upstream: socket.socket) -> None:
        client.setblocking(False)
        upstream.setblocking(False)
        peers = {client: upstream, upstream: client}
        pending = {client: bytearray(), upstream: bytearray()}
        read_open = {client: True, upstream: True}
        started = last_data = time.monotonic()
        try:
            while (any(read_open.values()) or any(pending.values())) and time.monotonic() - started < MAX_TUNNEL_SECONDS and time.monotonic() - last_data < TUNNEL_IDLE_SECONDS:
                readers = [sock for sock in peers if read_open[sock] and len(pending[peers[sock]]) < 1024 * 1024]
                writers = [sock for sock in peers if pending[peers[sock]]]
                readable, writable, exceptional = select.select(readers, writers, list(peers), 1.0)
                if exceptional:
                    break
                for source in readable:
                    try:
                        data = source.recv(65536)
                    except BlockingIOError:
                        continue
                    if not data:
                        read_open[source] = False
                        continue
                    last_data = time.monotonic()
                    pending[peers[source]].extend(data)
                for destination in writable:
                    try:
                        sent = destination.send(pending[destination])
                    except BlockingIOError:
                        continue
                    if sent:
                        del pending[destination][:sent]
                        last_data = time.monotonic()
                for source, destination in peers.items():
                    if not read_open[source] and not pending[destination]:
                        try:
                            destination.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
        finally:
            upstream.close()


def serve(socket_path: str, allowed_client_uid: int) -> None:
    os.umask(0o117)
    if os.path.lexists(socket_path):
        raise RuntimeError("egress socket path already exists")
    server = FixedDestinationProxy(socket_path, _ConnectHandler)
    try:
        if hasattr(socket, "SO_PASSCRED"):
            server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        os.chmod(socket_path, 0o660)
        # The connected client is necessarily a service UID; use the configured caller and
        # reject every other one before parsing any HTTP request.
        server.allowed_client_uid = allowed_client_uid
        _serve_with_peer_ch…8918 tokens truncated…known provider")
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
