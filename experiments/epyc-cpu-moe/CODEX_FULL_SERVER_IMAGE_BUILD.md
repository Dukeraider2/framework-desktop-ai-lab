# Codex execution brief: Build a complete, optimized CPU-only EPYC MoE Linux server image

**Task mode: IMPLEMENT AND BUILD. Do not stop at research or a proposed design.** Work on the existing `codex/epyc-moe-full-os-image` branch, produce an actual reproducible bootable Linux disk image, verify it in a VM, and open/update a PR. Never deploy to real disks or reboot the workstation without explicit user approval.

## Platform and immutable requirements
- Target: Gigabyte MZ71-OP0 Rev A00, **2× owned AMD EPYC 7571 (Naples/Zen 1), 64 physical cores/128 threads total, 512 GiB ECC RDIMM, 16 memory channels**, x86-64/UEFI if firmware permits. Discover the real topology and supported DIMM speeds on physical hardware, do not assume NUMA nodes equal sockets.
- This phase is **CPU-only**: no required ROCm, HIP, CUDA, NVIDIA software or GPU offload. Use AVX2/FMA3/F16C/BMI2 only where supported; prohibit AVX-512/VNNI assumptions.
- Ubuntu Server **26.04.1 LTS amd64** is the starting OS release. Verify the official image checksums, package availability and boot method. A documented LTS fallback is acceptable only when a verified technical blocker prevents the target release; do not silently substitute one.
- Rootless **Podman**, systemd/Quadlet; **no Docker installation**. Use the existing repository engineering governance. No credentials, secrets, private IPs, model weights or personal data in Git or image.
- System must ship preconfigured with the OS, kernel(s), dependencies, compiled CPU-only llama.cpp/llama-server, service units, NUMA tools, monitoring, and benchmark tools. A 400B model checkpoint is **not** baked in: keep model configuration flexible, enforce license/checksum/storage gate, and leave inference service disabled until a user-approved model is provisioned.

## Step 0: Import the versioned research framework
1. Read root `docs/engineering/*`, especially `DEVELOPMENT_WORKFLOW.md`, `RESOURCE_EFFICIENCY.md`, `PODMAN_FIRST_POLICY.md`, `ACCESS_GOVERNANCE.md`.
2. Read `experiments/epyc-cpu-moe/bootstrap/README.md`. The v0.1 research framework is stored in numbered Base64 bundle parts in that directory. Verify **every part** and reconstructed tarball hash. Extract to `experiments/epyc-cpu-moe/`, retaining the imported files in ordinary Git-tracked text/source form. Treat v0.1 scripts as untrusted prototypes requiring audits and bug fixes, not production-ready components.
3. Preserve the stock distribution kernel and boot image as a rollback baseline.

## Phase 1: Research, sources and build plan
Research **official primary documents**, explicitly verifying versions and options: Canonical Ubuntu 26.04.1/server images and release notes; Subiquity/autoinstall; systemd **mkosi** bootable disk images; Linux kernel documentation/Kconfig and kernel packaging; Gigabyte MZ71-OP0 Rev A00 manuals and BIOS/EPYC 7001 memory population guide; AMD Naples architecture, ISA and NUMA behavior; llama.cpp GGML CPU backend and exact build flag names; Podman/Quadlet; QEMU/OVMF; Linux `perf`, `numactl`, `hwloc` and power/telemetry methods.
- Produce `docs/SOURCE_LOCK.md`: URL, official owner, specific version/commit/digest, date checked, license, relevance, supported and unverified claims.
- Choose and document an actual image builder. **Prefer mkosi** for a fully provisioned bootable GPT/UEFI disk image if confirmed compatible with Ubuntu 26.04.1. Compare Canonical Subiquity autoinstall for an optional installer ISO. Do not mislabel a network-dependent installer as a fully preinstalled offline system.
- Produce a build matrix and design with space/RAM/disk resource budget, supply chain review, firmware/driver assumptions, artifact formats, reproducibility limitations, recovery strategy, and test gates. Use exact source pins or dated package snapshots when possible.

