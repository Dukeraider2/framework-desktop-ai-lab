# Kernel optimization track

## Principle: kernel development is part of the stack, but avoid premature replacement

User-space GGML SIMD code often dominates CPU decode time. Kernel scheduling, NUMA placement and page policy can still matter, but a custom kernel has meaningful reliability/security costs. First capture a **stock, patched Ubuntu LTS baseline**. In-place modifications to GRUB, BIOS, mitigations, CPU microcode, network drivers, IOMMU, or security modules are explicitly excluded from this package.

## Read-only inspection

`python3 tools/inventory.py --out results/inventory.json` records scheduler, NUMA, transparent huge page, current governor and kernel data without network addresses or credentials.

## Controlled runtime experiments

`tools/tune.py` proposes a small allowlisted set of runtime settings. Without `--apply --acknowledge` it is **read-only**. On apply it records originals in a local state file and restores through `--restore --acknowledge`. Profiles:

- `configs/tuning/baseline.json`: no changes.
- `configs/tuning/thp-madvise.json`: `transparent_hugepage/enabled=madvise` and `defrag=defer+madvise` (only when the kernel exposes them).
- `configs/tuning/numa-balancing-off.json`: `kernel.numa_balancing=0`. This may help deterministic first-touch placement or hurt if pages are misplaced.

Changing system-wide policies affects *other tasks*, too. Capture baseline, apply only on dedicated test hardware, rerun, and restore. THP on memory-mapped GGUF files is not guaranteed; use `/proc/<pid>/smaps` to confirm page backing.

## Kernel compile experiment

`kernel/prepare-kernel.sh` generates an **out-of-tree build configuration**, using a selected and pinned **local Linux source tree** and an existing host config plus `kernel/zen1-experiment.config`. It does **not compile, install, modify bootloader, reboot, or switch kernels**. Further compile/install/boot steps belong in a separate change request after documented compatibility checks.

Evaluate non-destructive configuration choices such as NUMA support, CPU sets, perf events, THP, HUGETLB and preemption features. Do not disable KASLR, Spectre/Meltdown mitigations, SMEP/SMAP, IOMMU, firewall or secure boot merely to improve benchmark scores. Keep NIC/storage drivers, initramfs and known-good kernel intact; confirm signed module requirements, DKMS drivers, out-of-band console and fallback boot path.

## Later research, not implemented

- cgroup v2 `cpuset.cpus.partition` isolation instead of irreversible `isolcpus=` boot parameters; requires topology-aware housekeeping CPUs.
- IRQ and RCU placement based on measured interrupt sources; never assign CPU IDs until physically inventoried.
- scheduler experiment via `sched_ext` if supported in the installed kernel; reject if no end-to-end win or if it increases tail latency.
- build multiple kernels with source SHA, config diff, toolchain, bootable rollback image and regression suite. Without a measured benefit, keep the distro kernel.

Reference: https://docs.kernel.org/admin-guide/cpu-isolation.html ; https://docs.kernel.org/admin-guide/mm/transhuge.html ; https://ubuntu.com/server/docs/explanation/performance/perf-tune-affinity-numa/ .

## Candidate compile-time throughput profile

The optional `kernel/profiles/throughput-hz100.config` proposes `CONFIG_HZ_100=y` and `CONFIG_PREEMPT_NONE=y`, where those options are meaningful for the pinned kernel. These are **hypotheses, not proven optimizations**. A lower scheduler tick can help overhead but can harm response latency; no-preemption can increase tail latencies and scheduling jitter. The kernel source must resolve the options via Kconfig and the reviewer must check `out/.config`. We **do not** set `isolcpus`, `nohz_full`, `mitigations=off`, or unsafe interrupt routing.

For example, to only prepare the alternate configuration:

```bash
./kernel/prepare-kernel.sh /path/to/linux <exact-kernel-SHA> /boot/config-$(uname -r) /tmp/epyc-kernel-out kernel/profiles/throughput-hz100.config
```

The optional `kernel/build-kernel.sh` can compile **only** the out-of-tree kernel image/modules from the exact prepared source SHA when explicitly run with `--execute`. It never installs or boots them. The exact target should be a patched, maintained kernel branch with reproducible source and boot rollback.

EPYC 7571 may expose **acpi-cpufreq** rather than amd-pstate; check `/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver` rather than forcing unsupported `amd_pstate` boot parameters. See https://docs.kernel.org/admin-guide/pm/amd-pstate.html .
