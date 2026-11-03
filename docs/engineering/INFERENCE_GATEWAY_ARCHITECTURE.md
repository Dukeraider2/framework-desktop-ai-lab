# LLM Inference Gateway Architecture

**Status:** Gateway path validated on the Framework Desktop host; agent-container integration and gateway hardening remain to be implemented.  
**Host:** Framework Desktop AI Max+ 395, Ubuntu 26.04.1 LTS  
**Current gateway:** Rootless Podman NGINX proxy  
**Current model backend:** Ollama

## 1. Purpose and ownership

The LLM Inference Gateway is shared infrastructure for language-model inference across Hermes, OpenCode, and future authorized clients. It separates client/agent orchestration from model serving and backend routing.

The gateway is an independent service. Hermes is a client and orchestrator; it does not own the gateway, model processes, or backend lifecycle. Agent containers must use the gateway rather than connecting directly to Ollama.

This LLM gateway is distinct from the **Coral Inference Gateway** planned for the Promethean OPS-M. The Coral service handles supported Edge TPU image/object inference over an application API. It is not a language-model gateway and does not provide a general remote-PCIe device abstraction.

## 2. Current validated topology

    Hermes (host service)       OpenCode / other authorized clients
              |                               |
              +---------------+---------------+
                              |
                              v
                  NGINX LLM Inference Gateway
                     host loopback :11435
                              |
                              v
                        Ollama :11434
                              |
                              v
                    qwen3-coder:30b
                    (current Hermes model)

The Framework host currently runs NGINX in a rootless Podman container using pasta networking. The host publishes the NGINX listener on loopback port 11435; NGINX forwards to Ollama on host loopback port 11434. The active configuration is maintained outside Git in the user's private configuration directory. Do not commit host-specific secrets, private endpoints, or unredacted configuration.

### Validation recorded 2026-11-03

- Direct Ollama /api/tags responded successfully.
- NGINX proxy /api/tags and OpenAI-compatible /v1/models responded successfully.
- An OpenAI-compatible /v1/chat/completions request through the proxy completed and returned the expected sentinel response.
- Hermes configuration was set to provider custom, base_url http://127.0.0.1:11435/v1, and default qwen3-coder:30b.
- The Hermes Gateway service restarted successfully.
- A real Hermes agent turn returned HERMES_INFERENCE_GATEWAY_OK.

These observations validate host-process Hermes → NGINX → Ollama → model → Hermes response. They do **not** validate access from a separate Podman agent container.

## 3. Responsibilities

| Component | Responsibility |
| --- | --- |
| Client/agent | Submit OpenAI-compatible inference requests and consume responses. |
| Hermes | Orchestrate tasks and agents; choose model/client settings allowed by policy. |
| LLM Inference Gateway | Provide a stable client endpoint, route requests to configured model backends, and eventually apply authentication, authorization, quotas, observability, and backend selection. |
| Ollama | Serve local models as one backend. |
| Other future backends | May include vLLM, llama.cpp, or remote inference services after separate compatibility and resource validation. |

Clients should not need backend-specific knowledge beyond the model identifier and supported API contract. Backend selection and routing policy belong at the gateway layer.

## 4. Agent-container connectivity requirement

The current gateway listener is bound to host loopback. A container's 127.0.0.1 refers to that container's own network namespace, not the host. Therefore, the host endpoint 127.0.0.1:11435 must not be copied unchanged into a separate agent container's configuration unless its network arrangement explicitly shares the host namespace (which is not the default and is not the preferred isolation model).

Before agent deployment, design and validate a controlled container-to-gateway path. Prefer a dedicated Podman network or a narrowly scoped host-side service path that does not expose Ollama directly. The implementation must document:
- How the agent container resolves and reaches the gateway.
- Which network(s) can reach the gateway and which cannot.
- Whether traffic is authenticated and how client identity is represented.
- How gateway access is revoked when an agent/task ends.
- How access is limited so agent containers cannot reach Ollama's backend listener directly.
- How host-only clients and remote tailnet clients are kept within their intended trust boundaries.