## Phase 2: Implement full image and kernel variants
Build a repeatable, scripted image pipeline in `experiments/epyc-cpu-moe/image/` that works from a clean compatible builder and emits:
1. A bootable **pre-provisioned raw disk image** (`.raw.zst` or `.img.zst`) and **qcow2** for QEMU UEFI smoke tests.
2. Optional **installer ISO** only if it truly installs the same preconfigured server, with a safe interactive storage target selection or strictly verified opt-in disk choice. Never hardcode a destructive disk target.
3. Installed packages and source-pinned **CPU-only llama.cpp** binaries; Zen1 profile and generic fallback; AVX2 kernel tests and GGML correctness checks; no requirement for downloading a 400B checkpoint at image creation.
4. **Baseline distro kernel**, plus an **experimental Zen 1 throughput kernel** as a separate selectable boot entry. Build from verified source, preserving driver, initramfs, networking, boot, security and mitigation support. Verify Kconfig fragments survive `olddefconfig`. Document CPU scheduler/IRQ/cgroup v2, NUMA, THP/huge pages, memory policies, SMT and kernel parameters as independent experiments. Do not claim arbitrary kernel flags improve inference. Do not disable mitigations, signature verification, AppArmor or Secure Boot for speed.
5. Podman rootless Quadlet for llama-server, loopback-only OpenAI-compatible endpoint, read-only model storage, explicit user mapping, restart/health/log/resource limits, safe first-boot provisioning, service inactive until model path validated. No Docker, privileged containers, broad host filesystem mounts, or Tailscale enrollment without human credentials/approval.
6. Server configuration: SSH key-based admin bootstrap without embedded keys, firewalls, time sync, unattended security updates with change controls, NVMe model/cache partitions adjustable at install time, no swap by default only after measurement and safe OOM policy; log rotation, monitoring and a simple inventory/status command.
7. Separate tuning profiles for distro baseline, THP, NUMA placement, huge pages and IRQ/affinity. Tune **userspace instruction kernels** (including Q4_K/Q5_K/repack) independently from kernel tuning. Preserve numerical correctness; use feature-detected fallback. Do not submit unsupported custom assembly as working code.
8. Full clean-build scripts, pinned manifests, artifact SHA256, provenance/SBOM if tools exist, documentation, safe rollback, restore tests and reproducibility notes. Keep release image binaries outside Git history and publish via reviewed GitHub release/artifacts if authorized.

## Phase 3: Compile, validate and report
- Actually run the image build; capture commands, source hashes, package manifest, build logs, sizes, exit codes, artifact SHA256. If compute/network/admin access blocks execution, isolate the blocker, report exactly which artifact was/was not built, and request only least-privilege access under Hermes governance. Do not claim success from a script that was never executed.
- Test UEFI QEMU boot via OVMF, non-destructive virtual disk, SSH/login provisioning, installed packages, `uname -r`, default distro kernel and experimental alternate entry, kernel module compatibility, rootless Podman/Quadlet, no GPU dependencies, loopback bind, disabled-until-provisioned service, reboots, persistence, update behavior and rollback.
- With a small licensed test GGUF (approved separately), smoke-test llama-server and an OpenAI-compatible request. Independently validate AVX2 dot-product oracle/overflow and GGML backend ops; profile prompt processing, decode tokens/sec, first-token latency, NUMA remote traffic, CPU cycles, power, memory and idle overhead where available.
- EPYC 7571 physical-hardware tests must be explicitly marked **pending** until performed on that machine. Report measured vs estimated outcomes distinctly.
- End with `BUILD_REPORT.md`, `TEST_REPORT.md`, `REPRODUCE.md`, `ROLLBACK.md`, `SECURITY_REVIEW.md`, source lockfile, checksums and exact output paths. Create GitHub issues/PRs for blockers and independent Stage 3 review, not an unreviewed merge.

## Operating rules
- **Do the work**: research → implement → compile → VM-test → correct failures → provide artifacts. Do not stop after producing another plan.
- Prefer scripts that are idempotent and dry-run capable. No `curl | bash`, `sudo` escalation or destructive operations outside reviewed isolated VM/image build context.
- Do not modify the Framework AI desktop services, its kernel, existing Tailscale gateway, running Ollama/ROCm installations or production system config.
- Record working source links and evidence. Correct wrong assumptions rather than fabricate benchmarks.
- Publish incremental commits to `codex/epyc-moe-full-os-image`, open a **draft PR** for independent review, and report exact commit/artifact status. Leave deployment to physical hardware for user approval.

### Authoritative starting references
- Canonical Ubuntu 26.04.1 release: https://wiki.ubuntu.com/Releases
- Subiquity autoinstall: https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html
- systemd mkosi: https://github.com/systemd/mkosi and https://manpages.ubuntu.com/manpages/resolute/man1/mkosi.1.html
- Linux CPU isolation: https://docs.kernel.org/admin-guide/cpu-isolation.html
- Linux boot parameters: https://docs.kernel.org/admin-guide/kernel-parameters.html
- llama.cpp: https://github.com/ggml-org/llama.cpp
- Podman policy in this repository: `docs/engineering/PODMAN_FIRST_POLICY.md`

**Definition of done:** source-locked, reproducible, security-conscious, full server image *actually compiled* and booted in a clean QEMU/UEFI VM; logged evidence and rollback, with physical EPYC performance awaiting later testing.
