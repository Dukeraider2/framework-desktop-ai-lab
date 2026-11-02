from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from integrations.hermes_project_awareness import inventory, mcp_stdio
from integrations.hermes_project_awareness.evidence import validate_claim
from integrations.hermes_project_awareness.github import (
    GitHubProvider, GitHubProviderError, GitHubSettings,
)
from integrations.hermes_project_awareness.audit_service import AuditLog
from integrations.hermes_project_awareness import mcp_client
from integrations.hermes_project_awareness.report import build_report, render_report
from integrations.hermes_project_awareness import hermes_plugin
from integrations.hermes_project_awareness.hermes_plugin import _sender_allowed


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def request(self, method, path, headers, body=None):
        self.calls.append((method, path, headers, body))
        return self.responses[path]


def github_provider(responses):
    provider = GitHubProvider(GitHubSettings("123", "456", "/run/credentials/test", "/run/proxy.sock"),
                              FakeTransport(responses))
    provider.auth.get = lambda: "test-read-only-token"
    return provider


def github_snapshot(kind, records, *, status="ok", url="https://github.com/Dukeraider2/framework-desktop-ai-lab/issues?q=is%3Aopen"):
    timestamp = "2026-11-01T12:00:00+00:00"
    return {"provider_id": "github", "schema_version": "1.0", "observed_at": timestamp,
            "status": status, "coverage": [kind], "records": records, "partial_reason": None,
            "evidence": [{"evidence_id": f"gh:{kind}", "provider": "github", "kind": kind,
                          "observed_at": timestamp, "summary": "Fixture evidence", "source_url": url,
                          "source_ref": kind}]}


class GitHubProviderTests(unittest.TestCase):
    def test_repository_summary_uses_only_fixed_read_endpoint(self):
        path = "/repos/Dukeraider2/framework-desktop-ai-lab"
        provider = github_provider({path: (200, {}, json.dumps({"full_name": "Dukeraider2/framework-desktop-ai-lab",
                                                                "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab",
                                                                "default_branch": "main"}).encode())})
        result = provider.call("repository_summary")
        self.assertEqual(result["records"][0]["default_branch"], "main")
        self.assertEqual(provider.transport.calls[0][0], "GET")
        self.assertEqual(result["evidence"][0]["source_url"], "https://github.com/Dukeraider2/framework-desktop-ai-lab")

    def test_rejects_unknown_operation_and_path_traversal(self):
        provider = github_provider({})
        with self.assertRaises(GitHubProviderError):
            provider.call("delete_repository")
        with self.assertRaises(GitHubProviderError):
            provider.call("read_document", {"path": "../private"})
        self.assertEqual(provider.transport.calls, [])

    def test_issue_operation_drops_pull_requests_and_marks_partial_pages(self):
        path = "/repos/Dukeraider2/framework-desktop-ai-lab/issues?state=open&per_page=100&sort=updated&direction=desc"
        rows = [{"number": 5, "title": "Issue", "state": "open", "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/5", "labels": []},
                {"number": 6, "title": "PR issue mirror", "state": "open", "pull_request": {"url": "x"}}]
        provider = github_provider({path: (200, {"link": '<https://api.github.com/page=2>; rel="next"'}, json.dumps(rows).encode())})
        result = provider.call("issues", {"state": "open"})
        self.assertEqual(result["coverage"], ["issues_open"])
        self.assertEqual([row["number"] for row in result["records"]], [5])
        self.assertEqual(result["status"], "partial")
        self.assertNotIn("assignees", result["records"][0])

    def test_invalid_branch_is_rejected_before_transport(self):
        provider = github_provider({})
        with self.assertRaises(GitHubProviderError):
            provider.call("recent_commits", {"branch": "main?redirect=host"})
        self.assertEqual(provider.transport.calls, [])

    def test_untrusted_repository_links_are_removed(self):
        path = "/repos/Dukeraider2/framework-desktop-ai-lab"
        provider = github_provider({path: (200, {}, json.dumps({
            "full_name": "Dukeraider2/framework-desktop-ai-lab",
            "html_url": "https://attacker.example/steal",
            "default_branch": "main",
        }).encode())})
        result = provider.call("repository_summary")
        self.assertIsNone(result["records"][0]["html_url"])
        self.assertEqual(result["evidence"][0]["source_url"], "https://github.com/Dukeraider2/framework-desktop-ai-lab")


