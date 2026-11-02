"""Hermes stdio MCP adapter. It exposes only fixed read operations and forwards over AF_UNIX."""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Any

from .ipc import request


PROVIDERS = {
    "github": {
        "socket": "/run/hermes-github/provider.sock",
        "operations": {
            "repository_summary": {"type": "object", "properties": {}, "additionalProperties": False},
            "read_document": {"type": "object", "properties": {"path": {"type": "string"}, "ref": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
            "tree": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"], "additionalProperties": False},
            "recent_commits": {"type": "object", "properties": {"branch": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 30}}, "additionalProperties": False},
            "issues": {"type": "object", "properties": {"state": {"type": "string", "enum": ["open", "closed", "all"]}}, "additionalProperties": False},
            "pull_requests": {"type": "object", "properties": {"state": {"type": "string", "enum": ["open", "closed", "all"]}}, "additionalProperties": False},
            "pull_request_reviews": {"type": "object", "properties": {"number": {"type": "integer", "minimum": 1}}, "required": ["number"], "additionalProperties": False},
        },
    },
    "inventory": {
        "socket": "/run/hermes-inventory/provider.sock",
        "operations": {
            name: {"type": "object", "properties": {}, "additionalProperties": False}
            for name in ("host_summary", "model_catalog", "project_directories", "service_inventory")
        },
    },
}

for _provider in PROVIDERS.values():
    for _schema in _provider["operations"].values():
        _schema["properties"]["request_id"] = {"type": "string", "pattern": "^[0-9a-f]{32}$"}


def _write(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":"), ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _dispatch(provider: str, message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
            "serverInfo": {"name": f"frameworklab-{provider}-read-only", "version": "0.1.0"}}}
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        tools = [{"name": name, "description": f"Read-only {provider} operation: {name}",
                  "inputSchema": schema, "annotations": {"readOnlyHint": True, "destructiveHint": False}}
                 for name, schema in PROVIDERS[provider]["operations"].items()]
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict) or set(params) - {"name", "arguments"}:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "invalid arguments"}}
        operation, args = params.get("name"), params.get("arguments", {})
        schema = PROVIDERS[provider]["operations"].get(operation)
        if schema is None or not isinstance(args, dict) or set(args) - set(schema.get("properties", {})):
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "operation or arguments are not allowed"}}
        try:
            args = dict(args)
            request_id = args.pop("request_id", None) or uuid.uuid4().hex
            response = request(PROVIDERS[provider]["socket"],
                               {"request_id": request_id, "operation": operation, "arguments": args})
            if "error" in response:
                return {"jsonrpc": "2.0", "id": msg_id, "result": {"isError": True, "content": [{"type": "text", "text": response["error"]}]}}
            rendered = json.dumps(response.get("result"), ensure_ascii=False, separators=(",", ":"))
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": rendered}], "isError": False}}
        except Exception:
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"isError": True, "content": [{"type": "text", "text": "provider is unavailable"}]}}
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "method not found"}}


def run(provider: str) -> None:
    if provider not in PROVIDERS:
        raise SystemExit("provider must be github or inventory")
    for line in sys.stdin.buffer:
        if len(line) > 1_048_576:
            break
        try:
            message = json.loads(line)
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise ValueError
            response = _dispatch(provider, message)
        except Exception:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "invalid JSON-RPC message"}}
        if response is not None and "id" in response:
            _write(response)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PROVIDERS:
        raise SystemExit("usage: mcp_stdio.py github|inventory")
    run(sys.argv[1])
