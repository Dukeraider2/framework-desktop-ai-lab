# Engineering Model Catalog and Acquisition Baseline

**Catalog version:** 1.0  
**Source decision date:** November 2026  
**Repository record updated:** 2026-11-03  
**Status:** Candidate catalog; no model is qualified or production-approved by virtue of appearing here.

> **Purpose:** Preserve the user's model-selection decisions in Git so that future assistant sessions and Hermes workflows do not depend on conversational memory. This catalog is the durable reference. When a decision changes, update this file and commit the change.

## 1. Governing decisions

The user explicitly prioritized building a broad model catalog for Hermes to choose from over completing all benchmarks before the catalog exists. Models are to be tested progressively as they are acquired. Do not reduce the catalog to the original five-model shortlist.

### Deployment and selection policy

| Parameter | Decision |
|---|---|
| Maximum complete local inference deployment | 100 GB |
| Preferred architecture | Mixture of Experts (MoE) |
| Activation profile | Prefer lower active parameter count relative to total parameters |
| Quantization | Q2 through Q8 where available |
| CPU/GPU offloading | Permitted |
| Local weights | Required for the local candidate catalog |
| Hosted models | Permitted as supplementary candidates; clearly distinguish from local deployments |
| ROCm | Compatibility must be verified for the exact checkpoint, quantization, runtime, and kernels |
| Acquisition | Hermes may download approved models |
| Evaluation | Required before qualification or production approval |
| Technical verification | Independent review required |

The 100 GB ceiling applies to the complete local deployment: model weights, runtime, context/KV cache, and overhead. A low active-parameter count does not make a model with enormous total weights fit in memory. DeepSeek-R1 and DeepSeek-V3 at 671B are therefore hosted candidates under this ceiling unless a genuinely viable deployment configuration is demonstrated.

Do not assume NVIDIA-specific formats such as NVFP4 work on AMD ROCm. Verify rather than infer compatibility.

## 2. Initial cross-disciplinary engineering shortlist

These five models were explicitly accepted into the Engineering Expert Candidate Pool:

| Priority | Model | Architecture | Published total / active parameters in source notes | Primary interest |
|---:|---|---|---|---|
| 1 | DeepSeek-R1 | MoE lineage | 671B base lineage / 37B base lineage | Complex engineering reasoning |
| 2 | Qwen3-235B-A22B | MoE | 235B / 22B | Mathematics and technical reasoning |
| 3 | NVIDIA Nemotron 3 Super | Hybrid MoE | 120B / approximately 12B | Technical reasoning and systems analysis |
| 4 | GPT-OSS 120B | MoE | 117B / 5.1B | Scientific reasoning and technical analysis |
| 5 | DeepSeek-V3 | MoE | 671B / 37B | Broad technical reasoning |

These are initial candidates, not verified downloadable checkpoints. Confirm exact model versions, parameter counts, licenses, quantizations, and deployment feasibility before acquisition.

**Deployment distinction:** DeepSeek-R1 and DeepSeek-V3 remain in the catalog, but are hosted candidates under the current 100 GB local ceiling. Qwen3-235B-A22B is hosted/experimental and memory-intensive. Do not treat all five as routine local downloads.

## 3. Consolidated engineering candidate catalog

The catalog is intentionally broader than the initial five. The categories below preserve the November 2026 selection notes and their preliminary classifications.

| Model | Architecture | Intended engineering use | Initial deployment classification |
|---|---|---|---|
| DeepSeek-R1 | MoE lineage | Complex electrochemical, electrical, mechanical, and systems reasoning | Hosted |
| DeepSeek-V3 | MoE | Cross-disciplinary engineering and systems analysis | Hosted |
| Qwen3-235B-A22B | MoE | Mathematical and scientific reasoning | Hosted / experimental |
| NVIDIA Nemotron 3 Super 120B | Hybrid MoE | Technical reasoning, mechanical analysis, systems analysis, agent coordination | Local evaluation; verify quantization and ROCm |
| NVIDIA Nemotron 3 Nano 30B | Hybrid MoE | Efficient engineering subagent and technical reasoning | High-priority local evaluation |
| GPT-OSS 120B | MoE | Scientific reasoning, engineering calculations, requirements and architecture analysis | Local evaluation; verify quantization and runtime |
| Qwen3-32B | Dense | Cell characterization, technical calculations, mechanical design reasoning | Local evaluation |
| Qwen3-Coder-Next | MoE | Embedded development, CAD scripting, automation, system implementation and integration | High-priority local evaluation |
| DeepSeek-Coder-V2-Lite | MoE | Firmware, embedded programming, engineering software | Local evaluation |
| Qwen3-30B-A3B | MoE | General technical specialist | Investigate |
| GLM-5 | MoE | Complex reasoning | Investigate |
| DeepSeek-V2-Lite | MoE | Lightweight analytical and engineering-software specialist | Local evaluation |
| Mixtral 8x22B | MoE | General engineering reasoning | Investigate |

