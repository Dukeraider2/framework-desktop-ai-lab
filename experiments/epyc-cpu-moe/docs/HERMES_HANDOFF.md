# Hermes project-manager handoff: Experimental EPYC CPU MoE Server Stack

## Scope and authority

Create a **new isolated server project** under `experiments/epyc-cpu-moe/` or in a new dedicated repository via owner-approved GitHub branch/PR. Source artifacts are in this package; **do not merge, deploy or enable** automatically. Hermes is project manager and access gate. OpenCode is an implementation worker, independent reviewer is separate. Changes that require additional access state the precise reason and least-privilege scope; Hermes either grants/denies with a practical alternative or escalates if none exists.

**Critical governance check:** The existing Framework Desktop model manager has a **100GB local deployment ceiling**. A 400B MoE server GGUF may exceed 200GB, so this must be explicitly evaluated as **a new server-specific capacity and deployment policy**, not silently treated as an exception on the Framework Desktop. The server does not inherit the desktop's tested ROCm GPU profile. No production activation until owner approves the server boundary and policy.

## Stage 1: Specification and evidence

- Pin upstream llama.cpp to an exact commit SHA and document sources.
- Verify EPYC 7571 microarchitecture, target Gigabyte MZ71-OP0 Rev A00 BIOS/NUMA, DIMM population and memory clocks from official manuals.
- Review `docs/ZEN1_GGML_AUDIT.md` against the pinned code. It was previously audited against moving `master` without a SHA.
- Validate kernel config fragment symbols against pinned maintained kernel source. Identify required network/storage drivers, security mitigations, kernel signing and rollback prerequisites.
- Define hardware test matrix, model eligibility (weights/license/GGUF quant mix), acceptance gates, and no-go criteria. Produce a GitHub issue and Stage 1 task package.

## Stage 2: Implementation and evidence

- Import this scaffold in a branch; keep rootless Podman and CPU-only kernel/service restrictions.
- Run portable Python checks and synthetic AVX2 checks. Log elapsed time, compiler, CPU and observed results.
- Build pinned llama.cpp baseline and Zen 1 variants on an available development host, if authorized. Build-only kernel artifacts are permitted only after Stage 1 review; never install them.
- Inspect actual Q4_K/Q5_K GEMV/`MUL_MAT_ID` dispatch and emitted assembly. Implement one small independent optimization at a time with GGML correctness tests. Track performance counter availability and static resource overhead.
- Report changes, evidence, unresolved risks, resource measurements, elapsed time, and exact rollback commands in Stage 2 report.

## Stage 3: Independent review

- Reviewer validates that no hidden Docker dependency, host network exposure, insecure GRUB flag, secret logging, unreviewed model policy exception, or source SHA drift occurred.
- Test numerical equivalence and container isolation; verify test coverage and reproducibility claims rather than relying on summaries.
- Score 0–10 on correctness, security, resource efficiency, reproducibility, compatibility and recovery; record review time and blocking findings.
- Deployment to the dual EPYC server, BIOS changes and any kernel installation **require a separate explicit owner authorization** after the hardware is available. No GPU acceleration in this phase.

## First GitHub issues (proposed, not yet created)

1. Pin, inventory and re-audit upstream GGML quantization dispatch.
2. Design safe supported baseline kernel and reversible NUMA/THP experiments.
3. Compile and validate synthetic AVX2 dot reference; establish GGML backend tests.
4. Review rootless Podman image and Quadlet networking/security boundary.
5. Define model registry capacity exception and CPU-specific 400B GGUF eligibility.
6. Define independent performance/electrical/thermal benchmarking and fallback kernel procedures.
