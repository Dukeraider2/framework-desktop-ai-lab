# Model Inventory and Acquisition Baseline

**Status:** Working baseline; host inventory must be refreshed before any download.
**Prepared:** 2026-11-02

## Previously observed host Ollama inventory

The following five tags were reported by a successful host-side Ollama inventory during the November 2, 2026 troubleshooting session. They are historical observations, not a substitute for a fresh API query:

| Exact Ollama tag | Recorded status | Notes |
|---|---|---|
| `qwen3-coder:30b` | Previously reported installed | Verify on host; earlier repository configuration alone did not prove installation. |
| `mannix/deepseek-coder-v2-lite-instruct:latest` | Previously reported installed | Verify exact tag on host. |
| `deepseek-coder:1.3b` | Previously reported installed | Verify exact tag on host. |
| `deepseek-coder:latest` | Previously reported installed | Verify exact tag on host. |
| `qwen3:8b` | Previously reported installed | Also independently referenced in the October 26 system status record. |

**Important:** This list is the previously observed installed inventory. It is not the requested list of additional models to acquire.

## Additional acquisition list

**Unresolved.** Repository records inspected on November 2, 2026 do not contain concrete exact Ollama tags for the previously discussed additional acquisition shortlist. The local model assignment matrix defines seven agent roles and context targets, but explicitly leaves model assignments unknown.

Do not interpret this missing shortlist as an empty acquisition list. Do not invent tags or silently substitute recommendations.

The operator must recover the exact previously selected acquisition tags from the original selection notes/conversation, then add them here before beginning the sequential download campaign.

| Exact Ollama tag | Intended capability/agent | Status | Source / selection evidence |
|---|---|---|---|
| To be recovered | To be recovered | Blocked: exact tag not recorded | Original model shortlist not present in repository records inspected |

## Required execution procedure

1. Query the **Ubuntu host** Ollama API at `http://127.0.0.1:11434/api/tags` from the host execution context. Do not query from the restricted Podman terminal and infer that no models exist.
2. Save the fresh host inventory with timestamp.
3. Compare it with the five historical tags above.
4. Recover and enter every exact acquisition tag before downloading. Do not replace the user's selected list with model recommendations.
5. Download one model at a time. For each model, wait for completion, confirm it appears in `/api/tags`, load it, run a simple role-relevant test, unload it, save results, and notify the user through the authorized WhatsApp integration if it is actually configured and a recipient is confirmed.
6. Record a separate success/failure report for every model. Never claim WhatsApp delivery without tool confirmation.

## Agent roles

- Moncappy Time: Hermes Core; Executive Coordinator.
- Dolly: Human Relations and Organizational Culture.
- Robin: Creative Director and Innovation.
- Betty: Quality Assurance and Institutional Knowledge.
- Richard Feynman: Scientific Research and Experimental Engineering.
- Alan Watts: Philosophy and Systems Thinking.
- Fulton J. Sheen: Ethics, Governance, and Moral Reasoning.

Agent identities remain independent of model configuration. Do not permanently assign models without the user's approval.

## Evidence and boundaries

- The local model assignment matrix on branch `codex/founding-agent-identities` states that no founding agent has a model assignment and that candidate context targets are not claims about installed model capabilities.
- The engineering registry policy sets a 100 GB maximum complete local deployment budget and prefers MoE where suitable; this is a deployment ceiling, not a required model list.
- Preserve the existing repository work, branches, untracked files, and open pull requests. This document does not authorize merging existing PRs or changing agent permissions.
