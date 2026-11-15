# Testing and acceptance plan

## Gate A: development host (can run now)

- Python unit tests for configuration and GGUF parser, tuning dry-run and malicious input rejection.
- Compile standalone AVX2 dot kernel; compare against scalar across random and extreme values. Do not call this a GGML kernel benchmark.
- `bash -n` all scripts; verify Containerfile/Quadlet are reviewed as deployment templates rather than tested services.
- Confirm that `tools/build_llama.py --dry-run` never builds or modifies external sources.

## Gate B: pinned upstream build

- Record exact 40-character llama.cpp SHA (no `master` as a reproducibility ref).
- Create baseline vs Zen 1 builds with compiler version, CMakeCache, binary SHA, build options. Repack OFF vs ON in separate directories.
- Confirm `llama-server --help`, `llama-bench --help`, `test-backend-ops`, and actual instructions via `objdump`.
- Compare Q4_K/Q5_K kernel outputs against GGML oracle, including scale/offset, packed fifth bits, NaN/Inf robustness and boundary lengths. Do not infer real GGML accuracy from synthetic integer tests.

## Gate C: target hardware benchmark (not performed)

- Capture `lscpu -e`, `numactl -H`, BIOS NPS, DIMM speed, kernel, clocks, package thermal and power information.
- 3–10 independent warmed repetitions of a fixed gguf (SHA256), seeds/prompts, context, and prompt+decode lengths.
- Log tokens/s separate for prompt evaluation and decoding, and latency P50/P95. Verify stable model residency and no swap.
- Verify actual GGML function dispatch, repack activation, NUMA page migrations and physical memory bandwidth. Optional `perf` counters may be unavailable.
- Compare baseline vs tuned using paired measurements and report confidence/variation, not only best result.

## Gate D: reliability and security

- Model load/restoration after service restart, read-only mounts, rootless Podman confinement, loopback-only listener, auth boundary for remote access.
- Overnight soak only after thermal validation and capacity checks; record OOM, ECC errors and kernel messages.
- Custom kernel trial is **gated by a known-good default boot**, serial/IPMI recovery, and explicit human approval. Roll back if performance does not improve or any I/O / boot regressions occur.

## Acceptance thresholds (engineering decision, not throughput promises)

- Zero mismatches for standalone exact integer dot-product tests.
- No regression in GGML backend correctness and model quality against upstream for any accepted patch.
- A proposed optimization should improve median end-to-end tg or pp by at least 5% over noise *or* improve tokens/joule with no throughput regression; 5% is a project gate, not a predicted gain.
- Critical service features must keep working; any unapproved privilege, network or kernel-boot change fails review.
