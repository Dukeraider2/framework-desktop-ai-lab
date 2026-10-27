# Ollama Tailscale Proxy Beta Guide

See `examples/nginx/ollama.conf` and `examples/quadlet/llm-proxy.container` for the reference configuration.

The tested flow is Tailscale Serve (tailnet-only) to a rootless Podman/NGINX proxy bound to `127.0.0.1:11435`, then Ollama on host loopback `127.0.0.1:11434`. NGINX sets the upstream Host header to `localhost:11434`, resolving the observed HTTP 403 in this setup.

## Verified

- Local `/api/tags` and `/v1/models`: HTTP 200.
- Non-streaming generation through persistent proxy: HTTP 200.
- Tailscale HTTPS `/api/tags` after cutover: HTTP 200.
- Android OpenAI-compatible client: basic prompt/response succeeded.

## Not yet verified

- Clean completed end-to-end streaming response.
- Startup after reboot without interactive login.
- Backup restoration.

## Safety

Keep Serve tailnet-only. Do not enable Funnel. Bind the proxy to loopback and keep Ollama on loopback. The proxy forwards API paths and adds no authentication or per-endpoint authorization, so access depends on the tailnet access policy. Do not publish private tailnet hostnames, IPs, credentials, or raw logs.

Test locally before changing Serve:

```bash
curl -i http://127.0.0.1:11435/api/tags
curl -i http://127.0.0.1:11435/v1/models
```

Only point Serve to `http://127.0.0.1:11435` after local checks pass. Verify the route from an authorized tailnet client and record rollback details privately. Consult current official documentation for your Tailscale and Podman versions.
