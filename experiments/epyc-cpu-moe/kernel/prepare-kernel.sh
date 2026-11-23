#!/usr/bin/env bash
# Prepare a custom Linux kernel .config in a separate build tree. Never compiles or installs.
set -euo pipefail
if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo 'Usage: prepare-kernel.sh /path/to/linux-source 40-char-git-sha /boot/config-$(uname -r) /path/to/output-build [optional-kconfig-fragment]' >&2
  exit 2
fi
src=$(realpath "$1")
expected_sha=$2
base=$(realpath "$3")
out=$(realpath -m "$4")
script_dir=$(cd "$(dirname "$0")" && pwd)
fragment="${5:-$script_dir/zen1-experiment.config}"
fragment=$(realpath "$fragment")
[[ -r "$fragment" ]] || { echo "Fragment not readable: $fragment" >&2; exit 2; }
[[ -d "$src/.git" || -f "$src/.git" ]] || { echo 'Need local Linux git checkout' >&2; exit 2; }
[[ "$expected_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Need pinned 40-digit SHA' >&2; exit 2; }
actual_sha=$(git -C "$src" rev-parse HEAD)
[[ "$expected_sha" == "$actual_sha" ]] || { echo "Source SHA mismatch: $actual_sha" >&2; exit 2; }
[[ -z "$(git -C "$src" status --porcelain)" ]] || { echo 'Linux source is dirty' >&2; exit 2; }
[[ -r "$base" ]] || { echo 'Base kernel config not readable' >&2; exit 2; }
[[ "$out" != "$src" ]] || { echo 'Build output cannot overwrite sources' >&2; exit 2; }
[[ -x "$src/scripts/kconfig/merge_config.sh" ]] || { echo 'Linux tree lacks merge_config.sh' >&2; exit 2; }
mkdir -p "$out"
cp "$base" "$out/base.config"
"$src/scripts/kconfig/merge_config.sh" -m -O "$out" "$out/base.config" "$script_dir/zen1-experiment.config" "$fragment"
make -C "$src" O="$out" olddefconfig
cp "$script_dir/zen1-experiment.config" "$out/experiment.fragment"
cp "$fragment" "$out/selected.fragment"
printf '%s\n' "$actual_sha" > "$out/kernel-source-sha.txt"
echo "Prepared only: $out/.config"
echo 'CHECK config options and build drivers before any separate compile, sign, install or boot attempt.'
