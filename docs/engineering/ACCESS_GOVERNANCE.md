# Agent Access and Governance

**Status:** Adopted policy direction. Technical enforcement mechanisms remain to be implemented and tested.

## Authority

Hermes is the first-line access authority for ordinary task-scoped permissions. For every agent it provisions, Hermes defines the Podman container environment and grants the minimum access required by that task. The user retains final authority over policy exceptions, unresolved access conflicts, and high-risk actions.

## Per-task Podman environment and permissions

Before creating an agent container, Hermes must define a task-scoped execution specification: task/issue, agent capability, base image, runtime and environment, workspace mounts, network destinations, device access, Linux capabilities, CPU/memory/process/storage/time limits, secret references, permitted APIs, lifetime, and cleanup. Access is deny-by-default where practical and must be justified by the task. Read-only mounts are preferred; writable mounts are limited to the task workspace. GPU/TPU/device access, credentials, and network egress are granted only when required.

Podman is the enforcement mechanism for container isolation and the configuration Hermes selects. Agents cannot grant themselves permissions or control the host Podman service. Do not mount the host Podman socket, broad home directories, host root, or general credential stores into an agent by default. Hermes may use a narrow provisioning interface; any validator enforces the user's standing policy and is not a competing permission authority.

## Access request requirements

An agent that needs access beyond its current permissions must request it from Hermes. Every request must state:
- Agent identity and task or GitHub issue.
- Resource or system requested.
- Specific permission and scope requested.
- Reason access is needed.
- Goal the agent intends to accomplish.
- Expected duration.
- Risks and alternatives already considered.

## Grant or deny

Hermes may grant or deny the request according to least privilege, task scope, security, and operational risk. A denial must include a practical alternative that addresses the agent's stated need. Alternatives may include a read-only API, narrowly scoped token, user-space installation, Podman container, reviewed script, or human-executed operation.

A denial without a viable alternative is not a resolved request.

## Escalation

If Hermes and the requesting agent cannot find a safe, workable alternative, Hermes must report the unresolved need to the user. The report must explain the task and intended outcome, why current permissions and alternatives are insufficient, requested access and duration, risks of granting access, risks of withholding access, mitigations, and a recommendation. The preferred outcome is a least-privilege solution found collaboratively by Hermes and the agent. The user makes the final decision when unresolved.

## Permission lifecycle

- Grant the narrowest permission that satisfies the task.
- Prefer read-only access when possible.
- Use temporary, task-scoped permissions where supported.
- Record grants, denials, alternatives, expirations, and escalations in GitHub.
- Revoke access when the task ends or the justification expires.
- Never expose secrets in issues, commits, reports, or agent prompts. Use an approved secret store or scoped credential mechanism.

## Human approval gates

Human approval is required for unresolved privilege escalations, production-impacting actions, destructive infrastructure changes, public publishing until its policy is separately approved, and production releases as defined by the project owner.
