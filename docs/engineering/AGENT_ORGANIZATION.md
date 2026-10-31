# Agent Organization and Responsibilities

**Status:** Role architecture approved for planning. Product selection, installation, and integration remain to be validated.

## Executive and management

- **User:** Owner and final decision-maker; resolves escalated access risks and approves production-impacting actions.
- **Quill / ChatGPT:** Technical director and planning partner for requirements, architecture, and review direction. It is not assumed to have direct access to the local host.
- **Hermes:** Proposed project and operations manager. Receives tasks, decomposes work, assigns agents, coordinates dependencies, manages access requests, tracks progress and time, and escalates unresolved risks.

## Specialist capabilities

The organization is capability-based. A role may be implemented by a dedicated agent, a specialized agent profile, or a tool controlled by an agent. Not every role requires a separate always-running process.

### Engineering
- Systems and infrastructure engineering.
- Application and API development.
- Feature and service integration.
- Game development and engine tooling.
- Authorized reverse engineering and systems analysis.
- Build and release engineering.

### Quality, security, and reliability
- Independent code and architecture review.
- QA, test execution, and regression testing.
- Security and dependency auditing.
- Performance and resource-efficiency analysis.
- Documentation and reference verification.

### Creative production
- Image generation and visual assets.
- 3D and game-asset production.
- AI video and short-form video generation.
- Scriptwriting, editing, audio, and post-production.
- Content production, packaging, and publishing preparation.
- Social-media planning, scheduling, analytics, and community operations.

### Research and knowledge
- Technical and product research.
- Hardware compatibility research.
- Manufacturer-documentation curation.
- Model evaluation and benchmarking.
- Knowledge-base maintenance.

## Candidate software, not final selections

OpenCode, OpenHands, Aider, Hermes, Ollama, ComfyUI, Ghidra, Blender, FFmpeg, n8n, and other tools are candidates or components discussed for evaluation. Listing a product does not mean it is installed, approved for every use, or integrated.

## Separation of duties

- Implementers must not approve their own work.
- Review and QA must be independent of implementation.
- Hermes coordinates reviews but does not substitute for independent technical review.
- Security-sensitive and production-impacting actions require applicable approval.
- Agent capabilities and permissions must be explicit and auditable.

## Resource-aware scheduling

Hermes should consult current resource telemetry before dispatching resource-intensive work. GPU inference, image/video generation, builds, and parallel agents must be scheduled against available CPU, RAM, GPU/VRAM, storage, and system responsiveness. Missing or stale telemetry must not be treated as available capacity.