class InventoryTests(unittest.TestCase):
    def _manifest(self, root: Path, *, source_path: Path, fields=None, kind="file", format_name="os_release") -> Path:
        allowed = str(source_path)
        field_line = ", ".join(json.dumps(x) for x in (fields or ["PRETTY_NAME"]))
        text = (f'allowed_paths = [{json.dumps(allowed)}]\n\n[[sources.host_summary]]\n'
                f'id = "os_release"\nkind = "{kind}"\npath = {json.dumps(allowed)}\n')
        if kind == "file":
            text += f'format = "{format_name}"\nfields = [{field_line}]\n'
        manifest = root / "sources.toml"
        manifest.write_text(text, encoding="utf-8")
        manifest.chmod(0o600)
        return manifest

    def test_reads_only_allowlisted_scalar_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "os-release"
            source.write_text('PRETTY_NAME="Test OS"\nVERSION_ID="1"\nSECRET="no"\n')
            manifest = self._manifest(root, source_path=source, fields=["PRETTY_NAME", "VERSION_ID"])
            result = inventory.collect("host_summary", manifest=manifest, require_root_owner=False,
                                       observed_at="2026-11-01T12:00:00+00:00")
            self.assertEqual(result["sources"][0]["fields"], {"PRETTY_NAME": "Test OS", "VERSION_ID": "1"})
            self.assertNotIn(str(source), json.dumps(result))
            self.assertEqual(result["evidence"][0]["provider"], "frameworkai1_inventory")

    def test_manifest_sensitive_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "config.json"
            source.write_text('{"api_token":"secret","model":"local"}')
            manifest = self._manifest(root, source_path=source, fields=["api_token"], format_name="json")
            with self.assertRaises(inventory.InventoryError):
                inventory.collect("host_summary", manifest=manifest, require_root_owner=False)

    def test_symlink_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real"
            real.write_text('PRETTY_NAME="Test"')
            link = root / "link"
            link.symlink_to(real)
            manifest = self._manifest(root, source_path=link)
            with self.assertRaises(inventory.InventoryError):
                inventory.collect("host_summary", manifest=manifest, require_root_owner=False)

    def test_missing_approved_source_is_partial_not_an_empty_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            present = root / "present"
            present.write_text('PRETTY_NAME="Test"')
            missing = root / "optional"
            manifest = root / "sources.toml"
            manifest.write_text(
                f'allowed_paths = [{json.dumps(str(present))}, {json.dumps(str(missing))}]\n'
                f'[[sources.host_summary]]\nid="os_release"\nkind="file"\npath={json.dumps(str(present))}\n'
                'format="os_release"\nfields=["PRETTY_NAME"]\n'
                f'[[sources.host_summary]]\nid="optional_gpu"\nkind="file"\npath={json.dumps(str(missing))}\n'
                'format="sysfs_text"\nfields=["value"]\n', encoding="utf-8")
            manifest.chmod(0o600)
            result = inventory.collect("host_summary", manifest=manifest, require_root_owner=False)
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["unavailable_sources"], ["optional_gpu"])
            self.assertEqual(len(result["sources"]), 1)

    def test_unapproved_probe_rejected(self):
        with self.assertRaises(inventory.InventoryError):
            inventory.collect("shell", manifest=Path("/does/not/exist"))


