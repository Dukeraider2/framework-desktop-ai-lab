# Strix Halo llama.cpp ROCm Toolbox

## Deployment status

Verified on the Framework Desktop with Ryzen AI Max+ 395 / Radeon 8060S (`gfx1151`), Ubuntu 26.04.1, kernel `7.0.0-38-generic`, rootless Podman 5.7.0 and ROCm 10.1 host tools. The container uses the upstream stable `rocm-10.0` toolbox; host ROCm, Python, PyTorch, ComfyUI and Ollama were left intact.

The toolbox provides an independent llama.cpp runtime. It is managed by a rootless user Quadlet and runs as `llama-cpp-rocm.service`. The API is published on host loopback `127.0.0.1:18080`. Through the existing loopback NGINX gateway, use `http://127.0.0.1:11435/llama/v1` as an OpenAI-compatible base URL. Existing Ollama requests at `http://127.0.0.1:11435/` continue to use Ollama.

## Upstream image and host compatibility

Use the upstream stable [`rocm-10.0` toolbox](https://github.com/kyuz0/amd-strix-halo-toolboxes), built for ROCm HIP and `gfx1151`. The upstream [`Dockerfile.rocm-10.0`](https://github.com/kyuz0/amd-strix-halo-toolboxes/blob/main/toolboxes/Dockerfile.rocm-10.0) enables `GGML_HIP=ON`, targets `gfx1151`, and includes RPC support. The alternative stable [`vulkan-radv` Dockerfile](https://github.com/kyuz0/amd-strix-halo-toolboxes/blob/main/toolboxes/Dockerfile.vulkan-radv) uses Mesa RADV and `GGML_VULKAN=ON`; keep this as a compatibility comparison, not the first deployment. Do not use upstream experimental tags for this baseline.

The upstream repository has no GitHub release tags; its image tags are rolling builds of llama.cpp master. This deployment pins the pulled image by digest:

```text
docker.io/kyuz0/amd-strix-halo-toolboxes@sha256:5893ef15c436f15bee2378c2b5ecfdf0f6c2c45a07f401a5dd2e3ce4a38edcf4
```

The image reported llama.cpp `0.7.0-dev` (build 11870, commit `74bca3950`). The [upstream AGENTS.md](https://github.com/kyuz0/amd-strix-halo-toolboxes/blob/main/AGENTS.md) calls for `/dev/kfd`, `/dev/dri`, a kernel newer than 6.18.4, and flags a known issue in linux-firmware `20251125`. This host has kernel 7.0.0-38 and firmware package `20260319.git217ca6e4.1ubuntu`; both GPU nodes are accessible to the user. `amd-smi` and `rocminfo` identify the Radeon 8060S / `gfx1151`.

The current host boot parameters contain no `amdgpu.gttsize` or `ttm.pages_limit` overrides. The GPU reports a 512 MB dedicated VRAM carveout and about 62,890 MB GTT. No boot or firmware settings were changed. The upstream host guide proposes `amdgpu.gttsize=126976 ttm.pages_limit=32505856`, expected to raise usable GTT toward 124 GB and permit larger allocations. These require a bootloader update and reboot and remain an optional future change. The guide also proposes `amd_iommu=off`; this deployment does not recommend applying it because it disables IOMMU protections and NPU access.

## Cockpit and Podman

The upstream [AI Toolbox Cockpit](https://github.com/kyuz0/ai-toolbox-cockpit) was installed in a user-local Python virtual environment from inspected upstream revision `59a6068551baf88a9bc6a7059cd5dacbd9fbb53a` (version `2026.11.2.1615`). Launch it with:

```bash
ai-toolbox-cockpit
```

Its server mode has a Podman backend; the inspected runner builds native `podman run` commands and passes GPU devices, keep-groups and loopback publication flags. No Docker package or Docker service was installed. This deployment uses the checked-in Quadlet below as its persistent source of truth; do not create a second Cockpit-managed container with the same model/API port.

## Files, model and container settings

- Repository Quadlet template: `deploy/strix-halo-llama/llama-cpp-rocm.container`
- Installed Quadlet: `${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd/llama-cpp-rocm.container`
- Model directory: `${XDG_DATA_HOME:-$HOME/.local/share}/llama.cpp/models`
- Model used for the smoke test: `Qwen3-0.6B-Q8_0.gguf`, 639,446,688 bytes, SHA-256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`
- Model source: [Qwen/Qwen3-0.6B-GGUF](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF), Apache-2.0

The smoke-test model was downloaded because no local GGUF was present. Do not fetch larger models without checking first. The host directory is mounted read-only at `/models`; cache writes go to `/tmp` in the container.

The container maps only `/dev/kfd` and `/dev/dri`, with `GroupAdd=keep-groups`, `UserNS=keep-id`, seccomp unconfined for the ROCm userspace, and SELinux label separation disabled for device access. It is not privileged and does not use host networking. The container listens on `0.0.0.0:8080` internally, but Podman publishes it only as host `127.0.0.1:18080`.

## Operations

Start, stop, restart, inspect and follow logs:

```bash
systemctl --user start llama-cpp-rocm.service
systemctl --user stop llama-cpp-rocm.service
systemctl --user restart llama-cpp-rocm.service
systemctl --user status llama-cpp-rocm.service
podman logs -f llama-cpp-rocm
```

The Quadlet declares `WantedBy=default.target`. Verify its generated startup link and status with:

```bash
systemctl --user is-enabled llama-cpp-rocm.service
systemctl --user list-dependencies default.target --plain
```

For a generated Quadlet, `is-enabled` reports `generated`; the generator creates `default.target.wants/llama-cpp-rocm.service`. This was verified on 2026-11-03. `loginctl show-user "$USER" -p Linger` reported `Linger=yes`; this setting was not changed. Restart recovery was verified without reboot: the unit became active and `/health` returned `{"status":"ok"}`.

The running image is pinned by digest. To update, inspect the upstream stable image and its Dockerfile, pull the chosen image, replace the digest in the Quadlet template and installed Quadlet, then recreate the service:

```bash
podman pull docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-10.0
podman image inspect --format '{{.RepoDigests}} {{.Id}}' docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-10.0
# Update the pinned digest in the template and installed user Quadlet after review.
systemctl --user daemon-reload
systemctl --user restart llama-cpp-rocm.service
curl -fsS http://127.0.0.1:18080/health
```

Do not rely on the rolling tag alone for reproducibility; record the selected digest and llama.cpp version in this document after an update.

## NGINX gateway route

The NGINX user Quadlet's pasta network now forwards host loopback port 18080 into its own network namespace. The added `/llama/` location strips that path prefix and forwards to llama.cpp. Example endpoints:

```text
Direct:   http://127.0.0.1:18080/v1/models
Gateway:  http://127.0.0.1:11435/llama/v1/models
OpenAI base URL through gateway: http://127.0.0.1:11435/llama/v1
```

The NGINX `/` location is unchanged and still forwards to Ollama on port 11434. The ComfyUI listener on 11436 is unchanged. Before editing either live NGINX file, make timestamped backups. Validate with `podman exec llm-proxy nginx -t`; the pasta host-port mapping takes effect when `llm-proxy.service` is restarted.

## Validation and benchmark

Run the repeatable benchmark with Python's standard library; it requires the API and `amd-smi` to be available:

```bash
python3 scripts/benchmark-strix-halo-llama.py
```

Defaults are one 64-token warm-up, three measured 256-token generations, a fixed 972-token prompt (12 repetitions), and one-second requested `amd-smi` sampling. The output JSON contains each run's prompt/generation tokens, latency and throughput, client-observed total latency, timestamped GPU activity and GTT/VRAM readings, plus summary statistics. Results are written under `results/strix-halo-llama/` with a UTC timestamped filename. Options include `--warmups`, `--runs`, `--tokens`, `--prompt-repeats`, `--sample-interval`, `--url`, `--model` and `--output-dir`.

Verified on 2026-11-03 local time (JSON timestamp is UTC):

- Rootless Podman successfully enumerated `ROCm0: AMD Radeon 8060S Graphics (62890 MiB, 61929 MiB free)` using `/dev/kfd` and `/dev/dri`.
- `/health` and `/v1/models` returned HTTP 200 from the direct endpoint.
- A direct 512-token completion returned HTTP 200. llama.cpp reported 28 prompt tokens at 2,749.1 tokens/s and 512 generated tokens at 199.8 tokens/s (2.558 s generation time).
- During GPU sampling across the completion, `amd-smi` reported gfx activity peaking at 88%; aggregate GTT use was 3,915 MB compared with the pre-run 2,650 MB baseline. `amd-smi process` attributed 1,315,352,576 bytes of GPU memory to `llama-server`. Dedicated VRAM stayed at its 481 MB baseline against a 512 MB carveout; Strix Halo uses shared GTT for larger GPU allocations.
- A completion through NGINX `/llama/completion` returned HTTP 200 at 204.9 tokens/s.
- An OpenAI-compatible `/llama/v1/chat/completions` request returned HTTP 200 and `gateway works.` at about 189 tokens/s with Qwen3 thinking disabled in the prompt.
- NGINX `nginx -t` passed before and after the proxy restart. Ollama `/api/tags` returned HTTP 200 before and after, with the same five model names.
- Existing ComfyUI `/system_stats` returned HTTP 200 both directly on 8188 and through the existing NGINX route on 11436 after restart.
- Both `llama-cpp-rocm.service` and `llm-proxy.service` are active. The llama.cpp host listener is bound only to `127.0.0.1:18080`.
- Repeatable 0.6B benchmark JSON: `results/strix-halo-llama/strix-halo-llama-benchmark-20261104T050314.098400Z.json`. It used 1 warm-up and 3 measured runs, each with 972 prompt tokens and 256 generated tokens. Mean prompt processing was 81.5 ms / 11,928.5 tokens/s; mean generation was 1,388.6 ms / 183.6 tokens/s; client total latency averaged 1,474.4 ms. Across four timestamped GPU samples, gfx activity peaked at 94%, aggregate GTT use at 3,915 MB, and dedicated VRAM use at 482 MB. The observed AMD-SMI sample spacing was about 1.22 seconds despite a 1.0-second requested interval.

### Existing larger Ollama models

`ollama list` reported `qwen3-coder:30b` (30.5B Q4_K_M, 18.6 GB), `mannix/deepseek-coder-v2-lite-instruct:latest` (15.7B Q4_0, 8.9 GB), and `qwen3:8b` (8.2B Q4_K_M, 5.2 GB). The only GGUF in the llama.cpp model directory is the 0.6B smoke-test file. Host `MemAvailable` was about 108 GB and the GPU reported about 58.9 GB free GTT at inventory time, so the Qwen3-Coder 30B artifact size is a plausible fit at the current 4K context configuration. This is a capacity estimate, not a llama.cpp compatibility or performance result. The larger Ollama models were left unbenchmarked; their service-owned model blobs were not copied or permissions changed.

This is a small 0.6B smoke test, not a representative performance result for larger models. Numbers depend on prompt length, clocks, sampling interval and concurrent activity. This is a ROCm baseline; Vulkan RADV has not been benchmarked.

## Known limitations

- Upstream tags track rolling builds; pin and record image digests.
- The smoke test uses a very small model. No local GGUF models existed at setup time.
- Prompt processing numbers from this short prompt are not comparable with long-context workloads.
- Dedicated VRAM is only 512 MB. The current firmware/boot configuration exposes about 62.9 GB GTT; changing GTT/TTM boot settings requires a separate reviewed change and reboot.
- API key is unset and llama.cpp logs that CORS allows all origins. The service is loopback-bound and the existing gateway is also loopback-published; any broader tailnet exposure remains governed by the existing Tailscale Serve and tailnet policy.
- Host-level GPU and API checks passed. A real reboot test and remote tailnet/Android access test have not been performed.

## References

- [AMD Strix Halo Toolboxes README and tags](https://github.com/kyuz0/amd-strix-halo-toolboxes)
- [ROCm 10.0 toolbox Dockerfile](https://github.com/kyuz0/amd-strix-halo-toolboxes/blob/main/toolboxes/Dockerfile.rocm-10.0)
- [Vulkan RADV toolbox Dockerfile](https://github.com/kyuz0/amd-strix-halo-toolboxes/blob/main/toolboxes/Dockerfile.vulkan-radv)
- [Toolboxes host setup guide](https://strix-halo-toolboxes.com/)
- [AI Toolbox Cockpit](https://github.com/kyuz0/ai-toolbox-cockpit)
- [Qwen3 0.6B GGUF model](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF)
