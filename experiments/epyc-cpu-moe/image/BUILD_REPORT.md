# Build status: BLOCKED — no operating-system artifacts produced

Date: 2026-11-14. Branch: codex/epyc-moe-full-os-image.
Starting repository commit: ab25f72f61352492a3a58d766dd2a78d2695b7e9.

## Work completed

Read the authoritative build brief, bootstrap instructions and engineering governance.
Cloned the designated branch in an isolated workspace; no production settings changed.
Verified all nine transport parts against the original Git blobs and required lengths.
Reconstructed 25,016 archive bytes; SHA-256:
`0594d36b92ede2beef8956d973db03398c1337375e21226bb96378ebe1b4d83a`.
Validated archive paths and file types before importing 32 ordinary source files.
`bootstrap/IMPORT_MANIFEST.json` records original import hashes, not post-audit hashes.
Transport files remain until the source audit and import review are complete.

Added a read-only builder preflight and tests. Independent reviewer examined imported
sources and identified the findings below. Removed Quadlet automatic enablement and
added a model-file existence condition; service remains an unvalidated prototype.
No model was downloaded and no provider or credentials were configured.

## Observed blocker and attempted alternatives

Host process is Windows. `wsl --list --quiet` exits 1: WSL is not installed.
Preflight exits 2: mkosi, Podman, qemu-system-x86_64, qemu-img, CMake, Ninja,
C compiler (`cc`) and zstd are absent from this process PATH. Git is present.
No alternate local Linux checkout/builder was identified in the inspected locations.
Initial sandbox Git clone failed DNS; approved network execution succeeded.
GitHub connector and approved GitHub CLI access work, but do not provide a Linux shell.
No host-wide virtualization/software installation was attempted.

Required access: Hermes-approved temporary isolated x86-64 Linux builder account,
with outbound access to approved upstream package/source repositories, writable
build storage and access to QEMU/OVMF. Verify resource capacity and tool versions
before allocating compilation jobs; no measured capacity or universal budget is asserted.
Privileges must be scoped to the isolated builder/image only. No production host
disk, bootloader, kernel, firewall, service or Docker changes are needed.
Alternative: explicitly approve provisioning a dedicated disposable Linux VM.

## Unfinished implementation and audit findings

- No mkosi image pipeline exists yet; Ubuntu 26.04.1 package/snapshot compatibility
  and signed source checks are not established. No fallback release selected.
- Kernel prepare script does not verify that fragment values survive olddefconfig.
- llama.cpp build paths are reused across commits; cached non-CPU backend settings
  need isolation and verification against a pinned upstream revision.
- Container Ubuntu tags and apt repositories are not immutable source locks.
- Quadlet identity mapping, health checks, resource limits and provisioning need Linux tests.
- Synthetic u5×s8 microkernel is not a Q5_K implementation; no GGML performance claims.
- No kernel, llama.cpp binary, root filesystem, raw image, qcow2 or ISO compiled.
- No UEFI boot, Secure Boot, SSH provisioning, rootless container, API inference,
  numerical native-kernel regression, update or rollback validation performed.
- Physical EPYC validation pending hardware availability.

## Reproduce current portable checks

From repository root:

```
python -m unittest discover -s experiments/epyc-cpu-moe/tests -v
python experiments/epyc-cpu-moe/image/preflight.py
```

Observed: 10 tests passed; preflight reports blocked and returns 2.
This is Python orchestration coverage, not compiled numerical or OS validation.
No timing/performance/resource improvement is claimed. Stage timing was not instrumented.
Independent review requested; no merge or release authorized by this report.

Rollback of this work requires reverting branch commits only. Nothing was deployed.
Real image rollback and restore procedures remain unimplemented and untested.
