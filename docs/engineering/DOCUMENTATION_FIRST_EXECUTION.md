# Documentation-First Technical Execution Standard

**Status:** Proposed for adoption through pull request.  
**Applies to:** Quill-assisted work, Hermes tasks, human operators, agents, scripts, services, hardware integrations, and operational procedures in this lab.

## Purpose

Prevent guessed commands, invented configuration keys, incorrect package names, unsupported assumptions, and avoidable system damage. Technical actions must be grounded in evidence applicable to the actual target system and version.

**Rule: Build from evidence. Execute verified procedures. Preserve what we learn.**

## 1. Trigger: treat unfamiliar work as a new integration

Apply this standard whenever introducing or materially changing software, packages, services, APIs, hardware, drivers, firmware, container images, integrations, or deployment procedures.

Before proposing an installation or state-changing command:

1. Identify the exact product, component, release/version, and intended task.
2. Identify the actual host OS/release, architecture, relevant hardware, runtime, and existing service state.
3. Locate the official documentation for that exact product and version.
4. Read the official installation or upgrade guide and relevant configuration/API references.
5. Inspect the installed tool's own help output and version output where available.
6. Check release notes, compatibility matrices, known breaking changes, and prerequisites.
7. Record source URLs, document/release versions, and retrieval date.

Use official vendor/project documentation first. Use source code, official repositories, and maintainer-published references when the documentation is incomplete. Community posts may provide leads, but must not be the sole authority for risky commands or security-sensitive configuration.

If authoritative documentation is unavailable or ambiguous, state exactly what is unknown and perform read-only discovery. Do not fill the gap by inventing plausible syntax.

## 2. Command verification requirements

Every command provided for execution must be classified:

- **Verified:** Syntax and behavior are supported by the applicable official documentation, installed command help, or an inspected authoritative source.
- **Observed:** The exact command was previously executed successfully in this environment and its output was retained. Re-check version and context before reuse.
- **Proposed/unverified:** Not yet confirmed. Do not present it as ready to execute. Prefer further research or a read-only test.

Before issuing a command, verify:

- Executable and subcommand names exist in the target version.
- Flags, positional arguments, quoting, paths, and configuration keys are valid.
- Required privileges and execution context are understood.
- Expected side effects and affected resources are identified.
- The command is appropriate for the actual OS, hardware, service version, and runtime.

Never infer CLI syntax from another product, an older release, naming conventions, or what a command "should" look like. Do not fabricate package names, service names, API routes, configuration keys, or file paths.

When useful, consult the program's own help output (for example, its documented `--help` or help subcommand), but verify the correct help invocation rather than assuming it.

## 3. Risk classification and execution

### Read-only discovery

Examples include version checks, help output, status queries, listing resources, and reading configuration. Prefer these first. Redact secrets and identifying information before sharing or committing output.

### Reversible or limited changes

Examples include creating a dedicated configuration file or starting a test container. Document the expected change, backup/rollback method, and validation before execution.

### High-impact or destructive changes

Examples include disk/partition operations, filesystem formatting, driver replacement, firewall/network changes, credential rotation, production deployment, data deletion, bulk updates, and commands that can interrupt existing services.

For these actions:
- Explain the exact target and expected impact.
- Confirm backups and a tested or credible rollback path.
- Inspect the target identity and current state immediately before acting.
- Require explicit user approval when the action is destructive, irreversible, security-sensitive, financially consequential, or production-impacting.
- Never bundle unrelated high-impact operations into one opaque command.

Do not change or restart unrelated working services. Do not recreate, remove, or migrate existing containers or data unless the task explicitly requires it and approval has been obtained.

## 4. Interactive execution loop

Use this sequence for hands-on technical work:

1. **Objective:** State the immediate outcome.
2. **Evidence:** Cite the official documentation/help/version evidence used.
3. **Preflight:** Inspect relevant current state using verified read-only commands.
4. **Action:** Provide one copy-and-paste command at a time, with a concise explanation of its effects.
5. **Observe:** Wait for the actual output.
6. **Evaluate:** Compare the output with the expected result; diagnose from evidence.
7. **Next action:** Only then provide the next command.
8. **Validate:** Run the documented health check or acceptance test.
9. **Record:** Save the exact successful procedure, versions, output summary, and rollback notes.

Do not send a long chain of commands that assumes every preceding command succeeded. Use multiple commands in one block only when they are read-only, independently safe, and their combined behavior is clear.

If output differs from expectations, stop the planned sequence. Do not improvise a corrective command. Re-check help, logs, documentation, and system state, then choose the next evidence-supported action.

## 5. Versioned technical knowledge records

For each service or integration, maintain a record in the repository:

- Product/service name and purpose.
- Tested version and target platform.
- Hardware/runtime prerequisites and compatibility evidence.
- Official documentation and release-note links.
- Retrieval date and applicable documentation version.
- Exact commands that were actually executed.
- Configuration file locations and sanitized examples.
- Expected output and observed result.
- Health checks and acceptance tests.
- Known limitations and unresolved issues.
- Backup, rollback, and recovery procedure.
- Last verification date and verification environment.

Separate **proposed**, **tested**, **verified**, and **deprecated** procedures. Never promote an untested suggestion into a verified runbook. If the exact historical command was not retained, say so; do not reconstruct it from memory.

Do not commit credentials, tokens, private keys, recovery material, personal identifiers, private network maps, raw unredacted logs, or proprietary files. Use placeholders for secrets and document where an authorized operator supplies them.

## 6. Reuse and retrieval

Before repeating work, search the repository's versioned knowledge base and relevant service records. Confirm that the documented version and platform still match the current environment. If they do not match, re-verify against current official sources before execution.

When new information is learned:
- Update the relevant service record or procedure.
- Include source references and verification date.
- Record the tested command and a sanitized result.
- Explain any change from the previous procedure.
- Submit governance changes through the repository's branch and pull-request process.

Git is the durable source of truth. Conversation memory is not a substitute for versioned technical records.

## 7. Agent behavior requirements

Quill, Hermes, and specialist agents must:

- Prefer verified facts over plausible inference.
- Clearly label uncertainty and distinguish evidence from recommendation.
- Never claim a command, installation, test, or configuration is verified unless evidence exists.
- Never invent command syntax to keep the workflow moving.
- Ask for or collect the minimum missing read-only evidence needed.
- Preserve working configurations and avoid scope creep.
- Record decisions and reproducible results in the appropriate project documentation.
- Escalate high-impact decisions for human approval.

Decisiveness means selecting the best evidence-supported action and moving forward. It does not mean guessing.

## 8. Definition of done for a new integration

An integration is not complete merely because installation succeeded. At minimum, its record must contain:

- Applicable official documentation and compatibility evidence.
- Exact installed version and environment.
- Verified installation/configuration procedure.
- A successful health check or functional acceptance test.
- Sanitized evidence of the observed result.
- Known limitations and recovery/rollback notes.
- A clear status: proposed, installed, tested, verified, or blocked.

## 9. Compact operator checklist

Before giving a command:

- [ ] Correct product and version identified.
- [ ] Actual OS, architecture, hardware, and runtime checked.
- [ ] Official documentation consulted.
- [ ] CLI help/version checked where applicable.
- [ ] Exact syntax and flags verified.
- [ ] Side effects and risk classified.
- [ ] Current state inspected.
- [ ] One command issued; output reviewed before proceeding.
- [ ] Result validated and recorded.

**Non-negotiable:** If the command cannot be verified, do not present it as executable. Research further or state the limitation.
