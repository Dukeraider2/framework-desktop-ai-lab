# Ollama + Tailscale + Rootless NGINX Proxy: Beta Setup Guide

This guide turns the tested beta configuration into a step-by-step procedure. It is written for a reader who knows basic terminal use but is not expected to know Podman Quadlet or NGINX.

**Scope:** expose an already-working local Ollama API to devices on your existing Tailscale tailnet, using Tailscale Serve and a rootless NGINX proxy. This is not a clean-machine installer for Ubuntu, ROCm, Ollama, or Tailscale.

**Tested environment:** Ubuntu 26.04.1 LTS, Podman 5.7.0, Tailscale 1.104.2, rootless Podman, and the NGINX unprivileged image. Other versions may behave differently.

**Beta limitations:** a basic Android OpenAI-compatible prompt/response and the local non-streaming inference path have passed. A clean completed streaming response, reboot startup without interactive login, and backup restoration are not verified. This guide has not been independently reproduced on a clean machine.

## What you are building

Request path:

1. An Android or other authorized tailnet client connects to the host's Tailscale HTTPS address.
2. Tailscale Serve forwards the request to the NGINX proxy on host loopback port `11435`.
3. NGINX forwards the request to Ollama on host loopback port `11434`, setting the upstream HTTP Host header to `localhost:11434`.
4. Ollama returns the API response through the same path.

The proxy listens only on `127.0.0.1:11435`. Do not publish this port on your LAN or expose Ollama's port to the internet. Do not enable Tailscale Funnel. The proxy does not add authentication or restrict API paths; tailnet access policy is therefore important.

## Before you start

You need:

- Ubuntu with a normal, non-root user account.
- Ollama installed and working locally.
- Tailscale connected to your tailnet.
- HTTPS certificates enabled for your tailnet in the Tailscale admin console, and Serve available.
- Podman with rootless mode, the `pasta` networking helper, and Quadlet support.
- A model already downloaded in Ollama.
- Terminal access to the host and an authorized device on the same tailnet.

If Serve reports that HTTPS is unavailable, stop and enable HTTPS certificates in the Tailscale admin console before proceeding. Do not work around that prerequisite by exposing the service publicly.

Check the existing components:

```bash
ollama list
curl -i http://127.0.0.1:11434/api/tags
tailscale version
tailscale status
podman --version
podman info --format '{{.Host.Security.Rootless}}'
```

Expected checks:
- Ollama's API request returns `HTTP/1.1 200 OK` and JSON containing your installed models.
- `tailscale status` shows the host connected.
- Podman reports a version and the final command prints `true`.

If a check fails, stop here and fix that prerequisite first. On Ubuntu, Podman can usually be installed with `sudo apt update && sudo apt install podman`, but confirm that the version in your distribution provides the Quadlet and `pasta` features used below. Do not switch to rootful or host-networked containers as a workaround.

## Step 1: Create the configuration directories

Run these commands as your normal user, not with `sudo`:

```bash
mkdir -p "$HOME/.config/llm-proxy"
mkdir -p "$HOME/.config/containers/systemd"
chmod 750 "$HOME/.config/llm-proxy"
```

If either destination already contains a configuration you need, back it up before editing. The following commands make timestamped copies of the two files if they already exist:

```bash
STAMP="$(date +%Y%m%d-%H%M%S)"
for FILE in "$HOME/.config/llm-proxy/default.conf" "$HOME/.config/containers/systemd/llm-proxy.container"; do
  if [ -e "$FILE" ]; then
    cp -a -- "$FILE" "$FILE.bak.$STAMP"
    printf 'Backup created: %s\n' "$FILE.bak.$STAMP"
  fi
done
```

Review the backup paths before continuing. The next steps replace the contents of the named files. If you already run a service called `llm-proxy`, do not overwrite its files until you understand what depends on it.

## Step 2: Create the NGINX configuration

Open the host-side configuration file:

```bash
nano "$HOME/.config/llm-proxy/default.conf"
```

Paste and save this complete configuration:

