# Local model inventory and assignment matrix

**Status:** No founding agent has a model assignment. The identities and SOUL files stay model-independent. The current local executor could not reach Ollama's read-only API, so model names, exact capabilities, parameter counts, context limits, loaded sizes, and performance are not verified.

## Observed host evidence

Collected in the restricted executor on `framework-ai1` (Ubuntu 26.04.1):

- CPU: AMD Ryzen AI MAX+ 395, 16 cores / 32 threads.
- Memory visible to `free`: 122 GiB total, 108 GiB available at observation time; 8 GiB swap.
- DRM sysfs: Framework / AMD Radeon device (`vendor=0x1002`, `device=0x1586`). Sysfs reported 512 MiB in the DRM `mem_info_vram_total` field; this is not a measurement of total shared UMA capacity.
- The executor could not access `127.0.0.1:11434` (`socket: operation not permitted`). `/dev/kfd` was absent in its namespace; `rocminfo` reported it could not open KFD and that this user is not in `video`. No group or device permissions were changed.
- Cgroup memory/CPU limit files were unavailable at the expected `/sys/fs/cgroup` paths. The observed host memory cannot therefore be treated as the service's effective resource limit.

The only existing Hermes configuration visible in `hermes profile list` is `qwen3-coder:30b` for `default` and `frameworklab`. That proves a configured model name, not current Ollama installation, successful inference, its exact active parameter count, context, or performance. Do not copy this binding to founding profiles without the inventory below.

## Assignment matrix

Context targets below are proposed task-package requirements, not claims about installed model capability. “Active parameters” must be reported separately from total parameters when the model architecture supports that distinction; do not estimate it from the model name.

| Agent | Reasoning / coding need | Proposed context target | Current model | Memory / performance evidence | Assignment |
|---|---|---:|---|---|---|
| Moncappy Time | Strong multi-step planning, synthesis; coding is secondary | 16k | Unknown | Not collected | None |
| Dolly | Reliable conversational reasoning, inclusive writing; coding is secondary | 8k | Unknown | Not collected | None |
| Robin | Broad ideation, reframing, creative writing; coding is secondary | 8k | Unknown | Not collected | None |
| Betty | Careful evidence comparison, test reasoning, code review | 16k | Unknown | Not collected | None |
| Richard Feynman | Strong coding, mathematics, scientific reasoning, debugging | 16k | Unknown | Not collected | None |
| Alan Watts | Strong abstract reasoning, systems analysis, long-form synthesis | 16k | Unknown | Not collected | None |
| Fulton J. Sheen | Strong ethical/governance reasoning, careful long-form argument | 16k | Unknown | Not collected | None |

The context targets should be adjusted if actual project task packages exceed or do not need them. No personality prompt may be used as a substitute for model capability.

## Collection and selection procedure

Run the repository collector on the host after confirming the local Ollama service is healthy:

```bash
cd /opt/hermes-project-awareness
python3 scripts/agents/collect-local-model-inventory.py > /tmp/hermes-model-inventory.json
```

It reads `ollama list`, `ollama show --verbose`, `ollama ps`, CPU/memory/cgroup metadata, and selected DMI fields. It does not read model weights, credentials, full Modelfiles, or unrelated home files. Review the resulting file locally and redact any model names before attaching it to GitHub.

For performance measurements, after reviewing the inventory and available capacity, run the opt-in small local benchmark:

```bash
python3 scripts/agents/collect-local-model-inventory.py --benchmark > /tmp/hermes-model-benchmark.json
```

This runs one short, 32-token-capped local inference per installed Ollama model, unloads each model with `keep_alive=0s`, and records Ollama's generation/prompt timing counters. It uses no hosted API. The machine operator should avoid running it while production inference is busy. Do not assign a model until the inventory, hardware limits, actual loaded size, context, coding/science reasoning evals, and measured tokens/second have been reviewed.

## Selection rules

1. Prefer a model that is already installed and runs locally; do not download models or enable paid providers as part of selection.
2. Record model ID, architecture, context limit, quantization, total parameters, active parameters (if applicable), Ollama-reported loaded size, and whether CPU/GPU layers are used.
3. Measure reasoning, coding, scientific/mathematical, and long-context tasks using reproducible local prompts and independent scoring. Keep the prompt/results in test artifacts, not in SOUL files.
4. Measure cold-load and warm-generation speed on the actual inference service and record available memory before and during load.
5. Assign profiles individually. Keep model/provider settings outside `SOUL.md`, registry identity, and worker permissions.
