# Agent identities and GitHub communication

**Status:** Seven persistent Hermes identity distributions are implemented and installed locally. Their constrained profiles currently have no model binding, GitHub MCP, WhatsApp channel, or assignment/response integration. GitHub coordination is therefore not yet operational for these identities.

## Identity and model separation

`agents/registry.json` is the stable organizational directory. Each record names one Hermes profile distribution under `agents/profiles/<id>/`. A profile contains its own `SOUL.md` and constrained `config.yaml`. The SOUL defines identity and conduct; it contains no model, provider, credential, channel, or tool authorization. A model can be changed in that profile's model configuration without changing the identity. The local installations are in `~/.hermes/profiles/<id>` and are managed by Hermes profile distributions, so identity persists independently of session memory and process restarts.

All seven are fictional personas inspired by the public characteristics and intellectual contributions of the named people. They do not claim to be those individuals. Each SOUL has the same requirement for independent conclusions, evidence-backed disagreement, uncertainty, and revision when evidence changes. Moncappy coordinates but remains subject to review.

Each profile starts with no selected model, no plugins, no MCP servers, and only the local `todo`, `memory`, `session_search`, and `clarify` CLI toolsets. It has no terminal, browser, delegation, WhatsApp, or GitHub capability. This is an intentional fail-closed baseline; the profile cannot act on a GitHub assignment until a reviewed profile-specific integration is installed. Do not clone `default` or copy its `.env` into agent profiles.

## GitHub as organizational record

GitHub Issues, PRs, comments, reviews, and versioned documentation remain the durable work and decision record. Internal stable agent IDs identify the intended author/recipient; actual GitHub events remain authored by the configured human or GitHub App account. The current profiles cannot comment, assign work, create branches, or approve PRs. No agent receives a GitHub credential.

A safe event path is implemented as a dedicated poller using the existing repository-scoped read-only GitHub provider. It polls bounded issue-comment and assignment endpoints over AF_UNIX, then emits authorized tasks into a durable queue. `agents/dispatch_policy.py` accepts only records created by the provider-sealed factory; model output cannot set an authentication boolean or construct a trusted record. It requires the fixed repository, allowlisted actor, exact assignment label, one explicit `/agent run <id> <action>` directive, and static per-agent action allowlist. Plain mentions are notifications only. `agents/event_ledger.py` atomically stores event IDs, decisions, audit hashes, tasks, and cursor updates; duplicate IDs are rejected. `agents/task_router.py` exposes static claims/completions but does not launch a model or write to GitHub. The code is unit-tested; host services, credentials, and live event routing are not yet operationally demonstrated.

Before a task is dispatched, the coordinator must validate all of the following:

1. Repository owner/name and event type are in a fixed allowlist.
2. The GitHub event is obtained over authenticated provider access; comments are treated as untrusted text.
3. The requesting actor is in a separately administrator-managed maintainer allowlist.
4. The issue/PR is in scope and the assignee/explicit task directive matches a registered agent ID.
5. The requested action is in that profile's static capability policy and any required human approval is recorded.
6. The request is assigned a durable event ID and written to the audit log before dispatch.

Plain `@agent` mentions are notifications only. They never authorize an action. An agent may dispute another agent's conclusion by citing source records, but it cannot grant permissions to itself or another agent.

Posting replies, assigning GitHub work, and submitting review records require a separate fixed GitHub write adapter and repository-only GitHub App installation. The minimum proposed App permissions are Metadata: read, Contents: read, Issues: read/write, and Pull requests: read/write. Do not grant Contents: write, Administration, Actions, or organization permissions. Keep this App's key out of Hermes profiles and workers, separate from the read-only provider credential. The adapter must allow only typed operations (for example, comment on an existing issue/PR or request a review); it must reject arbitrary REST paths, raw HTTP methods, repository selection, commit/push/merge, and approval of the writer's own implementation. Write operations need an independent audit record and authorization check. This component is not implemented. The repository administrator must create/install the separate App and grant these exact repository-scoped permissions; the existing read-only App/provider must remain read-only.

## Worker and reviewer separation

Worker agents receive only their fixed profile tools and a bounded task package. They do not receive host mounts, host sockets, provider credentials, arbitrary Podman access, or write-capable GitHub clients. The existing OpenCode launcher and bridge remain separate and unchanged; no founding persona is mapped to a shell-enabled OpenCode role by default. A worker's output is an untrusted proposal. An independent reviewer with read-only evidence access checks it; the implementer cannot approve its own work. Human branch protection and repository review rules remain authoritative.

## Audit and recovery

The event ledger stores event delivery ID, issue number, sender login, matched agent ID, authorization decision, task ID, body digest, and timestamps. It does not retain comment bodies, GitHub credentials, or raw environment values. A dedicated service identity owns the 0600 SQLite database under a 0700 state directory. Hash chaining detects edits to retained records; a separately protected checkpoint is required to detect full-history replacement. Event insertion, audit append, queue creation, and cursor update share a transaction. Provider, schema, audit, cursor, or deduplication failure prevents cursor advancement. Host-side ownership, retention, and external checkpoint validation remain to be confirmed.

## Implementation state and owner dependencies

Provider adapters, the event poller/ledger/router, MCP tools, plugin wrapper, identity distributions, and deployment templates exist in this source tree. They are not installed as a live provider or model runner on the host. All seven identities remain model-unset. GitHub App credentials, approved WhatsApp sender enrollment, service identities, AppArmor/systemd enforcement, MCP profile merge, gateway diagnosis/recovery, and live demonstrations remain outstanding. A separate write-capable GitHub App and adapter are not implemented and require repository-owner authorization.
