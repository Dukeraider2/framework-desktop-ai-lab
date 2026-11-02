# Hermes project awareness: host deployment and validation

This runbook is an operator handoff for PR #5 and PR #6. It does not claim that
the package has been installed. Run commands in order on `framework-ai1` from a
root-controlled terminal. Keep a maintenance window available for the gateway
restart; do not edit the existing WhatsApp configuration until the provider
smoke checks pass.

## Execution matrix

| Work item | Owner | State/evidence needed |
| --- | --- | --- |
| Bounded provider code, event ledger, dispatch policy, tests, package, docs | Implementation team | Completed in these branches; automated results recorded in PR description |
| Verify gateway's live state and exact exit cause | Host administrator | Collect commands below before taking recovery action |
| Install service identities, AppArmor and systemd policy, package files | Host administrator | Requires root and actual-host policy validation |
| Approve each inventory source and exact model directory | Repository/host owner | Explicitly review source fields and local filesystem path |
| Create/install repository-scoped GitHub App and provision private key | Repository owner plus host administrator | Needs App ID, installation ID and private key provisioned locally; never send key in chat |
| Authorize WhatsApp sender identities | User/owner | Confirm canonical `user:<id>` values out of band |
| Install plugin/MCP entries into the active Hermes profile | Host administrator | Back up config and preserve existing toolsets/channel settings |
| Collect real Ollama inventory and run model-backed sessions | Host operator and account owner | Ollama socket and actual runtime must be accessible |
| WhatsApp status, authorization-denial, agent and event end-to-end demonstrations | Live operator | Requires connected phone, credentials and services |
| Add the separate write-capable GitHub App | Repository owner authorization | Not part of these read-only credentials; defer until separately approved |

## 0. Confirm host and preserve state

Run as the Hermes account, then an administrator where marked. Save outputs in
the local change record with tokens, phone numbers, paths containing personal
data, and credential material redacted.

```sh
hostnamectl
lsb_release -a
hermes --version
hermes status
hermes gateway status
hermes profile list
hermes mcp list
hermes plugins list
systemctl status hermes-gateway.service --no-pager || true
systemctl list-units --all 'hermes*' --no-pager
```

The unit name above is a probe, not an assumption. Inspect the installed service
manager and Hermes documentation to identify the actual gateway unit before
acting. Record current profile/config backups and working WhatsApp state:

```sh
umask 077
mkdir -p "$HOME/hermes-awareness-backup"
cp -a "$HOME/.hermes/config.yaml" "$HOME/hermes-awareness-backup/config.yaml" 2>/dev/null || true
cp -a "$HOME/.hermes/profiles/default" "$HOME/hermes-awareness-backup/default-profile" 2>/dev/null || true
```

## 1. Gateway diagnostics and controlled recovery

First establish the actual service name and cause. Do not infer an exit reason
from old application logs. Replace `GATEWAY_UNIT` only after step 0 identifies
it. Commands are diagnostic and read-only:

```sh
systemctl show GATEWAY_UNIT -p LoadState -p ActiveState -p SubState -p Result -p ExecMainCode -p ExecMainStatus -p ExecMainStartTimestamp -p ExecMainExitTimestamp
systemctl status GATEWAY_UNIT --no-pager -l
journalctl -u GATEWAY_UNIT --since '2 hours ago' --no-pager -o short-iso
hermes gateway status
hermes logs gateway -n 300
```

Review systemd journal and Hermes logs together. Record the exact error, owning
service manager, and whether a config/profile error, explicit idle stop, process
failure, or host resource event is supported by evidence. If logs have rotated
or no causal evidence exists, state “cause undetermined”; do not guess. Validate
the unchanged config and dependencies, then recover using the normal manager:

```sh
hermes gateway start
hermes gateway status
```

If the service is explicitly systemd-managed, use `sudo systemctl start
GATEWAY_UNIT` instead of `hermes gateway start`, then check status and journal.
Do not use both control paths. If recovery fails, preserve the new logs and stop
before editing configuration; investigate that error first. Restart is not
needed when the gateway is already healthy.

## 2. Build, transfer, and verify the bundle

From the repository checkout, create the deployment artifact:

```sh
./scripts/package-hermes-project-awareness.sh ./dist
cd ./dist
sha256sum -c hermes-project-awareness-0.2.0.tar.gz.sha256
tar -tzf hermes-project-awareness-0.2.0.tar.gz | less
```

