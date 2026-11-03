# Podman-First Container Policy

**Status:** Mandatory architecture requirement.

## Default runtime

Podman is the standard container runtime for this lab and its projects. Prefer rootless containers where practical, with systemd integration such as Quadlet where appropriate. Use compatible image formats and build tooling based on verified support.

## Hermes-created agent workloads

All agents that Hermes provisions for task execution use Podman containers by default. Hermes defines the environment and minimum task-required access for each agent individually. The task specification must cover image/version, command, environment, workspace mounts, network, devices, capabilities, resource limits, credentials, lifetime, and cleanup. Podman enforces the declared container settings.

Use rootless, non-privileged containers by default. Drop unnecessary capabilities, avoid host namespaces and broad host mounts, do not expose the Podman socket to agents, and provide only task-scoped writable storage, network access, devices, and secrets. An agent cannot self-escalate. A VM is an exception only when a documented task requirement cannot be met safely by Podman and the user approves it. See [Hermes-Managed Podman Agent Runtime](HERMES_PODMAN_AGENT_RUNTIME.md).

## Docker requirement response

If a project, upstream application, installer, Compose file, CI workflow, or dependency claims Docker is required:

1. Do not install Docker as an immediate workaround.
2. Inspect source code, Dockerfiles, Compose definitions, scripts, APIs, SDKs, CI workflows, volume assumptions, networking, socket access, permissions, and daemon-specific behavior.
3. Identify which requirements are truly Docker-specific and which merely assume a Docker-compatible interface.
4. Document dependency and compatibility analysis in the GitHub task.
5. Identify a Podman-native replacement or compatibility approach.
6. Port deployment files, scripts, service definitions, permissions, networking, storage, and operational instructions as required.
7. Rebuild using Podman.
8. Run functional, integration, security, persistence, restart, and resource tests.
9. Have an independent reviewer verify that the port has not weakened isolation or introduced unnecessary privileges.
10. Document remaining incompatibilities and obtain user approval before any exception.

Do not assume Docker Compose compatibility is perfect. Verify the exact Compose provider and features used by the application.

## Security and operations

- Prefer rootless execution.
- Avoid privileged containers and host socket exposure.
- Use least-privilege mounts, devices, capabilities, and network access.
- Keep secrets out of images, source control, logs, and agent context.
- Apply explicit resource limits where appropriate.
- Document lifecycle, health checks, persistence, backup, and rollback.
- Measure container and service overhead.

## Exceptions

An upstream README or installer does not grant an exception. If a genuine blocker remains after investigation and no safe Podman-compatible solution exists, document the issue, alternatives, risks, and impact, then escalate to the user for a final decision.
