#!/usr/bin/env bash
# Display suspicious vector operations in the compiled GGML library binary (no source edits).
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo 'Usage: inspect-assembly.sh /path/to/GGML-CPU-object-or-library' >&2
  exit 2
fi
obj=$1
[[ -f "$obj" ]] || { echo 'File not found' >&2; exit 2; }
command -v objdump >/dev/null || { echo 'Requires binutils objdump' >&2; exit 2; }
objdump -d -Mintel "$obj" | grep -Ei 'vpmaddubsw|vpmaddwd|vpshufb|vpsrlw|vpand|vpsignb|vpaddd' | head -100 || true
