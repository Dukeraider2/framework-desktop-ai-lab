# EPYC CPU MoE v0.1 source bootstrap

This directory holds the **exact research framework v0.1** originally prepared on 2026-11-14, transported into the public project branch as nine numbered base64 parts. This was a transport step only; **the source is not yet expanded or production-tested**. Codex must unpack, audit, version and commit the normal source files before building the OS image.

## Integrity manifest

- Source archive: `epyc-cpu-moe-experimental-v0.1.tar.xz` (tar containing one `epyc-cpu-moe-experimental/` top-level directory)
- Transport parts: `bundle/part00.b64` to `bundle/part08.b64`, each 4096 bytes except the last (588)
- Combined Base64 length: **33,356 bytes**.
- Decoded archive length: **25,016 bytes**.
- Expected SHA-256: `0594d36b92ede2beef8956d973db03398c1337375e21226bb96378ebe1b4d83a`
- GitHub-stored content was independently reconstructed and hashed: **verified match**.
- Archive contains 32 files (the previously generated `SHA256SUMS.txt` excluded because it referred to the pre-transport layout); regenerate per-file checksums after import.

## Safe import from repository root

```bash
set -euo pipefail
target=experiments/epyc-cpu-moe
test ! -e "$target/README.md" || { echo 'Source already imported; refusing overwrite'; exit 1; }
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
cat "$target"/bootstrap/bundle/part*.b64 | base64 --decode > "$tmp"
echo "0594d36b92ede2beef8956d973db03398c1337375e21226bb96378ebe1b4d83a  $tmp" | sha256sum -c -
tar -tJf "$tmp"  # inspect before extraction
tar -xJf "$tmp" -C "$target" --strip-components=1 --no-same-owner
python3 -m unittest discover -s "$target/tests" -v
```

No sudo, device writes, kernel installation, service enablement, or reboot occurs. Imported files are development prototypes. The separate full-image build brief is `../CODEX_FULL_SERVER_IMAGE_BUILD.md`.

**Mandatory follow-up:** Commit extracted source as normal files, review it for errors, then remove the redundant Base64 transport files in the Codex implementation PR after their contents are safely committed and verified. Do not embed model checkpoints or a 400B model in Git.
