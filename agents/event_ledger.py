"""Durable, fail-closed event and dispatch ledger (SQLite, local service only)."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any


class LedgerError(RuntimeError):
    pass


class EventLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        parent = self.path.parent
        try:
            parent_stat = parent.lstat()
        except OSError as exc:
            raise LedgerError("ledger parent directory is unavailable") from exc
        if not stat.S_ISDIR(parent_stat.st_mode) or stat.S_ISLNK(parent_stat.st_mode) or parent_stat.st_mode & 0o022:
            raise LedgerError("ledger parent directory permissions are unsafe")
        if self.path.exists() and (self.path.is_symlink() or not self.path.is_file()):
            raise LedgerError("ledger path must be a regular file")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        db = self._connect()
        try:
            db.executescript("""
                    CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS events(
                      event_id TEXT PRIMARY KEY, body_sha256 TEXT NOT NULL,
                      actor TEXT NOT NULL, issue_number INTEGER NOT NULL,
                      agent_id TEXT, action TEXT, authorized INTEGER NOT NULL,
                      reason TEXT NOT NULL, observed_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS tasks(
                      task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id),
                      agent_id TEXT NOT NULL, action TEXT NOT NULL,
                      issue_number INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
                      created_at TEXT NOT NULL, claimed_at TEXT, result_ref TEXT
                    );
                    CREATE TABLE IF NOT EXISTS audit(
                      sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                      payload TEXT NOT NULL, previous_hash TEXT NOT NULL,
                      entry_hash TEXT NOT NULL UNIQUE
                    );
                """)
        except sqlite3.Error as exc:
            raise LedgerError("could not initialize durable event ledger") from exc
        finally:
            db.close()

    def cursor(self) -> tuple[str, int] | None:
        db = self._connect()
        try:
            rows = dict(db.execute("SELECT key, value FROM metadata WHERE key IN ('since','page')").fetchall())
        finally:
            db.close()
        if not rows:
            return None
        if set(rows) != {"since", "page"}:
            raise LedgerError("event cursor is incomplete")
        try:
            page = int(rows["page"])
        except ValueError as exc:
            raise LedgerError("event cursor is malformed") from exc
        if page < 1 or page > 1000:
            raise LedgerError("event cursor is outside its permitted range")
        return rows["since"], page

    def bootstrap(self, since: str) -> None:
        with self._transaction() as db:
            existing = db.execute("SELECT value FROM metadata WHERE key='since'").fetchone()
            if existing:
                return
            db.execute("INSERT INTO metadata(key,value) VALUES('since',?)", (since,))
            db.execute("INSERT INTO metadata(key,value) VALUES('page','1')")
            self._append_audit(db, {"event": "cursor_bootstrapped", "since": since})

    def process_page(self, records: list[dict[str, Any]], decisions: list[Any], *,
                     body_hashes: list[str], next_since: str, next_page: int,
                     observed_at: str) -> dict[str, int]:
        if len(records) != len(decisions) or len(records) != len(body_hashes):
            raise LedgerError("event processing batch is inconsistent")
        if next_page < 1 or next_page > 1000:
            raise LedgerError("next page is outside its permitted range")
        counts = {"new": 0, "duplicates": 0, "authorized": 0, "denied": 0}
        try:
            with self._transaction() as db:
                for record, decision, digest in zip(records, decisions, body_hashes, strict=True):
                    event_id = f"github-comment:{record['id']}"
                    existing = db.execute("SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone()
                    if existing:
                        counts["duplicates"] += 1
                        self._append_audit(db, {"event": "duplicate_rejected", "event_id": event_id})
                        continue
                    allowed = bool(decision.allowed)
                    agent_id = decision.agent_id if allowed else None
                    action = decision.action if allowed else None
                    reason = str(decision.reason)[:80]
                    db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)",
                               (event_id, digest, str(record.get("actor", ""))[:100],
                                int(record["issue_number"]), agent_id, action, int(allowed), reason, observed_at))
                    counts["new"] += 1
                    if allowed:
                        db.execute("INSERT INTO tasks(event_id,agent_id,action,issue_number,created_at) VALUES(?,?,?,?,?)",
                                   (event_id, agent_id, action, int(record["issue_number"]), observed_at))
                        counts["authorized"] += 1
                    else:
                        counts["denied"] += 1
                    self._append_audit(db, {"event": "directive_authorized" if allowed else "directive_denied",
                                            "event_id": event_id, "issue_number": int(record["issue_number"]),
                                            "actor": str(record.get("actor", ""))[:100],
                                            "agent_id": agent_id, "action": action, "reason": reason,
                                            "body_sha256": digest})
                db.execute("INSERT INTO metadata(key,value) VALUES('since',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (next_since,))
                db.execute("INSERT INTO metadata(key,value) VALUES('page',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(next_page),))
                self._append_audit(db, {"event": "cursor_advanced", "since": next_since, "page": next_page,
                                        "batch_size": len(records)})
        except (sqlite3.Error, KeyError, TypeError, ValueError) as exc:
            raise LedgerError("event batch was not durably processed; cursor was not advanced") from exc
        return counts

    def claim_task(self, agent_id: str, *, claimed_at: str,
                   lease_expired_before: str | None = None) -> dict[str, Any] | None:
        """Claim one task for a future separately sandboxed worker adapter."""
        from agents.dispatch_policy import AGENT_ACTIONS
        if agent_id not in AGENT_ACTIONS:
            raise LedgerError("unknown agent identity")
        try:
            with self._transaction() as db:
                if lease_expired_before:
                    expired = db.execute("SELECT task_id,agent_id,event_id FROM tasks WHERE state='claimed' AND claimed_at<?",
                                         (lease_expired_before,)).fetchall()
                    db.execute("UPDATE tasks SET state='pending',claimed_at=NULL WHERE state='claimed' AND claimed_at<?",
                               (lease_expired_before,))
                    for old in expired:
                        self._append_audit(db, {"event": "task_lease_expired", "task_id": old["task_id"],
                                                "agent_id": old["agent_id"], "event_id": old["event_id"]})
                row = db.execute("SELECT task_id,event_id,agent_id,action,issue_number FROM tasks "
                                 "WHERE state='pending' AND agent_id=? ORDER BY task_id LIMIT 1", (agent_id,)).fetchone()
                if row is None:
                    return None
                db.execute("UPDATE tasks SET state='claimed',claimed_at=? WHERE task_id=? AND state='pending'",
                           (claimed_at, row["task_id"]))
                self._append_audit(db, {"event": "task_claimed", "task_id": row["task_id"],
                                        "agent_id": agent_id, "event_id": row["event_id"]})
                task = dict(row)
                if task["action"] not in AGENT_ACTIONS[agent_id]:
                    raise LedgerError("persisted task exceeds the agent capability policy")
                return task
        except sqlite3.Error as exc:
            raise LedgerError("task claim was not durably recorded") from exc

    def finish_task(self, task_id: int, *, agent_id: str, result_ref: str, completed_at: str) -> None:
        if (not isinstance(result_ref, str) or len(result_ref) > 300 or "\n" in result_ref
                or not result_ref.startswith("https://github.com/Dukeraider2/framework-desktop-ai-lab/")):
            raise LedgerError("task result reference is invalid")
        with self._transaction() as db:
            result = db.execute("UPDATE tasks SET state='complete',result_ref=? WHERE task_id=? AND state='claimed' AND agent_id=?",
                                (result_ref, task_id, agent_id))
            if result.rowcount != 1:
                raise LedgerError("task is not claimable or already complete")
            self._append_audit(db, {"event": "task_completed", "task_id": task_id,
                                    "agent_id": agent_id, "result_ref": result_ref, "completed_at": completed_at})

    def verify_audit(self) -> bool:
        previous = "0" * 64
        db = self._connect()
        try:
            rows = db.execute("SELECT payload,previous_hash,entry_hash FROM audit ORDER BY sequence").fetchall()
        finally:
            db.close()
        for row in rows:
            if row["previous_hash"] != previous:
                return False
            expected = hashlib.sha256((previous + row["payload"]).encode("utf-8")).hexdigest()
            if row["entry_hash"] != expected:
                return False
            previous = expected
        return True

    def _transaction(self):
        return _Transaction(self._connect())

    @staticmethod
    def _append_audit(db: sqlite3.Connection, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        row = db.execute("SELECT entry_hash FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
        previous = row["entry_hash"] if row else "0" * 64
        entry_hash = hashlib.sha256((previous + encoded).encode("utf-8")).hexdigest()
        db.execute("INSERT INTO audit(payload,previous_hash,entry_hash) VALUES(?,?,?)",
                   (encoded, previous, entry_hash))


class _Transaction:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def __enter__(self) -> sqlite3.Connection:
        self.connection.execute("BEGIN IMMEDIATE")
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self.connection.rollback() if exc_type else self.connection.commit()
        finally:
            self.connection.close()
        return False