```nginx
server {
    listen 8080;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:11434;
        proxy_http_version 1.1;
        proxy_set_header Host localhost:11434;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

Set readable file permissions. The file contains no credentials; the directory remains private to the owner and group:

```bash
chmod 644 "$HOME/.config/llm-proxy/default.conf"
stat -c '%a %n' "$HOME/.config/llm-proxy" "$HOME/.config/llm-proxy/default.conf"
```

Expected modes are `750` for the directory and `644` for the file. The NGINX container needs to read the file through a bind mount.

**Why set the Host header?** In this setup, direct requests through Tailscale Serve initially returned HTTP 403. Requests using `Host: localhost:11434` returned HTTP 200. The proxy makes that upstream header consistent.

## Step 3: Create the rootless Quadlet service

Quadlet is a Podman feature that generates a systemd user service from a declarative `.container` file.

Open the service definition:

```bash
nano "$HOME/.config/containers/systemd/llm-proxy.container"
```

Paste and save:

```ini
[Unit]
Description=Rootless NGINX proxy for local Ollama API

[Container]
Image=docker.io/nginxinc/nginx-unprivileged:stable-alpine
ContainerName=llm-proxy
Network=pasta:-T,11434
PublishPort=127.0.0.1:11435:8080
Volume=%h/.config/llm-proxy/default.conf:/etc/nginx/conf.d/default.conf:ro
DropCapability=all
NoNewPrivileges=true

[Service]
Restart=on-failure
TimeoutStartSec=900

[Install]
WantedBy=default.target
```

The network option forwards only host TCP port `11434` into the container's `pasta` network namespace. The published NGINX port is bound to host loopback only. The configuration mount is read-only, and the container drops Linux capabilities.

Reload the user systemd manager and start the generated service:

```bash
systemctl --user daemon-reload
systemctl --user start llm-proxy.service
systemctl --user status llm-proxy.service --no-pager
```

If the unit is not found or fails, do not continue to the Tailscale step. Check the installed Podman/Quadlet version and inspect:

```bash
journalctl --user -u llm-proxy.service -n 100 --no-pager
podman ps -a --filter name=llm-proxy
podman logs --tail=100 llm-proxy
```

The first start may need to download the NGINX image, so allow time for it.

## Step 4: Test the proxy locally first

Run:

```bash
curl -i http://127.0.0.1:11435/api/tags
curl -i http://127.0.0.1:11435/v1/models
```

Both should return `HTTP 200` and JSON listing the models Ollama knows about.

Then test a real, non-streaming generation. Replace `qwen3:8b` with a model shown by `ollama list` if yours differs:

```bash
curl -sS http://127.0.0.1:11435/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3:8b","prompt":"Reply with exactly: proxy-ok","stream":false}'
```

Expected: JSON with a generated response. Model output may vary. If either discovery test or generation fails, do not change Tailscale Serve yet. Check the service logs and verify direct Ollama access on port `11434`.

Confirm the listener is loopback-only:

```bash
ss -ltn | grep ':11435'
```

The local address should be `127.0.0.1:11435`, not `0.0.0.0:11435` or a LAN address.

## Step 5: Save the current Tailscale Serve state

This step changes the existing tailnet HTTPS route. Before changing it, record its current status and the prior backend **in a private local note**:

```sudo tailscale serve status```

Do not publish the output if it contains your private MagicDNS hostname or other identifying information. If this host serves other applications, understand the current Serve configuration before changing anything. Do not use `tailscale serve reset` as a routine step because it can remove other Serve configuration.

## Step 6: Point Tailscale Serve at the proxy

Only after the local checks pass, run:

```bash
sudo tailscale serve --bg http://127.0.0.1:11435
sudo tailscale serve status
```

The status should show a tailnet HTTPS endpoint forwarding to `http://127.0.0.1:11435`. Keep the endpoint private. The current Tailscale CLI accepts `http://127.0.0.1:<port>` as a local reverse-proxy target; see the official [Tailscale Serve CLI documentation](https://tailscale.com/docs/reference/tailscale-cli/serve).

From the host, test the HTTPS endpoint using your actual private tailnet hostname:

```bash
curl -i https://YOUR-PRIVATE-TAILNET-HOSTNAME/api/tags
curl -i https://YOUR-PRIVATE-TAILNET-HOSTNAME/v1/models
```

