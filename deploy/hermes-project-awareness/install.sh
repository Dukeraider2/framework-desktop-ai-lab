#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run this installer as root after reviewing the extracted bundle." >&2
  exit 1
fi
bundle_root="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd -P)}"
share="$bundle_root/usr/share/hermes-project-awareness"
payload="$bundle_root/opt/hermes-project-awareness"
if [[ ! -d "$payload/integrations/hermes_project_awareness" || ! -d "$share/systemd" ]]; then
  echo "bundle layout is invalid" >&2
  exit 2
fi
if [[ ${HERMES_AWARENESS_REPLACE:-0} != 1 ]]; then
  for target in /opt/hermes-project-awareness /etc/apparmor.d/hermes-project-awareness \
      /usr/share/hermes-project-awareness/config \
      /usr/share/hermes-project-awareness/deploy \
      /etc/systemd/system/hermes-github-egress.service /etc/systemd/system/hermes-github.service \
      /etc/systemd/system/hermes-inventory.service /etc/systemd/system/hermes-project-awareness-audit.service \
      /etc/systemd/system/hermes-agent-dispatch.service; do
    if [[ -e "$target" || -L "$target" ]]; then
      echo "Existing target found: $target. Review it and set HERMES_AWARENESS_REPLACE=1 only for an approved upgrade." >&2
      exit 3
    fi
  done
fi
for unit in hermes-github-egress.service hermes-github.service hermes-inventory.service \
            hermes-project-awareness-audit.service hermes-agent-dispatch.service; do
  [[ -f "$share/systemd/$unit" ]] || continue
  if systemctl is-active --quiet "$unit"; then
    echo "Refusing to replace active unit: $unit" >&2
    exit 4
  fi
done

backup="/var/backups/hermes-project-awareness/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$backup/existing" "$(dirname -- "$backup/manifest")"
manifest="$backup/manifest"
: > "$manifest"
backup_target() {
  local target="$1" relative
  relative="${target#/}"
  if [[ -e "$target" || -L "$target" ]]; then
    install -d -m 0700 "$backup/existing/$(dirname -- "$relative")"
    cp -a -- "$target" "$backup/existing/$relative"
    printf 'restore\t%s\n' "$target" >> "$manifest"
  else
    printf 'remove\t%s\n' "$target" >> "$manifest"
  fi
}

targets=(/opt/hermes-project-awareness /etc/apparmor.d/hermes-project-awareness \
  /usr/share/hermes-project-awareness/config \
  /usr/share/hermes-project-awareness/deploy \
  /etc/systemd/system/hermes-github-egress.service /etc/systemd/system/hermes-github.service \
  /etc/systemd/system/hermes-inventory.service /etc/systemd/system/hermes-project-awareness-audit.service \
  /etc/systemd/system/hermes-agent-dispatch.service)
for unit in "${targets[@]}"; do backup_target "$unit"; done

install -d -m 0755 /opt/hermes-project-awareness /etc/systemd/system \
  /etc/apparmor.d /usr/share/hermes-project-awareness
cp -a "$payload/." /opt/hermes-project-awareness/
install -m 0644 "$share/apparmor/hermes-project-awareness" /etc/apparmor.d/hermes-project-awareness
install -d -m 0755 /usr/share/hermes-project-awareness/config
cp -a "$share/config/." /usr/share/hermes-project-awareness/config/
install -d -m 0755 /usr/share/hermes-project-awareness/deploy
cp -a "$share/deploy/." /usr/share/hermes-project-awareness/deploy/
for unit in hermes-github-egress.service hermes-github.service hermes-inventory.service \
            hermes-project-awareness-audit.service hermes-agent-dispatch.service; do
  [[ -f "$share/systemd/$unit" ]] || continue
  install -m 0644 "$share/systemd/$unit" "/etc/systemd/system/$unit"
done

apparmor_parser -Q -K /etc/apparmor.d/hermes-project-awareness
apparmor_parser -r /etc/apparmor.d/hermes-project-awareness
systemctl daemon-reload
printf 'Installed files. No units were enabled or started. Backup: %s\n' "$backup"
printf 'Operator next steps are in /opt/hermes-project-awareness/docs/operator-runbook.md\n'
