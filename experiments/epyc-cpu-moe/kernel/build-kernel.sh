#!/usr/bin/env bash
# Separate build-only stage. Must not install, sign, boot, or replace the OS kernel.
set -euo pipefail
if [[ $# -lt 2 || $# -gt 4 ]]; then
  echo 'Usage: build-kernel.sh /path/to/linux-source /path/to/prepared-build [--execute] [jobs]' >&2
  exit 2
fi
src=$(realpath "$1")
out=$(realpath "$2")
mode=${3:-'--dry-run'}
jobs=${4:-8}
[[ "$mode" == '--dry-run' || "$mode" == '--execute' ]] || { echo 'Require --dry-run or --execute' >&2; exit 2; }
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'jobs must be positive integer' >&2; exit 2; }
[[ -f "$out/.config" && -f "$out/kernel-source-sha.txt" ]] || { echo 'First run prepare-kernel.sh' >&2; exit 2; }
sha_expected=$(cat "$out/kernel-source-sha.txt")
sha_actual=$(git -C "$src" rev-parse HEAD)
[[ "$sha_expected" == "$sha_actual" ]] || { echo 'Source SHA differs from prepared configuration' >&2; exit 2; }
[[ -z "$(git -C "$src" status --porcelain)" ]] || { echo 'Refuse build from dirty kernel source' >&2; exit 2; }
cmd=(make -C "$src" O="$out" -j "$jobs" bzImage modules)
printf 'build command (build only, no install): '; printf '%q ' "${cmd[@]}"; echo
if [[ "$mode" == '--dry-run' ]]; then echo 'DRY RUN: no compile'; exit 0; fi
"${cmd[@]}"
echo "Build completed. Artifacts under $out. Not installed, booted, signed or validated."