The names above are catalog labels, not guaranteed exact Ollama tags. Before pulling, identify and verify the exact official checkpoint and distribution tag. Do not silently substitute a similarly named model.

### Preliminary consolidated pool and local priority

| Model | Disciplines | MoE | Initial local priority |
|---|---|---:|---|
| Nemotron 3 Nano | All four | Yes | High |
| Nemotron 3 Super | All four | Yes | High |
| GPT-OSS 120B | All four | Yes | High |
| Qwen3-235B-A22B | All four | Yes | Medium; experimental |
| DeepSeek-R1 | All four | Yes / lineage | Hosted |
| DeepSeek-V3 | All four | Yes | Hosted |
| Qwen3-32B | All four | No | Medium |
| Qwen3-Coder-Next | Electrical, mechanical, systems | Yes | High |
| DeepSeek-Coder-V2-Lite | Electrical, battery, systems | Yes | Medium |

These are candidate associations, not demonstrated expertise or qualification.

## 4. Specialty coverage

### Electrical engineering
Evaluate:
- DeepSeek-R1, Qwen3-235B-A22B, Nemotron 3 Super
- GPT-OSS 120B
- Qwen3-Coder-Next
- DeepSeek-Coder-V2-Lite

Test circuit analysis, analog/digital electronics, power electronics, PCB design, signal integrity, microcontroller architecture, component selection, electrical safety calculations, and interpretation of actual circuit diagrams/schematics.

### Battery engineering
Evaluate:
- DeepSeek-R1, Qwen3-235B-A22B, Nemotron 3 Super
- GPT-OSS 120B
- Qwen3-32B
- DeepSeek-V2-Lite

Test cell chemistry and characterization, SOC/SOH estimation, BMS design, thermal management, cell abuse testing, pack architecture, current distribution, failure analysis, and UN 38.3 testing concepts. Emphasize numerical accuracy and identification of unsafe assumptions.

### Mechanical engineering
Evaluate:
- Nemotron 3 Super, GPT-OSS 120B, Qwen3-235B-A22B, DeepSeek-R1
- Qwen3-32B
- Qwen3-Coder-Next

Test structural analysis, material selection, tolerances, heat transfer, fluid dynamics, mechanical assemblies, manufacturing processes, CAD automation, and finite-element analysis. Validate actual mechanics and geometry, not merely explanatory fluency.

### Systems engineering
Evaluate:
- Nemotron 3 Super, GPT-OSS 120B, Qwen3-235B-A22B
- DeepSeek-R1, DeepSeek-V3
- Qwen3-Coder-Next

Test requirements development, interface definition, architecture, FMEA, fault-tree analysis, reliability, verification and validation, configuration management, system integration, and technical risk management.

A shared model may serve multiple specialties only after passing the corresponding specialty tests. Language models can help formulate engineering problems; validated engineering software must perform authoritative numerical simulation where required.

## 5. Evaluation protocol

Each model should be tested against repeatable problems in the four specialties. Record:
- Accuracy and independently verifiable conclusions
- Reasoning quality and explicit assumptions
- Ability to identify missing data and unsafe assumptions
- Response latency and throughput
- CPU, RAM, GPU/unified-memory utilization
- Model load time, context behavior, stability, and errors
- Exact checkpoint, quantization, runtime, and relevant kernel/backend versions

Do not confuse explaining an engineering concept with solving an engineering problem. For example, explaining battery thermal runaway is not equivalent to correctly calculating a thermal design, identifying assumptions, and rejecting an unsafe result.

