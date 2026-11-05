# FMM Stage 1 / Stage 2 evidence — 2026-11-05

Task: [Issue #11](https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/11). Implementer: Codex. Branch: `feat/framework-model-manager`, starting at `874447e`. Authority: explicit user instruction to implement the first read-only deliverable, test, commit and attempt push/draft PR. No deployment, package installation, merge or production configuration change was authorized or performed.

## Stage 1 scope and references

Acceptance scope: explicit-root GGUF inventory; Git registry separate from observations; RAM/GPU/storage/rootless Podman observations; authenticated loopback HTTP API; non-executable memory planning; permanently disabled lifecycle interface; tests, architecture, schemas, evidence and rollback documentation. The issue's later production controllers, gateway registration and storage tiers remain future work.

Core repository policies read: [constitution](../engineering/CONSTITUTION.md), [documentation-first execution](../engineering/DOCUMENTATION_FIRST_EXECUTION.md), [workflow](../engineering/DEVELOPMENT_WORKFLOW.md), [access governance](../engineering/ACCESS_GOVERNANCE.md), [agent organization](../engineering/AGENT_ORGANIZATION.md), [resource efficiency](../engineering/RESOURCE_EFFICIENCY.md), [model/integration registry](../engineering/MODEL_AND_INTEGRATION_REGISTRY.md), [Podman-first policy](../engineering/PODMAN_FIRST_POLICY.md), engineering README and stage templates. These govern authority, separation of duties, the decimal 100 GB complete-deployment ceiling, explicit activation, least privilege and evidence. Existing [llama.cpp](../STRIX_HALO_LLAMACPP.md), [gateway operations](../LLM_PROXY_OPERATIONS.md) and [OPSEC](../OPSEC.md) records supplied paths, health endpoints and publication boundaries. No applicable AGENTS.md was present in this worktree or its parent directories.

Official references retrieved 2026-11-05:

| Reference | Applicability |
| --- | --- |
| [Podman 5.7 info](https://docs.podman.io/en/v5.7.0/markdown/podman-info.1.html) | JSON rootless identity; historical repository runtime version, current live version blocked |
| [Podman ps](https://docs.podman.io/en/latest/markdown/podman-ps.1.html) | Container JSON listing; current documentation, live version match unverified |
| [Podman 5.7 stats](https://docs.podman.io/en/v5.7.0/markdown/podman-stats.1.html) | One-shot stats and documented JSON field names; rootless cgroup limitations |
| [AMDGPU sysfs](https://docs.kernel.org/gpu/amdgpu/driver-misc.html) | VRAM/GTT byte counters; checked against readable live sysfs |
| [Python HTTP server](https://docs.python.org/3/library/http.server.html) | Standard-library HTTP interface and its production limitations |

Stage estimates were not recorded before execution; no retrospective estimate is presented as an initial one. Scope and references were established from Issue #11 and user constraints before coding. Stage 3 requires a separate independent reviewer; the implementer has not approved this work.

## Implementation and rationale

`apps/fmm/core.py` contains discovery, strict manifest validation, telemetry, fixed local Podman queries, read-only service probes, conservative planning and the disabled controller. `apps/fmm/__main__.py` exposes the CLI and authenticated HTTP interface. `registry/fmm.json` contains four disabled catalogue records with unknown deployment budgets and no private paths. JSON schema, OpenAPI contract and operational documentation live beside this report; `tests/test_fmm.py` tests boundaries with isolated fixtures.

Python standard library avoids new packages, SDKs, agents or background processes. A single HTTP worker serializes observations; no queue, reservation engine, scheduler or lifecycle lock is needed while execution is impossible. Unknown evidence is represented explicitly. File presence and GGUF magic never confer qualification. Full SHA256 reads are opt-in to avoid unnecessary model I/O. There are no production deploy files and no Podman socket integration.

The API's default 8 GB safety reserve is configurable prototype policy, not a measured production budget. Planning enforces 100,000,000,000 bytes using the greater known estimate/peak and checks current RAM and GTT separately. It does not infer a budget from file size, active parameter count or Podman stats. Every plan remains non-executable.

## Validation and discovery evidence

Environment: existing Framework Desktop worktree, Python 3.14.4. Exact commands:

| Command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | 21 tests passed; 0 failures, 0 skips, final run 0.516 s |
| `python3 -m compileall -q apps/fmm tests` | Passed |
| `python3 -m apps.fmm validate` | Valid registry, 4 models |
| `python3 -m apps.fmm --root "$HOME/.local/share/llama.cpp/models" inventory` | 4 identified GGUF files; no scan errors; no full hashes requested |
| `python3 -m apps.fmm status` | RAM, GTT/VRAM, GPU activity and storage readable; Podman unavailable inside sandbox |
| `python3 -m apps.fmm services` | With approved loopback network access: 11 fixed probes HTTP 200 before and after final verification |
| `git diff --check` | Passed before commit |

The initial test run failed four HTTP fixture tests because the sandbox prohibited socket creation. Running the unchanged suite with approved loopback socket access resolved these environment errors; later tests also passed. No tests were skipped to conceal the restriction.

Observed GGUF identification, not integrity verification:

| File | Bytes |
| --- | ---: |
| `Qwen3-0.6B-Q8_0.gguf` | 639,446,688 |
| `Qwen3-8B.gguf` | 5,225,374,496 |
| `Qwen3-Coder-30B.gguf` | 18,556,688,736 |
| `gpt-oss-120b-MXFP4.gguf` | 63,387,346,208 |

The GPT-OSS file is now present compared with the issue's earlier acquisition status. It was not downloaded, hashed, loaded, qualified or enabled by this implementation. Filename alone is not proof of quantization or completeness. All catalogue records remain disabled.

Ollama returned five IDs: `qwen3-coder:30b`, `mannix/deepseek-coder-v2-lite-instruct:latest`, `deepseek-coder:1.3b`, `deepseek-coder:latest`, `qwen3:8b`; `/api/ps` returned no loaded IDs during both observations. These aliases are not counted as additional weights. Both llama.cpp model-ID endpoints remained unchanged. Direct health and gateway routes for Ollama, both llama.cpp backends and ComfyUI returned HTTP 200. No inference was requested. Active sessions remain unknown; health or an empty Ollama loaded list does not prove all services are idle. Hermes/OpenCode process health was not independently probed.

Gateway configuration and three existing Quadlet files were fingerprinted read-only before and after checks; all four SHA256 fingerprints matched. Raw fingerprints/paths are kept in a private temporary baseline outside Git. No live configuration export is published. This is a configuration identity check, not a full disaster-recovery snapshot. Existing recovery instructions remain in the gateway and llama.cpp runbooks.

Podman version/help and inventory attempts inside the sandbox failed because Podman tried to change `/run/user/1000/libpod` permissions on a read-only filesystem. No chmod, package install, socket exposure, privileged retry or runtime repair was attempted. Rootless parsing/command allowlists/redaction were fixture-tested; live Podman version/container/volume/stat collection remains unverified. Full Phase 0 ComfyUI checkpoint inventory, session telemetry and a verified restore snapshot remain outstanding.

## Resource evidence and limits

No persistent process was deployed: persistent service/process delta is zero by construction. A one-shot sample observed approximately 79.95 GB RAM available, 37.38 GB GTT available, 0.108 GB dedicated VRAM available and 706.71 GB storage available. GPU activity reported 100%; the existing runtime record warns that this sensor can remain saturated for a loaded model. These are time-specific observations, not capacity commitments.

A Python `subprocess.run` harness measured CLI wall time with `time.perf_counter`: validate 55.41 ms, inventory 56.20 ms, status 63.67 ms. Linux `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` across those children was 29,908 KiB. These are single samples, not a benchmark distribution; status includes the failed sandbox Podman attempt. GGUF discovery reads four magic bytes per regular GGUF, plus filesystem metadata, rather than streaming the weights. No baseline FMM process existed, so a before/after runtime comparison is unavailable. Idle HTTP CPU/RSS, power, disk throughput and production latency were not measured; no performance qualification is claimed.

## Rollback, review and remaining gates

Stop only a temporary FMM process and revert this feature through a reviewed Git change. No model or service rollback is needed because they were not modified. Production rollback execution was neither needed nor tested.

Independent Stage 3 review, score and QA remain pending. Future work needs durable audit/idempotency, per-model locks and reservations, authenticated scoped lifecycle approvals, session draining, readiness/tool/context/offload validation, atomic gateway update/rollback and separately approved Podman deployment packaging. Do not treat this PR as completing the issue's production phases or close the whole issue on merge.

GitHub metadata checked during work reports PR #10 already merged at `2942856`, despite the issue's older statement that it was open. Fetching main refreshed only local Git metadata. This work did not merge, rewrite or alter PR #10.

Time report: Stage 1 active time not separately measured; Stage 2 active/elapsed time approximately 15 minutes (estimate, no continuous timer), waiting time not separately measured. Stage 2 verification completed 2026-11-05 around 13:07 UTC. Stage 3 time/completion is pending. There was no recorded initial estimate from which to calculate variance.
