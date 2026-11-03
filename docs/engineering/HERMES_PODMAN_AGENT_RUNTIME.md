# Hermes-Managed Podman Agent Runtime

**Status:** Adopted architecture direction; implementation and enforcement are not yet complete.  
**Applies to:** Every agent process or specialist agent that Hermes provisions for task execution on the AI lab hosts.

## 1. Decision

Agents created or dispatched by Hermes run in Podman containers. Podman is the mandatory execution runtime for these agent workloads. A VM is not the default execution unit for an individual Hermes-created agent. A VM may be used only when a task has a documented isolation or platform requirement that containers cannot satisfy, and the exception is approved by the user.

Hermes is the task orchestrator and first-line access authority. For each task, Hermes defines the agent's container environment and grants only the minimum access required to complete that task. This is a per-task decision, not one broad permission profile shared by all agents.

Podman enforces the container configuration that Hermes requests. Host-level safeguards and the user's approval requirements remain in force; Hermes must not treat its orchestration role as authority to bypass them.

## 2. Roles and authority

| Component | Responsibility |
| --- | --- |
| User | Owns the lab, sets standing policy, and decides unresolved high-risk exceptions and production-impacting actions. |
| Hermes | Decomposes tasks, selects agent capabilities, defines each task's runtime/environment/access specification, provisions and supervises agents through Podman, records grants/denials, and escalates unresolved risks. |
| Provisioning interface | Converts Hermes' approved task specification into a Podman container configuration. It should be narrow, auditable, and not expose unrestricted host control to agents. |
| Podman | Enforces container isolation, namespaces, mounts, devices, capabilities, resource limits, network configuration, and lifecycle. |
| Agent | Performs only its assigned task within the granted container environment. It cannot grant itself additional access. |
| Independent reviewer | Reviews implementation, security, test evidence, and whether the requested access was proportionate. It does not approve its own implementation. |

Hermes is the policy decision-maker for ordinary task-scoped access within the standing policy. This design does **not** require a second autonomous policy authority that competes with Hermes. A narrow preflight validator may reject malformed or policy-violating container specifications, but it must enforce the owner's standing rules rather than silently redefine task permissions.

## 3. Per-task execution specification

Before provisioning an agent, Hermes records a task-scoped execution specification containing, at minimum:

- Task/issue identifier, purpose, acceptance criteria, agent role, and expected lifetime.
- Base image and version/digest policy.
- Runtime command, working directory, required packages, and environment variables.
- CPU, memory, process/thread, storage, and execution-time limits appropriate to the workload.
- Network mode and explicitly required destinations/protocols.
- Filesystem mounts, with read-only access by default and narrowly scoped writable workspaces.
- Device access, including GPU/TPU or other hardware, only when required and validated.
- Linux capabilities and security options; drop unnecessary capabilities.
- Credential/secret references and scope. Do not place secrets in image layers, Git, logs, or general agent prompts.
- Permitted tools and APIs, including whether the agent may access Git, the Inference Gateway, or other services.
- Cleanup, expiration, output retention, and evidence collection requirements.

The execution specification must distinguish required access from optional convenience. If the task can be completed with a read-only mount, no host device, or no network, those privileges are not granted.

## 4. Default security posture

Unless a task specification justifies a narrower exception:

1. Use rootless Podman.
2. Do not run privileged containers.
3. Drop all unnecessary Linux capabilities; do not use host PID, IPC, or network namespaces by default.
4. Do not mount the host root filesystem, home directory, Podman socket, container-engine socket, SSH agent socket, or broad credential directories into an agent.
5. Give each agent a dedicated workspace. Mount source inputs read-only where possible and only the task workspace writable.
6. Deny or isolate network access by default; add only the connectivity required for the task. Egress must be deliberate and documented.
7. Grant GPU, TPU, USB, PCIe, or other device access only when the workload needs it and the host/device path has been validated.
8. Apply CPU, memory, process, disk, and time limits appropriate to the task. Do not invent universal numeric budgets; measure the host and workload.
9. Use task-scoped credentials with the shortest practical lifetime. Prefer secret mounts or an approved secret mechanism over plaintext environment variables.
10. Do not permit an agent container to control the host Podman service or provision sibling containers unless that specific task is explicitly delegated and authorized.
11. Terminate and clean up temporary agents and revoke task-scoped access when work ends.
12. Preserve audit records without retaining secrets or unnecessary sensitive task data.

These are default guardrails, not a claim that every control is already configured. Each control must be validated on the installed Podman version and host.

## 5. Hermes access-request workflow

