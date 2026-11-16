# Architecture and staged development contract

## CPU-only data path

```
Hermes / authorized OpenAI-compatible client
   -> host loopback or authenticated Tailscale gateway (future)
   -> rootless Podman llama-server (model /models:ro)
   -> GGML CPU dispatcher
   -> Q4_K/Q5_K/Q6_K expert kernels and optional repacked GEMV
   -> NUMA-aware CPU threads, CPU cache and local DDR4 across EPYC dies
```

No direct internet exposure. Loopback-only in the provided Quadlet; any LAN or Tailscale endpoint requires a separately approved authenticated proxy. Never reuse workstation inference ports blindly. Secrets do not go into Git.

## Hardware constraints

- 2 × EPYC 7571, Zen 1, 64 total physical cores (128 SMT threads), AVX2/FMA/F16C/BMI2, no AVX-512/VNNI.
- Each Naples socket contains four dies with two memory channels per die. Dual-socket default may expose up to eight NUMA nodes; firmware NPS settings determine actual Linux view. **Never hardcode two NUMA nodes.**
- Target 512 GiB DDR4 ECC RDIMM; prefer symmetrical channel populations; check DIMM speed/ranks and actual speed from BIOS and `dmidecode` before drawing bandwidth conclusions. Verify 16×32GiB versus 32×16GiB.
- Model once in a shared process address space. NUMA placement is not replication; Linux can map distinct weight pages in distinct memory nodes.

## Component boundaries

1. **Kernel baseline**: supported Ubuntu Server LTS, updated/security-patched; record `uname`, kernel config, BIOS/firmware and CPU topology. Unsupported custom kernels never replace baseline in-place.
2. **Kernel experiment**: change one runtime option (THP, NUMA auto balancing, optionally governor if available), collect before/after, restore. Only then consider a separate compile-and-boot custom kernel using `kernel/prepare-kernel.sh`. Kernel optimizations can hurt throughput; results decide.
3. **Inference engine**: exact upstream commit, baseline and `-march=znver1` build variants, Q4_K/Q5_K dispatch and repack traces; preserve `ggml` API and tests. No handwritten assembly until the optimizer fails to produce target instructions.
4. **Kernel laboratory**: test arithmetic overflow and correctness for unsigned 5-bit weights and signed 8-bit activations. Later port a proven change into GGML in a separate small patch with backend-ops verification.
5. **Service**: rootless Podman Quadlet, local bind only, read-only weights, no privileged containers, no GPU passthrough, no Docker.
6. **Observability**: read-only probes, run/commit metadata, reproducible `llama-bench` JSON, `perf` counters where permitted; do not leak host secrets.
7. **Governance**: Hermes approves privileges and security boundary changes; OpenCode implements in an isolated branch; independent review gates before integration.

## Experiment matrix (future EPYC hardware validation)

| Experiment | Baseline | Variant | Key metric |
|---|---|---|---|
| Instruction set | stock upstream | Zen 1 CFLAGS | end-to-end tg/pp, IPC |
| Repack | GGML_CPU_REPACK=OFF | ON | expert GEMV actual dispatch and tg |
| NUMA | OS default | distribute / numactl | tg, remote pages, locality |
| Thread count | 16 | 32 / 48 / 64 | tg, CPU utilization |
| Memory pages | distro defaults | THP madvise | tg, faults, tail latency |
| NUMA auto balancing | default | explicitly disabled | tg, page migrations |
| Kernel | stock LTS | proposed rebuilt LTS kernel | tg, stability, network, regressions |
| Quantization | Q4_K_M | Q5_K_M | quality, RAM, tg, pp |

**Comparability rules:** identical GGUF and prompt, warmed cache, run order randomized, temperature/frequency logged, medians plus spread, roll back between states. For model comparison, report tensor type histogram, not only file name.

## Stage gates

- **Stage 1 (specification):** exact source refs, hardware capability detection, equations, rollback and acceptance criteria; no host mutations.
- **Stage 2 (implementation):** compile isolated kernels, add tests, document changes, produce build artifacts; no target-server deployment.
- **Stage 3 (independent review and measured validation):** static/security review, no privileged actions until explicit approval; EPYC hardware test when available.

Only benchmark data recorded from the actual EPYC hardware may be used to claim practical tokens/sec.
