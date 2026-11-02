# Project awareness deployment gates

This source tree contains provider and service templates. It is not installed or enabled by this document.

## Required owner/admin actions

1. Review the architecture and the files under `apparmor/`, `systemd/`, and `config/` for this specific Ubuntu/Python build. The profiles are written for `/usr/bin/python3` and Python 3.14; validate paths and library loading on the target before enforcement. Load profiles in enforce mode; never use complain mode for provider activation.
2. Create distinct non-login service identities: `hermes-inventory`, `hermes-github`, `hermes-github-egress`, and `hermes-audit`; create only the client groups referenced by units. Ensure none is in sudo, wheel, container-admin, device-admin, or the Hermes user group. Set an explicit UID for the Hermes gateway and audit clients in root-owned `/etc/hermes-project-awareness/runtime.env` (mode 0640, owned by root and a narrowly scoped reader group).
3. Install this package read-only at `/opt/hermes-project-awareness`; install AppArmor profiles and systemd units through the host's reviewed change process. Copy `config/runtime.env.example` to the root-owned runtime environment file and fill only the numeric UIDs for the gateway, GitHub provider, and audit clients. Validate `systemd-analyze verify` and `apparmor_parser` before enabling. Verify socket paths/groups and peer UIDs against actual IDs. Never loosen a profile because a test fails without reviewing the needed access.
4. Create `/etc/hermes-inventory/sources.toml` from the example as root, exact-path only, mode 0640. Confirm every path is readable by the inventory UID and visible in its mount namespace, and every other path is denied by AppArmor. Do not add home/model/project paths until each exact path and exposed fields are owner-approved. The example intentionally leaves model catalog, project directory, and service inventory unavailable.
5. For GitHub, an owner creates and installs a GitHub App for this one repository with only contents/issues/pull-request read permissions. Store its private key through root-managed systemd credentials; do not put key material in `.env`, Hermes config, or the repository. Set numeric App and installation IDs in `/etc/hermes-project-awareness/github.env`. Leave `github-egress-policy-approved` absent until an administrator has implemented and tested a narrow resolver/API CIDR egress policy; the unit otherwise denies all IP networking.
6. Create `/etc/hermes-project-awareness/authorized-whatsapp-senders` root-owned, mode 0640, empty by default. Add only owner-confirmed canonical sender IDs to authorize. Never substitute a display name. The existing WhatsApp allow-all option does not grant project-data access.
7. Review the Hermes v0.22.5 example config, install the plugin, and merge only the two MCP servers and the explicit WhatsApp toolset into `default`. Verify `hermes-whatsapp` tool membership before and after; no `frameworklab-*` raw provider tools may be in WhatsApp toolsets. Do not modify the `frameworklab` profile or OpenCode launcher/bridge.
8. Start only the audit service first, check protected log ownership and permissions, then provider services. Do not restart WhatsApp until provider smoke tests and profile/tool visibility checks pass. A gateway restart may interrupt the existing transport; schedule and observe it on the actual host.

## Tests to record before the WhatsApp demonstration

- Unit tests: `python3 -m unittest -v tests.test_hermes_project_awareness`.
- Syntax: `python3 -m py_compile integrations/hermes_project_awareness/*.py integrations/hermes_project_awareness/hermes_plugin/__init__.py`.
- Host policy: `apparmor_parser` syntax plus enforce-mode confirmation; systemd unit verification; negative reads for Hermes credentials, unrelated home files, arbitrary `/etc`, and unapproved model paths; no sudo/capabilities/IP route on inventory UID.
- IPC: wrong UID and invalid schema rejected for both providers; audit socket failure suppresses data; hash-chain tamper prevents audit service startup.
- GitHub: test repository-only App auth, documented endpoints, pagination/partial state, API errors, TLS failure, and absence of mutation methods. Confirm egress fails to all destinations except the approved API policy.
- Hermes: validate MCP initialize/tools-list/call against installed Hermes; ensure WhatsApp sees wrapper only; verify allowlisted DM works and unauthorized/group/missing-context senders get no data.
- End-to-end: demonstrate the exact request through WhatsApp and keep a redacted transcript plus source links and timestamps as review evidence.

Do not claim completion until all end-to-end criteria in `HERMES_PROJECT_AWARENESS_ARCHITECTURE.md` pass.
