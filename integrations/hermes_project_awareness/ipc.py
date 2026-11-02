"""Bounded AF_UNIX request/response transport used only by fixed provider adapters."""

from __future__ import annotations

import json
import socket
from typing import Any


MAX_FRAME = 1_048_576
SOCKET_TIMEOUT = 15.0


def request(socket_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_FRAME:
        raise ValueError("request exceeds IPC frame limit")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(SOCKET_TIMEOUT)
        client.connect(socket_path)
        client.sendall(body + b"\n")
        chunks = bytearray()
        while len(chunks) <= MAX_FRAME:
            chunk = client.recv(4096)
            if not chunk:
                break
            chunks.extend(chunk)
            if b"\n" in chunk:
                break
        if not chunks or len(chunks) > MAX_FRAME or b"\n" not in chunks:
            raise ValueError("provider returned an invalid or oversized IPC frame")
    result = json.loads(bytes(chunks).split(b"\n", 1)[0])
    if not isinstance(result, dict):
        raise ValueError("provider response must be an object")
    return result
