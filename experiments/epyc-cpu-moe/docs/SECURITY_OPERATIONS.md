# Security, continuity, and operations

- Production boundary: inference container only publishes `127.0.0.1:8088` on host. No public LAN listener. For Hermes or remote clients, use an independently reviewed Tailscale Serve or authenticated gateway and keep access/authorization explicit.
- Rootless Podman is mandatory. The Quadlet is disabled until user setup and approval. No `--privileged`, host network, extra capabilities, Docker or ROCm mount.
- Model directory is read-only in container. Do not mount host home directories or source repositories writable. Hash GGUF before use. Keep secrets outside config and repo.
- Kernel tuning profiles mutate only named sysctl/sysfs endpoints with backup and restoration, and require positive acknowledgement plus root. No bootloader changes. On crash during an applied profile, restore manually from the state file.
- Containers have resource impact: a 400B model can use hundreds of GiB RAM plus KV cache and working buffers. Monitor kernel OOM and reserve RAM for OS; never globally pin or lock all RAM without a budget.
- Keep package updates, CPU microcode, BIOS, firmware and ECC monitoring in the operational checklist. Security mitigations stay enabled by default.
- Recoverability: known-good distro kernel, initramfs, boot-order/console access and configuration backup must be verified before any custom-kernel install.
- Logs and metrics can contain prompts and addresses: redact before sharing to GitHub. No auth tokens or private network identifiers.
