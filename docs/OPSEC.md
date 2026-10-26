# Public Repository OPSEC

This repository is public. Commands should remain useful and executable without exposing personal or infrastructure-specific secrets.

## Never commit
- Passwords, API tokens, credentials, OAuth tokens, Tailscale auth/node keys or session cookies
- Stream keys or private streaming URLs
- Private IP/VLAN maps, tailnet addresses or internal DNS names
- MAC addresses, serial numbers, unique device IDs, personal usernames or account emails
- Unredacted logs, private screenshots or full configuration exports

## Command-writing standard
Prefer environment/system paths over hard-coded personal paths:

```bash
printf 'Home: %s\n' "$HOME"
printf 'Config: %s\n' "${XDG_CONFIG_HOME:-$HOME/.config}"
printf 'Data: %s\n' "${XDG_DATA_HOME:-$HOME/.local/share}"
```

For machine-specific values, declare an explicit placeholder and explain how to replace it:

```bash
INTERFACE="REPLACE_WITH_INTERFACE_NAME"
```

Label commands containing placeholders clearly. Do not use values that could accidentally be valid secrets.

## Before every public commit
- [ ] Search staged changes for token/password/secret/authkey/streamkey and private addresses.
- [ ] Review screenshots and terminal output.
- [ ] Remove serial numbers and MAC addresses.
- [ ] Ensure private files, environment files and model caches are not staged.
- [ ] Review `.gitignore`.
- [ ] Never commit a secret expecting to remove it later.

Keep raw logs locally if needed; publish only the minimum sanitized lines required to support a conclusion.
## Automated local preflight

Run a review against the proposed diff before publishing. Treat scanner output as sensitive and keep it local; false positives still require manual review.

Example checks from the repository root:

```bash
git status --short
git diff --check
git diff -- . ':!*.svg'
```

For an initial credential-pattern sweep of changed text files, use a trusted local secret scanner (for example, Gitleaks) and review findings manually. Do not paste raw scanner output or full logs into public issues. A clean working-tree scan does not prove old Git history is clean; if a real secret was committed, revoke/rotate it first and separately assess history remediation.
