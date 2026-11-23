#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run identity provisioning as root." >&2
  exit 1
fi
gateway_user="${HERMES_GATEWAY_USER:-}"
if [[ ! "$gateway_user" =~ ^[a-z_][a-z0-9_-]{0,31}$ || "$gateway_user" == root ]]; then
  echo "Set HERMES_GATEWAY_USER to the verified non-root Hermes gateway account." >&2
  exit 2
fi
getent passwd "$gateway_user" >/dev/null || { echo "Gateway user does not exist." >&2; exit 3; }
if command -v sudo >/dev/null 2>&1 && sudo -n -l -U "$gateway_user" 2>/dev/null | grep -qi 'may run'; then
  echo "Gateway user has sudo authorization; do not grant it provider socket groups." >&2
  exit 4
fi

groups=(hermes-inventory-client hermes-github-client hermes-egress-clients hermes-audit-clients hermes-agent-dispatch hermes-provider-runtime)
for group in "${groups[@]}"; do
  getent group "$group" >/dev/null || groupadd --system "$group"
done

ensure_service_user() {
  local user="$1" primary="$2" extra="$3"
  if getent passwd "$user" >/dev/null; then
    local record shell home
    record="$(getent passwd "$user")"
    shell="$(cut -d: -f7 <<< "$record")"
    home="$(cut -d: -f6 <<< "$record")"
    if [[ "$shell" != /usr/sbin/nologin || "$home" != /nonexistent ]]; then
      echo "Existing $user identity is not the expected non-login service account; review manually." >&2
      exit 5
    fi
  else
    useradd --system --no-user-group --gid "$primary" --groups "$extra" \
      --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin "$user"
  fi
}

ensure_service_user hermes-inventory hermes-inventory-client "hermes-audit-clients,hermes-provider-runtime"
ensure_service_user hermes-github hermes-github-client "hermes-audit-clients,hermes-egress-clients,hermes-provider-runtime"
ensure_service_user hermes-github-egress hermes-egress-clients "hermes-egress-clients,hermes-provider-runtime"
ensure_service_user hermes-audit hermes-audit-clients "hermes-audit-clients,hermes-provider-runtime"
ensure_service_user hermes-agent-dispatch hermes-agent-dispatch hermes-github-client

usermod -aG hermes-inventory-client,hermes-github-client,hermes-audit-clients "$gateway_user"
printf 'Provisioned non-login provider identities and added gateway account %s to only the provider client groups.\n' "$gateway_user"
printf '\nNumeric UIDs for root-owned configuration (verify before writing):\n'
printf 'HERMES_PROVIDER_CLIENT_UID=%s\n' "$(id -u "$gateway_user")"
printf 'HERMES_PROVIDER_CLIENT_UIDS=%s,%s\n' "$(id -u "$gateway_user")" "$(id -u hermes-agent-dispatch)"
printf 'HERMES_GITHUB_PROVIDER_UID=%s\n' "$(id -u hermes-github)"
printf 'HERMES_AUDIT_CLIENT_UIDS=%s,%s,%s\n' "$(id -u "$gateway_user")" "$(id -u hermes-github)" "$(id -u hermes-inventory)"
printf '\nRestart the gateway only through its normal manager after reviewing group membership and MCP settings.\n'