Transfer it using the organization's approved file channel. On the host, verify
the checksum against the independently transmitted value, extract to a
root-owned staging directory, and verify the bundle's internal manifest:

```sh
sudo install -d -o root -g root -m 0700 /var/tmp/hermes-project-awareness-stage
sudo tar -xzf /path/to/hermes-project-awareness-0.2.0.tar.gz -C /var/tmp/hermes-project-awareness-stage
cd /var/tmp/hermes-project-awareness-stage/hermes-project-awareness
sudo sha256sum -c SHA256SUMS
```

Inspect the package listing and change record before installation. Installation
loads AppArmor and copies unit files but does not enable or start services.

## 3. Provision the least-privilege identities

Verify the real gateway account with `ps -eo user,pid,args | rg '[h]ermes.*gateway'`
and `getent passwd <candidate>`. Then run the packaged helper with that exact
non-root account. This command creates non-login system users/groups and adds
only the gateway's client-group memberships; it intentionally fails if the
gateway account is absent or has sudo rights.

```sh
sudo env HERMES_GATEWAY_USER='<verified-account>' /opt/hermes-project-awareness/scripts/provision-identities.sh
id '<verified-account>'
sudo -l -U '<verified-account>'
```

Review every group and UID printed by the helper. Stop if the gateway account
already belongs to unrelated privileged groups; do not remove existing
membership automatically. Confirm providers have no sudo rule, no interactive
shell, no home directory, no container/device-admin group, and only the named
client or audit group memberships.

## 4. Install and validate AppArmor/systemd package

Run the packaged installer only after reviewing all files in the bundle. It
backs up exact targets, validates AppArmor syntax, loads the provider profile,
and reloads systemd; it does not enable/start units.

```sh
sudo /var/tmp/hermes-project-awareness-stage/hermes-project-awareness/usr/share/hermes-project-awareness/deploy/install.sh \
  /var/tmp/hermes-project-awareness-stage/hermes-project-awareness
sudo systemd-analyze verify /etc/systemd/system/hermes-*.service
sudo apparmor_status
sudo aa-status
```

Confirm the four provider profiles are in enforce mode and all units pass
`systemd-analyze verify`. The confinement requires an actual-host check of
Python 3.14 and imported module/library paths before enablement. Do not switch
to complain mode or broaden filesystem/network access to clear a denial. If
syntax, loading, or service verification fails, stop and use rollback in the
rollback section after ensuring these units are inactive.

## 5. Approve inventory sources explicitly

Create `/etc/hermes-inventory/sources.toml` from the bundled example, owned by
root and readable only by the inventory service group. Review every exact path
and exposed field. This build allows selected OS/CPU/memory/DMI/DRM data,
fixed Ollama and ComfyUI loopback GET endpoints, and explicitly approved model
directories filtered to regular files with selected extensions. The default
manifest does not expose arbitrary directory listings, process arguments,
environment variables, filesystem trees, or service-manager commands. Podman
container inventory and Tailscale state remain unavailable until a separately
reviewed read-only mediator is supplied; do not grant socket/CLI access.

```sh
sudo install -d -o root -g hermes-inventory-client -m 0750 /etc/hermes-inventory
sudo install -o root -g hermes-inventory-client -m 0640 \
  /usr/share/hermes-project-awareness/config/sources.toml.example \
  /etc/hermes-inventory/sources.toml
sudoedit /etc/hermes-inventory/sources.toml
```

The fixed local HTTP readers run in a private network namespace by default.
If Ollama or ComfyUI status is approved, install the reviewed loopback-only
drop-in and verify the cgroup network policy before starting the provider:

```sh
sudo install -d -o root -g root -m 0755 /etc/systemd/system/hermes-inventory.service.d
sudo install -o root -g root -m 0644 \
  /usr/share/hermes-project-awareness/systemd/hermes-inventory-local-runtime.conf.example \
  /etc/systemd/system/hermes-inventory.service.d/local-runtime.conf
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/hermes-inventory.service
```

This drop-in permits loopback only; if the local services bind to a different
address, do not broaden it without separate review.

