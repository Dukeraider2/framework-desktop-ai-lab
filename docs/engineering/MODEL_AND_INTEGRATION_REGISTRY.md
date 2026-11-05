# Model and Integration Registry Governance

**Status:** Proposed standard, pending repository-owner review. This document defines registry behavior; it does not mean any model or provider has been installed, connected, enabled, or validated.

## 1. Purpose

Maintain a version-controlled catalog that lets Hermes select from known model candidates while keeping model knowledge separate from actual runtime availability and provider connectivity.

The registries answer two different questions:

- **Model registry:** What models are known, what are they suited for, and where could they run?
- **Integration registry:** Which runtimes and providers have been configured, tested, and explicitly enabled for Hermes to use?

A model appearing in the catalog does not make it callable. A provider appearing in the integration catalog does not authorize account creation, credential entry, installation, or network connection.

## 2. Operating principles

1. **Local-first:** Prefer downloadable, locally executable open-weight models where practical. Local operation should remain the default foundation.
2. **Hosted supplementary:** Hosted inference may supplement local models, but must not become an unannounced dependency.
3. **No implicit paid usage:** Paid APIs, subscriptions, metered services, or services that may incur charges remain disabled unless the user explicitly authorizes the specific provider, account, and intended use.
4. **Free does not mean enabled:** A free hosted tier may have quotas, changing terms, data-use conditions, or upgrade paths. It remains unavailable until the user declares its setup ready and the integration is tested and enabled.
5. **User-controlled activation:** Hermes must not connect to, register for, configure credentials for, or invoke a provider merely because it is catalogued or marked as a candidate.
6. **Evidence-based metadata:** Distinguish verified facts, provider claims, estimates, and unknowns. Record the exact model identifier/checkpoint and source.
7. **Reversible changes:** Installation, model downloads, configuration changes, and provider integrations must have documented scope, storage impact, and rollback where applicable.
8. **Secrets stay out of Git:** Never commit API keys, tokens, passwords, private endpoints, or credential-bearing configuration. Store secrets only in an approved secret/configuration mechanism with least-privilege access.
9. **No self-approval:** An agent may propose or update catalog metadata, but it cannot independently approve its own integration or promote its own work to production-enabled status.
10. **Catalog first, evaluate progressively:** Candidate breadth is useful. Do not require exhaustive benchmarking before listing a candidate. Record uncertainty and improve entries as models are actually used.

## 3. Local deployment constraints and preferences

The current user-defined policy is:

- **Hard ceiling:** 100 GB maximum memory budget for one local model deployment.
- Count the complete deployment footprint, not only the model file or active parameters: resident weights, runtime allocations, context/KV cache, offloaded portions, and relevant overhead must fit within the deployment budget.
- **MoE is preferred**, not mandatory. Record total parameters and active parameters when authoritative sources provide them.
- Quantization is allowed and encouraged where a supported checkpoint/runtime exists.
- CPU/GPU offloading is allowed, subject to measured compatibility and performance.
- Do not infer total memory requirements from active parameter count. MoE routing reduces per-token computation but does not necessarily remove inactive expert weights from memory.
- ROCm/AMD compatibility must be verified for the exact checkpoint, quantization format, runtime, and hardware. NVIDIA-specific formats or kernels must not be presumed compatible with AMD.
- Hosted candidates are not subject to the local 100 GB limit, but must be labelled hosted and governed by provider cost, privacy, availability, and authorization rules.

These constraints are user-defined selection policy, not claims that any specific model has been tested on the Framework Desktop.

## 4. Model lifecycle statuses

Use one status per model deployment record. Status applies to a specific checkpoint and deployment configuration, not merely a model family.

| Status | Meaning | May Hermes select it? |
|---|---|---|
| Catalogued | Identified and recorded; evidence may be incomplete | No |
| Candidate | Considered for one or more task categories | No |
| Approved candidate | User accepts it for possible evaluation/acquisition | No |
| Installed | Exact local weights are present in a known runtime | Not by status alone |
| Qualified | Passed documented task-specific checks in a specified configuration | Only if deployment is also enabled |
| Preferred | Recommended for specified tasks based on recorded evidence | Only if deployment is also enabled |
| Restricted | Available only under explicit conditions or per-task authorization | Only within those conditions |
| Disabled | Deliberately unavailable for routing | No |
| Retired | Removed from active consideration; retained for history | No |