Replace the placeholder locally. Do not paste your real hostname into public issues, screenshots, or commits. The requests should return HTTP 200 and the model list without manually setting a Host header. If not, stop and diagnose before changing Android client settings.

## Step 7: Configure the Android client

In an OpenAI-compatible client, use:

- **Base URL:** `https://YOUR-PRIVATE-TAILNET-HOSTNAME/v1`
- **API key:** leave blank if the client permits it and does not require a key
- **Model:** choose a model name returned by `/v1/models`, such as `qwen3:8b`

The Android device must be connected to the same tailnet and allowed by your tailnet access policy. Do not make the service public to solve an access issue. First test `/api/tags` and `/v1/models` from the phone's browser or an HTTP client, then test a prompt in the app.

A basic Android OpenAI-compatible prompt/response passed in the original environment. Streaming still needs a clean completed end-to-end test.

## Step 8: Optional user-service startup before login

The service has been observed running under the user systemd manager. A real reboot test without interactive login has not been completed. If you want the user service manager to run before login, enable lingering for your user:

```bash
sudo loginctl enable-linger "$USER"
loginctl show-user "$USER" -p Linger
```

Expected output includes `Linger=yes`. This does not by itself prove the proxy will start after reboot. After saving your work, reboot during a maintenance window, do not log in interactively, and test from another authorized tailnet device. Only then record boot startup as verified.

## Troubleshooting

### Local Ollama API works, but proxy returns an error

```bash
systemctl --user status llm-proxy.service --no-pager
journalctl --user -u llm-proxy.service -n 100 --no-pager
podman logs --tail=100 llm-proxy
podman exec llm-proxy nginx -t
```

Check that the host config path is correct, the file is readable, the container is running, and the upstream is still at `127.0.0.1:11434`.

### HTTP 403 through Tailscale HTTPS

Confirm that Serve points to port `11435`, then test the local proxy. In the observed setup, setting the upstream Host header to `localhost:11434` resolved the 403. Do not assume every 403 has the same cause; inspect the current route and sanitized logs.

### Port 11435 is not listening

```bash
systemctl --user restart llm-proxy.service
systemctl --user status llm-proxy.service --no-pager
ss -ltn | grep ':11435'
```

If it fails again, inspect the journal and container logs rather than repeatedly restarting.

### Android client cannot connect

Check tailnet connectivity and access policy first. Confirm the private HTTPS URL works from another tailnet client and that the client base URL ends in `/v1`. Do not enable Funnel or bind the proxy to a LAN interface as a workaround.

## Rollback

If the new route fails and the previous route was the direct Ollama backend used in this project, restore that prior target with:

```bash
sudo tailscale serve --bg 11434
sudo tailscale serve status
```

Use this only if that was your recorded previous configuration. The old direct route returned HTTP 403 in the original setup, so this is a configuration rollback, not a guaranteed working fix. If the host had other Serve routes, restore the exact previous configuration instead of overwriting it with this example.

To stop the proxy without stopping Ollama:

```bash
systemctl --user stop llm-proxy.service
```

To start it again:

```bash
systemctl --user start llm-proxy.service
```

Stopping the proxy does not disable the Tailscale Serve route. If the route still points to the proxy, remote API requests will fail until the proxy is restarted or Serve is pointed elsewhere.

## Security and privacy

- Keep Tailscale Serve tailnet-only. Never enable Funnel for this setup.
- Do not expose Ollama's port `11434` or proxy port `11435` on LAN/public interfaces.
- The proxy has no authentication and forwards API paths. Tailnet policy determines who can reach it.
- Do not publish private hostnames, tailnet IPs, access keys, recovery material, raw logs, packet captures, or unredacted screenshots.
- This guide does not restrict container outbound network access; do not claim it does.
- The sample uses the mutable `stable-alpine` image tag. For a hardened deployment, select and test a pinned image digest and document the update process.

## References

- [Tailscale Serve CLI reference](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [Tailscale Serve overview](https://tailscale.com/docs/features/tailscale-serve)
- [Podman Quadlet documentation](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- [Podman networking options](https://docs.podman.io/en/stable/markdown/podman-run.1.html)
- [NGINX command-line options](https://nginx.org/en/docs/switches.html)
- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api/introduction.mdx)
- [Ollama OpenAI compatibility](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx)
