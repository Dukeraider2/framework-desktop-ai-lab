# ComfyUI on Framework Desktop — AMD ROCm

**Observed platform:** Framework Desktop, AMD Ryzen AI Max+ 395 / Radeon 8060S Graphics  
**Observed OS:** Ubuntu 26.04.1 LTS (Resolute)  
**Record date:** 2026-10-29  
**Status:** ComfyUI starts on the AMD HIP backend; model discovery was corrected; private tailnet access and the local model-management utility were configured. A completed image-generation result and post-reboot behavior are not yet recorded.

This is an installation and operations record for the tested machine, not a universal installer or a claim that every ComfyUI workflow/model is compatible with every ROCm release.

## 1. Observed software and hardware

| Item | Observed value |
|---|---|
| GPU | AMD Radeon 8060S Graphics |
| GPU architecture | gfx1151 |
| ComfyUI | 0.43.0 |
| Python reported by ComfyUI | 3.14.4 |
| PyTorch | 2.13.0+rocm10.1.0 |
| ComfyUI-reported ROCm version tuple | (7, 16) |
| Comfy-kitchen | 0.2.40 |
| ComfyUI frontend package | 1.57.4 |
| ComfyUI workflow templates | 0.11.98 |
| Operating system | Ubuntu 26.04.1 LTS |
| ComfyUI local listener | 127.0.0.1:8188 |

ComfyUI startup output identified the device as “AMD Radeon 8060S Graphics : native”, reported architecture gfx1151, and initialized the HIP backend. The startup log reported 62,890 MB total VRAM and 125,781 MB total RAM. These are ComfyUI runtime-reported memory figures on this unified-memory platform; they should not be interpreted as a separate dedicated-VRAM specification.

The startup log also reported OpenGL_accelerate unavailable. ComfyUI nevertheless continued through “Starting server” and advertised its GUI at the loopback URL. Do not install optional acceleration modules just to silence a non-fatal message unless a workflow or measured issue requires them.

## 2. Installation layout

The observed installation uses this layout:

    $HOME/AI/ComfyUI/
    ├── app/
    │   ├── main.py
    │   └── models/
    │       ├── diffusion_models/
    │       ├── text_encoders/
    │       └── vae/
    └── venv/

The Python environment is at $HOME/AI/ComfyUI/venv. The ComfyUI application entry point is at $HOME/AI/ComfyUI/app/main.py.

A working foreground launch command, using the canonical virtual-environment interpreter path, is:

    cd "$HOME/AI/ComfyUI/app" &&
    "$HOME/AI/ComfyUI/venv/bin/python" main.py \
      --listen 127.0.0.1 --port 8188

Keep the terminal open while running this foreground process. The loopback bind is intentional: remote access is provided by Tailscale Serve rather than by exposing ComfyUI on the LAN. The command used during the observed restart invoked the venv as ../venv/bin/python and printed a non-fatal sys.prefix/sys.exec_prefix path warning before starting. Use the canonical absolute interpreter path above on a future restart; removal of that warning with the canonical path has not yet been recorded.

Read-only listener check:

    ss -ltnp | grep ':8188'

The expected listener is 127.0.0.1:8188, not 0.0.0.0:8188.

## 3. Model placement and workflow

The Android ComfyChair client reached the ComfyUI prompt screen through the private endpoint, but its first generation request returned HTTP 400. The desktop ComfyUI workflow panel then showed the required Z-Image workflow models as missing. The downloaded files were in Downloads rather than ComfyUI's model directories.

The two downloaded files were moved into these locations:

| File | Observed size | Destination |
|---|---:|---|
| qwen_3_4b.safetensors | 7.5 GB | app/models/text_encoders/ |
| z_image_turbo_bf16.safetensors | 12 GB | app/models/diffusion_models/ |

The exact directory layout is consistent with ComfyUI's Z-Image and text-encoder documentation. The ComfyUI Z-Image guide also lists ae.safetensors under models/vae. The local sorter has a mapping for that filename, but it was not present in Downloads during the recorded dry run; its installed state was not independently checked as part of this record.

The files were moved, not downloaded a second time. After placement, the user reported that the model list was “good now”. This confirms the missing-model listing was resolved at that checkpoint. It does not by itself confirm that a complete generation finished successfully.

