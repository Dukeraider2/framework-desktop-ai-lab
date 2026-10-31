# Resource Efficiency and Hardware-Aware Engineering

**Status:** Mandatory production engineering principle.

## Objective

Maximize useful work while minimizing unnecessary runtime overhead, resource contention, energy use, and operational complexity. Resource efficiency is a first-class requirement, not post-release cleanup.

## Required measurements

Measure relevant dimensions before and after significant changes:
- CPU utilization, execution time, and peak load.
- RAM resident set size and peak memory.
- GPU utilization and GPU memory/VRAM.
- Disk capacity and read/write I/O.
- Network throughput and background traffic.
- Process and thread counts.
- Startup time and initialization cost.
- Idle consumption and background activity.
- End-to-end latency and throughput under representative load.
- Power or energy consumption where reliable measurement is available.

Record workload, host, software versions, measurement method, sample duration, and whether values are measured, estimated, or inferred.

## Baselines and regression control

- Establish a representative baseline before optimization or major changes.
- Compare the new implementation against that baseline.
- Investigate material increases in idle usage, memory, latency, process count, or I/O.
- Set numerical budgets per service and workload after measuring the actual host. Do not invent universal limits.
- Resource regression can block Stage 3 approval when it exceeds the task budget or lacks a justified tradeoff.
- Distinguish interactive workloads from batch workloads and protect system responsiveness.

## Language and implementation choices

- Prefer lean Python for orchestration, automation, API integration, and pipeline glue when it meets performance and reliability requirements.
- Do not rewrite working Python in Rust or another language without a measured, material benefit.
- Consider compiled or lower-level components for demonstrated bottlenecks, not as a default.
- Account for native library overhead, dependency footprint, startup cost, memory use, and maintainability when comparing implementations.
- Avoid unnecessary frameworks, daemons, abstractions, duplicate services, and always-on agents.

## Hardware-aware optimization

Agents are encouraged to investigate supported CPU instruction sets, SIMD/vectorization, optimized numerical libraries, cache-aware data layout, memory locality, parallel processing, GPU acceleration, and other hardware features when there is a measurable efficiency gain.

Requirements:
- Verify instruction and accelerator support on target hardware.
- Detect capabilities at runtime where portability is required.
- Provide a correct fallback for unsupported hardware.
- Benchmark representative workloads.
- Verify numerical correctness, stability, and security.
- Document hardware and software assumptions.
- Do not trade correctness, compatibility, or responsiveness for a narrow benchmark win.

## Scheduling

The resource manager and Hermes scheduler should account for available CPU, RAM, GPU/VRAM, storage, and current workload before dispatching expensive tasks. Avoid GPU overcommitment and uncontrolled parallel inference or generation. Queue or defer work when capacity is insufficient. Stale or missing telemetry must not be interpreted as free capacity.

## Required implementation report

Stage 2 reports baseline and post-change measurements, methodology, workload, resource delta, bottlenecks, and optimization tradeoffs. Stage 3 independently checks the claims and weighs resource efficiency as 20 points of the review score.
