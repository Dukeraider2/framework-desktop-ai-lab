# Baseline Inventory and Requirements

## Hardware to inventory
- Framework Desktop and AMD Ryzen AI Max+ 395
- GPU/APU details and device IDs
- RAM capacity and firmware/BIOS version
- Storage devices and filesystems
- Wired/wireless network controllers
- USB devices, including the UGREEN capture card
- External SSDs intended for system images

Do not publish serial numbers, MAC addresses, unique IDs, private IP addresses, personal hostnames or unredacted hardware dumps.

## Baseline software categories
Exact package names must be checked for the chosen Ubuntu release:
- Ubuntu updates and security fixes
- Firmware update tooling, where supported
- Git and basic CLI diagnostics
- Network diagnostics
- Vulkan loader/driver and lightweight test utility
- Tailscale from official Linux instructions
- Selected system imaging/recovery tool
- ROCm/HIP from the validated compatibility matrix
- Python virtual environment tooling
- Compatible PyTorch build
- OBS Studio and V4L2 tools
- Rust toolchain when a concrete tool or utility is selected

Avoid overlapping GPU stacks and unreviewed installation scripts. Do not run opaque privileged download-and-execute commands without reviewing the source and script.

## Read-only initial inventory commands
These inspect the current install; they do not prove the configuration is correct.

```bash
printf '%s\n' '=== OS ==='
cat /etc/os-release
printf '%s\n' '=== Kernel ==='
uname -r
printf '%s\n' '=== PCI devices ==='
lspci -nnk
printf '%s\n' '=== USB devices ==='
lsusb
printf '%s\n' '=== Block devices ==='
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
printf '%s\n' '=== Network interfaces ==='
ip -brief link
printf '%s\n' '=== Firmware tooling ==='
if command -v fwupdmgr >/dev/null 2>&1; then fwupdmgr get-devices; else echo 'fwupdmgr not installed'; fi
```

Sanitize output before publication: remove serials, MACs, hostnames, private addresses and identifying details.