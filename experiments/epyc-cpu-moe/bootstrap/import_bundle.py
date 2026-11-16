"""Verify the versioned transport and import regular files without executing them."""
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / 'experiments/epyc-cpu-moe'
EXPECTED = '0594d36b92ede2beef8956d973db03398c1337375e21226bb96378ebe1b4d83a'


def main():
    parts = []
    manifest = {}
    for index in range(9):
        path = TARGET / f'bootstrap/bundle/part{index:02}.b64'
        data = path.read_bytes()
        relative = path.relative_to(ROOT).as_posix()
        original = subprocess.check_output(['git', 'show', f'ab25f72f61352492a3a58d766dd2a78d2695b7e9:{relative}'], cwd=ROOT)
        if data != original or len(data) != (588 if index == 8 else 4096):
            raise ValueError(f'Transport mismatch: {relative}')
        manifest[relative] = hashlib.sha256(data).hexdigest()
        parts.append(data)
    archive = base64.b64decode(b''.join(parts), validate=True)
    if len(archive) != 25016 or hashlib.sha256(archive).hexdigest() != EXPECTED:
        raise ValueError('Archive checksum or size mismatch')
    files = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:xz') as tar:
        seen = set()
        for member in tar.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or '\\' in member.name or ':' in member.name:
                raise ValueError(f'Unsafe path: {member.name}')
            if not name.parts or name.parts[0] != 'epyc-cpu-moe-experimental':
                raise ValueError('Unexpected archive root')
            if member.isdir():
                continue
            if not member.isfile() or len(name.parts) < 2:
                raise ValueError(f'Unsupported archive member: {member.name}')
            relative = Path(*name.parts[1:])
            output = TARGET / relative
            normalized = relative.as_posix().casefold()
            if normalized in seen or output.exists():
                raise ValueError(f'Duplicate or existing output: {relative}')
            seen.add(normalized)
            files.append((output, tar.extractfile(member).read(), member.mode))
    if len(files) != 32:
        raise ValueError(f'Expected 32 files, found {len(files)}')
    for path, data, mode in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode & 0o777)
        manifest[path.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
    (TARGET / 'bootstrap/IMPORT_MANIFEST.json').write_text(
        json.dumps({'archive_sha256': EXPECTED, 'files_sha256': manifest}, indent=2) + '\n', encoding='utf-8')
    print(f'Verified 9 transport parts and archive; imported {len(files)} files.')


if __name__ == '__main__':
    main()