An agent that needs access beyond its current specification must request it from Hermes. The request identifies the task, resource, exact permission, purpose, duration, risks, and alternatives. Hermes may grant or deny the request within the standing policy. A denial must provide a practical alternative. If a safe solution requires a policy exception or elevated host/production access, Hermes escalates to the user before proceeding.

Grants are task-scoped, recorded, and revoked when the task ends or the justification expires. See [Access and Governance](ACCESS_GOVERNANCE.md).

## 6. Inference Gateway access

Agents should consume language-model inference through the shared LLM Inference Gateway, not connect directly to Ollama or manage model runtimes themselves.

- The gateway owns routing to model backends.
- Hermes and other authorized clients are gateway clients.
- Agent containers receive only the gateway endpoint and credentials/network access needed for their task.
- Do not mount Ollama model storage or the host Ollama socket into agent containers.
- Do not expose Ollama's backend port to agent networks as a shortcut.
- The current host-loopback gateway endpoint is not automatically reachable from a separate Podman network namespace. A container-to-gateway network path must be designed and tested before agent containers are configured to use it.
- The current NGINX proxy has no built-in authentication or per-client authorization. Before exposing it to a broader agent network, define and validate an appropriate trust boundary, authentication/authorization approach, and network restrictions.

See [LLM Inference Gateway Architecture](INFERENCE_GATEWAY_ARCHITECTURE.md).

## 7. Lifecycle and evidence

The intended lifecycle is:

1. Hermes receives a task and creates/approves the task package.
2. Hermes selects an agent capability and writes the task execution specification.
3. The provisioning interface validates the specification against standing policy.
4. Podman creates the isolated container with only the declared resources and access.
5. Hermes monitors task progress, resource use, and time.
6. The agent produces artifacts, test results, and an implementation report.
7. An independent reviewer checks the work and the access actually granted.
8. Hermes stops the container, collects approved outputs, revokes temporary credentials, and removes temporary resources.
9. Git records the task, implementation, evidence, review, and approval state.

Persistent services and reusable worker pools require separate lifecycle specifications; do not silently turn a disposable task agent into a privileged always-on service.

## 8. Implementation phases and acceptance gates

### Phase A — Inventory and design
- Inspect the installed Hermes version, current gateway/service configuration, Podman version, rootless status, Quadlet/systemd integration, and existing scripts.
- Identify the supported Hermes mechanism for provisioning and supervising Podman agents.
- Produce a task execution-spec schema and a permission mapping to Podman settings.
- Document current gaps without changing working services.

### Phase B — Minimal restricted agent
- Provision one disposable, rootless, non-privileged agent with no unnecessary host mounts, no device access, and tightly restricted networking.
- Demonstrate that the agent cannot access host files outside its declared workspace or control Podman.
- Demonstrate resource limits, lifecycle cleanup, and auditable logs.

### Phase C — Task-scoped capabilities
- Add controlled read-only repository access and a dedicated writable worktree.
- Add narrowly scoped network access and secrets only for tasks that require them.
- Test denial, escalation, expiration, and revocation paths.

### Phase D — Inference Gateway integration
- Establish an authenticated/restricted route from an agent container to the LLM Inference Gateway.
- Verify that agent inference requests reach the gateway and that the gateway routes to the configured backend.
- Verify that agents cannot bypass the gateway to access Ollama directly.
- Measure request latency, throughput, and host/GPU resource impact.

### Phase E — Multi-agent operation
- Run multiple agents with separate workspaces and task specifications.
- Verify no shared writable worktree, credential leakage, uncontrolled resource contention, or privilege crossover.
- Test agent failure, timeout, cancellation, host restart, and cleanup behavior.

A phase is complete only when commands, versions, configuration, test output, limitations, and reviewer findings are recorded. Do not mark proposed controls as implemented or verified without evidence.

## 9. Explicit non-goals

- Docker is not an alternate default runtime.
- Agent containers do not receive unrestricted host access.
- Hermes does not own or replace the LLM Inference Gateway.
- Agent containers do not directly manage Ollama or model files.
- This design does not imply that every specialist role needs a permanently running container.
- This document does not approve automatic Proxmox changes, production deployment, or destructive operations.

## 10. Related standards

- [Engineering Constitution](CONSTITUTION.md)
- [Agent Organization](AGENT_ORGANIZATION.md)
- [Access and Governance](ACCESS_GOVERNANCE.md)
- [Podman-First Container Policy](PODMAN_FIRST_POLICY.md)
- [Three-Stage Engineering Workflow](DEVELOPMENT_WORKFLOW.md)
- [LLM Inference Gateway Architecture](INFERENCE_GATEWAY_ARCHITECTURE.md)
