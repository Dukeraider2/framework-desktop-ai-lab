# Proxmox Lab Monitoring and Agent Implementation Plan

**Status:** Planning; no deployment steps in this document have been executed.
**Working rule:** Verify each stage before proceeding. Prefer one change at a time and record actual output.

## Phase 1 — Recover access and establish a baseline

1. Identify one CSI node to use as the initial test target.
2. Recover its management IP if necessary, using local console/network records rather than guessing.
3. Confirm browser access to its Proxmox web interface.
4. Record the exact Proxmox version and basic cluster/node state.
5. Record findings without publishing credentials or sensitive network details.

**Exit criteria:** A known node is reachable and its Proxmox interface works.

## Phase 2 — Select and prepare the independent monitoring computer

1. Choose a spare physical machine and record CPU, RAM, storage, and network interfaces.
2. Decide whether to use the existing OS or install a supported server OS after checking compatibility and backup requirements.
3. Confirm it can reach the Proxmox management network.
4. Avoid changing the CSI cluster just to set up monitoring.

**Exit criteria:** Monitoring machine is identified, reachable, and ready for a small prototype.

## Phase 3 — Verify read-only API access

1. Consult the official documentation matching the installed Proxmox version.
2. Create a dedicated API identity/token with only the permissions required for status queries.
3. Store credentials outside the repository, with restrictive file permissions or an appropriate secret store.
4. Test a small read-only request for node status, then VM/container state.
5. Check error handling for authentication failure and unreachable nodes.

**Exit criteria:** A repeatable authenticated request returns actual Proxmox data without administrator credentials.

## Phase 4 — Build a minimal browser dashboard

1. Use the monitoring computer to serve a simple dashboard.
2. Display node name, online status, and available workload state.
3. Make refresh time and stale/error state explicit.
4. Keep the first version read-only; no infrastructure-changing buttons.

**Exit criteria:** The dashboard displays verified live information for the first node.

## Phase 5 — Expand cluster visibility and decide on historical metrics

1. Add the remaining nodes using verified management addresses.
2. Add supported CPU, RAM, storage, and network readings.
3. Evaluate whether Proxmox-provided data meets the requirements.
4. If historical graphs or richer metrics are required, evaluate Prometheus and Grafana and any necessary lightweight collectors.
5. Configure conservative alert thresholds only after baseline behavior is observed.

**Exit criteria:** All reachable nodes are represented and metric provenance/freshness is clear.

## Phase 6 — Add optional MCP read-only access

1. Define a small allowlist of queries, such as list nodes, list workloads, retrieve resource summaries, and retrieve alert state.
2. Use read-only credentials and validate inputs.
3. Return concise results with timestamps and error states.
4. Test that requests cannot modify or delete infrastructure.
5. Only then connect Hermes to these tools.

**Exit criteria:** Hermes can query accurate monitoring data without infrastructure write permissions.

## Phase 7 — Implement the development workflow

1. Create isolated development environments for coding and tests.
2. Use Git branches or pull requests so agents do not share an uncontrolled write directory.
3. Separate code generation, independent review, and test execution where practical.
4. Automate unit and regression tests with explicit pass/fail output.
5. Send failures and review findings back for bounded revision attempts.
6. Require human approval before merging or deploying.

**Exit criteria:** A task can produce a reviewed pull request with test evidence.

## Phase 8 — Resource-aware scheduling and hardening

1. Measure real workload resource use.
2. Define per-job CPU/RAM limits and minimum free-capacity thresholds.
3. Let Hermes recommend placement using monitoring data before considering automated placement.
4. Add audit logs, backups, update procedures, and recovery tests.
5. Review security boundaries before granting any write capability.

**Exit criteria:** Scheduling recommendations are explainable, tested, and fail safely when telemetry is unavailable.

## Working notes

- Start with one node and a minimal page; do not build the whole platform at once.
- Do not assume node IPs, software versions, package names, API permissions, or model-proxy settings.
- Use official vendor documentation and inspect command output before the next system-level change.
- Mark a task complete only after its exit criteria are observed.
