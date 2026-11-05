# Local inference providers for Hermes and OpenCode

This guide records the local inference providers available to Hermes and OpenCode. It does not change the inference containers, model files, NGINX routes, or agent defaults.

## Provider catalog

The model IDs below were read from each provider's OpenAI-compatible `/v1/models` endpoint on 2026-11-04.

| Provider | API base URL | Agent model ID | Reported model ID |
|---|---|---|---|
| Ollama | `http://127.0.0.1:11435/v1` | `qwen3-coder:30b` | `qwen3-coder:30b` |
| llama.cpp ROCm Qwen3 0.6B | `http://127.0.0.1:11435/llama/v1` | OpenCode: `qwen3-0.6b`; Hermes: `/models/Qwen3-0.6B-Q8_0.gguf` | `/models/Qwen3-0.6B-Q8_0.gguf` |
| llama.cpp ROCm Qwen3-Coder 30B | `http://127.0.0.1:11435/llama-coder/v1` | OpenCode: `qwen3-coder-30b`; Hermes: `/models/Qwen3-Coder-30B.gguf` | `/models/Qwen3-Coder-30B.gguf` |

The OpenCode custom-provider model keys are friendly selectors; their `modelID` values are the exact IDs returned by llama.cpp. The existing Ollama provider uses its API's discovered model IDs, including `qwen3-coder:30b`, `mannix/deepseek-coder-v2-lite-instruct:latest`, `deepseek-coder:1.3b`, `deepseek-coder:latest`, and `qwen3:8b`.

## Hermes configuration and selection

Hermes is installed natively (`0.22.5`). Named custom providers are defined in the supported `providers:` map in `~/.hermes/config.yaml` and in each existing profile's `config.yaml` under `~/.hermes/profiles/`. The entries use the profile keys `ollama-local`, `llama-rocm-06b`, and `llama-rocm-coder-30b`, with `transport: chat_completions` and the endpoint/model pairs above.

The existing primary model remains `qwen3-coder:30b` on provider `custom` at the Ollama gateway. The `frameworklab` profile also remains on `qwen3-coder:30b` at its pre-existing URL. Every profile's `terminal.backend` and other existing settings were preserved.

Select a provider for one CLI run without changing the active default:

```bash
hermes chat --provider ollama-local -m qwen3-coder:30b
hermes chat --provider llama-rocm-06b -m /models/Qwen3-0.6B-Q8_0.gguf
hermes chat --provider llama-rocm-coder-30b -m /models/Qwen3-Coder-30B.gguf
```

In an interactive session, the corresponding named-provider selectors are `custom:ollama-local:qwen3-coder:30b`, `custom:llama-rocm-06b:/models/Qwen3-0.6B-Q8_0.gguf`, and `custom:llama-rocm-coder-30b:/models/Qwen3-Coder-30B.gguf`.

## OpenCode configuration and selection

OpenCode `2.2.5` runs natively through `~/.local/bin/opencode`, which execs the installed `~/.opencode/bin/opencode` binary in standalone mode. Its global configuration is `~/.config/opencode/opencode.json`; it uses the installed v2 `providers` schema with `package`, `settings.baseURL`, and `models`/`modelID` entries. No additional inference gateway or persistent proxy was added.

The current model remains `ollama/qwen3-coder:30b`. Ollama keeps its existing provider ID and gateway URL. The added providers are `llama-rocm/qwen3-0.6b` and `llama-coder-rocm/qwen3-coder-30b`.

Run a one-off selection:

```bash
opencode run --model ollama/qwen3-coder:30b "Reply with a short greeting"
opencode run --model llama-rocm/qwen3-0.6b "Reply with a short greeting"
opencode run --model llama-coder-rocm/qwen3-coder-30b "Reply with a short greeting"
```

The interactive `/models` picker also lists the configured providers. OpenCode's model entry for Qwen3 0.6B marks tools unsupported based on the direct API probe; the 30B entry advertises tools because its direct endpoint returned an OpenAI function call in validation.

The OpenCode config also adds an optional `compact-local-coder` agent. It keeps a short prompt and only exposes read, edit, and shell tools, allowing the 4K Qwen3-Coder 30B endpoint to fit an agent request. It does not change the default `build` agent or current model. Use it for the short-context llama.cpp models:

```bash
opencode run --agent compact-local-coder --model llama-rocm/qwen3-0.6b "Reply with a short greeting"
opencode run --agent compact-local-coder --model llama-coder-rocm/qwen3-coder-30b "Implement a small coding task"
```

## Validation results

Hermes and OpenCode versions and configs were inspected before changes. OpenCode's provider format was checked against the installed v2-compatible configuration behavior and the official [OpenCode provider guide](https://opencode.ai/v2/docs/providers/) and [model guide](https://opencode.ai/v2/docs/models/). Hermes named-provider syntax was checked against its installed version's provider documentation and implementation.

