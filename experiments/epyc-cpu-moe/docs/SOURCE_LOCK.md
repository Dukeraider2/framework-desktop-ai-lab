# Source verification ledger — incomplete, not a release lock

Checked 2026-11-14. Do not build a release from this ledger yet.

| Source | Version / owner | Verification and limits |
| --- | --- | --- |
| Bootstrap archive | v0.1, repository starting commit ab25f72f61352492a3a58d766dd2a78d2695b7e9 | SHA-256 0594d36b92ede2beef8956d973db03398c1337375e21226bb96378ebe1b4d83a verified locally; per-file import ledger provided; licensing must be confirmed before redistribution |
| https://releases.ubuntu.com/26.04.1/ | Canonical, 26.04.1 | Official index inspected; ISO not downloaded, checksum/signature not verified; package snapshot not locked |
| https://github.com/systemd/mkosi | systemd project, no revision selected | Official repository inspected; Linux builder unavailable, Ubuntu compatibility and exact options not validated |

Kernel, llama.cpp/GGML, compiler, Podman/Quadlet, QEMU/OVMF and Ubuntu packages
remain unpinned. Upstream licensing and exact commits/digests are outstanding.
Manufacturer manuals, Zen 1 ISA details and tuning references remain to be verified
before implementation. Imported docs/SOURCES.md is a prototype reference list,
not evidence of independent verification in this session.
