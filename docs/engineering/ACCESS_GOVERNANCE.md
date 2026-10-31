# Agent Access and Governance

**Status:** Adopted policy direction. Technical enforcement mechanisms remain to be implemented and tested.

## Authority

Hermes is the proposed first-line access manager. The user retains final authority over unresolved access conflicts and high-risk exceptions.

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
