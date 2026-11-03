# Proposed Multi-Agent Development Workflow

**Status:** Proposed workflow; Hermes host inference integration was validated on 2026-11-03. Hermes-managed Podman agent provisioning and the Proxmox workflow remain to be implemented and validated.

## Goal

Use the approved organization and reporting structure in [Organization and Reporting Structure](engineering/AGENT_ORGANIZATION.md) to coordinate a controlled software-development pipeline. Git is the shared source of truth. The shared LLM Inference Gateway is a separate service. The Proxmox monitoring/deployment integration is a separate planning track.

## Workflow

1. **Task intake:** A human supplies a task and acceptance criteria.
2. **Planning:** A coordinator breaks the task into bounded implementation and test steps.
3. **Implementation:** Hermes provisions a coding agent in a rootless Podman container with a task-specific environment, dedicated workspace, minimum required mounts/network/devices/credentials, resource limits, and a dedicated Git branch. A VM is an approved exception only when the task cannot be met safely by Podman.
4. **Independent review:** A reviewer examines the diff against requirements, correctness, security, and maintainability. The reviewer should not silently rewrite the implementation.
5. **Testing:** A test agent or runner executes the defined test suite in a separately scoped Podman container/workspace.
6. **Revision:** Test failures and review findings are returned to the coding agent for a bounded number of retries.
7. **Pull request:** The branch, diff, test output, and review findings are presented for human review.
8. **Merge approval:** A human decides whether to merge.
9. **Deployment approval:** Deployment is a separate step and requires explicit authorization.

## Infrastructure awareness

Once monitoring is working, Hermes may query selected data such as node availability, free memory, CPU load, workload state, and active alerts. The first implementation should provide recommendations only, not automatic Proxmox changes.

Scheduling decisions must account for stale or missing metrics. When monitoring data is unavailable, the safe behavior is to stop or ask for human input rather than assume capacity is available.

## Isolation and safety

- Use separate Podman containers, branches, and workspaces; do not let multiple agents edit the same working tree concurrently.
- Hermes defines per-agent environment and least-privilege access; Podman enforces it. Do not give agents the host Podman socket or unrestricted host mounts.
- Do not place production secrets or broad Proxmox credentials in agent environments.
- Limit network access and credentials to the minimum required for each job.
- Use disposable or snapshotted test environments where practical.
- Preserve test output and review history.
- Require human approval for merges, deployments, and infrastructure-changing actions.
- Establish timeouts, resource limits, and bounded retry counts.

## Initial acceptance criteria

The first workflow prototype should demonstrate:
- A task can be checked into a dedicated branch.
- The implementation can be reviewed independently.
- Automated tests produce recorded pass/fail results.
- Failed tests lead to a bounded revision attempt.
- A human can inspect the final diff and evidence before merging.

Do not treat this proposal as proof that Hermes can already provision Podman agents or that the Proxmox workflow is deployed. Host-process Hermes inference through the LLM Inference Gateway was validated on 2026-11-03; separate agent-container connectivity to the gateway remains unverified. See the [Hermes Podman runtime](engineering/HERMES_PODMAN_AGENT_RUNTIME.md) and [LLM Inference Gateway architecture](engineering/INFERENCE_GATEWAY_ARCHITECTURE.md).