Do not add ComfyUI model paths before verifying the active ComfyUI path and
approving that exact directory. Do not expose model file contents. Any path
change requires both manifest allowlisting and matching AppArmor/systemd
read-only rules. Validate `tomllib` parse, directory visibility, denied
unapproved paths, no symlink traversal, and maximum output bounds before
starting inventory.

## 6. Provision root-managed GitHub read credentials and actor policy

The repository owner creates/installs a GitHub App for
`Dukeraider2/framework-desktop-ai-lab` with repository metadata, contents,
issues, and pull-request **read-only** permissions. The host administrator
provisions its private key locally, outside Hermes profiles and worker
containers. The private key is never entered into this chat or committed.

```sh
sudo install -d -o root -g hermes-github-client -m 0750 /etc/hermes-project-awareness
sudo install -o root -g hermes-github-client -m 0640 \
  /usr/share/hermes-project-awareness/config/github.env.example \
  /etc/hermes-project-awareness/github.env
sudoedit /etc/hermes-project-awareness/github.env
sudo install -o root -g hermes-github -m 0400 /secure/local/path/github-app-key.pem \
  /etc/hermes-project-awareness/github-app-key.pem
```

`github.env` contains only the numeric App and installation IDs and the fixed
repository owner/name. Confirm the provider's systemd `LoadCredential` makes
the key available only to its process. Create the root-managed GitHub actor
allowlist using the example file and add only maintainers approved to issue
directives. A mention remains notification only; task directives require the
actor allowlist, an exact repository, an assigned issue with `agent:<id>` label,
and the agent's static action policy. The dispatch service cannot write to
GitHub.

The GitHub provider's outbound address policy must be reviewed independently.
Do not create the `github-egress-policy-approved` marker or start egress until
the administrator has validated fixed DNS resolution and API-only destinations
against current GitHub metadata and the host firewall. The write-capable App,
if separately approved in the future, must use another identity/credential and
typed write adapter.

## 7. Root-managed runtime configuration and audit

Create `/etc/hermes-project-awareness/runtime.env` from the example. Fill
numeric peer UIDs from the verified output; do not put secrets there. Restrict
ownership and mode to root and the required service-read group. The audit
service owns its protected append-only data directory; verify the configured
group and socket mode before starting dependents.

```sh
sudo install -o root -g hermes-provider-runtime -m 0640 \
  /usr/share/hermes-project-awareness/config/runtime.env.example \
  /etc/hermes-project-awareness/runtime.env
sudoedit /etc/hermes-project-awareness/runtime.env
sudo install -o root -g hermes-github-client -m 0640 \
  /usr/share/hermes-project-awareness/config/github-client-uids.env.example \
  /etc/hermes-project-awareness/github-client-uids.env
sudoedit /etc/hermes-project-awareness/github-client-uids.env
```

Review ownership/permissions for the audit directory, event ledger, cursor,
socket paths, GitHub App key, allowlists, inventory manifest, and runtime files.
On audit write failure, providers/reporting and event cursor advancement must
fail closed. Confirm restart recovery preserves the cursor and dedupe ledger.

## 8. Sender enrollment and MCP/profile installation

The owner supplies canonical WhatsApp Agent Platform direct-sender IDs through
an approved out-of-band process. Create the sender allowlist root-owned,
readable by the gateway's dedicated group, and mode 0640. Keep it empty until
the value is verified. The plugin rejects groups, missing session context,
unknown senders, and non-Agent-Platform channels.

```sh
sudo install -o root -g hermes-audit-clients -m 0640 \
  /usr/share/hermes-project-awareness/config/authorized-whatsapp-senders.example \
  /etc/hermes-project-awareness/authorized-whatsapp-senders
sudoedit /etc/hermes-project-awareness/authorized-whatsapp-senders
```

Before profile edits, use `hermes --help`, `hermes plugins --help`, and
`hermes mcp --help` from the deployed v0.22.5 installation. Install the native
plugin under the Hermes user's plugin directory using the documented install
method and validate it (`hermes plugins validate <plugin-path> --json`). The
plugin reads sender identity from Hermes session context; that API is currently
a private v0.22.5 import and must be revalidated on every Hermes upgrade.

Register two stdio MCP commands in the active `default` profile only:

```text
python3 -m integrations.hermes_project_awareness.mcp_stdio github
python3 -m integrations.hermes_project_awareness.mcp_stdio inventory
```