Useful model-directory checks:

    find "$HOME/AI/ComfyUI/app/models" -maxdepth 2 -type f \
      \( -iname '*.safetensors' -o -iname '*.ckpt' -o -iname '*.gguf' \) \
      -printf '%P\n' | sort

    ls -lh \
      "$HOME/AI/ComfyUI/app/models/text_encoders/qwen_3_4b.safetensors" \
      "$HOME/AI/ComfyUI/app/models/diffusion_models/z_image_turbo_bf16.safetensors"

After placing model files, use the ComfyUI model refresh control when available. If a workflow still reports a missing model, inspect the node's expected filename and folder before downloading or renaming anything. Do not assume similarly named model variants are interchangeable.

## 4. Private remote access through Tailscale Serve

ComfyUI listens only on 127.0.0.1:8188. Tailscale Serve provides the HTTPS tailnet entry point and proxies traffic back to that local listener.

The observed configuration command was:

    sudo tailscale serve --bg --https=8444 http://127.0.0.1:8188

The machine required sudo for the Serve configuration because the current Linux user was not yet configured as the Tailscale operator. The command reported an HTTPS endpoint on port 8444 and described it as available within the tailnet. The status output marked the route “tailnet only”.

Use a placeholder in public documentation and local notes:

    https://<device>.<tailnet>.ts.net:8444/

The actual MagicDNS hostname, tailnet name, IP addresses, device names, account identifiers, and screenshots are intentionally not published.

Other Serve routes already existed and were preserved during this change:
- The default HTTPS listener proxied to local port 11435.
- HTTPS port 8443 proxied to local port 11436.
- HTTPS port 8444 now proxies to local port 8188 for ComfyUI.

Do not run tailscale serve reset to troubleshoot ComfyUI; it would remove unrelated Serve routes. To inspect the active routes:

    tailscale serve status

To remove only the ComfyUI route, if required:

    sudo tailscale serve --https=8444 off

Do not enable Funnel for this workload. Keep ComfyUI bound to loopback and keep the Serve endpoint tailnet-only. Tailscale Serve applies the tailnet's access-control policy; tailnet membership and ACL/grant policy still matter.

### ComfyChair client fields

The ComfyChair server editor uses separate fields for name, hostname, port, and authentication. The server's hostname field should contain the tailnet MagicDNS hostname only (no https scheme and no trailing slash); the port is 8444. The actual hostname is private and is not included in this repository. The app returned a ComfyUI HTTP 400 after the route was configured, which showed that requests were reaching the ComfyUI application. A complete generation result remains pending verification.

## 5. Model download sorter

The model sorter is a Bash utility installed as:

    $HOME/bin/comfy-model-sort

It maps exact filenames to their approved model directories, supports a dry-run mode, uses mv -n to avoid overwriting a destination, and leaves unknown safetensors files in Downloads. Current filename mappings:

| Exact filename | Destination |
|---|---|
| qwen_3_4b.safetensors | models/text_encoders/ |
| z_image_turbo_bf16.safetensors | models/diffusion_models/ |
| ae.safetensors | models/vae/ |

The ae.safetensors mapping is included because it is used by the documented Z-Image model layout; the file was absent from Downloads during the original dry run and is not recorded as installed.

Dry run:

    "$HOME/bin/comfy-model-sort" --dry-run

Perform sorting:

    "$HOME/bin/comfy-model-sort"

The sorter is intentionally conservative. New model names must be mapped only after checking their architecture/workflow documentation and the exact destination. It does not infer destinations from fuzzy filename matches.

## 6. Automatic download watcher

The watcher is installed as:

    $HOME/bin/comfy-model-watch

It uses inotifywait to watch the top level of Downloads for close_write and moved_to events. It reacts only to names ending in .safetensors, waits for the file size to remain stable across repeated checks, then invokes the sorter. Unknown files remain untouched.

Ubuntu package installation was performed after checking the candidate in the configured Ubuntu 26.04 repositories:

    sudo apt install inotify-tools

The package install output identified inotify-tools and libinotifytools0 at package version 4.25.9.0-1. The inotifywait --help output reported command version 4.23.9.0 on the tested machine; preserve this distinction rather than assuming these two displayed version strings are identical.

The watcher is managed by a per-user systemd unit:

    $HOME/.config/systemd/user/comfy-model-watch.service

The unit is enabled and active at the last observed checkpoint. It uses the user service manager and default.target. A full reboot test and behavior when the user is logged out have not been recorded. User lingering was not verified in this ComfyUI setup.

