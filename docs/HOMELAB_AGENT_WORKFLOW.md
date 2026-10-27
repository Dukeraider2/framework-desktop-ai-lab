# Proposed Multi-Agent Development Workflow

**Status:** Concept only; agent roles and integration have not yet been deployed or validated.

## Goal

Use Hermes and the existing local model proxy to coordinate a controlled software-development pipeline on the Proxmox lab. Git is the shared source of truth. Agent environments should be isolated, and important changes should remain reviewable by a human.

## Workflow

1. **Task intake:** A human supplies a task and acceptance criteria.
2. **Planning:** A coordinator breaks the task into bounded implementation and test steps.
3. **Implementation:** A coding agent works in an isolated VM/container and on a dedicated Git branch.
4. **Independent review:** A reviewer examines the diff against requirements, correctness, security, and maintainability. The reviewer should not silently rewrite the implementation.
5. **Testing:** A test runner executes the defined test suite in an isolated environment.
6. **Revision:** Test failures and review findings are returned to the coding agent for a bounded number of retries.
7. **Pull request:** The branch, diff, test output, and review findings are presented for human review.
8. **Merge approval:** A human decides whether to merge.
9. **Deployment approval:** Deployment is a separate step and requires explicit authorization.

## Infrastructure awareness

Once monitoring is working, Hermes may query selected data such as node availability, free memory, CPU load, workload state, and active alerts. The first implementation should provide recommendations only, not automatic Proxmox changes.

Scheduling decisions must account for stale or missing metrics. When monitoring data is unavailable, the safe behavior is to stop or ask for human input rather than assume capacity is available.

## Isolation and safety

- Use separate branches and workspaces; do not let multiple agents edit the same working tree concurrently.
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

Do not treat this proposal as proof that Hermes, GitHub, the model proxy, or any agent tools are already integrated.
