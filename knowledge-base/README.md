# Laboratory Knowledge Base

The knowledge base is organized around both **hardware/equipment** and **projects**. GitHub is the versioned source of truth for curated knowledge, references, integration records, and decisions.

## Knowledge categories

- **Hardware and equipment:** One dedicated page per physical device or significant component, including its integration into the lab.
- **Projects:** Project-specific requirements, architecture, decisions, implementation notes, validation, and known limitations.
- **Manufacturer documentation:** Manuals, datasheets, firmware notes, official compatibility matrices, and vendor technical documentation.
- **Engineering standards:** Approved constitution, security, deployment, testing, and performance standards.
- **Research and reference materials:** Additional technical sources, experiments, compatibility findings, and verified research.
- **Temporary task context:** Task-specific notes and attachments linked from GitHub Issues or Pull Requests. Promote durable findings into the relevant knowledge location.
- **Agent operational memory:** Non-secret, task-relevant operational notes. This is not a substitute for versioned project facts or authoritative references.

## Suggested layout

- hardware/<category>/<manufacturer>-<model>/
- projects/<project-name>/
- manufacturer-documentation/<manufacturer>/<product-family>/
- engineering-standards/
- research/
- agent-memory/

Each hardware page must include an integration section describing how the device connects to and is used by the lab. Each project page links to relevant equipment pages and references.

## Agent contributions

Agents are encouraged to add useful source material to the appropriate location. Every contribution must identify source and provenance, applicability, version/revision, publication date when available, retrieval date, and the claim or decision it supports.

Mark new contributions as **Proposed / Unverified** until an independent agent or qualified reviewer verifies source authenticity, technical accuracy, revision, and applicability. Only then may it be marked **Verified**. Keep disagreements and limitations visible.

Prefer official manufacturer documentation for hardware specifications and compatibility. Third-party material may supplement it but must be clearly identified. Respect copyright and license terms: do not commit manuals or other documents unless redistribution is permitted. Link to the official source and preserve metadata when redistribution is not allowed.

## Safety and OPSEC

Never commit passwords, API tokens, private keys, device keys, private network maps, sensitive identifiers, or unredacted logs. Redact sensitive information before adding evidence. Avoid storing large generated assets, model weights, caches, or binaries in Git unless a project explicitly requires and licenses them.

## Templates

- [Equipment page template](hardware/_templates/equipment-page.md)
