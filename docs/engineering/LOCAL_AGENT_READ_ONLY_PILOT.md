# Local Hermes and OpenCode Read-Only Pilot

**Status:** Implemented and exercised as a local read-only pilot. This is not a production approval, a merge approval, or authorization to enable agent write access.

## Purpose

Validate a bounded local workflow in which Hermes acts as the coordinating assistant and OpenCode performs repository inspection inside a constrained rootless Podman container. The goal is to prove that task delegation and result retrieval can work without granting the coding agent write access to the project, host credentials, or the general network.

This document records the observed pilot and its limits. It does not replace the broader [Engineering Governance](README.md), [Access and Governance](ACCESS_GOVERNANCE.md), or [Podman-First Container Policy](PODMAN_FIRST_POLICY.md).

## Components

- **Hermes:** Interactive coordinator and task intake. Its native agent-delegation path is disabled for this integration.
- **MCP bridge:** Local stdio service exposing exactly four operations to Hermes: `submit_task`, `task_status`, `task_result`, and `cancel_task`.
- **OpenCode:** Local coding/inspection runtime, launched through a dedicated rootless Podman container.
- **Ollama:** Model inference is provided through a narrowly scoped local proxy. This is not general network access.
- **GitHub:** Repository history, review, and documentation remain the collaboration record. The pilot itself does not push, merge, or modify the default branch.

## Security boundary and effective configuration

The validated inspection container was configured with the following controls:

- Rootless Podman execution under the ordinary user account.
- No general container network access (`network=none`).
- No published container ports.
- No host devices passed through.
- Read-only container root filesystem.
- Read-only project workspace and read-only policy/configuration mounts.
- No host SSH directory or GitHub credentials mounted into the container.
- No service-account password or equivalent credential exposed to Hermes.
- All Linux capabilities dropped; `no-new-privileges` enabled.
- CPU, memory, and process-count limits applied.
- Interactive Hermes operation with manual approval; one-shot Hermes execution is not used because testing found that its approval behavior did not meet the intended boundary.
- MCP bridge exposes only the four named task lifecycle operations. Direct requests for an unexposed shell tool were rejected.

The local bridge and service configuration may contain machine-specific paths and runtime details. Those belong in local configuration, not in version control. Do not publish tokens, passwords, private tailnet names, private IP addresses, device identifiers, or unredacted logs.

## Validation performed

The following checks were reported as successful during the pilot:

1. Hermes connected to the local stdio MCP bridge.
2. The bridge advertised the four intended task lifecycle tools.
3. Hermes submitted a harmless repository-inspection task to OpenCode.
4. OpenCode read the repository's agent instructions and listed the project root.
5. Hermes retrieved and summarized the result.
6. A direct attempt to invoke a tool not exposed by the bridge was rejected.
7. A write attempt inside the mounted project workspace failed with `EROFS`; no probe file was created.
8. Inspection confirmed read-only mounts for the workspace and selected policy/configuration files.
9. Container inspection confirmed rootless execution, disabled general networking, no published ports/devices, read-only root, dropped capabilities, `NoNewPrivs=1`, and resource limits.
10. The local inference proxy returned HTTP 200 for the model-tags check while general container networking remained disabled.
11. Separate system checks reported the existing ROCm/PyTorch GPU path, Ollama, ComfyUI HTTP endpoint, and Tailscale service healthy after the pilot changes.

These are recorded as observed checks from this pilot, not as an independently reproduced test suite or a guarantee about future versions.

## Known limitations and unverified items

- The OpenCode API session-wait route used by the bridge is experimental/version-sensitive. Revalidate it after OpenCode upgrades.
- A Hermes shell-probe turn reported an unknown task ID. The corresponding OpenCode inspection completed, but the anomaly was not fully diagnosed and should remain open for investigation.
- A native OpenCode runtime permission-denial event was not observed. The read-only filesystem failure is evidence of the mount boundary, not proof that every OpenCode tool-level permission rule is configured correctly.
- The `cancel_task` bridge operation was not tested end to end.
- Reboot persistence was not tested.
- The pilot did not establish that the complete systemd lifecycle, restart behavior, or failure recovery is production-ready.
- No independent security audit has been completed.

## Operating mode

### Current: read-only inspection

Read-only inspection is the only mode validated in this pilot. Keep it as the default. Use it for bounded repository reading, status checks, and evidence gathering. Do not infer permission to edit files from successful task delegation.

### Future: development mode (disabled)

Development mode is not enabled by this pilot and must remain disabled until the repository owner explicitly authorizes a separate implementation phase. Any future implementation environment must:

- Use a dedicated feature branch and isolated feature workspace.
- Exclude the default branch's writable checkout and all host credentials.
- Retain rootless Podman, least privilege, network restrictions, resource limits, and auditability.
- Keep changes reviewable as diffs with recorded test output.
- Use an independent reviewer that did not author the change.
- Require explicit human approval before commit, push, pull-request merge, deployment, or infrastructure changes.

No agent may grant itself additional permissions, broaden its own tool list, or approve its own changes.

## Rollback and operational caution

The pilot used temporary local gateway/container processes. Those were stopped after validation; the existing local inference proxy was left running. No reboot was performed. If the pilot is resumed, inspect the current service/container state first rather than assuming the previous runtime state persists.

Do not remove or reconfigure the existing ROCm, PyTorch, Ollama, ComfyUI, Tailscale, or systemd setup as part of agent experimentation without a separately reviewed change plan.

## Adoption decision

**Recommendation:** retain the implementation on its feature branch for human review. The read-only delegation path demonstrated useful end-to-end behavior, but the unresolved task-ID anomaly, untested cancellation/reboot behavior, and missing native permission-denial evidence mean it should be treated as a successful prototype, not a fully certified security boundary.

The repository owner decides whether to accept the documentation, request further tests, authorize a separate development-mode phase, or close the pilot.