Use Hermes CLI/profile configuration rather than replacing the profile file.
Back up first. Merge only these two MCP entries and the single
`frameworklab_project_status` tool into the explicit WhatsApp toolset. Preserve
all existing `hermes-whatsapp` tools and channel/account settings. Do not expose
raw provider tools or add tools to the `frameworklab` profile or OpenCode
launcher. Validate config syntax, active profile, plugin load, and tool list
before gateway restart.

## 9. Start order and smoke checks

Start/enable only after all static and host policy checks pass. These are new
units and do not replace the existing WhatsApp gateway service.

```sh
sudo systemctl enable --now hermes-project-awareness-audit.service
sudo systemctl status hermes-project-awareness-audit.service --no-pager
sudo systemctl enable --now hermes-inventory.service
sudo systemctl status hermes-inventory.service --no-pager
sudo systemctl enable --now hermes-github-egress.service
sudo systemctl status hermes-github-egress.service --no-pager
sudo systemctl enable --now hermes-github.service
sudo systemctl status hermes-github.service --no-pager
sudo systemctl enable --now hermes-agent-dispatch.service
sudo systemctl status hermes-agent-dispatch.service --no-pager
```

Run the provider schema and negative authorization suite from the installed
tree, verify only the gateway UID and dispatch UID can connect to the intended
provider sockets, check AppArmor denials for secrets/unapproved files, and
confirm no provider has shell, sudo, Podman socket, or unrestricted network
access. Dispatch queues tasks only; a model runner and GitHub write adapter are
not configured by this package.

After provider smoke tests and explicit WhatsApp tool visibility validation,
restart the gateway using the normal manager selected in section 1:

```sh
hermes gateway restart
hermes gateway status
```

If systemd owns it, use `sudo systemctl restart GATEWAY_UNIT` and immediately
check status/journal. Test an allowlisted direct sender request, an unknown
sender, group chat, and missing sender context. Only the authorized direct
request may receive project evidence. Save a redacted real transcript with the
GitHub evidence URLs and provider timestamps.

## 10. Local-model collection and agent sessions

Collect the actual model inventory after verifying the Ollama service and local
API access. Metadata mode is read-only. Benchmark mode causes one short local
generation for each installed model and is optional; it makes no paid API call.

```sh
python3 /opt/hermes-project-awareness/scripts/collect-local-model-inventory.py \
  > "$HOME/hermes-model-inventory.json"
python3 /opt/hermes-project-awareness/scripts/collect-local-model-inventory.py --benchmark \
  > "$HOME/hermes-model-benchmark.json"
```

Review active and total parameter counts, context, quantization, peak memory,
load and generation time, cgroup limits, and intended concurrent sessions before
binding models. Keep identities/SOUL files separate from model assignments.
Assign only local models whose measured capability/resource profile fits the
role; until then all seven profiles remain model-unset. Start one session per
profile, verify SOUL loading and model identity, then restart and repeat. Do not
submit GitHub reviews or comments under an agent identity until a real
model-backed authorized session and independent review record are demonstrated.

## 11. Rollback

Stop only the newly introduced provider/dispatch units. Do not stop or remove
Hermes, WhatsApp, Ollama, ComfyUI, Podman, Tailscale, or OpenCode services.
Use the exact rollback script from the installed bundle; it refuses active or
enabled units and preserves the ledger/audit data. Review its printed scope
before running. Preserve the installation backup and logs.

```sh
sudo systemctl disable --now hermes-agent-dispatch.service hermes-github.service \
  hermes-github-egress.service hermes-inventory.service hermes-project-awareness-audit.service
sudo /usr/share/hermes-project-awareness/deploy/rollback.sh /var/backups/hermes-project-awareness/<timestamp>
```

The rollback command path and backup argument must be checked against the
installed package version first. Restore Hermes profile settings from the
owner's backup only if the MCP/plugin merge caused a verified regression.

## Acceptance record and unmet live requirements

Record actual command output, UTC timestamps, service identities, policy modes,
negative tests, and redacted transcripts. Passing Python tests and a valid
package are not live demonstrations. The remaining live gates are: provider
service installation/enforcement, root credential provisioning, current
GitHub App access, authorized WhatsApp sender IDs, gateway recovery if needed,
actual WhatsApp request/denial, event processing on GitHub, and model-backed
sessions for seven agents. No review may be posted as an agent identity before
those sessions exist.
