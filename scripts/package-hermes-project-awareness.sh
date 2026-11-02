#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
output_dir="${1:-$repo_root/dist}"
package_version="${PACKAGE_VERSION:-0.2.0}"
if [[ ! "$package_version" =~ ^[A-Za-z0-9._-]{1,40}$ ]]; then
  echo "invalid PACKAGE_VERSION" >&2
  exit 2
fi
mkdir -p -- "$output_dir"
output_dir="$(cd -- "$output_dir" && pwd -P)"
temp_root="$(mktemp -d)"
trap 'rm -rf -- "$temp_root"' EXIT
bundle="$temp_root/hermes-project-awareness"
mkdir -p "$bundle/opt/hermes-project-awareness" \
  "$bundle/usr/share/hermes-project-awareness/systemd" \
  "$bundle/usr/share/hermes-project-awareness/apparmor" \
  "$bundle/usr/share/hermes-project-awareness/config" \
  "$bundle/usr/share/hermes-project-awareness/deploy"

tar -C "$repo_root" --exclude='*/__pycache__' --exclude='*.pyc' -cf - \
  integrations/hermes_project_awareness \
  | tar -C "$bundle/opt/hermes-project-awareness" -xf -
if [[ -d "$repo_root/agents" ]]; then
  tar -C "$repo_root" --exclude='*/__pycache__' --exclude='*.pyc' -cf - agents \
    | tar -C "$bundle/opt/hermes-project-awareness" -xf -
fi
if [[ -f "$repo_root/scripts/agents/collect-local-model-inventory.py" ]]; then
  install -D -m 0644 "$repo_root/scripts/agents/collect-local-model-inventory.py" \
    "$bundle/opt/hermes-project-awareness/scripts/agents/collect-local-model-inventory.py"
fi
install -d -m 0755 "$bundle/opt/hermes-project-awareness/docs"
install -m 0644 "$repo_root/integrations/hermes_project_awareness/docs/deployment.md" \
  "$bundle/opt/hermes-project-awareness/docs/deployment.md"
install -m 0644 "$repo_root/docs/engineering/HERMES_HOST_OPERATOR_RUNBOOK.md" \
  "$bundle/opt/hermes-project-awareness/docs/operator-runbook.md"
install -m 0644 "$repo_root/integrations/hermes_project_awareness/apparmor/hermes-project-awareness" \
  "$bundle/usr/share/hermes-project-awareness/apparmor/hermes-project-awareness"
for unit in hermes-github-egress.service hermes-github.service hermes-inventory.service \
            hermes-project-awareness-audit.service; do
  install -m 0644 "$repo_root/systemd/$unit" "$bundle/usr/share/hermes-project-awareness/systemd/$unit"
done
if [[ -f "$repo_root/systemd/hermes-agent-dispatch.service" ]]; then
  install -m 0644 "$repo_root/systemd/hermes-agent-dispatch.service" \
    "$bundle/usr/share/hermes-project-awareness/systemd/hermes-agent-dispatch.service"
fi
install -m 0644 "$repo_root/systemd/hermes-inventory-local-runtime.conf.example" \
  "$bundle/usr/share/hermes-project-awareness/systemd/hermes-inventory-local-runtime.conf.example"
cp -a "$repo_root/integrations/hermes_project_awareness/config/." \
  "$bundle/usr/share/hermes-project-awareness/config/"
install -m 0755 "$repo_root/deploy/hermes-project-awareness/install.sh" \
  "$bundle/usr/share/hermes-project-awareness/deploy/install.sh"
install -m 0755 "$repo_root/deploy/hermes-project-awareness/rollback.sh" \
  "$bundle/usr/share/hermes-project-awareness/deploy/rollback.sh"
install -m 0755 "$repo_root/deploy/hermes-project-awareness/provision-identities.sh" \
  "$bundle/opt/hermes-project-awareness/scripts/provision-identities.sh"
find "$bundle" -type d -name __pycache__ -prune -exec rm -rf -- {} +
find "$bundle" -type f -name '*.pyc' -delete
(cd "$bundle" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
archive="$output_dir/hermes-project-awareness-$package_version.tar.gz"
tar -C "$temp_root" --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner \
  -czf "$archive" hermes-project-awareness
sha256sum "$archive"
sha256sum "$archive" > "$archive.sha256"
echo "Created: $archive"
echo "Checksum: $archive.sha256"
