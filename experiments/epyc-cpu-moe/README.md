# EPYC CPU MoE Experimental Server Stack

**v0.1.0-development | Designed 2026-11-14 | Not deployed, tuned, or performance-tested on EPYC 7571.**

A reproducible **CPU-only** software stack and experimental optimization harness for a 400B-class MoE model on a dual AMD EPYC 7571, 512 GiB DDR4 ECC, NUMA-aware Linux server. This repository is intentionally isolated from the running Framework AI Desktop stack. It can be imported under `experiments/epyc-cpu-moe/` in the user's existing AI-lab repository after review.

## Design goals

- **No ROCm/CUDA dependence** for this phase. Disable GPU offload explicitly.
- **Rootless Podman + systemd Quadlet** for the eventual inference service; keep the HTTP service loopback-only by default.
- **Upstream llama.cpp pinned by exact commit**, with distinct baseline, Zen 1 and repack experiments. No unreviewed source patches.
- **Kernel included in the experiments**, but test a supported distro kernel first; don't replace a working boot kernel without measured evidence and a rollback mechanism.
- **NUMA-informed, not NUMA-assumed:** Naples contains four dies per socket; firmware may expose multiple nodes per socket. Discover topology before binding.
- **Least privilege / governance:** Hermes approval for deployment or changing host settings; never install Docker, disable security mitigations, or alter boot settings automatically.
- **Performance & correctness**: score decode tokens/sec, prompt tokens/sec, time to first token, memory distribution, power if observable, numerical correctness and rollback.

## Layer map

| Layer | Status in this package | Components |
|---|---|---|
| Hardware / BIOS | Specification | Naples topology, 16-channel population check, BIOS NPS/SMT tests |
| OS | Specification | Ubuntu Server 26.04 LTS candidate; retain stock kernel as baseline |
| Linux kernel | Source preparation, config and runtime tuning tools | Baseline vs experimental config, reversible THP / NUMA balancing profiles, never installs |
| CPU kernels | Compilable standalone reference prototype | AVX2 `VPMADDUBSW` + `VPMADDWD` unsigned-5-bit/signed-8-bit dot test; scalar oracle |
| Inference | Source-build script, no upstream code bundled | llama.cpp GGML AVX2, pinned SHA, Zen 1 CMake options |
| Container | Build recipe + opt-in Quadlet | CPU-only rootless Podman service, read-only model storage, loopback binding |
| Management | Documented interface | Existing Hermes PM / OpenCode worker, OpenAI-style API consumer |
| Diagnostics | Executable read-only tools | Host inventory, GGUF format histogram, benchmark wrapper, tune apply/rollback |
| Security / continuity | Design specification | Offline model hashes, network boundary, backup, fallback kernel |

## Start with development, not deployment

1. Read `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, and `docs/KERNEL_EXPERIMENTS.md`.
2. Perform safe local validation: `python3 -m unittest discover -s tests -v` and `bash -n kernel/prepare-kernel.sh tools/*.sh`.
3. Compile/test **the synthetic integer dot-product reference** (on a supporting x86 host) using `make -C microkernels check`.
4. When server hardware exists, capture a read-only topology: `python3 tools/inventory.py --out results/inventory.json`.
5. With an **existing pinned** checkout of upstream llama.cpp, run `python3 tools/build_llama.py --source /path/to/llama.cpp --profile baseline --dry-run`. Read `tools/build_llama.py --help` before enabling a build.
6. Future hardware test: choose a GGUF, verify hash (`tools/gguf_inventory.py`), then use `tools/benchmark.py --dry-run` to inspect experimental commands.
7. Only later: build a rootless Podman image and enable the included Quadlet after reviewing bind mount, image digest, auth boundary, CPU mapping and endpoint policy.

**No `sudo`, no kernel changes, no server started, no GitHub push in this package. The existing AI lab model registry has a 100 GB desktop deployment ceiling; the proposed 400B server requires an explicitly approved **separate capacity policy** before deployment. See `docs/HERMES_HANDOFF.md`.**

## Critical limitations

- The AVX2 reference only proves an integer identity on synthetic 5-bit weights. It **does not implement GGUF Q5_K layout, GGML quantization scales, or numerical equivalence to the live backend**.
- The kernel config fragment is **a proposed experiment**, not a proven superior kernel. It does not replace the distribution's security and device-driver configuration.
- Actual throughput for any 400B MoE checkpoint is **unknown**. Earlier estimates should not be treated as benchmarks.
- Podman, CMake, Linux kernel and llama.cpp flags can change. The first test on the exact pinned source/platform must verify them before enabling.
