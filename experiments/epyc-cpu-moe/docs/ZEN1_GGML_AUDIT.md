# Zen 1 / EPYC 7571: GGML Q4_K and Q5_K Integer Dot-Product Audit

**Research date:** 2026-11-14
**Target:** Dual AMD EPYC 7571 (Zen 1), CPU-only inference, 512 GB ECC DDR4, 400B-class MoE.
**Reference:** `ggml-org/llama.cpp`, upstream `master` inspected on research date. **Commit SHA not captured**; pin the checkout before implementation.
**Status:** Static source review complete. No code changed, compiled, or benchmarked on an EPYC 7571.

## Executive finding

The core AVX2 integer dot-product sequence is **already fused** in upstream GGML. The promising optimization is not adding a missing `VPMADDUBSW` path. It is validating which implementation the production runtime actually calls, then reducing **Q5_K decode overhead**, **Q4_K scale/offset overhead**, and unnecessary execution dependencies on Zen 1. For Q4_K there is an **existing x86 AVX2 8×8 repacked GEMV path** that must be benchmarked against the plain dot kernel before modifications. The default CMake configuration declares `GGML_CPU_REPACK=ON`, but actual use depends on model-loading and runtime configuration.

## Inspected source paths

- [`ggml/src/ggml-cpu/arch/x86/quants.c`](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cpu/arch/x86/quants.c): `ggml_vec_dot_q4_K_q8_K` approximately lines 1907–2065; `ggml_vec_dot_q5_K_q8_K` approximately lines 2067–2155 (AVX2 portions).
- [`ggml/src/ggml-cpu/arch/x86/repack.cpp`](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cpu/arch/x86/repack.cpp): `ggml_gemv_q4_K_8x8_q8_K` approximately line 1244 onward.
- [`ggml/src/ggml-cpu/repack.cpp`](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cpu/repack.cpp): repack dispatch approximately lines 4615–4670 and support for `GGML_OP_MUL_MAT_ID` approximately 4793–4826.
- [`ggml/src/ggml-common.h`](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-common.h): `block_q4_K`, `block_q5_K`, and `block_q8_K` layouts approximately lines 302–351.
- [`ggml/CMakeLists.txt`](https://github.com/ggml-org/llama.cpp/blob/master/ggml/CMakeLists.txt): `GGML_CPU_REPACK` defaults to `ON` at the time reviewed.

## Confirmed behavior

| Feature | Q4_K | Q5_K |
| --- | --- | --- |
| Superblock | 256 weights | 256 weights |
| On-disk packed block | 144 bytes; 4.5 bits/weight | 176 bytes; 5.5 bits/weight |
| Subblock quantization | 8 groups of 32 values | 8 groups of 32 values |
| AVX2 nibble extraction | Present | Present |
| Fifth-bit reconstruction | Not needed | Present; high-bit mask/shift pipeline |
| `VPMADDUBSW` | Present | Present |
| `VPMADDWD` | Present | Present |
| FP32 scale/offset accumulation | Present | Present |
| x86 AVX2 repack dispatch | **Present** for Q4_K with eligible row dimensions | **No x86 AVX2 branch** in inspected dispatch; Q5_K dispatch there targets ARM NEON |

### Dot product composition

1. Load packed low (and, for Q5_K, high) quantized weight bits.
2. Expand into unsigned bytes in 0–15 / 0–31 range and load signed Q8_K activation bytes.
3. Execute unsigned×signed byte multiply-add using `VPMADDUBSW`.
4. Multiply grouped 16-bit products by packed quantization scales via `VPMADDWD` into 32-bit lanes.
5. Accumulate, convert to FP32, apply per-block scales, and subtract the zero-point/min correction computed from Q8_K `bsums`.

**Safety:** `VPMADDUBSW` has *saturating* signed 16-bit results. For the inspected unsigned Q4_K and Q5_K ranges, even a pair of `31 × 128` terms sums to only 7936, so the expected intermediate dot pairs do not saturate. A generic signed-INT8 implementation **cannot** assume this property; preserve operand constraints and create tests for extremes.

## Optimization candidates, ranked

**P0: Determine actual dispatch and baseline.** `Q4_K` may run through repacked 8×8 GEMV rather than `ggml_vec_dot_q4_K_q8_K`. MoE expert matrices can use `GGML_OP_MUL_MAT_ID`, which upstream repack explicitly recognizes. A micro-optimization to a bypassed kernel would have no production effect. Benchmark `--repack` on/off (using the actual version's supported flags) and log the chosen path.

**P1: Q5_K fifth-bit reconstruction.** The AVX2 inner loop repeatedly processes `hmask`, `bit`, shifts, and additions for fifth bits. Since the 256-weight block has a fixed four-iteration loop, compare the generated Zen 1 assembly for regular code against a version with static/unrolled shifts and independent operations. Check whether GCC/Clang already constant-fold and unroll this code before implementing any rewrite.

**P2: Q4_K scale/min preparation and vector dependencies.** The AVX2 loop reconstructs the twelve-byte packed scales/mins into temporary words, prepares Q8_K block sums, and performs repeated scale shuffles. Inspect emitted instructions and look for redundant loads/shuffles; do not assume redundant work without examining disassembly. Compare two independent integer accumulators, with a single final combination, against the existing single `sumi` chain.

**P3: 128-bit vs 256-bit Zen 1 variants.** Benchmark SSSE3/SSE4.x-width vs AVX2-width inner loops where practical. Zen 1 has narrower execution resources for 256-bit operations, but a 128-bit rewrite can double instruction count; choose based on target silicon results rather than intuition.

**P4: Q5_K repacked x86 path.** Upstream source contains Q5_K 8×8 repack interfaces, but the inspected optimal-repack dispatch does **not** select x86 AVX2 for Q5_K. Building a correct efficient Zen 1 repacked Q5_K GEMV implementation could be a bigger project than instruction-level edits. Only tackle it after observing meaningful Q5_K weights in the target GGUF and demonstrating the normal Q5_K implementation is costly.

**P5: Adjacent formats.** A GGUF named `Q4_K_M` can also contain Q6_K and other tensor types. Analyze the actual tensor histogram, especially large routed-expert tensors, before choosing which primitive to optimize.

## Correctness and benchmark gates

1. **Reproducibility:** Record upstream commit SHA, compiler and version, `GGML_*` CMake options, CPU microcode, kernel, NUMA mode, and actual quantization types.
2. **Numeric tests:** Compare every candidate against reference GGML across random inputs, scale extremes, negative/positive activations, zero points, all-zero rows, block boundary cases, and multiple row lengths. Preserve existing quantization accuracy tolerances and verify with `test-backend-ops` (ensure tests actually ran; a zero-case run is not a pass).
3. **Kernel measurement:** Profile `q4_K × q8_K` and `q5_K × q8_K` isolated CPU dot products and repacked GEMV where applicable. Report cycles per 256-weight block, instructions, IPC, and effective data traffic; include hot-cache and working-set-larger-than-LLC cases.
4. **Model measurement:** On target EPYC hardware, compare untouched upstream and patched builds using identical GGUF, prompt, token count, and NUMA policies; report median prompt-processing and decode tokens/sec from repeated warmed runs.
5. **System impact:** Measure LLC/cache misses, remote NUMA access, physical memory bandwidth, CPU frequency, package power, and tokens/joule. Reject a change that wins only in a microbenchmark but regresses whole-model throughput, precision, or energy efficiency.

## Explicit non-goals

- No ROCm dependency or GPU involvement in this CPU-only phase.
- No new quantization file format, weight expansion in RAM, or persistent duplicated weights.
- No handwritten assembly before proving compiler intrinsic code is insufficient.
- No speculative throughput-gain claim before an EPYC 7571 benchmark.
- No assumption that all `master` branches remain unchanged after this audit date.

## Recommended immediate implementation order

**Step 1**: Capture and pin an upstream baseline; confirm `Q4_K/Q5_K` tensor distribution and which plain/repacked path serves `MUL_MAT_ID` on the target 400B MoE.
**Step 2**: Inspect compiler-generated assembly for `ggml_vec_dot_q5_K_q8_K`; implement a tightly isolated prototype of fixed/unrolled fifth-bit extraction if the assembly shows work that can be eliminated.
**Step 3**: Add correctness and kernel-benchmark cases before changing dispatch.
**Step 4**: Benchmark on the dual EPYC server, then decide whether a Q4_K scale-path optimization or a new Q5_K repacked x86 implementation is justified.

**Bottom line:** The central instructions are already in place. Before optimizing integer assembly, establish **which quantized execution path the server actually uses**. That is the most likely way to avoid wasted engineering effort.
