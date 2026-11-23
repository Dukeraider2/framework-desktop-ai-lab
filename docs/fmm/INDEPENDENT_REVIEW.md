# FMM independent validation — 2026-11-05

**Assessment: FAIL for isolated rootless Podman deployment readiness.** The read-only prototype is useful and its controls are substantially sound, but container packaging, a safe host collector and live acceptance evidence are missing. This assessment does not authorize deployment. The small remediation below needs independent review; this reviewer does not approve its own fix.

What this change does: FMM discovers explicitly selected GGUF files, observes resources and services, and makes non-executable memory plans. A bearer token grants read-only access; Hermes remains administrative authority and load/unload/switch always refuse execution.

## Review identity and baseline

Reference: [Issue #11](https://github.com/Dukeraider2/framework-desktop-ai-lab/issues/11), [merged PR #12](https://github.com/Dukeraider2/framework-desktop-ai-lab/pull/12). Reviewer: a separate Codex review invocation; no separate human identity or independent approval is claimed. Review is of the prior implementation; the remediation requires another reviewer.

GitHub confirmed main at `c8ab9703caa2ac05b4c70cc8a1a43c8e2c781c2d`, PR #12 merged at 13:15:28 UTC, head `35989abcae16a27d41366f59ba27aed53235bd2c`. The supplied worktree actually remained clean on `feat/framework-model-manager` at `35989ab`; local main was `810bb9c`, origin/main `2942856`. Five latest local commits were `35989ab`, `874447e`, `5fb4ede`, `812d476`, `155f8b4`. GitHub blob SHAs for all ten PR files matched the local baseline exactly: README, three app files, original tests, registry and four FMM documents. Thus the reviewed FMM source is the merged source despite stale local refs.

Fetching into the original worktree failed because its shared Git metadata is read-only. A separate normal local clone in temporary storage was created without hardlinks, on `fix/fmm-independent-validation`. Network Git fetch failed DNS resolution. GitHub's connected API provides the permitted publication path, based on the verified merged main. The original workspace and production definitions were not edited.

Policies inspected: every document in `docs/engineering/`, the Stage 3 template, OPSEC, FMM README/implementation report/API contract/manifest schema, gateway operations and llama.cpp runtime records. No applicable AGENTS.md was found in the worktree or ancestor locations checked. Policy requirements include Hermes authority, independent review, GitHub coordination, Podman, no self-approval, resource evidence and no production changes. Proposed standards were distinguished from mandatory policy. The task supplied scope and acceptance constraints; no governance rules were changed.

Official references checked on 2026-11-05: [Python HTTP server](https://docs.python.org/3.14/library/http.server.html), [Python HTTP exceptions](https://docs.python.org/3.14/library/http.client.html), [AMDGPU sysfs counters](https://docs.kernel.org/gpu/amdgpu/driver-misc.html). Python documentation currently renders 3.14.10; installed interpreter is 3.14.4. Local standard-library behavior and regression execution supply exact installed-version evidence. No new runtime/package integration was performed. Podman version/help and live behavior could not be verified because initialization fails before those commands complete.

## Findings and security assessment

No confirmed Critical or High exploit was found within the documented trusted-root, operator-only prototype scope. This is not a general production security certification.

### Must fix

1. **Medium — HTTP protocol failures abort all remaining service observations.** Baseline `apps/fmm/core.py:240-252`, especially the exception boundary at line 251; `apps/fmm/__main__.py:61-69,86` propagates the failure instead of returning a structured result. A response read raising `http.client.IncompleteRead` escapes because it is an `HTTPException`, not an `OSError` or `ValueError`. One broken backend then aborts later probes and the API request, with no application audit event. Regression `test_http_protocol_failure_does_not_abort_other_probes` reproduced the uncaught exception before the fix. Minimal remedy: import/catch `HTTPException` at the per-endpoint boundary. The regression now confirms the failed probe is unavailable, all eleven probes are attempted, a later health probe succeeds and partial payload bytes are not disclosed. Patched reference: `apps/fmm/core.py:252`.

### Deployment blockers and residual risks

2. **High readiness blocker — no isolated deployment/collector implementation.** `docs/fmm/README.md:75`, `apps/fmm/core.py:104-160,225-236`. The source observes the current namespace's /proc, filesystem, local Podman and 127.0.0.1 endpoints. Placing it unchanged inside an isolated container does not establish correct host disk availability, host Podman identity or host service access. There is no FMM Containerfile/Quadlet or snapshot consumer. Implement and independently validate the documented narrow host collector and rootless packaging in a separately scoped change; do not mount the socket/storage or substitute privileged/host networking as a workaround. This is an explicitly deferred feature, not a regression in the first deliverable.

3. **Medium residual availability risk — serialized development HTTP interface.** `apps/fmm/__main__.py:14-29`, `apps/fmm/core.py:238-252`. One request occupies the only worker; eleven two-second endpoint timeouts can hold it roughly 22 seconds, four Podman calls can consume up to 40 seconds, and a slow peer can extend a connection by sending data within each five-second socket timeout. No absolute request deadline or rate limit exists. This is disclosed development scope, so no speculative server redesign was added. Before operational deployment, measure delays, bound total work and validate overload behavior.

4. **Low operational limitation — audit is volatile and cannot establish caller identity.** `apps/fmm/__main__.py:22,49-68,87-88`. It records bounded method/operation/status events without token/body values, but disappears on exit and all token holders share authority. This is appropriate only for read-only prototype access. Durable audit and scoped Hermes authorization remain mandatory before lifecycle control; no lifecycle enable path was introduced.

### Boundaries examined

| Area | Evidence and conclusion |
| --- | --- |
| Authentication/authorization | All supported GET/POST routes authenticate with constant-time ASCII bearer comparison before observations. Literal IPv4 loopback binding only; Origin rejected. Unsupported HTTP methods use the base handler's generic errors and do not execute observations; no blanket claim that every parser error is authenticated/audited. Token possession is not Hermes identity. |
| Hermes | Controller has no enable switch and rejects all three lifecycle operations. No administrative host command, gateway edit or model mutation is exposed. |
| HTTP input | Exact JSON media type, one Content-Length, no Transfer-Encoding, 4096-byte cap, model_id-only shape. Socket-free protocol tests exercise real request parsing/dispatch. Live bind/request handling remains blocked. |
| Paths/symlinks | HTTP cannot choose roots/paths. File symlinks use O_NOFOLLOW, directory links are skipped, nonregular files are ignored; missing roots report errors. Hardlinks deduplicate by device/inode. Trusted roots and read-only mounts remain required: ancestor symlinks/concurrent directory replacement are not a confinement boundary. No hostile concurrent replacement guarantee is claimed. |
| Registry | Strict fields, duplicate IDs, lifecycle, byte counts, digest syntax and extra-field rejection tested. Four starter records valid and disabled. This checks the Python validator and schema field agreement, not a full independent JSON-Schema engine conformance run. |
| Memory | Decimal 100,000,000,000-byte complete-deployment ceiling, maximum known estimate/peak, reserve, separate RAM and GTT checks; no additive shared-memory double counting. Unknown/stale/future telemetry fails eligibility. No reservations or measured per-model budgets exist; every plan is non-executable. |
| AMD telemetry | Live sysfs VRAM/GTT subtraction and GPU busy values available; no ROCm compute or offload qualification performed. Sensor activity does not establish active sessions or capacity. |
| Podman | Fixed argv, no shell, forced local mode, stripped remote destination variables, nonroot check and rootless identity check. Output redacts command/environment/mounts. Fixtures test these; actual containers cannot be enumerated. Query failure reports unavailable with no repair. |
| Failure isolation | Missing telemetry/files/Podman handled conservatively. HTTP protocol failure fixed and regression-tested. Optional Podman stats failure still makes aggregate inventory unavailable; it does not imply no containers exist. |
| Efficiency | Standard library only; inventory reads four magic bytes rather than streaming weights. No full model hashes, builds, downloads, inference requests or persistent processes. No production throughput/idle/power qualification claimed. |

## Executed validation and non-destructive failure matrix

Installed Python: **3.14.4**. Commands run from repository root unless noted:

| Command/check | Exact result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` baseline | 21 tests: 17 passed, 4 ERROR, 0 skipped; each API test fails at socket creation with PermissionError errno 1. Suite FAILED. |
| `python3 -m unittest discover -s tests -p test_fmm_review.py -v` before fix | 5 tests: 4 passed, 1 ERROR (uncaught IncompleteRead). |
| Complete suite after fix | 26 tests: 22 passed, same 4 socket ERRORs, 0 skipped; suite FAILED due environment. No blanket pass claim. |
| `python3 -m compileall -q apps/fmm tests` | Exit 0. |
| `python3 -m apps.fmm validate` | Exit 0, `valid: true`, 4 models. |
| `python3 -m apps.fmm --root "$HOME/.local/share/llama.cpp/models" inventory` | Exit 0, 4 files, no scan errors, no full hashes. |
| `python3 -m apps.fmm status` | Exit 0, RAM/VRAM/GTT/storage readable; Podman unavailable. |
| `python3 -m apps.fmm services` | Exit 0, all 11 observations unavailable, HTTP status null; host service health UNVERIFIED, not failed. |
| `podman --version` | Initialization fails: runtime directory sticky-bit chmod attempted on read-only filesystem. No permission change/retry outside sandbox. |
| `git diff --check` | Exit 0. |

| Failure case | Executed evidence |
| --- | --- |
| Invalid manifests/duplicate IDs | Original RegistryTests reject invalid SHA, traversal ID, wrong types, extra fields and duplicate model IDs. |
| Missing directories/invalid GGUF/symlinks | Original InventoryTests reject missing/symlink roots, symlink files and invalid magic; verify hardlink dedup and unchanged fixture content/mtime. GGUF magic is identification only: structurally broken files with correct magic are not qualified. |
| Missing GPU telemetry | Original telemetry and policy tests exercise missing values and empty GPU list; eligibility false. |
| Unavailable Podman | Original mocked FileNotFoundError returns unavailable; actual sandbox initialization also unavailable. |
| Unauthorized API | New in-memory real-handler request yields 401; valid authenticated health 200; Origin 403. No listener opened. |
| Malformed/oversized/framing | New protocol tests yield 400 for malformed/deep JSON, duplicate Content-Length and Transfer-Encoding; 413 for 4097 bytes. |
| Lifecycle operations | All three real-handler fixture requests return 409, accepted false; original controller tests deny them directly. |
| >100 GB/headroom/stale telemetry | Original policy tests reject measured peak 100,000,000,001 bytes, insufficient/unknown RAM/GTT, zero/future timestamps; exactly 100 GB fixture permitted only as non-executable plan with adequate headroom. |
| Broken upstream HTTP/JSON | New fixtures isolate HTTPException; deep JSON also rejects without aborting later probes on this interpreter. |

These protocol fixtures use BytesIO and the actual BaseHTTPRequestHandler parser; they do not simulate a successful socket bind or replace the four failed integration tests. Live FMM API and health checks must be repeated in an already permitted loopback environment. No sandbox bypass or permission change was requested.

Observed checkpoint identification (not integrity/compatibility verification):

| Basename | Bytes |
| --- | ---: |
| Qwen3-0.6B-Q8_0.gguf | 639,446,688 |
| Qwen3-8B.gguf | 5,225,374,496 |
| Qwen3-Coder-30B.gguf | 18,556,688,736 |
| gpt-oss-120b-MXFP4.gguf | 63,387,346,208 |

No model was loaded, hashed in full, downloaded, qualified or enabled. Ollama blob and ComfyUI non-GGUF checkpoint integrity are outside the scanner's supported formats and were not independently established. Registry desired metadata remains separate from installed state.

## Before/after production comparison and resource evidence

Read-only private snapshots were retained in temporary storage, without committing raw paths, configuration exports, tokens or fingerprints. SHA256/size/mtime fingerprints match for **one installed gateway configuration and all three installed .container Quadlets**. All four GGUF files retain identical size and mtime; full content identity is not proven because weights were not hashed. No model writes occurred.

| Quantity | Before | After |
| --- | ---: | ---: |
| Sample epoch UTC seconds | 1793884811.4567888 | 1793884931.3348558 |
| RAM available, bytes | 79,551,115,264 | 79,568,572,416 |
| GTT available, bytes | 37,411,889,152 | 37,392,949,248 |
| VRAM available, bytes | 106,074,112 | 108,191,744 |
| GPU busy sensor | 100% | 100% |
| Storage available, bytes, same workspace filesystem | 706,710,470,656 | 706,707,038,208 |
| Live containers | Unavailable | Unavailable |
| Eleven inference/gateway probes | All inaccessible | All inaccessible |

An initial post sample used the temporary clone filesystem; it was excluded and resampled against the original workspace filesystem for comparability. Resource differences are time samples under existing workloads, not attributable FMM regression measurements. No persistent FMM process exists. Child command measurements in the temporary clone using perf_counter/subprocess: validate **55.29 ms**, inventory **53.02 ms**, status **63.15 ms**; child peak RSS **29,592 KiB** across those children. Single samples only; status includes failed Podman initialization. CPU utilization, I/O rate, power, idle server RSS and production latency were not measured.

No container start/stop/restart/exec, model write, gateway change, host install, socket exposure, chmod, lifecycle enablement, deployment or merge was performed. Configuration identity is verified; continued running-container identity and endpoint health cannot be confirmed through this sandbox. Previous PR claims of 11 HTTP 200 responses were read as historical evidence only and are not presented as this review's results.

## Remediation, publication and rollback

Only `apps/fmm/core.py` runtime behavior changes: catch the HTTP client's protocol exception family per probe. Five socket-free regression/security tests are added in `tests/test_fmm_review.py`; this report records findings, constraints and rollback. No dependency is added. A dedicated branch and draft PR are used; no merge or deployment is authorized. Git transport is unavailable, so publication uses the connected GitHub API with main as the parent. Local review clone and published branch can have different commit identities; changed file content is verified when publishing.

Rollback: revert the remediation through a reviewed Git change, restoring the prior per-probe exception boundary and removing the added tests/report if desired. No production configuration restore, service restart or model rollback is necessary. No FMM process was started. Runtime rollback was not executed because nothing was deployed.

## Stage 3 provisional score and next gates

Weights are the repository's provisional rubric, not an owner-approved numerical certification.

| Category | Maximum | Score | Reason |
| --- | ---: | ---: | --- |
| Specification compliance | 15 | 11 | First read-only deliverable largely met; isolated deployment absent. |
| References/source verification | 10 | 8 | Main source hashes and official references checked; live Podman version blocked. |
| Reasoning/evidence | 15 | 12 | Scope and unknowns explicit; prior live claims cannot be repeated here. |
| Architecture | 10 | 6 | Safe disabled controller; host/container observation boundary unfinished. |
| Code quality | 10 | 8 | Lean implementation; confirmed exception isolation defect fixed. |
| Testing | 10 | 5 | Broad fixtures; four real socket tests and live endpoints blocked. |
| Security/dependencies | 10 | 8 | Least privilege/no extra dependencies; development server/volatile audit limits. |
| Resource efficiency | 20 | 10 | Small one-shot measurements; operational load/idle measurements absent. |
| **Total** | **100** | **78** | Conditional prototype acceptance only; deployment gates override score. |

**Verdict: do not deploy.** Required next steps: independent review of the fix; complete all 26 tests including loopback integration in an authorized environment; collect actual rootless Podman/container inventory and repeat all direct/gateway health checks; implement separately reviewed isolated packaging and a narrow authenticated read-only host snapshot collector; verify mount/resource/network limits and container overhead without host socket access. Future lifecycle authorization, durable audit, reservations, session drain and gateway modification remain disabled and outside this remediation.

Time: initial Stage 3 estimate not recorded; active/elapsed work approximately 5 minutes at report creation (estimate, not continuous timing); blocked/wait time not separately measured. Validation snapshots completed around 13:22 UTC. No retrospective initial estimate or precise variance is fabricated.
