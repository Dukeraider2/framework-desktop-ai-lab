# Proxy Platform Profiles and Compatibility Boundaries

This document separates the reusable proxy architecture from the hardware-specific local inference stack. A configuration is not considered verified merely because its components are expected to be compatible.

## Profile A: Framework Desktop / AMD AI Max+ 395

**Status: tested reference profile for the current beta.**

Observed host environment:

- Framework Desktop with AMD Ryzen AI Max+ 395 and Radeon 8060S integrated GPU.
- Ubuntu 26.04.1 LTS.
- Podman 5.7.0 in rootless mode.
- Tailscale 1.104.2.
- NGINX unprivileged container image using the `stable-alpine` tag.
- Ollama with `qwen3:8b`.

Observed validation includes a local Ollama API response, local proxy API responses, non-streaming generation, Tailscale HTTPS `/api/tags`, and a basic Android OpenAI-compatible prompt/response.

Still unverified: a clean completed end-to-end streaming response, service startup after reboot without interactive login, backup restoration, independent reproduction on a clean machine, and the procedure on other platforms.

The AMD GPU/ROCm/HIP steps belong to the workstation build, not the proxy requirements. The proxy itself forwards HTTP requests to Ollama and does not depend on the GPU vendor.

## Profile B: Generic Linux host

**Status: architecture is intended to be reusable; no independent host validation recorded.**

Expected prerequisites:

- Linux host with a running local Ollama API reachable at `127.0.0.1:11434`.
- A normal non-root user with a functioning systemd user manager.
- Rootless Podman with Quadlet support and `pasta` networking available.
- Tailscale connected to the desired tailnet, with Serve and HTTPS certificates available.
- A model already installed in Ollama.

The current example uses these host-specific integration points:

- `$HOME/.config/containers/systemd/llm-proxy.container`
- `$HOME/.config/llm-proxy/default.conf`
- user unit `llm-proxy.service`
- host loopback port `11435` forwarding to Ollama on `11434`
- Tailscale Serve forwarding to `http://127.0.0.1:11435`

Before running the guide on another distribution, verify the installed Podman/Quadlet version, the `Network=pasta:-T,11434` behavior, bind-mount permissions, systemd user service behavior, and Tailscale Serve CLI syntax. If any prerequisite differs, stop and adapt the setup deliberately rather than blindly copying commands.

## Profile C: Other hardware or container environments

**Status: not validated by this repository.**

NVIDIA, Intel, CPU-only, other AMD systems, non-systemd distributions, rootful containers, Docker, Kubernetes, and other proxy implementations are not covered by the tested profile. Some may be able to run the same general request path, but they require their own documented prerequisites and tests. Do not infer compatibility from the Framework Desktop results.

GPU drivers and model performance are separate concerns. Validate Ollama and its selected inference backend on the target host first, then validate the proxy as a separate layer.

## Minimum acceptance checklist for a new host

Record the host OS/version, kernel, Ollama version, container runtime/version, Tailscale version, and image reference. Then verify each layer separately:

1. Direct Ollama `GET /api/tags` returns HTTP 200 on host loopback.
2. Rootless Quadlet service starts and stays active.
3. Proxy `GET /api/tags` and `GET /v1/models` return HTTP 200 locally.
4. A non-streaming generation completes through the proxy.
5. Proxy listener is bound only to `127.0.0.1`.
6. Tailscale Serve forwards to the proxy and the HTTPS API request succeeds from an authorized tailnet client.
7. An OpenAI-compatible client completes a prompt/response.
8. A streaming response completes successfully.
9. Startup after reboot without interactive login is tested if required.
10. Backup and rollback steps are checked against the host's actual configuration.

Mark each item as passed, failed, or not tested. Do not describe the platform as supported until the relevant acceptance tests have been run and recorded.

## Security boundaries

- Keep the service tailnet-only. Do not enable Tailscale Funnel for this pattern.
- Keep the proxy and Ollama listeners on loopback unless a separately reviewed architecture requires otherwise.
- The example proxy does not add authentication or filter API paths; tailnet access controls are important.
- The example's `stable-alpine` image tag is mutable. For reproducible hardened deployments, pin a verified digest and document how updates are reviewed and tested.