class MCPAdapterTests(unittest.TestCase):
    def test_provider_tool_list_is_read_only_and_input_closed(self):
        response = mcp_stdio._dispatch("github", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))
        self.assertFalse(any("write" in tool["name"] or "delete" in tool["name"] for tool in tools))

    def test_mcp_call_forwards_only_fixed_operation(self):
        with mock.patch.object(mcp_stdio, "request", return_value={"result": {"provider_id": "github"}}) as request:
            response = mcp_stdio._dispatch("github", {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                                        "params": {"name": "repository_summary", "arguments": {}}})
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(json.loads(response["result"]["content"][0]["text"])["provider_id"], "github")
        self.assertEqual(request.call_args.args[1]["operation"], "repository_summary")

    def test_unknown_mcp_tool_and_extra_arguments_fail_closed(self):
        bad_name = mcp_stdio._dispatch("github", {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
                                                   "params": {"name": "delete", "arguments": {}}})
        extra = mcp_stdio._dispatch("inventory", {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                                   "params": {"name": "host_summary", "arguments": {"path": "/etc/passwd"}}})
        self.assertIn("error", bad_name)
        self.assertIn("error", extra)

    def test_hermes_mcp_client_builds_bounded_stdio_exchange(self):
        payload = {"provider_id": "github", "schema_version": "1.0", "status": "ok",
                   "coverage": ["repository_summary"], "observed_at": "2026-11-01T12:00:00Z",
                   "records": [], "evidence": []}
        stdout = (json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}) + "\n" +
                  json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"isError": False,
                      "content": [{"type": "text", "text": json.dumps(payload)}]}}) + "\n").encode()
        completed = types.SimpleNamespace(returncode=0, stdout=stdout)
        with mock.patch.object(mcp_client.subprocess, "run", return_value=completed) as run:
            result = mcp_client.call_provider("github", "repository_summary", request_id="a" * 32)
        self.assertEqual(result["provider_id"], "github")
        call = run.call_args
        self.assertEqual(call.args[0][-3:], ["-m", "integrations.hermes_project_awareness.mcp_stdio", "github"])
        self.assertEqual(call.args[0][-1], "github")
        wire = [json.loads(line) for line in call.kwargs["input"].splitlines()]
        self.assertEqual(wire[-1]["params"]["arguments"]["request_id"], "a" * 32)
        self.assertNotIn("GITHUB", call.kwargs["env"])


class ReportTests(unittest.TestCase):
    def test_report_links_each_project_claim_to_authoritative_evidence(self):
        snapshots = [
            github_snapshot("pull_requests_open", [{"number": 8, "title": "Work", "state": "open",
                                                      "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab/pull/8"}]),
            github_snapshot("pull_requests_closed", [{"number": 7, "title": "Finished", "state": "closed", "merged_at": "2026-10-31T00:00:00Z",
                                                        "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab/pull/7"}]),
            github_snapshot("issues_open", [{"number": 9, "title": "Task", "state": "open", "labels": [],
                                               "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/9"}]),
        ]
        report = build_report(snapshots)
        self.assertTrue(all(c["evidence_ids"] for c in report["claims"] if c["classification"] != "Unverified"))
        rendered = render_report(report)
        self.assertIn("Verified complete", rendered)
        self.assertIn("In progress", rendered)
        self.assertIn("Unverified", rendered)
        self.assertIn("pull/7", rendered)
        self.assertIn("issues/9", rendered)

    def test_closed_issue_is_complete_only_with_completed_reason(self):
        report = build_report([github_snapshot("issues_closed", [
            {"number": 10, "title": "Done", "state": "closed", "state_reason": "completed",
             "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/10"},
            {"number": 11, "title": "Not planned", "state": "closed", "state_reason": "not_planned",
             "html_url": "https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/11"},
        ])])
        claims = {row["text"]: row["classification"] for row in report["claims"]}
        self.assertEqual(claims["Completed issue [#10](https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/10): Done"], "Verified complete")
        self.assertEqual(claims["Closed issue [#11](https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/11): Not planned"], "Unverified")

    def test_unverified_claims_need_reason_and_unknown_references_fail(self):
        with self.assertRaises(ValueError):
            validate_claim({"classification": "Verified complete", "text": "Done", "evidence_ids": []}, set())
        with self.assertRaises(ValueError):
            validate_claim({"classification": "Unverified", "text": "Unknown", "evidence_ids": []}, set())
        with self.assertRaises(ValueError):
            validate_claim({"classification": "In progress", "text": "Unknown", "evidence_ids": ["missing"]}, set())


