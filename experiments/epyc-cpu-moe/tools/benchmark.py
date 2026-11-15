#!/usr/bin/env python3
"""Build a repeatable CPU-only llama-bench invocation; execution is opt-in."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def bench_command(binary: Path, model: Path, threads: int, prompt: int, decode: int, runs: int, numa: str) -> list[str]:
    if min(threads, prompt, decode, runs) <= 0:
        raise ValueError('thread, prompt, decode and run counts must be positive')
    if numa not in ('distribute', 'isolate', 'numactl'):
        raise ValueError('invalid NUMA choice')
    return [str(binary), '-m', str(model), '-t', str(threads), '-p', str(prompt), '-n', str(decode),
            '-r', str(runs), '-ngl', '0', '--numa', numa, '-o', 'json']


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(16 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--threads', type=int, default=64)
    p.add_argument('--prompt', type=int, default=512)
    p.add_argument('--decode', type=int, default=128)
    p.add_argument('--runs', type=int, default=5)
    p.add_argument('--numa', choices=['distribute', 'isolate', 'numactl'], default='distribute')
    p.add_argument('--out', type=Path, default=Path('results/llama-bench.json'))
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', default=True)
    mode.add_argument('--execute', action='store_true')
    args = p.parse_args()
    cmd = bench_command(args.binary, args.model, args.threads, args.prompt, args.decode, args.runs, args.numa)
    print(shlex.join(cmd))
    if not args.execute:
        print('DRY RUN: no model opened or benchmark executed.')
        return
    if not args.binary.is_file() or not args.model.is_file():
        p.error('the binary and GGUF model must both exist')
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=7200)
    except subprocess.TimeoutExpired:
        p.error('benchmark timed out')
    if done.returncode != 0:
        p.error(f'benchmark exited {done.returncode}: {done.stderr[-1500:]}')
    result = {'captured_utc': datetime.now(timezone.utc).isoformat(), 'command': cmd,
              'gguf_sha256': sha256_file(args.model), 'stdout': done.stdout, 'stderr_tail': done.stderr[-3000:]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Wrote benchmark record to {args.out}')


if __name__ == '__main__':
    main()
