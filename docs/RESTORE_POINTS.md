# Restore-Point Strategy

Use a full system/disk imaging tool selected after checking disk layout, encryption, filesystem, boot configuration and recovery requirements. Clonezilla is a candidate, not yet selected.

## Planned checkpoints
- **RP0 — Clean OS:** Ubuntu installed/updated and baseline checks pass; before ROCm.
- **RP1 — Network + Vulkan:** Driver/firmware identified, Tailscale access tested from another device, Vulkan test passes.
- **RP2 — ROCm/HIP:** GPU discovery and tiny compute test pass.
- **RP3 — PyTorch:** Compatible backend and tiny GPU tensor test pass. No model weights included.
- **Optional RP4 — Streaming:** Stable OBS/capture configuration verified.

## External SSD qualification
When physically available:
1. Check model, capacity, interface and health/SMART data where supported.
2. Confirm there is no data to retain before repurposing it.
3. Confirm filesystem and image format compatibility.
4. Ensure enough free space for the image and growth margin.
5. Verify image integrity using the imaging tool's verification feature.
6. Document recovery media and restore steps.

## Rules
- Keep model weights, datasets and caches outside OS images where possible.
- Restoring an image overwrites the selected destination. Identify the target by model/capacity and verify twice.
- Test recovery media before relying on it.
- Keep an independent copy of important documentation.