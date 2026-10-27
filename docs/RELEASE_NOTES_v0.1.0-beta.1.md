# v0.1.0-beta.1

First community beta of the rootless NGINX reverse-proxy recipe for accessing a local Ollama API through tailnet-only Tailscale Serve.

## Validation

Tested on one Framework Desktop running Ubuntu 26.04:
- Local `/api/tags`, `/v1/models`, and non-streaming generation through the persistent proxy returned HTTP 200.
- Tailscale HTTPS `/api/tags` returned HTTP 200 after Serve was pointed to the proxy.
- An Android OpenAI-compatible client completed a basic prompt/response.
- Streaming emitted incremental chunks, but a clean completed streaming response remains to be validated.
- Reboot startup without login and backup restoration remain unverified.

This is a beta recipe, not a production security boundary. It adds no API authentication. Keep Serve tailnet-only, do not enable Funnel, and review tailnet access policy.
