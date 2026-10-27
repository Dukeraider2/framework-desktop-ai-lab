# Framework Desktop AI Lab

A reproducible, OPSEC-conscious build log for an AMD Ryzen AI Max+ 395 Framework Desktop running Ubuntu Desktop. The project covers local AI, GPU compute, remote access, and a separate streaming/recording workflow.

> **Status:** Active validation. HIP smoke test, Vulkan device enumeration, Ollama GPU placement, and encrypted-backup checksum verification have been observed. The cause of the Tailscale HTTPS HTTP 403 has been isolated to the upstream Host header; the permanent proxy fix is planned, not deployed. See the [2026-10-26 status update](docs/STATUS_2026-10-26.md) and [LLM proxy operations guide](docs/LLM_PROXY_OPERATIONS.md).

## Goals
- Establish a clean, maintainable Ubuntu Desktop baseline.
- Verify network drivers and firmware rather than assuming the defaults are optimal.
- Re-establish Tailscale access after reinstall without copying old identity/key files.
- Validate Vulkan separately from ROCm/HIP compute.
- Add a compatible PyTorch build only after ROCm is verified.
- Run a small local inference test before downloading larger models.
- Validate a UGREEN HDMI capture device with Linux and OBS at 1080p60.
- Prefer open-source tools and evaluate Rust applications where useful.
- Keep documentation executable, reproducible, and safe for a public repository.

## Engineering rules
1. Verify compatibility from current official documentation before selecting OS/kernel/driver versions.
2. Make one change at a time and record expected and actual results.
3. Review destructive disk operations before execution; positively identify target disks.
4. Keep model weights, datasets, and caches outside OS restore images.
5. Never publish credentials, device keys, private IP maps, MAC addresses, serial numbers, or unredacted logs.
6. Never mark a test as passed until its output has been observed on the target system.
7. Prefer variables such as `$HOME` and `$XDG_CONFIG_HOME` over hard-coded personal paths.

## Roadmap

| Phase | Goal | Exit criteria |
|---|---|---|
| 0 | Compatibility research | Dated, source-backed OS/kernel/ROCm/Vulkan/PyTorch matrix |
| 1 | Clean Ubuntu baseline | OS boots, updates and inventory verified; RP0 captured |
| 2 | Network and Tailscale | Driver/firmware identified and remote access tested |
| 3 | Vulkan | Lightweight render test passes; compute test if practical |
| 4 | ROCm/HIP | GPU discovery and tiny GPU compute test pass |
| 5 | PyTorch | Compatible backend performs a small GPU tensor operation |
| 6 | Local inference | Lightweight model runs; weights stored separately |
| 7 | Streaming | Capture card and OBS stable at 1080p60 |
| 8 | Rust/open-source tooling | Useful tools evaluated; optional inventory utility documented |

## Restore points
- **RP0:** Clean, updated Ubuntu baseline, before ROCm.
- **RP1:** Network/Tailscale and Vulkan verified.
- **RP2:** ROCm/HIP verified.
- **RP3:** PyTorch verified. Exclude model weights.
- **Optional RP4:** Stable streaming configuration.

Use an imaging tool selected after checking external SSD health, capacity, filesystem and recovery requirements. Verify images and recovery media before relying on them.

## Repository map
- `docs/PLAN.md` — phased plan and gates
- `docs/COMPATIBILITY.md` — compatibility decision matrix
- `docs/BASELINE.md` — inventory and baseline requirements
- `docs/RESTORE_POINTS.md` — backup and restore strategy
- `docs/NETWORK_AND_TAILSCALE.md` — driver verification and remote access
- `docs/GPU_VALIDATION.md` — Vulkan, ROCm/HIP and PyTorch tests
- `docs/STREAMING.md` — capture card and OBS
- `docs/OPSEC.md` — public repository hygiene
- `docs/STATUS_2026-10-25.md` — earlier sanitized status snapshot
- `docs/STATUS_2026-10-26.md` — LLM HTTP 403 diagnosis and current proxy status
- `docs/LLM_PROXY_OPERATIONS.md` — planned proxy architecture, config maintenance, startup, controls, and rollback
- `docs/INSTALLATION_RECORD.md` — installation sequence, exact retained commands, and observed verification results
- `docs/TEST_LOG_TEMPLATE.md` — repeatable test records
- `docs/SOURCES.md` — official references

## Current known context
- Target platform: AMD Ryzen AI Max+ 395 Framework Desktop running Ubuntu 26.04 (Resolute).
- ROCm/HIP smoke test passed for `gfx1151`; Vulkan device enumeration identifies the Radeon GPU through RADV.
- Ollama successfully loaded `qwen3:8b` with GPU placement reported at 100% during the observed test.
- An encrypted secondary-SSD backup was created and its checksums verified; full restore recovery has not been tested.
- Ollama local `/api/tags` and `/v1/models` return HTTP 200. The same routes through Tailscale HTTPS return HTTP 403 unless the upstream Host header is overridden to `localhost:11434`. A Podman reverse-proxy fix is planned but not deployed.
- The UGREEN capture device workflow remains unvalidated; exact model and sustained 1080p60 behavior are not verified.

See the dated status logs for test boundaries. Only observed results are marked as passes.
