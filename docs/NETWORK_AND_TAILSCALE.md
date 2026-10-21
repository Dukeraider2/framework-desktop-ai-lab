# Network Drivers and Tailscale Recovery

## Network driver verification
For each wired/wireless adapter, record PCI/USB ID, kernel driver, firmware, link state and the official reference used to assess support.

Read-only commands:

```bash
ip -brief link
lspci -nnk
lsusb
```

For a known Ethernet interface, replace the placeholder with the interface name shown by `ip -brief link`:

```bash
INTERFACE="REPLACE_WITH_INTERFACE_NAME"
sudo ethtool -i "$INTERFACE"
sudo ethtool "$INTERFACE"
```

These commands inspect driver/link information; they do not install or change drivers. A kernel-provided driver is not automatically inferior. Check the exact device ID and supported driver first.

## Tailscale after reinstall
Tailscale identity is not simply tied to the MAC address. It relies on cryptographic node identity/state and tailnet registration, so a clean OS installation may appear as a new machine.

1. Keep any current device name in a private note if needed; do not publish tailnet details.
2. Install Tailscale using official Linux instructions.
3. Authenticate the new installation through the supported flow.
4. Consult official device-management documentation if reusing the existing tailnet entry is important.
5. Do not copy old Tailscale state directories or private machine keys into the fresh install.
6. Test from another authorized device.
7. Remove stale entries only after confirming the new connection works.

Public logs must not contain auth keys, node keys, tokenized login URLs, tailnet IPs or admin screenshots.