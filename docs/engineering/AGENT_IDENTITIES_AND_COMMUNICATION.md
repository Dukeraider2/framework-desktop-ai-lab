# Agent identities and GitHub communication

**Status:** Seven persistent Hermes identity distributions are implemented and installed locally. Their constrained profiles currently have no model binding, GitHub MCP, WhatsApp channel, or assignment/response integration. GitHub coordination is therefore not yet operational for these identities.

## Identity and model separation

`agents/registry.json` is the stable organizational directory. Each record names one Hermes profile distribution under `agents/profiles/<id>/`. A profile contains its own `SOUL.md` and constrained `config.yaml`. The SOUL defines identity and conduct; it contains no model, provider, credential, channel, or tool authorization. A model can be changed in that profile's model configuration without changing the identity. The local installations are in `~/.hermes/profiles/<id>` and are managed by Hermes profile distributions, so identity persists independently of session memory and process restarts.

All seven are fictional personas inspired by the public characteristics and intellectual contributions of the named people. They do not claim to be those individuals. Each SOUL has the same requirement for independent conclusions, evidence-backed disagreement, uncertainty, and revision when evidence changes. Moncappy coordinates but remains subject to review.

Each profile starts with no selected model, no plugins, no MCP servers, and only the local `todo`, `memory`, `session_search`, and `clarify` CLI toolsets. It has no terminal, browser, delegation, WhatsApp, or GitHub capability. This is an intentional fail-closed baseline; the profile cannot act on a GitHub assignment until a reviewed profile-specific integration is installed. Do not clone `default` or copy its `.env` into agent profiles.

## GitHub as organizational record

GitHub Issues, PRs, comments, reviews, and versioned documentation remain the durable work and decision record. Internal stable agent IDs identify the intended author/recipient; actual GitHub events remain authored by the configured human or GitHub App account. The current profiles cannot comment, assign work, create branches, or approve PRs. No agent receives a GitHub credential.

A safe event path is a dedicated polling coordinator using the existing repository-scoped read-only GitHub provider. It keeps a durable cursor and deduplicated event ledger, polls bounded issue/PR/comment/review endpoints, and emits normalized work notices to the agent control plane. This avoids opening an inbound host listener and reuses the current fixed GitHub API egress boundary. `agents/dispatch_policy.py` implements the pure fail-closed authorization decision for one normalized comment; it requires the authenticated source flag, fixed repository, allowlisted actor, exactly one `/agent run <id> <action>` directive, and a static per-agent action allowlist. It does not authenticate GitHub, persist a cursor, deduplicate deliveries, or execute tasks. The scheduler, event ledger, routing adapter, and operational tests are not implemented.

Before a task is dispatched, the coordinator must validate all of the following:

1. Repository owner/name and event type are in a fixed allowlist.
2. The GitHub event is obtained over authenticated provider access; comments are treated as untrusted text.
3. The requesting actor is in a separately administrator-managed maintainer allowlist.
4. The issue/PR is in scope and the assignee/explicit task directive matches a registered agent ID.
5. The requested action is in that profile's static capability policy and any required human approval is recorded.
6. The request is assigned a durable event ID and written to the audit log before dispatch.

Plain `@agent` mentions are notifications only. They never authorize an action. An agent may dispute another agent's conclusion by citing source records, but it cannot grant permissions to itself or another agent.

Posting replies, assigning GitHub work, and submitting review records require a separate fixed GitHub write adapter and a repository installation with only the required Issues and Pull Requests write permissions. Keep that credential out of Hermes profiles and workers. The adapter must allow only typed operations (for example, comment on an existing issue/PR or request a review); it must reject arbitrary REST paths, raw HTTP methods, repository selection, commit/push/merge, and approval of the writer's own implementation. Write operations need an independent audit record and authorization check. This component is not implemented. The repository administrator must grant the GitHub App write permissions and install/update it; the existing read-only App/provider must remain read-only.

## Worker and reviewer separation

Worker agents receive only their fixed profile tools and a bounded task package. They do not receive host mounts, host sockets, provider credentials, arbitrary Podman access, or write-capable GitHub clients. The existing OpenCode launcher and bridge remain separate and unchanged; no founding persona is mapped to a shell-enabled OpenCode role by default. A worker's output is an untrusted proposal. An independent reviewer with read-only evidence access checks it; the implementer cannot approve its own work. Human branch protection and repository review rules remain authoritative.

## Audit and recovery

The planned event ledger records event delivery ID, repository, issue/PR number, sender login, matched agent ID, authorization decision, task ID, provider evidence IDs, and timestamps. It does not record WhatsApp message bodies, GitHub credentials, or raw environment values. A protected owner-controlled service identity owns the append-only ledger. Hash chaining detects edits to retained records; a separately protected checkpoint is needed to detect full-history replacement. If event verification, identity, audit write, durable cursor, or deduplication state fails, dispatch stops and no write is attempted. Audit loss must never silently advance the cursor.

## Implementation state and owner dependencies

The read-only GitHub provider, inventory provider, MCP adapters, and WhatsApp report wrapper are source-only templates in this workspace. They are not installed or configured on the host. GitHub App installation credentials and exact approved WhatsApp sender enrollment are absent from this integration. Service identities, AppArmor/systemd enforcement, MCP profile config, and gateway recovery need host-side provisioning. A write-capable GitHub App permission change requires repository-owner participation.
