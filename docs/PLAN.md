# Build Plan

## Phase 0 — Compatibility research (no system changes)
- [ ] Confirm exact APU/GPU details from vendor documentation.
- [ ] Verify supported Ubuntu Desktop release and kernel for the target hardware and chosen AMD stack.
- [ ] Verify explicit ROCm support for this APU and intended workloads.
- [ ] Identify matching AMD Linux graphics, HIP and PyTorch installation guidance.
- [ ] Confirm Vulkan/Mesa requirements.
- [ ] Record exact official URLs, access date, support status and caveats.
- [ ] Freeze the version matrix before reinstalling.

**Gate:** Do not choose an ISO or install commands until compatibility research is recorded.

## Phase 1 — Clean OS baseline
1. Verify the selected ISO checksum.
2. Prepare installation media.
3. Confirm the target disk and that nothing needs to be retained.
4. Install Ubuntu Desktop and apply supported updates.
5. Record OS release, kernel, firmware, storage and hardware inventory.
6. Verify reboot and basic stability.
7. Create RP0.

## Phase 2 — Network and Tailscale
1. Identify each interface, PCI/USB ID, driver, firmware and link state.
2. Compare the actual driver against official documentation.
3. Install Tailscale from its official Linux instructions.
4. Authenticate through the supported flow; do not copy old Tailscale state or private keys.
5. Test from another authorized device.
6. Remove stale tailnet entries only after the new connection is confirmed.
7. Create RP1 after network and Vulkan validation.

## Phase 3 — Vulkan
1. Enumerate Vulkan devices.
2. Run a small trusted Vulkan rendering demo; a rotating cube is a smoke test, not an AI compute benchmark.
3. If practical, run a separate lightweight Vulkan compute test.
4. Record the selected device, result and errors.

## Phase 4 — ROCm/HIP
1. Install only the packages listed for the verified OS/kernel/ROCm combination.
2. Record package versions and source.
3. Run the matching device discovery tool.
4. Run a tiny HIP operation and verify it executes on the intended GPU, not CPU fallback.
5. Create RP2 after success.

## Phase 5 — PyTorch and inference
1. Create a dedicated Python virtual environment.
2. Install the PyTorch build matched to the selected ROCm release.
3. Run a small tensor test and confirm backend/device.
4. Download one lightweight model only after the stack passes.
5. Keep weights and caches outside system images.
6. Record inference latency, throughput if available, memory and fallback behavior.
7. Create RP3.

## Phase 6 — Streaming
1. Identify the exact UGREEN model and USB IDs.
2. Check V4L2 video and audio enumeration.
3. Install OBS from an official/trusted source.
4. Test passthrough, capture, audio sync and local recording at 1080p60.
5. Run a sustained local test before going live.
6. Record dropped frames, load and temperature.

## Phase 7 — Open-source and Rust tools
Evaluate applications one by one for functionality, license, maintenance, security, resource use and compatibility. Avoid replacing stable tools solely because an alternative is written in Rust.

For every change, document objective, rationale, prerequisites, commands, expected result, actual result, troubleshooting and rollback.