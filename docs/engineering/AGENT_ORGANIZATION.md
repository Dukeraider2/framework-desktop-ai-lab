# Organization and Reporting Structure

**Status:** Authoritative source of truth for organizational roles, reporting lines, communication, and deployment placement.

## Reporting structure

```text
OWNER (Gabriel)
  |
  v
HERMES (Chief of Staff and System Coordinator)
  |
  v
WORKER AGENTS
  |-- Research
  |-- Engineering / Development
  |-- Operations / Infrastructure
  |-- QA / Independent Review
  |-- Creative Production
  |-- Other task-specific specialists
```

## Roles

- **Owner:** Sets priorities and standing policy. Makes final decisions on escalations, policy exceptions, and actions requiring owner approval.
- **Hermes:** The single coordinator and the owner's sole operational point of contact. Receives every task from the owner, plans and delegates work, selects and supervises worker agents, controls ordinary task-scoped access, evaluates returned work, and reports results to the owner.
- **Worker agents:** Perform only work assigned by Hermes. They report to Hermes, never directly to the owner. An agent needing additional access requests it from Hermes. Hermes grants or denies it within standing policy; a denial includes a practical alternative. If no safe workable alternative exists or an owner-level decision is required, Hermes escalates to the owner.

## Communication rule

The only normal command and reporting path is:

```text
OWNER <-> HERMES <-> WORKER AGENTS
```

The owner communicates with Hermes, not with worker agents. Worker-agent messages, questions, requests, progress, and deliverables are routed through Hermes. No worker agent is an alternate coordinator or owner-facing endpoint.

## Deployment placement

- **Hermes runs natively at the Ubuntu host/system level, outside all containers.** It remains a host-level service so it can coordinate the system and manage worker-container lifecycle.
- **Only worker agents that Hermes deploys are containerized**, using rootless Podman by default. Each worker receives a task-scoped environment and only the access required for its assignment.
- Hermes supervises worker containers through the host's Podman installation. Worker agents do not receive unrestricted host access or control of the host Podman service.
- The LLM Inference Gateway and other shared infrastructure are separate services. Their interfaces and security requirements belong in their respective technical specifications.

## Authority

Hermes is the first-line authority for ordinary task coordination and task-scoped worker access under the owner's standing policy. The owner retains final authority over policy changes, exceptions, unresolved escalations, and owner-reserved actions.

This file is the sole source of truth for the organization chart and the rules above. Other documents must link here rather than restating, paraphrasing, or redefining these roles, reporting lines, communication paths, or deployment placement.