## 6. Candidate lifecycle

Use these statuses consistently:

| Status | Meaning |
|---|---|
| Candidate | Listed for Hermes to consider; not necessarily installed or tested |
| Installed | Downloaded and available locally; verify from host inventory |
| Qualified | Passed documented tests for a particular task or specialty |
| Preferred | Recommended for that task based on comparative evidence |
| Restricted | Available only with additional authorization |
| Retired | Removed from active selection |

A candidate may be hosted-only or experimental. Keep deployment mode visible; do not imply that every candidate is locally deployable.

## 7. Acquisition and notification workflow

1. Read this catalog before proposing or downloading models.
2. Query the Ubuntu host Ollama API at `http://127.0.0.1:11434/api/tags` from the host execution context. Do not infer host inventory from a restricted container or sandbox.
3. Save a timestamped inventory and distinguish already-installed models from acquisition candidates.
4. Verify the exact checkpoint/tag, license, quantization, total size, memory requirements, and ROCm/runtime compatibility.
5. Acquire one model at a time. Do not run concurrent large downloads or loads.
6. After each download, verify host inventory, load and test the model, unload it, record results, and release resources before proceeding.
7. Mon Capitán creates a simple role-relevant test for each model.
8. Send an individual WhatsApp report after each model only through a configured, authorized integration and confirmed recipient. Never claim delivery without connector confirmation. If unavailable, save the report and record the notification as blocked.
9. Do not automatically delete models or permanently assign a model to an agent without user approval.

## 8. Agent roles for role-relevant testing

- Moncappy Time: Hermes Core; Executive Coordinator.
- Dolly: Human Relations and Organizational Culture.
- Robin: Creative Director and Innovation.
- Betty: Quality Assurance and Institutional Knowledge.
- Richard Feynman: Scientific Research and Experimental Engineering.
- Alan Watts: Philosophy and Systems Thinking.
- Fulton J. Sheen: Ethics, Governance, and Moral Reasoning.

Agent identities remain independent of model configuration. This engineering catalog does not establish permanent model-to-agent assignments.

## 9. Previously observed host inventory (historical)

The following five Ollama tags were reported by a successful host-side inventory during the November 2, 2026 troubleshooting session. They are historical observations and must be rechecked against the host API before use:

| Exact Ollama tag | Historical status |
|---|---|
| `qwen3-coder:30b` | Previously reported installed |
| `mannix/deepseek-coder-v2-lite-instruct:latest` | Previously reported installed |
| `deepseek-coder:1.3b` | Previously reported installed |
| `deepseek-coder:latest` | Previously reported installed |
| `qwen3:8b` | Previously reported installed |

This inventory is not the acquisition catalog. Do not confuse installed models with the broader candidate pool.

## 10. Durable decision and change-control rules

- This file is the durable source of truth for the engineering model catalog and the decisions recorded here.
- Conversation memory is not an authoritative record. If a user decision is made in chat, update this file (or a linked decision record) and commit it to Git.
- Preserve source distinctions: user-approved candidates, research suggestions, installed inventory, verified technical facts, and assistant recommendations must not be conflated.
- Do not remove a candidate because it is too large for local deployment; mark it hosted-only or experimental as appropriate.
- Do not add a new candidate as user-approved without explicit user agreement. Suggestions must be marked as suggestions.
- Record material changes with date, rationale, and source. Do not overwrite historical decisions silently.
- Do not merge pull requests, alter permissions, or change agent authority without explicit authorization.

## 11. Source provenance

This catalog is reconstructed from the user's November 3, 2026 uploaded selection notes, titled `Pasted text(20261103-055349).txt`, including:
- Initial five-model shortlist and explicit acceptance into the Engineering Expert Candidate Pool.
- Deployment constraints and memory feasibility distinctions.
- Four engineering specialty matrices and evaluation requirements.
- Additional candidates and consolidated engineering pool.
- User's explicit direction to prioritize a broad Hermes selection catalog and test progressively.
- The candidate lifecycle statuses.

Where the source notes describe architecture or parameter counts as published specifications, those figures remain provisional until checked against the exact checkpoint. No outside research or hardware benchmark is implied by this document.