A model can be qualified for one task category and remain only a candidate for another. Record qualifications at the task/category level.

## 5. Integration lifecycle statuses

Integration status is independent of model status.

| Status | Meaning | May Hermes connect or invoke it? |
|---|---|---|
| Catalogued | Provider/runtime is documented as an option | No |
| Approved candidate | Provider is acceptable for possible setup | No |
| Pending setup | Awaiting user-directed setup, credentials, or configuration | No |
| Configured | Credentials/configuration have been supplied through the approved secure process | No |
| Ready | Connection and required health checks have succeeded; user has declared setup ready | Not until enabled |
| Enabled | User-authorized integration is available to Hermes under its defined scope | Yes, within scope |
| Disabled | Integration is unavailable to Hermes | No |
| Restricted | Available only under explicit scope, limits, or authorization | Only within those conditions |
| Retired | No longer available; retained for history | No |

**Required activation gate:** Hermes may use a provider only when its integration record is marked **Enabled**, the relevant model deployment is available, and the requested operation is within the integration's approved scope. Cataloguing, approval as a candidate, configuration, or a successful test alone does not grant permission to invoke it.

The user explicitly decides when an integration is ready for activation. A successful technical test is necessary but does not replace that authorization.

## 6. Initial hosted-provider candidates

The following providers are recorded as **approved candidates for possible setup**, not as configured, ready, or enabled integrations:

| Provider | Intended use | Current status | Activation condition |
|---|---|---|---|
| OpenRouter | Unified access to selectable hosted models, including eligible free endpoints | Approved candidate; pending setup | User-directed setup, policy/price review, connection test, then explicit enablement |
| Groq | Hosted inference for models offered under its current free tier | Approved candidate; pending setup | Verify current model availability, quotas, data terms, and user-directed setup |
| Google AI Studio | Gemini API experimentation under current free-tier terms | Approved candidate; pending setup | Review current data-use terms, quotas, model access, and user-directed setup |
| Mistral AI | Hosted inference/experimentation where a free tier is currently offered | Approved candidate; pending setup | Verify current plan, model access, quotas, and user-directed setup |
| Cloudflare Workers AI | Hosted inference under current account/free allocation terms | Approved candidate; pending setup | Verify current allocation, billing behavior, data terms, and user-directed setup |
| SambaNova | Hosted inference where a free allocation is currently offered | Approved candidate; pending setup | Verify current access, quotas, model availability, and user-directed setup |

Free-tier availability, quotas, supported models, and terms can change. These entries do not guarantee that a provider currently offers unlimited or permanently free inference. Check current official provider documentation at implementation time. Do not silently fall back to a paid endpoint or paid tier if a free quota is exhausted.

## 7. Model registry record

Each model entry should capture as many of these fields as are known. Unknown values must be marked unknown rather than guessed.

| Field | Description |
|---|---|
| Registry ID | Stable internal identifier |
| Display name / model family | Human-readable name |
| Exact model ID | Provider/repository/checkpoint identifier |
| Developer / publisher | Model publisher |
| Source URL | Official model card or repository |
| License | Exact license and relevant use restrictions |
| Lifecycle status | Status from Section 4 |
| Task categories | Software development, technical analysis, engineering specialties, scientific research, general research, etc. |
| Capabilities | Coding, reasoning, vision, tool calling, long context, structured output, and other evidenced capabilities |
| Architecture | Dense, MoE, hybrid, or other; cite the source |
| Total / active parameters | Record separately when published |
| Context window | Exact documented limit and any runtime constraints |
| Quantizations | Exact available formats/checkpoints; do not infer availability |
| Weight size | Checkpoint size for the exact quantization |
| Deployment target | Local runtime/provider and exact version, or hosted provider |
| Hardware/runtime compatibility | Verified, reported, unverified, or incompatible |
| Memory budget | Measured deployment footprint where available; otherwise estimate with assumptions |
| Data/privacy notes | Local processing or provider data handling and retention notes |
| Cost class | Local/no per-request provider charge, free-tier with limits, metered, subscription, or unknown |
| Evaluation notes | Tasks tried, results, date, and evidence |
| Preferred use / limitations | Evidence-backed routing guidance |
| Last verified | Date and person/agent that checked the record |

