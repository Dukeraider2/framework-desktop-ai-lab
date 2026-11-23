#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run rollback as root." >&2
  exit 1
fi
backup="${1:-}"
manifest="$backup/manifest"
if [[ -z "$backup" || ! -f "$manifest" || -L "$manifest" ]]; then
  echo "Usage: rollback.sh /var/backups/hermes-project-awareness/<timestamp>" >&2
  exit 2
fi
units=(hermes-agent-dispatch.service hermes-project-awareness-audit.service hermes-inventory.service hermes-github.service hermes-github-egress.service)
for unit in "${units[@]}"; do
  if systemctl is-active --quiet "$unit" || systemctl is-enabled --quiet "$unit"; then
    echo "Stop and disable $unit through the reviewed host procedure before rollback." >&2
    exit 3
  fi
done
allowed=(/opt/hermes-project-awareness /etc/apparmor.d/hermes-project-awareness
  /usr/share/hermes-project-awareness/config
  /usr/share/hermes-project-awareness/deploy
  /etc/systemd/system/hermes-github-egress.service /etc/systemd/system/hermes-github.service
  /etc/systemd/system/hermes-inventory.service /etc/systemd/system/hermes-project-awareness-audit.service
  /etc/systemd/system/hermes-agent-dispatch.service)
while IFS=$'\t' read -r action target; do
  [[ -n "$target" ]] || continue
  case " ${allowed[*]} " in *" $target "*) ;; *) echo "Unexpected path in backup manifest." >&2; exit 4;; esac
  if [[ "$target" == /etc/apparmor.d/hermes-project-awareness ]]; then
    if [[ -f "$target" ]]; then apparmor_parser -R "$target" || true; fi
  fi
  if [[ "$action" == restore ]]; then
    relative="${target#/}"
    rm -rf -- "$target"
    install -d -m 0755 "$(dirname -- "$target")"
    cp -a -- "$backup/existing/$relative" "$target"
    if [[ "$target" == /etc/apparmor.d/hermes-project-awareness ]]; then
      apparmor_parser -r "$target"
    fi
  elif [[ "$action" == remove ]]; then
    rm -rf -- "$target"
  else
    echo "Invalid backup manifest action." >&2
    exit 5
  fi
done < <(tac "$manifest")
systemctl daemon-reload
echo "Package files rolled back. /var/lib/hermes-agent-dispatch and audit records were preserved."
