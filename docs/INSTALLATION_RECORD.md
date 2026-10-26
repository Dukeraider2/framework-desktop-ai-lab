# Installation Record: Framework Desktop AI Lab

**Record date:** 2026-10-25  
**Target:** Framework Desktop, AMD Ryzen AI Max+ 395 / Radeon 8060S-class integrated GPU  
**OS observed:** Ubuntu 26.04.1 LTS (Resolute)  
**Purpose:** Record the steps and checks that were actually observed. This is not a clean-room installer. Where the exact original command was not retained, that is stated explicitly instead of reconstructing it from memory.

## 1. OS and baseline

Ubuntu 26.04.1 LTS was reported by `/etc/os-release`. The system package index was refreshed and an initial inventory was saved locally.

Commands observed in the setup workflow:

```bash
sudo apt update
mkdir -p ~/framework-backup
lspci -nnk | grep -A 4 -Ei 'VGA|Display|3D'
cat /etc/os-release | grep -E 'PRETTY_NAME|VERSION_ID'
uname -r
```

The full inventory was kept locally. Do not publish raw inventory output without removing serial numbers, MAC addresses, private addresses, hostnames, and other identifying values.

Official references:
- [Ubuntu releases](https://releases.ubuntu.com/)
- [Ubuntu documentation](https://help.ubuntu.com/)

## 2. Encrypted secondary backup SSD

A secondary 512 GB SSD was configured with LUKS encryption and an ext4 filesystem, then mounted as a backup destination. A root-only recovery manifest was saved locally. A system archive set was created; SHA-256 checksums were verified.

Observed outcome:
- Backup directory was created on the encrypted volume.
- Root filesystem, boot, and EFI archives plus system/storage/package metadata were included.
- Archive checksums verified successfully.
- Some extended-attribute warnings on snap squashfs paths and one socket skipped during tar were reported; archive verification completed.
- A full bare-metal restore has **not** been tested.

**The exact disk-formatting, LUKS, filesystem, mount, and archive commands from the original session were not retained in the available record. They are intentionally not recreated here.** Do not use generic disk commands on a live system without confirming the target device by model and capacity and reviewing every destructive operation.

Security: never commit the recovery manifest, passphrase, archive files, device serials, or raw storage output.

## 3. Vulkan / Mesa

Vulkan tools were installed and device enumeration was checked with:

```bash
vulkaninfo --summary
```

Observed result: the Radeon 8060S-class GPU appeared through Mesa RADV (reported version 26.0.8). This verifies device enumeration only; it is not a benchmark and does not prove ROCm works.

References:
- [Vulkan](https://vulkan.org/)
- [Mesa documentation](https://docs.mesa3d.org/)

The exact package-install command was not retained in the available record.

## 4. AMD ROCm and HIP

ROCm 10.1.0-3 was installed using AMD's official package repository. The target GPU was identified as `gfx1151`. `rocminfo` discovered the Radeon GPU and the Ryzen AI NPU.

A small HIP smoke test was compiled and executed using:

```bash
/opt/rocm/core-10.1/bin/hipcc --offload-arch=gfx1151 /tmp/hip-smoke.cpp -o /tmp/hip-smoke && /tmp/hip-smoke
```

Observed result: one HIP GPU was reported and the test returned the expected square values `0 1 4 9`.

The original repository-addition and package-install command sequence was not retained in the available record. For reproducible installation, follow the current [official AMD ROCm documentation](https://rocm.docs.amd.com/) and matching [ROCm release notes](https://rocm.docs.amd.com/en/latest/release/release.html) for the exact OS, kernel, and hardware. Do not substitute a remembered command from another ROCm release.

## 5. Tailscale and SSH

Tailscale was installed from its official Linux package repository; version 1.104.2 was observed. The host was registered in the tailnet and the Android phone was shown as another tailnet device. Device names, tailnet IPs, and MagicDNS hostnames are intentionally omitted from this public record.

OpenSSH server was installed and socket activation enabled with:

```bash
sudo systemctl enable --now ssh.socket
```

The service was enabled, but end-to-end SSH access from another tailnet device was not yet confirmed; an earlier attempt timed out before authentication.

Tailscale Serve was configured to proxy the local Ollama service:

```bash
sudo tailscale serve --bg 11434
```

The command reported an HTTPS endpoint forwarding to `http://127.0.0.1:11434`. The actual endpoint is deliberately not published. Keep this service tailnet-only; do not expose Ollama's API port to the public internet.

Current unresolved issue: an Android Ollama client returns HTTP 403 through the HTTPS endpoint. The responding layer has not yet been isolated. Do not change provider settings or authentication values without first comparing local API responses with responses through Tailscale Serve.

Official references:
- [Tailscale installation for Linux](https://tailscale.com/kb/1031/install-linux/)
- [Tailscale Serve](https://tailscale.com/kb/1312/serve/)
- [OpenSSH documentation](https://www.openssh.com/manual.html)

## 6. Ollama and local model

Ollama was installed using its official installer. The installer reported AMD GPU readiness. The model was downloaded and launched with:

```bash
ollama run qwen3:8b
```

GPU placement was checked with:

```bash
ollama ps
```

Observed result: `qwen3:8b` appeared with 100% GPU placement and a reported context length of 40960 at the time of inspection. This confirms a working inference smoke test, not sustained performance or a benchmark.

Ollama's local API is normally available at `http://localhost:11434/api`; its OpenAI-compatible endpoints use `http://localhost:11434/v1/`. Refer to the current official documentation:
- [Ollama Linux installation](https://ollama.com/download/linux)
- [Ollama API introduction](https://github.com/ollama/ollama/blob/main/docs/api/introduction.mdx)
- [Ollama OpenAI compatibility](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx)

The exact original installer invocation was not retained in the available record, so it is not reproduced here.

## 7. Current validation summary

| Component | Observed status | What the result proves |
|---|---|---|
| Ubuntu | Installed; release identified | OS release was reported by the target |
| Encrypted backup | Archive checksums verified | Archive integrity check passed; restore not tested |
| Vulkan | Device enumerated | GPU visible to Vulkan/RADV |
| ROCm/HIP | Smoke test passed | HIP GPU discovery and a small kernel execution worked |
| Ollama | Model inference started; 100% GPU placement reported | A small local inference path worked at the time of test |
| SSH | Socket enabled | Service activation enabled; remote login still unconfirmed |
| Tailscale Serve | Proxy command accepted | HTTPS proxy configured; client access not yet verified end-to-end |
| Android Ollama client | HTTP 403 | Unresolved; cause not yet identified |
| PyTorch | Not recorded as installed/validated | No pass claimed |
| OBS/capture device | Not validated | No pass claimed |

## OPSEC before publishing further logs

- Do not publish tailnet IPs, MagicDNS hostnames, auth URLs, keys, tokens, SSH fingerprints, MAC addresses, serial numbers, or private screenshots.
- Never commit the LUKS recovery manifest, passphrase, encrypted backup archives, or model weights.
- Treat the exact historical Git repository and local filesystem as separate surfaces; a current-file scrub alone does not prove Git history is free of secrets.
- Keep diagnostics local and share only the minimum sanitized output needed to support a conclusion.