class SenderAuthorizationTests(unittest.TestCase):
    def test_exact_authorized_direct_sender_passes_and_other_context_fails(self):
        fake_context = types.ModuleType("gateway.session_context")
        values = {"HERMES_SESSION_PLATFORM": "whatsapp", "HERMES_SESSION_CHAT_TYPE": "dm",
                  "HERMES_SESSION_USER_ID": "15551234567@s.whatsapp.net",
                  "HERMES_SESSION_CHAT_ID": "15551234567@s.whatsapp.net"}
        fake_context.get_session_env = lambda key, default="": values.get(key, default)
        fake_gateway = types.ModuleType("gateway")
        with tempfile.TemporaryDirectory() as td:
            allowlist = Path(td) / "senders"
            allowlist.write_text("15551234567@s.whatsapp.net\n")
            allowlist.chmod(0o640)
            with mock.patch.dict(sys.modules, {"gateway": fake_gateway, "gateway.session_context": fake_context}):
                self.assertTrue(_sender_allowed(allowlist_path=allowlist, require_root_owner=False))
                values["HERMES_SESSION_USER_ID"] = "15550000000@s.whatsapp.net"
                self.assertFalse(_sender_allowed(allowlist_path=allowlist, require_root_owner=False))
                values["HERMES_SESSION_PLATFORM"] = "telegram"
                self.assertFalse(_sender_allowed(allowlist_path=allowlist, require_root_owner=False))
                values["HERMES_SESSION_PLATFORM"] = "whatsapp"
                values["HERMES_SESSION_CHAT_TYPE"] = "group"
                self.assertFalse(_sender_allowed(allowlist_path=allowlist, require_root_owner=False))

    def test_audit_failure_prevents_provider_access(self):
        with mock.patch.object(hermes_plugin, "_sender_allowed", return_value=True), \
             mock.patch.object(hermes_plugin, "audit_record", side_effect=OSError("audit unavailable")), \
             mock.patch.object(hermes_plugin, "call_provider") as provider_call:
            response = hermes_plugin._run_status({"focus": "overall"})
        self.assertIn("No provider data was requested", response)
        provider_call.assert_not_called()

    def test_plugin_registers_only_the_authorized_status_tool(self):
        class Context:
            def __init__(self):
                self.tools = []
            def register_tool(self, **kwargs):
                self.tools.append(kwargs)
        context = Context()
        hermes_plugin.register(context)
        self.assertEqual(len(context.tools), 1)
        self.assertEqual(context.tools[0]["name"], "frameworklab_project_status")
        self.assertEqual(context.tools[0]["toolset"], "frameworklab-awareness")


class AuditLogTests(unittest.TestCase):
    def test_hash_chained_log_verifies_and_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            directory.chmod(0o700)
            log = AuditLog(directory)
            event = {"request_id": "a" * 32, "event": "started", "provider": "hermes",
                     "operation": "project_status"}
            first = log.append(event)
            self.assertEqual(len(first), 64)
            self.assertEqual(AuditLog(directory)._last_hash, first)
            path = next(directory.glob("audit-*.jsonl"))
            path.write_text(path.read_text().replace('"result":"ok"', '"result":"error"'))
            with self.assertRaises(RuntimeError):
                AuditLog(directory)

    def test_audit_schema_rejects_sensitive_or_unbounded_payloads(self):
        from integrations.hermes_project_awareness.audit_service import _validate_event
        with self.assertRaises(ValueError):
            _validate_event({"request_id": "a" * 32, "event": "started", "provider": "hermes",
                             "operation": "project_status", "message": "do not log content"})


if __name__ == "__main__":
    unittest.main()
