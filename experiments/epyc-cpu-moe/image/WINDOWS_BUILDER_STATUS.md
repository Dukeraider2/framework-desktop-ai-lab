# Windows Podman builder provisioning

2026-11-14: owner selected Linux VM with Podman for the isolated builder.

Installed RedHat.Podman 5.8.10 using the WinGet source, exact version, hash
verification enabled, silent mode, no automatic reboot and dependencies skipped.
Observed `podman --version`: `podman version 5.8.10`.
Observed `podman machine list`: empty; no pre-existing VM was changed.

Official installer SHA-256 reported by WinGet:
`1d4ad41b58f8881c30272cd70e1c05570f272ef74338848c1b776c668c427e7a`.

WSL is absent. Attempted Microsoft.WSL 3.0.5 installation through WinGet;
installer hash verified, installation rejected with 0x80073d28 (administrator
privileges required). Requested Windows elevation with Start-Process -Verb RunAs.
At last observation that process remained pending and WSL was still unavailable.
No Windows restart was requested or performed. Linux VM not created yet.

Microsoft.WSL package SHA-256 reported by WinGet:
`98cb1219de93ceb8ec59ee136f7019f6f2078f23d61d04540e6db546a52b93a5`.

Next gate: complete administrator-approved WSL installation, check required Windows
virtualization features and reboot requirement, and obtain owner authorization
before any reboot. Then create a named dedicated Podman machine after verifying
resource limits and restricting shared host directories. Do not rely on default
machine mounts: installed help lists the user profile and C drive as defaults.
Rootless Podman is required. No inference/build validation has occurred.

References checked for applicable Windows setup:

- https://github.com/podman-container-tools/podman/blob/v5.8.10/docs/tutorials/podman-for-windows.md
- https://docs.podman.io/en/latest/markdown/podman-machine-init.1.html
- https://learn.microsoft.com/en-us/windows/wsl/basic-commands

Installed `podman machine init --help` was inspected. Windows guide warns that
automatic WSL setup can restart Windows; do not accept that automatic path while
the owner's explicit no-reboot-without-approval rule applies.