| Agent / provider | Conversation and stream | Tool/function call | Temporary coding task | Result |
|---|---|---|---|---|
| Hermes / Ollama | Passed; streaming JSON emitted incremental text | Passed; Hermes used `write_file` and `terminal` | Passed; wrote and ran `add(a,b)` assertion in a temporary directory | Supported |
| OpenCode / Ollama | Passed; native CLI returned the requested response, API stream ended with `[DONE]` | Passed through the coding task's file and shell tools; direct function-call response also returned | Passed; native OpenCode wrote and ran `add.py` in `/tmp` | Supported |
| Hermes / llama.cpp 0.6B | Agent startup refused the service's 4,096-token context; Hermes requires at least 64,000. Direct API stream completed, but a short direct chat ended during reasoning with empty final content. | No tool call returned by the direct endpoint probe | Not run because Hermes rejects the context before a turn | Not currently usable in Hermes |
| OpenCode / llama.cpp 0.6B | Default `build` prompt exceeded the service limit (5,432 vs. 4,096). The compact agent returned a normal response. | Direct forced-function request returned no `tool_calls`; OpenCode marks tools unsupported. | No tool-based coding task; model has no usable function-call support. | Chat only through `compact-local-coder` |
| Hermes / llama.cpp Qwen3-Coder 30B | Passed; streamed a normal response with the configured 65,536-token model window | Passed; Hermes invoked `write_file` and `terminal` | Passed; created `check.txt`, read it back as `TOOL_OK` | Supported at 65,536 context |
| OpenCode / llama.cpp Qwen3-Coder 30B | Passed through the normal `build` agent with the configured 65,536-token context | Passed; default build agent used file and shell tools | Passed; created and ran `sum.py` asserting `add(19, 23) == 42` in `/tmp` | Supported with default `build`; `compact-local-coder` remains optional |

The direct checks used each API's exact model ID. All three `/v1/models` requests and the chat/stream requests returned HTTP 200; the llama.cpp 30B endpoint returned `qwen3-coder-30b` only through the Ollama API and `/models/Qwen3-Coder-30B.gguf` through llama.cpp. The direct llama.cpp 0.6B short response was not a successful conversational answer, and its forced function call did not produce a tool call. In Stage 6, only the Qwen3-Coder service context was raised to 65,536; the 0.6B service remains at 4,096.

Qwen3-Coder 30B is configured with 65,536 context and output limits in OpenCode's installed v2 schema; Hermes advertises the same model context in its supported named-provider model metadata. Both agents successfully used tools with the backend. The 0.6B service remains at 4,096 context: Hermes rejects it for its minimum context requirement, and OpenCode's default `build` prompt can exceed it. The compact agent remains available for short-context models, but the normal `build` agent now works with Qwen3-Coder 30B. The active OpenCode model remains `ollama/qwen3-coder:30b`, and no agent defaults or permissions were changed.

After the Stage 6 configuration, Hermes passed `hermes config check`, and `HERMES_PROFILE=frameworklab hermes config get` resolved the Coder provider model context to 65,536. The Hermes gateway stayed active. OpenCode v2 configuration loaded, and the default `build` agent used `llama-coder-rocm/qwen3-coder-30b` to create and run a coding task in `/tmp`. The coder API reported `n_ctx=65536`, its service remained enabled and active, and logs confirmed flash attention plus 49/49 layers offloaded. Ollama's `/v1/models`, the existing 0.6B `/llama/v1/models`, and ComfyUI `/system_stats` through port 11436 all returned HTTP 200; the Ollama, 0.6B, Hermes gateway and NGINX user services remained active. Stage 6 did not modify NGINX routes, model files, or any other inference service.

## Backups and restore

Backups were made before editing. The primary Hermes config and `frameworklab` profile backups use suffix `.bak-20261104-180529`; the other seven profile backups use `.bak-20261104-181504`. The original OpenCode runtime config backup is `~/.config/opencode-lab/runtime/opencode.json.bak-20261104-180529`. The OpenCode config backup taken before adding the optional compact agent is `~/.config/opencode/opencode.json.bak-20261104-182621`.

To restore the pre-integration Hermes files, copy each backup over its matching file. For example:

```bash
cp ~/.hermes/config.yaml.bak-20261104-180529 ~/.hermes/config.yaml
cp ~/.hermes/profiles/frameworklab/config.yaml.bak-20261104-180529 ~/.hermes/profiles/frameworklab/config.yaml
```

For the other profiles, use the matching `.bak-20261104-181504` file. To restore OpenCode's previous provider settings while keeping the native launcher:

```bash
cp ~/.config/opencode-lab/runtime/opencode.json.bak-20261104-180529 ~/.config/opencode/opencode.json
```

This removes the added OpenCode models while retaining the previous active model and Ollama settings. The native launcher remains in place.

Before the 64K context change, Stage 6 made a complete backup of the primary and profile Hermes configs, OpenCode config, installed and repository Quadlets, and both project documents at `~/.local/share/llama.cpp/backups/stage6-20261105T024403Z/`. Restore the relevant file from that directory if needed. Restoring the installed Quadlet requires `systemctl --user daemon-reload` followed by `systemctl --user restart llama-cpp-qwen3-coder.service`.
