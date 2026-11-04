# LLM Proxy: Design and Operations

> **Status: Local routes verified.** The rootless NGINX proxy is running as a Quadlet-generated user service. Ollama remains at `/`; the separate llama.cpp ROCm backend is available at `/llama/`. Both NGINX configuration syntax and local inference routes pass. Boot behavior after a real reboot, desktop shortcuts, and Android/Tailscale end-to-end access remain unverified.

## Scope

This document covers the rootless reverse proxy in front of Ollama and the optional llama.cpp backend. llama.cpp runtime details, image pin, GPU mappings and benchmark are in [STRIX_HALO_LLAMACPP.md](STRIX_HALO_LLAMACPP.md). MCP and Hermes integrations are out of scope.

The proxy rewrites the upstream HTTP `Host` header. During diagnosis, Ollama returned `403 Forbidden` for requests forwarded with the tailnet HTTPS hostname, but returned `200 OK` when the upstream request used `Host: localhost:11434`. The persistent proxy is now the Tailscale Serve backend, and same-host HTTPS `/api/tags` was verified to return `200 OK` without a manual Host override. Android client access and reboot startup still need verification.

## Agreed design

- **Runtime:** Podman container.
- **Privilege model:** Prefer rootless Podman, managed by a user-level systemd/Quadlet service. Confirm on the target Ubuntu system before installation.
- **Boot startup:** User lingering is enabled and the service is wired under the user `default.target`; verify it after a real reboot before claiming boot startup is confirmed.
- **Desktop controls:** Start, Stop, and Status shortcuts for this service only. The files exist and scripts pass shell syntax checks. Status displayed the service correctly; Stop and Start were both verified by double-clicking their desktop icons, and the service state changed as expected.
- **Proxy configuration:** A standalone editable NGINX configuration file, mounted read-only into the container.
- **Request paths:** No application-code allowlist. NGINX configuration controls routing; `/` continues to forward to Ollama at `localhost:11434`, and `/llama/` forwards to the separate llama.cpp API at `localhost:18080` with the prefix stripped. Do not introduce path restrictions unless intentionally configured and tested.
- **Network exposure:** NGINX is published only on host loopback `127.0.0.1:11435`. Tailscale Serve forwards the existing tailnet-only HTTPS route to that port. Do not enable Funnel. Keep Ollama's existing loopback binding unchanged.
- **Lifecycle separation:** Starting or stopping the proxy must not start or stop Ollama.
- **Recovery:** Preserve the previous Serve configuration and proxy config backup before cutover or edits.

### Access-control implication

Transparent forwarding is not endpoint access control. Every API path reachable through the proxy can be forwarded unless the NGINX configuration explicitly says otherwise. Access to the service is therefore governed in part by Tailscale's tailnet access policy. The policy observed during diagnosis allowed all tailnet connections; do not describe this as a device-specific allowlist. If narrower access is needed, review tailnet policy separately rather than assuming the proxy restricts callers.

## Implemented file and service names

These are the deployed names and paths.

- Host-side proxy config: `${XDG_CONFIG_HOME:-$HOME/.config}/llm-proxy/default.conf`
- Rootless Quadlet: `${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd/llm-proxy.container`
- Generated user service: `llm-proxy.service`
- Container name: `llm-proxy`
- Loopback-only proxy listener: `127.0.0.1:11435`

### Rootless Podman network path

Use rootless Podman with its own `pasta` network namespace, **not** `--network=host`. Host networking would give the container direct access to the host's localhost TCP/UDP services and abstract Unix sockets, weakening the isolation goal.

A temporary rootless container was tested with this command against a temporary Python HTTP server bound to host loopback:

```bash
podman run --rm --network=pasta:-T,18081 docker.io/library/busybox:1.37.0 wget -S -O- http://127.0.0.1:18081/
```

The request returned HTTP 200. The same pattern was then tested against Ollama:

```bash
podman run --rm --network=pasta:-T,11434 docker.io/library/busybox:1.37.0 wget -S -O- http://127.0.0.1:11434/api/tags
```

That request also returned HTTP 200 and the expected model list. The temporary Python test server was stopped and port 18081 was confirmed to have no listener afterward.

The deployed NGINX Quadlet uses:

```ini
[Container]
Network=pasta:-T,11434,-T,8188,-T,18080
PublishPort=127.0.0.1:11435:8080
PublishPort=127.0.0.1:11436:8081
```

Interpretation:
- The container uses its own network namespace.
- The pasta forwards let NGINX reach host Ollama at `127.0.0.1:11434`, ComfyUI at `127.0.0.1:8188`, and llama.cpp at `127.0.0.1:18080` from its own network namespace.
- NGINX listeners are published only to host loopback: container `8080` at `127.0.0.1:11435`, and container `8081` at `127.0.0.1:11436`.
- The existing `/` location proxies to `http://127.0.0.1:11434` and sets `Host: localhost:11434`. The added `/llama/` location proxies to `http://127.0.0.1:18080/`, stripping the prefix.
- The localhost Ollama and llama.cpp API checks passed after restarting the Quadlet service. Tailnet and Android access remain unverified in this change.

The `pasta -T` mapping makes the forwarded connection appear to the host as originating from loopback; treat that as an explicit trust-boundary decision. Do not enable host networking or rebind Ollama to a LAN-facing address as a shortcut. Proxy boot behavior after a real reboot, desktop shortcuts, and Android/Tailscale access are not yet validated for this deployment.

### Configuration file permissions