Do not assume that pasta, host.containers.internal, a shared network, or a loopback mapping behaves a particular way without checking the installed Podman version and running a test.

## 5. Security requirements and current gaps

The current NGINX proxy is a functional reverse proxy, not yet a complete multi-client security gateway. Its current configuration does not provide built-in API authentication, per-client authorization, quotas, or model-level access controls. The loopback binding and existing host/tailnet boundaries limit reachability, but do not constitute per-agent identity.

Before expanding access beyond the current host process:
1. Define the intended client trust zones (host services, task containers, tailnet clients).
2. Choose and validate an authentication/authorization mechanism suitable for those zones.
3. Restrict network reachability to approved clients.
4. Avoid passing a shared broad credential to every agent; use task-scoped credentials where feasible.
5. Keep secrets out of source control, images, logs, and agent prompts.
6. Add request-size, timeout, concurrency, and resource controls appropriate to the host.
7. Log request metadata needed for operations without logging prompts/responses or sensitive payloads by default.
8. Test that unauthorized clients are rejected and that an agent cannot bypass the gateway to reach Ollama.

Do not expose ports 11434 or 11435 on public interfaces as a workaround. Do not enable Tailscale Funnel. Any change to the current working proxy or Tailscale routing requires a documented preflight, backup, validation, and rollback plan.

## 6. Backend evolution

The initial backend is Ollama. Future backend adapters are candidates, not commitments. Each backend requires:
- Verified API compatibility and model naming behavior.
- Health/readiness checks and failure handling.
- Model discovery and capability reporting.
- Context/output limits and streaming/tool-call compatibility tests.
- GPU/VRAM and system-resource measurements.
- Concurrency and queueing behavior.
- Documented fallback and rollback behavior.

The gateway should expose a stable client contract and keep backend-specific behavior behind adapters/configuration. Avoid adding a complex orchestration framework before a demonstrated need.

## 7. Observability and operations

The gateway should eventually provide:
- Liveness and readiness checks that distinguish proxy health from backend/model health.
- Structured, sanitized access/error logs.
- Request counts, error rates, latency, token usage where available, queue depth, and backend identity.
- Resource metrics for CPU, RAM, GPU/VRAM, and network I/O.
- Timeouts, bounded concurrency, backpressure, and predictable failure responses.
- Service supervision, startup ordering, backup, rollback, and recovery procedures.

Do not claim these capabilities exist until they are implemented and tested. Preserve the current working NGINX/Ollama path while introducing changes in small, reversible stages.

## 8. Implementation sequence

1. Inventory the current NGINX container, configuration, Podman network mode, systemd/Quadlet service, Ollama service, model list, and client configuration. Do not change them during inventory.
2. Record exact versions and sanitized configuration; identify the source-of-truth host files without copying secrets into Git.
3. Design the agent-container network path and trust boundaries.
4. Prototype one restricted Podman agent and prove it can reach the gateway but cannot reach Ollama directly or unrelated host services.
5. Add authentication/authorization appropriate to the approved client zones.
6. Add health, logging, metrics, request controls, and backend abstraction incrementally.
7. Test multiple agents, concurrent requests, cancellation, gateway/backend failure, and host restart.
8. Update the operational guide with observed commands and results.

## 9. Relationship to the Coral gateway

The Coral gateway remains a separate project and service on the Promethean OPS-M. It serves Edge TPU-compatible image/object workloads and Frigate integration. Do not merge the Coral device API into the LLM routing service or describe the Coral as an Ollama backend. A future common resource directory or dispatch layer may be researched separately, but it is not a prerequisite for either gateway.

## Related documents

- [Hermes-Managed Podman Agent Runtime](HERMES_PODMAN_AGENT_RUNTIME.md)
- [Podman-First Container Policy](PODMAN_FIRST_POLICY.md)
- [Access and Governance](ACCESS_GOVERNANCE.md)
- [LLM proxy beta guide](../OLLAMA_TAILSCALE_PROXY_GUIDE.md)
- [Coral Inference Gateway](../CORAL_INFERENCE_GATEWAY/README.md)