## 8. Integration registry record

Each provider/runtime integration should have a separate record containing:

- Stable integration ID and provider/runtime name.
- Integration status from Section 5.
- Supported model IDs and endpoints.
- Authentication method, with secret values stored elsewhere.
- Credential reference (name/path/secret-store identifier only; never the credential itself).
- Approved data classification and permitted task categories.
- Current free-tier limits or billing mode, with source and verification date.
- Whether use can incur charges and the required approval boundary.
- Network destinations and required outbound access.
- Health-check procedure and last observed result.
- Rate limits, timeouts, concurrency, and fallback behavior.
- Data retention/training terms and privacy review.
- User authorization record, scope, and date.
- Disable/rollback procedure and owner.

## 9. Hermes model-selection procedure

For each task:

1. Classify the task and required capabilities.
2. Consult the model registry for candidates assigned to that task.
3. Exclude models that are disabled, retired, incompatible, or outside the applicable authorization.
4. For local candidates, check the complete deployment memory budget against the 100 GB ceiling and verify the exact runtime/quantization/hardware combination.
5. For hosted candidates, confirm that the integration is **Enabled**, the exact model is available through it, the task is within scope, and the request will not trigger unapproved charges.
6. Prefer qualified/preferred models when evidence exists. Otherwise, choose among eligible candidates only if their status and authorization permit use; request user direction when acquisition or activation is needed.
7. Do not silently download/install a new model, create an account, enter credentials, enable a provider, or switch to paid service. Model acquisition and provider activation follow their separately authorized workflows.
8. Record the selected model/deployment, task category, relevant configuration, and outcome where practical.
9. If no eligible model is available, explain the gap and ask for authorization or use an already enabled alternative.

## 10. Model acquisition and provider activation boundaries

- A catalog entry is not permission to download weights or install software.
- A model marked approved candidate may be evaluated for acquisition, but any acquisition authority must be separately and explicitly defined.
- A provider marked approved candidate or pending setup cannot be contacted by Hermes.
- Credentials are entered only through the user-directed secure setup path; never solicit or store secrets in Markdown or Git.
- Do not accept provider terms, create paid resources, enable billing, upgrade plans, or incur charges without explicit user authorization.
- Free-to-paid fallback is prohibited unless explicitly authorized.
- Enabling an integration requires successful configuration/health checks and the user's explicit direction.
- Disabling an integration must immediately remove it from routing eligibility without deleting its historical record.

## 11. Maintenance and audit

- Keep registry changes in Git branches and pull requests under the repository's engineering change-control process.
- Record source URLs, exact model IDs, checkpoint revisions, retrieval/verification dates, licenses, and relevant terms.
- Mark stale or changed provider terms for re-verification.
- Never describe a candidate as installed, tested, qualified, preferred, or enabled without evidence.
- Preserve historical records when entries are disabled or retired.
- Update the registry when a model, checkpoint, quantization, runtime, provider plan, or authorization changes.
- Keep credentials, private endpoints, personal data, and sensitive project content out of registry files.

## 12. Initial user-defined selection policy

The following decisions are established for the catalog:

- Local-first and open-weight models are preferred.
- MoE architectures are preferred, not mandatory.
- Quantization and CPU/GPU offloading are permitted.
- The local deployment ceiling is 100 GB, including complete inference overhead.
- Hosted free-tier providers may be catalogued as approved candidates.
- Paid hosted inference is disabled by default and requires explicit authorization.
- Hosted providers listed in this document are not configured, ready, or enabled.
- Hermes may select only deployments and integrations that have passed the required lifecycle and authorization gates.
- Candidate lists are allowed to grow and change as work proceeds; benchmarking can occur progressively rather than blocking catalog inclusion.
