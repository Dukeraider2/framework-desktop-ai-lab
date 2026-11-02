"""Durable, content-free audit delivery to the isolated local audit receiver."""

from __future__ import annotations

import json
import socket
from typing import Any


AUDIT_SOCKET = "/run/hermes-audit/audit.sock"
MAX_AUDIT_FRAME = 16 * 1024


class AuditUnavailable(RuntimeError):
    pass


def record(event: dict[str, Any], *, socket_path: str = AUDIT_SOCKET) -> None:
    """Require an fsync acknowledgement before a provider returns any data."""
    body = json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_AUDIT_FRAME:
        raise AuditUnavailable("audit event exceeds size limit")
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3.0)
            client.connect(socket_path)
            client.sendall(body + b"\n")
            response = bytearray()
            while len(response) <= 256:
                chunk = client.recv(64)
                if not chunk:
                    break
                response.extend(chunk)
                if b"\n" in chunk:
                    break
            result = bytes(response)
        response = json.loads(result)
        if not isinstance(response, dict) or response.get("accepted") is not True:
            raise AuditUnavailable("audit receiver rejected the event")
    except (OSError, ValueError, TypeError) as exc:
        raise AuditUnavailable("audit receiver is unavailable") from exc
