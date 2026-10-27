# Framework Desktop AI Lab

A reproducible, OPSEC-conscious build log for an AMD Ryzen AI Max+ 395 Framework Desktop running Ubuntu Desktop.

> **Proxy beta materials:** Community testing is open for the v0.1.0-beta.1 candidate. Local proxy discovery and non-streaming inference passed, Tailscale HTTPS `/api/tags` returned HTTP 200 after cutover, and an Android OpenAI-compatible client completed a basic prompt/response. A clean completed streaming test, reboot startup without login, and backup restoration remain unverified. See [beta notes](docs/RELEASE_NOTES_v0.1.0-beta.1.md), [beta guide](docs/OLLAMA_TAILSCALE_PROXY_GUIDE.md), [proxy operations](docs/LLM_PROXY_OPERATIONS.md), and [status log](docs/STATUS_2026-10-26.md).

## Project goals

- Maintain a clean Ubuntu Desktop baseline.
- Verify networking, Vulkan, ROCm/HIP, and local inference independently.
- Keep instructions reproducible and public documentation OPSEC-conscious.
- Validate the UGREEN capture workflow and OBS at 1080p60.

## Safety rules

1. Make one change at a time and record observed results.
2. Review destructive disk operations and identify target disks positively.
3. Never publish credentials, device keys, private IP maps, MAC addresses, serial numbers, or unredacted logs.
4. Keep model weights and caches outside OS restore images.
5. Use `$HOME` and `$XDG_CONFIG_HOME` instead of personal hard-coded paths.

## Repository map

- `docs/PLAN.md` — phased plan
- `docs/COMPATIBILITY.md` — compatibility matrix
- `docs/BASELINE.md` — system baseline
- `docs/RESTORE_POINTS.md` — backup and restore strategy
- `docs/NETWORK_AND_TAILSCALE.md` — networking and remote access
- `docs/GPU_VALIDATION.md` — Vulkan, ROCm/HIP, and PyTorch
- `docs/STREAMING.md` — capture card and OBS
- `docs/OPSEC.md` — public repository hygiene
- `docs/LLM_PROXY_OPERATIONS.md` — proxy operations and rollback
- `docs/OLLAMA_TAILSCALE_PROXY_GUIDE.md` — beta guide
- `docs/RELEASE_NOTES_v0.1.0-beta.1.md` — beta scope and limitations
- `examples/nginx/ollama.conf` — NGINX example
- `examples/quadlet/llm-proxy.container` — rootless Quadlet example
- `docs/INSTALLATION_RECORD.md` — retained commands and observations
- `docs/TEST_LOG_TEMPLATE.md` — test log template
- `docs/SOURCES.md` — official references

## Platform status

- Framework Desktop, Ryzen AI Max+ 395, Ubuntu 26.04.
- ROCm/HIP smoke test passed for `gfx1151`; Vulkan enumerates the Radeon GPU.
- Ollama loaded `qwen3:8b` with GPU placement reported at 100% in the observed test.
- Encrypted backup checksums verified; restore not tested.
- UGREEN capture workflow and sustained 1080p60 behavior remain unverified.

Only observed results are marked as passes. See dated status records for test boundaries.
