# Compatibility Matrix

**Status: Pending research.** Do not treat version numbers or support claims from prior conversation as confirmed.

| Component | Decision required | Official source | Status |
|---|---|---|---|
| Ubuntu Desktop | Supported release for target APU and AMD stack | Ubuntu releases; AMD Linux docs | Pending |
| Kernel | Supported branch for chosen Ubuntu/ROCm combination | AMD compatibility matrix | Pending |
| AMD graphics stack | Correct Linux package/driver for integrated graphics | AMD Linux docs; Ubuntu/Mesa docs | Pending |
| ROCm/HIP | Explicit support for Ryzen AI Max+ 395 and intended workload | AMD ROCm docs and release notes | Pending |
| Vulkan | Loader, Mesa driver and test tool | Ubuntu, Mesa and Vulkan docs | Pending |
| Python | Version compatible with selected PyTorch build | PyTorch docs | Pending |
| PyTorch | Build matching OS, Python and ROCm | PyTorch official installation docs | Pending |
| Tailscale | Linux install and device recovery process | Tailscale docs | Pending |
| OBS Studio | Trusted installation method for chosen Ubuntu release | OBS official docs | Pending |
| Capture card | Exact model and Linux video/audio interface support | UGREEN product page/manual; V4L2 docs | Pending |

For each decision record date checked, exact version/product, direct source URL, supported/unsupported/unclear status, caveats and required physical test.

A source landing page alone does not prove a specific hardware/software combination is supported. Do not confuse a Windows Adrenalin release with Linux drivers. Vulkan visibility does not prove ROCm support; these are separate paths.