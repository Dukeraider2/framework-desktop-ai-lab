# Development status: v0.1.0, 2026-11-14

## Implemented artifacts

- Architecture and governance specification, CPU-only model serving plan, read-only topology inventory.
- Upstream llama.cpp source build templates for generic and Zen 1 AVX2, repack ON/OFF, exact SHA guard.
- Experimental kernel configuration preparation and opt-in compile-only scripts and two kernel fragments (no install/boot automation), plus reversible runtime sysctl/sysfs tuning script.
- CPU-only rootless Podman image recipe and opt-in local-only systemd Quadlet with metrics and read-only model volume.
- Offline synthetic u5×s8 scalar vs AVX2 integer dot-product test with packed synthetic Q5 unpacking (not actual GGML format).
- GGUF v3 metadata-only tensor histogram, benchmark dry-run wrapper, localhost health check, source audit and acceptance gates.

## Observed development-host checks

- `python3 -m unittest discover -s tests -v`: **7 passed**.
- `make -C microkernels check`: **200 synthetic comparisons passed** on the available AVX2-capable development host; this is **not an EPYC 7571 benchmark**.
- `bash -n kernel/prepare-kernel.sh tools/inspect-assembly.sh`: passed.
- `python3 -m py_compile tools/*.py`: passed.
- `python3 tools/tune.py --profile baseline`: dry-run, no host changes.

## Not yet accomplished

- No model checkpoint selected, downloaded, loaded, or benchmarked. No verified GGUF quantization mix.
- No GGML source compiled or modified; upstream audit lacks commit SHA; no `test-backend-ops` run.
- No kernel source prepared/compiled/installed/booted or benchmarked; no server-specific kernel gain established.
- No Podman image built or Quadlet activated, no server endpoint running.
- No hardware installation or resource measurement on dual EPYC 7571; no claim of practical tokens/sec.
- No GitHub commit/branch/PR created. This package can be reviewed and imported into the lab repository later.
