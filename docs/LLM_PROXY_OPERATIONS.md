# LLM Proxy: Design and Operations

> **Status: Planned, not deployed.** This document records the agreed design and the intended maintenance workflow. The proxy container, desktop shortcuts, and boot-start configuration have not yet been installed. Do not run the operational commands below until the implementation confirms the service/container names and listener port.

## Scope

This phase covers only a small reverse proxy in front of Ollama. MCP and Hermes integrations are out of scope.

The proxy's immediate purpose is to rewrite the upstream HTTP `Host` header. During diagnosis, Ollama returned `403 Forbidden` for requests forwarded with the tailnet HTTPS hostname, but returned `200 OK` when the upstream request used `Host: localhost:11434`. The permanent proxy fix has not yet been deployed or retested from Android.

## Agreed design

- **Runtime:** Podman container.
- **Privilege model:** Prefer rootless Podman, managed by a user-level systemd/Quadlet service. Confirm on the target Ubuntu system before installation.
- **Boot startup:** User service should start without an interactive desktop login. This is expected to require systemd user lingering and a Quadlet install target; test with a real reboot.
- **Desktop controls:** Start, Stop, and Status shortcuts for this service only.
- **Proxy configuration:** A standalone editable NGINX configuration file, mounted read-only into the container.
- **Request paths:** No application-code allowlist. NGINX configuration controls routing; the initial design is transparent forwarding for Ollama API paths, with the upstream `Host` set to `localhost:11434`. Do not introduce path restrictions unless intentionally configured and tested.
- **Network exposure:** No public-facing listener. Keep Tailscale Serve tailnet-only and do not enable Funnel. Keep Ollama's existing loopback binding unchanged.
- **Lifecycle separation:** Starting or stopping the proxy must not start or stop Ollama.
- **Recovery:** Preserve the previous Serve configuration and proxy config backup before cutover or edits.

### Access-control implication

Transparent forwarding is not endpoint access control. Every API path reachable through the proxy can be forwarded unless the NGINX configuration explicitly says otherwise. Access to the service is therefore governed in part by Tailscale's tailnet access policy. The policy observed during diagnosis allowed all tailnet connections; do not describe this as a device-specific allowlist. If narrower access is needed, review tailnet policy separately rather than assuming the proxy restricts callers.

## Planned file and service names

These are proposed names to make documentation and desktop controls consistent. Confirm them during implementation before using commands.

- Host-side proxy config: `${XDG_CONFIG_HOME:-$HOME/.config}/llm-proxy/default.conf`
- Rootless Quadlet: `${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd/llm-proxy.container`
- Generated user service: `llm-proxy.service`
- Container name: `llm-proxy`
- Proposed loopback-only proxy listener: `127.0.0.1:11435`

### Preferred network path (CLI connectivity tested; Quadlet still pending)

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

The proposed Quadlet configuration is:

```ini
[Container]
Network=pasta:-T,11434
PublishPort=127.0.0.1:11435:8080
```

Interpretation:
- The container uses its own network namespace.
- The tested `pasta:-T,11434` setting lets container-side `127.0.0.1:11434` reach the host's Ollama listener on `127.0.0.1:11434`.
- The intended NGINX listener on container port `8080` will be published only to host loopback at `127.0.0.1:11435`; it will not be published on LAN interfaces.
- Tailscale Serve will target `http://127.0.0.1:11435` only after local proxy tests pass.
- NGINX will proxy to `http://127.0.0.1:11434` and set `proxy_set_header Host localhost:11434;`.

The CLI networking behavior has been observed to work with the installed versions. **Quadlet parsing, systemd service behavior, the published proxy port, and the complete NGINX proxy are not yet validated.** Validate those separately before cutover. The `pasta -T` mapping makes the forwarded connection appear to the host as originating from loopback; treat that as an explicit trust-boundary decision. Do not enable host networking or rebind Ollama to a LAN-facing address as a shortcut.

This network arrangement does not turn NGINX into a general-purpose forward proxy or alter the host's default route. Its configured upstream remains Ollama. However, don't claim that the container has no outbound network access; rootless `pasta` may permit normal outbound connections. Network egress restriction is a separate control and is not part of this minimal first implementation.

## Routine desktop controls

Once implementation is complete and the names above are confirmed, the desktop shortcuts should invoke these user-level operations:

```bash
systemctl --user start llm-proxy.service
systemctl --user stop llm-proxy.service
systemctl --user status llm-proxy.service --no-pager
```

The **Stop** action should stop only the proxy. The **Status** shortcut should show the unit state and useful failure details. Shortcuts should not grant general administrative privileges.

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

Example workflow using the planned names:

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

The proxy listener port in these examples is provisional. Confirm it against the implemented configuration.

```bash
curl -i http://127.0.0.1:11435/api/tags
curl -i http://127.0.0.1:11435/v1/models
```

Both requests should return `200 OK` with the expected Ollama model response. These tests alone do not prove that the proxy rewrites the upstream header: the end-to-end test must also confirm that the normal tailnet HTTPS request succeeds without manually setting a `Host` header.

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