Service operations:

    systemctl --user status comfy-model-watch.service --no-pager
    systemctl --user start comfy-model-watch.service
    systemctl --user stop comfy-model-watch.service
    systemctl --user restart comfy-model-watch.service
    systemctl --user enable comfy-model-watch.service
    systemctl --user disable comfy-model-watch.service
    journalctl --user -u comfy-model-watch.service -f

## 7. Desktop GUI: ComfyUI Model Manager

A Python/Tkinter desktop utility was created at:

    $HOME/bin/comfy-model-manager.py

The desktop launcher is installed in the user's application menu and Desktop folder. The application uses the system interpreter at /usr/bin/python3, not the separate shell-selected interpreter at /opt/pyvenv/bin/python3.

The following packages/components were verified on the target machine:
- System Python: 3.14.4.
- Tkinter: 8.6, provided by the matching Ubuntu python3.14-tk package.
- inotifywait: available at /usr/bin/inotifywait.

The GUI was launched successfully after installing the matching Tkinter package. Its observed controls include:
- Watcher state and autostart state.
- Start, stop, restart, enable autostart, disable autostart, and refresh status.
- Manual sorter dry run and actual sorting, with confirmation before moving files.
- Folder shortcuts for Downloads, all model folders, text encoders, diffusion models, and VAE.
- A service-log panel populated from journalctl and refreshed periodically.

The GUI manages the model-watcher service and sorter. It does not manage the ComfyUI server process, Ollama, Tailscale, or Proxmox.

## 8. Installation and deployment notes

The repository includes the sorter, watcher, user service template, and desktop manager source. Before deploying to a different machine:
1. Confirm the ComfyUI root and application directory.
2. Confirm the model folders used by that installation.
3. Review the exact filename mapping before enabling automatic moves.
4. Confirm inotify-tools and the system Python/Tkinter package names for the selected Ubuntu release.
5. Keep the ComfyUI listener loopback-only if using Tailscale Serve as the remote entry point.
6. Replace all local paths with the target user's actual paths.
7. Keep the Serve route tailnet-only; do not use Funnel for this deployment.
8. Test the service controls and a dry run before permitting automatic sorting.

The sample service expects the scripts to be installed under $HOME/bin and the ComfyUI layout under $HOME/AI/ComfyUI/app. These assumptions must be reviewed before use on another layout.

## 9. Verified status and remaining work

| Item | Recorded result |
|---|---|
| ComfyUI startup | Started successfully on 127.0.0.1:8188 |
| AMD GPU backend | HIP detected; Radeon 8060S / gfx1151 selected |
| Model placement | Qwen text encoder and Z-Image Turbo diffusion model moved into correct folders |
| ComfyUI model list | User reported missing-model panel was resolved after placement |
| Tailscale Serve route | Port 8444 configured and reported tailnet-only |
| ComfyChair | Reached ComfyUI; HTTP 400 occurred before models were placed |
| Model sorter | Created, syntax-checked, and dry-run verified |
| Download watcher | Enabled and active under user systemd manager |
| Desktop manager | Launched successfully; displayed active watcher and enabled autostart |
| Full image generation | Not yet recorded as completed |
| Reboot/power-cycle test | Not yet performed |
| ComfyChair final generation test after model placement | Not yet recorded |

## 10. Official references

- [ComfyUI documentation](https://docs.comfy.org/)
- [ComfyUI Z-Image workflow and model placement](https://docs.comfy.org/ja/tutorials/image/z-image/z-image)
- [ComfyUI DualCLIPLoader and text_encoders directory](https://docs.comfy.org/built-in-nodes/DualCLIPLoader)
- [ComfyUI GitHub repository](https://github.com/Comfy-Org/ComfyUI)
- [AMD ROCm documentation](https://rocm.docs.amd.com/)
- [Tailscale Serve overview](https://tailscale.com/docs/features/tailscale-serve)
- [Tailscale Serve CLI reference](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [inotifywait manual](https://www.man7.org/linux/man-pages/man1/inotifywait.1.html)
- [systemd user special targets](https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html)

## OPSEC

This repository is public. Do not add tailnet IP addresses, MagicDNS hostnames, tailnet names, personal usernames, account identifiers, device keys, auth URLs, private screenshots, model weights, or raw unredacted logs. Use placeholders in examples. Keep model files and local logs outside the repository.
