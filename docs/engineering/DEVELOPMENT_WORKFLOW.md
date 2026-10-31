# Three-Stage Engineering Workflow

Every significant engineering task follows three documented stages. GitHub Issues, Projects, Pull Requests, comments, reviews, and repository documentation are the primary coordination system. Do not add Jira or another project-management platform unless a demonstrated GitHub limitation prevents the workflow; evaluate a free alternative only if needed.

## Stage 1 — Task specification and reference package

**Coordinator:** Hermes, with technical direction from Quill and the user as required.

Create a GitHub issue or task package containing:
- Task identifier, purpose, scope, and expected outcome.
- Functional and non-functional requirements.
- Acceptance criteria and validation plan.
- Dependencies, constraints, risks, and out-of-scope items.
- Resource expectations and known budgets.
- Assigned agent and required capabilities.
- Core reference materials attached or explicitly linked to versioned repository documents.
- Relevant manufacturer manuals, official API documentation, approved architecture, prior implementation records, and standards.
- Estimated completion time for Stages 1, 2, and 3.

Core references must be accessible to the implementer as part of the task package. Prefer repository-controlled copies where licensing permits. For external documents that cannot be redistributed, attach a stable source link and record title, revision, publication date, retrieval date, and applicable product/version. Pin repository references to a commit or version when practical.

Stage 1 output: approved task definition and reference package. No implementation begins until scope and references are sufficiently clear.

## Stage 2 — Implementation and evidence report

**Responsible:** Assigned implementation agent.

The agent works in an isolated workspace and dedicated branch. Its report must include:
- Summary of changes and affected files/components.
- Technical rationale and concise decision summaries.
- Core references used, with links and the claims or requirements they support.
- Additional research sources, provenance, and applicability.
- Alternatives considered and why the selected approach was chosen.
- Assumptions, unresolved questions, and known limitations.
- Dependencies added, removed, or changed, including runtime/container implications.
- Tests executed, exact results, and tests not performed.
- Security and compatibility considerations.
- Resource measurements and comparison with baseline.
- Estimated and actual Stage 2 time.

Provide decision summaries, evidence, and citations rather than private internal chain-of-thought. The goal is independently auditable decisions, not disclosure of hidden internal reasoning.

## Stage 3 — Independent technical review

**Responsible:** Reviewer independent of the implementation agent.

The reviewer examines the Stage 1 package and Stage 2 report and independently verifies:
- Requirements and acceptance-criteria compliance.
- Correct use and applicability of core references.
- Accuracy and provenance of additional sources.
- Coherence of the implementation rationale.
- Whether evidence supports the stated decisions.
- Unsupported assumptions, contradictions, and missing considerations.
- Architecture, interfaces, dependencies, and maintainability.
- Security, permissions, and Podman compliance.
- Test adequacy and reproducibility.
- Resource efficiency and regressions.

The reviewer must not merely repeat the implementer's claims. It should inspect relevant code, sources, tests, and measurements. It provides findings, required corrections, and a documented score.

### Review score — 100 points

| Category | Points |
| --- | ---: |
| Specification compliance | 15 |
| Reference utilization and source verification | 10 |
| Technical reasoning and evidence coherence | 15 |
| Architectural coherence | 10 |
| Code quality and maintainability | 10 |
| Testing and verification | 10 |
| Security and dependency management | 10 |
| Resource efficiency | 20 |
| **Total** | **100** |

Suggested classification: 95–100 Excellent; 85–94 Approved; 70–84 Conditional approval with conditions resolved or explicitly accepted; 50–69 Requires revision; below 50 Rejected. Critical security failures, unsupported high-risk claims, mandatory-policy violations, or severe resource regressions can block approval regardless of score.

Stage 3 output: review report, category scores, evidence, findings, and estimated/actual Stage 3 time.

## Time reporting for every stage

Each stage records initial estimated duration, actual active work duration, waiting/blocked duration, total elapsed duration, completion timestamp, and variance from estimate with reasons for material variance. Stage 1 records estimates for all three stages. Do not fabricate precise durations when telemetry is unavailable; mark values as estimates or measurements.

## GitHub collaboration and source of truth

- GitHub Issues track tasks, questions, and blockers.
- Comments and Discussions support agent collaboration and decisions.
- Branches and Pull Requests carry implementation and review.
- Reports and evidence are attached or linked from the issue/PR.
- Git history preserves code, specifications, decisions, and approved references.
- GitHub Projects may be used for cross-task tracking.
- A separate project-management product is not introduced without demonstrated need.

## Merge and release

Reviewers do not merge their own reviews. QA results and review findings must be available before approval. The user retains final approval for production-impacting changes and releases. Deployment is separate from merge and requires its own authorization and rollback plan.
