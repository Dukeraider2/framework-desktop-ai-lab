# GPU Validation Plan

Graphics rendering, Vulkan compute, ROCm/HIP and PyTorch are separate paths. Passing one does not prove the others work.

## A. Inventory
Capture sanitized output from:

```bash
lspci -nnk
uname -r
```

Record the GPU device ID, bound kernel driver and relevant errors.

## B. Vulkan
Use a lightweight, trusted Vulkan demo suitable for the selected Ubuntu release. A rotating cube is a visual smoke test, not a benchmark and not proof that ROCm works.

Record Vulkan device enumeration, selected GPU, render result and driver/loader errors. If practical, test a small Vulkan compute example separately.

## C. ROCm/HIP
Only install after confirming support for the exact APU, Ubuntu release and kernel.
- Run the device discovery utility specified by the matching AMD docs.
- Run a tiny HIP operation.
- Verify allocation and execution occur on the intended GPU.
- Device discovery alone is not proof that every workload is supported.

## D. PyTorch
Install the compatible build using official instructions, then run a small test in a dedicated environment:

```python
import torch

print("PyTorch:", torch.__version__)
print("HIP runtime:", getattr(torch.version, "hip", None))
print("GPU available:", torch.cuda.is_available())

if not torch.cuda.is_available():
    raise SystemExit("GPU backend unavailable; this is not a pass.")

device = torch.device("cuda")
x = torch.arange(16, dtype=torch.float32, device=device)
y = (x * x).sum()
print("Device:", torch.cuda.get_device_name(0))
print("Test result:", y.item())
```

ROCm-enabled PyTorch uses the familiar `torch.cuda` API for compatibility. Confirm the HIP version and device name. If the backend is unavailable, stop and troubleshoot rather than accepting CPU fallback.

All tests remain **Not run** until executed on the target machine.