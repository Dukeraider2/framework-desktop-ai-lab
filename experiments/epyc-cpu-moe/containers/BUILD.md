# Manual deployment gate (later; not run here)

1. Obtain and verify the exact upstream llama.cpp commit SHA. Verify licenses and dependencies.
2. On a build host matching Zen 1, review `containers/Containerfile` and build manually using **rootless Podman**:
   `podman build --build-arg LLAMA_COMMIT=<40-character-SHA> -f containers/Containerfile -t localhost/epyc-moe:dev .`
3. **Important:** This recipe assumes the pinned version builds its `llama-server` executable without dynamic GGML libraries when `BUILD_SHARED_LIBS=OFF`; verify with `ldd` before deployment. Do not claim it is proven.
4. Edit `quadlet/epyc-moe.container` to select the approved model filename, CPU threads, context size and actual NUMA mode; review access controls. The image tag is local and mutable; pin its digest for deployment.
5. Create `~/epyc-moe-models` and place a verified GGUF there. Quadlet mounts this directory read-only. Build host should not be the EPYC server unless desired.
6. Copy Quadlet to `~/.config/containers/systemd/`, run `systemctl --user daemon-reload`, then `systemctl --user start epyc-moe.service`. Test local-only `/health` and authorized OpenAI-compatible requests. To stop: `systemctl --user stop epyc-moe.service`. Keep the machine's network firewall and existing proxy rules untouched until reviewed.
7. Confirm `systemctl --user status epyc-moe.service`, and that only `127.0.0.1:8088` is exposed. Avoid using `systemctl enable` on generated Quadlet services; they use the Quadlet `[Install]` section.

**No Docker. No GPU devices. No privileged container. No automatic remote listening.**