The NGINX unprivileged image could not read the host-mounted file when it was mode `640`, because the container process uses a different UID mapping. Changing the file to mode `644` allowed NGINX to read it. The parent directory was left at mode `750`, restricting traversal to the owner/group. Keep the config free of secrets. During implementation, verify the actual UID mapping and read access instead of broadening directory permissions or running NGINX as root.

This network arrangement does not turn NGINX into a general-purpose forward proxy or alter the host's default route. Its configured upstreams are the specific Ollama, ComfyUI and llama.cpp listeners described above. However, don't claim that the container has no outbound network access; rootless `pasta` may permit normal outbound connections. Network egress restriction is a separate control and is not part of this implementation.

## Routine desktop controls

The desktop shortcuts invoke these user-level operations:

```bash
systemctl --user start llm-proxy.service
systemctl --user stop llm-proxy.service
systemctl --user status llm-proxy.service --no-pager
```

The **Stop** action stops only the proxy. The **Status** shortcut shows the unit and container state. All three scripts passed individual Bash syntax checks, and the Status script successfully displayed a status window. Direct invocation of the Stop script confirmed Ollama stayed running; direct invocation of the Start script returned a success message and the service/API returned to active/HTTP 200. GNOME double-click behavior has not yet been fully verified. Shortcuts should not grant general administrative privileges.

For container diagnostics:

```bash
podman ps --filter name=llm-proxy
podman logs --tail=100 llm-proxy
journalctl --user -u llm-proxy.service -n 100 --no-pager
```

Logs may contain internal hostnames, request paths, or identity headers. Review and sanitize them before publishing or sharing.

## Updating the proxy configuration

Use this workflow after the container and config mount have been installed. The host-side file is the source of truth; do not edit a file only inside the running container.

1. Back up the current config.
2. Edit the host-side NGINX config file.
3. Validate the new configuration inside the container.
4. Reload NGINX only if validation passes.
5. Check both local API routes.
6. If the local checks pass, verify the tailnet HTTPS route and Android client.
7. Record the change and observed results; never mark a test passed without its output.

Example workflow using the deployed paths:

```bash
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/llm-proxy/default.conf"
cp "$CONFIG" "$CONFIG.bak.$(date +%Y%m%d-%H%M%S)"
${EDITOR:-nano} "$CONFIG"
```

Validate before applying:

```bash
podman exec llm-proxy nginx -t
```

Only if the test succeeds, gracefully reload NGINX:

```bash
podman exec llm-proxy nginx -s reload
```

If validation fails, do not reload. Restore the backup, validate again, and reload only after a successful validation. If the reload or post-change tests fail, restore the known-good file, run `nginx -t`, and reload. If the container is stopped, start it and inspect the logs before trying to validate or reload.

## Post-update verification

The deployed proxy listener is `127.0.0.1:11435`.

```bash
curl -i http://127.0.0.1:11435/api/tags
curl -i http://127.0.0.1:11435/llama/v1/models
```

The first request should return the Ollama model list; the second should return the llama.cpp model list. Both returned `200 OK` during local verification. Also test a non-streaming generation request and a streaming generation request before changing proxy configuration.

These tests alone do not prove that the proxy rewrites the upstream header: the end-to-end test must also confirm that the normal tailnet HTTPS request succeeds without manually setting a `Host` header.

After local checks, test from an authorized tailnet client. Keep the actual private tailnet URL out of public documentation and screenshots. If a result fails, capture the HTTP status and relevant sanitized logs before changing more than one thing.

## Boot startup

The intended implementation is a rootless Quadlet service under the user's systemd manager. Quadlet and linger configuration must be checked against the installed Podman version. Verify:

- The Quadlet contains the correct install target for the generated user service.
- User lingering is enabled if needed so the user service manager runs before desktop login.
- The proxy starts after a real reboot with no interactive login.
- The proxy can still be stopped manually and remains stopped until explicitly started or rebooted according to the final service policy.
- A proxy failure does not stop Ollama.

Do not assume boot startup works merely because the container starts from a terminal.

## Rollback

Before switching Tailscale Serve to the proxy, record the current Serve target locally. Do not include the private tailnet hostname in this public document.

If the new proxy fails after cutover:

1. Use the desktop Stop shortcut or `systemctl --user stop llm-proxy.service`.
2. Inspect `journalctl --user -u llm-proxy.service` and `podman logs llm-proxy`.
3. Restore the previous NGINX config if a config edit caused the problem.
4. Restore the prior Tailscale Serve target only if necessary to return to the previous state. The prior direct-to-Ollama route may return the known HTTP 403; it is a baseline rollback, not a confirmed working fix.
5. Retest from a tailnet client before recording recovery as successful.

Do not use `tailscale serve reset` as a routine troubleshooting step; it can remove Serve configuration beyond the one route under investigation.

## Change record

For each config change, record:

- Date and purpose
- File changed (never include secrets)
- Backup created
- Config test result
- Reload result
- Local `/api/tags` and `/v1/models` results
- Tailnet and Android result
- Rollback performed, if any

Keep raw logs and host-specific configuration local. Publish only sanitized commands, configuration, and observed outcomes.

## References

- [Podman Quadlet and systemd integration](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- [Podman networking options](https://docs.podman.io/en/stable/markdown/podman-run.1.html)
- [passt/pasta manual: `--tcp-ns` namespace port forwarding](https://passt.top/builds/latest/web/passt.1.html)
- [Rootless Podman networking examples: host-local access through a narrowly configured pasta forward](https://github.com/eriksjolund/podman-networking-docs#outbound-tcpudp-connections-to-the-hosts-localhost)
- [NGINX command-line options, including configuration test and reload](https://nginx.org/en/docs/switches.html)
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
