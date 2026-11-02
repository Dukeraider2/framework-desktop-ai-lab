"""Unprivileged audit receiver with daily hash-chained, fsync-acknowledged records."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import socket
import socketserver
import stat
import struct
import sys
import threading
from pathlib import Path
from typing import Any


MAX_FRAME = 16 * 1024
LOG_DIR = Path("/var/log/hermes-project-awareness")
SOCKET_PATH = "/run/hermes-audit/audit.sock"
_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")
_EVENTS = frozenset({"denied", "started", "provider_started", "provider_completed", "failed", "completed"})
_PROVIDERS = frozenset({"hermes", "github", "inventory"})
_OPERATIONS = frozenset({"project_status", "host_summary", "model_catalog", "project_directories", "service_inventory",
                         "repository_summary", "read_document", "branches", "recent_commits", "issues_open",
                         "pull_requests_open", "pull_requests_closed", "pull_request_reviews", "tree"})
RETENTION_DAYS = 90
MAX_DAILY_BYTES = 8 * 1024 * 1024


class AuditLog:
    def __init__(self, directory: Path = LOG_DIR, *, clock=None):
        self.directory = directory
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self.lock = threading.Lock()
        self._failed = False
        directory_st = directory.lstat()
        if not stat.S_ISDIR(directory_st.st_mode) or directory_st.st_uid != os.getuid() or directory_st.st_mode & 0o077:
            raise PermissionError("audit log directory ownership or permissions are invalid")
        self._last_hash = self._verify_existing()
        self._purge_old()

    def _files(self) -> list[Path]:
        return sorted(self.directory.glob("audit-????????.jsonl"))

    def _verify_existing(self) -> str:
        previous = "0" * 64
        have_record = False
        for path in self._files():
            st = path.lstat()
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                    or st.st_mode & 0o077 or st.st_size > MAX_DAILY_BYTES):
                raise PermissionError("audit log file ownership or permissions are invalid")
            for line in path.read_bytes().splitlines():
                row = json.loads(line)
                recorded = row.pop("record_hash")
                expected_prev = row.pop("previous_hash")
                if not have_record and expected_prev != previous:
                    # The first retained file may continue a chain whose earlier segments
                    # have expired. Integrity is then verifiable from this retention window.
                    previous = expected_prev
                if expected_prev != previous:
                    raise RuntimeError("audit hash chain is discontinuous")
                expected = hashlib.sha256((previous + _canonical(row)).encode("utf-8")).hexdigest()
                if recorded != expected:
                    raise RuntimeError("audit hash chain verification failed")
                previous = recorded
                have_record = True
        return previous

    def _purge_old(self) -> None:
        cutoff = self.clock().astimezone(dt.timezone.utc).date() - dt.timedelta(days=RETENTION_DAYS)
        for path in self._files():
            try:
                file_date = dt.datetime.strptime(path.stem.removeprefix("audit-"), "%Y%m%d").date()
                if file_date < cutoff:
                    path.unlink()
            except ValueError as exc:
                raise RuntimeError("audit filename is malformed") from exc

    def append(self, event: dict[str, Any]) -> str:
        row = _validate_event(event)
        with self.lock:
            if self._failed:
                raise OSError("audit writer is in a failed state")
            now = self.clock().astimezone(dt.timezone.utc)
            self._purge_old()
            row["recorded_at"] = now.isoformat(timespec="seconds")
            previous = self._last_hash
            digest = hashlib.sha256((previous + _canonical(row)).encode("utf-8")).hexdigest()
            record = {**row, "previous_hash": previous, "record_hash": digest}
            path = self.directory / f"audit-{now:%Y%m%d}.jsonl"
            encoded = (_canonical(record) + "\n").encode("utf-8")
            created = not path.exists()
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                st = os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
                    raise PermissionError("audit log file has unsafe permissions")
                if st.st_size + len(encoded) > MAX_DAILY_BYTES:
                    raise OSError("daily audit size limit reached")
                offset = 0
                while offset < len(encoded):
                    offset += os.write(fd, encoded[offset:])
                os.fsync(fd)
                if created:
                    dir_fd = os.open(self.directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
            except Exception:
                self._failed = True
                raise
            finally:
                os.close(fd)
            self._last_hash = digest
            return digest


def _canonical(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict) or set(event) - {"request_id", "event", "provider", "operation", "result", "evidence_ids"}:
        raise ValueError("audit event fields are invalid")
    if not isinstance(event.get("request_id"), str) or not _REQUEST_ID.fullmatch(event["request_id"]):
        raise ValueError("audit request id is invalid")
    if event.get("event") not in _EVENTS or event.get("provider") not in _PROVIDERS or event.get("operation") not in _OPERATIONS:
        raise ValueError("audit event kind is invalid")
    result = event.get("result", "ok")
    evidence_ids = event.get("evidence_ids", [])
    if result not in {"ok", "error", "denied"} or not isinstance(evidence_ids, list) or len(evidence_ids) > 50:
        raise ValueError("audit result metadata is invalid")
    if any(not isinstance(value, str) or len(value) > 160 for value in evidence_ids):
        raise ValueError("audit evidence identifiers are invalid")
    return {"request_id": event["request_id"], "event": event["event"], "provider": event["provider"],
            "operation": event["operation"], "result": result, "evidence_ids": evidence_ids}


class _AuditRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server: _AuditServer = self.server  # type: ignore[assignment]
        try:
            _pid, uid, _gid = struct.unpack("3i", self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
            if uid not in server.allowed_uids:
                return self._ack(False)
            raw = self.rfile.readline(MAX_FRAME + 1)
            if not raw.endswith(b"\n") or len(raw) > MAX_FRAME:
                return self._ack(False)
            event = json.loads(raw)
            server.audit_log.append(event)
            self._ack(True)
        except Exception as exc:
            print(f"audit-receiver error={type(exc).__name__}", file=sys.stderr, flush=True)
            self._ack(False)

    def _ack(self, accepted: bool) -> None:
        self.wfile.write((b'{"accepted":true}\n' if accepted else b'{"accepted":false}\n'))
        self.wfile.flush()


class _AuditServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, path: str, allowed_uids: set[int], audit_log: AuditLog):
        self.allowed_uids, self.audit_log = allowed_uids, audit_log
        super().__init__(path, _AuditRequestHandler)


def serve(path: str = SOCKET_PATH, log_dir: Path = LOG_DIR, allowed_uids: set[int] | None = None) -> None:
    if os.path.lexists(path):
        raise RuntimeError("audit socket already exists")
    if allowed_uids is None:
        raw = os.environ.get("HERMES_AUDIT_CLIENT_UIDS", "")
        if not raw or any(not item.strip().isdigit() for item in raw.split(",")):
            raise RuntimeError("audit client UID list is not configured")
        allowed_uids = {int(item.strip()) for item in raw.split(",")}
    audit_log = AuditLog(log_dir)
    os.umask(0o117)
    server = _AuditServer(path, allowed_uids, audit_log)
    try:
        os.chmod(path, 0o660)
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    serve()
