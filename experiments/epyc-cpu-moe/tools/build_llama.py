#!/usr/bin/env python3
"""Reproducible pinned-local-source llama.cpp CMake build plan; dry-run default."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import shlex
import subprocess
import sys


def make_commands(source: Path, build: Path, profile: str, repack: bool) -> list[list[str]]:
    if profile not in ('baseline', 'zen1'):
        raise ValueError('profile must be baseline or zen1')
    cmake = ['cmake', '-S', str(source), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release',
             '-DGGML_CPU=ON', '-DGGML_NATIVE=OFF', '-DGGML_AVX=ON', '-DGGML_AVX2=ON',
             '-DGGML_FMA=ON', '-DGGML_F16C=ON', '-DGGML_BMI2=ON', '-DGGML_SSE42=ON',
             '-DGGML_AVX_VNNI=OFF', '-DGGML_AVX512=OFF',
             '-DGGML_CUDA=OFF', '-DGGML_HIP=OFF',
             '-DLLAMA_BUILD_TESTS=ON', f'-DGGML_CPU_REPACK={"ON" if repack else "OFF"}']
    if profile == 'zen1':
        cmake += ['-DCMAKE_C_FLAGS=-O3 -march=znver1 -mtune=znver1',
                  '-DCMAKE_CXX_FLAGS=-O3 -march=znver1 -mtune=znver1']
    return [cmake, ['cmake', '--build', str(build), '--parallel', '8', '--target', 'llama-server', 'llama-bench', 'test-backend-ops']]


def git_sha(path: Path) -> str:
    result = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True, help='Existing local llama.cpp checkout')
    p.add_argument('--profile', choices=['baseline', 'zen1'], default='baseline')
    p.add_argument('--repack', choices=['on', 'off'], default='on')
    p.add_argument('--build-root', type=Path, default=Path('build-experimental'))
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', default=True)
    mode.add_argument('--execute', action='store_true', help='Opt-in local compile, never installs')
    p.add_argument('--expect-sha', help='Required 40-digit git commit SHA for execute mode')
    args = p.parse_args()
    src = args.source.resolve()
    if not (src / 'CMakeLists.txt').exists() or not (src / '.git').exists():
        p.error('--source must be an existing local llama.cpp Git checkout')
    try:
        sha = git_sha(src)
    except (OSError, subprocess.CalledProcessError):
        p.error('failed to retrieve git HEAD')
    if args.execute and (not args.expect_sha or args.expect_sha != sha or len(sha) != 40):
        p.error('--execute requires --expect-sha matching the exact current 40-digit HEAD')
    build = (args.build_root / f'{args.profile}-repack-{args.repack}').resolve()
    commands = make_commands(src, build, args.profile, args.repack == 'on')
    print(json.dumps({'upstream_sha': sha, 'profile': args.profile, 'repack': args.repack,
                      'build_dir': str(build), 'commands': [shlex.join(c) for c in commands],
                      'execute': bool(args.execute)}, indent=2))
    if not args.execute:
        print('DRY RUN: no build performed.')
        return
    if subprocess.run(['git', '-C', str(src), 'status', '--porcelain'], capture_output=True, text=True, check=True).stdout.strip():
        p.error('source working tree is dirty: refuse non-reproducible build')
    for cmd in commands:
        subprocess.run(cmd, check=True)
    build.mkdir(parents=True, exist_ok=True)
    (build / 'experiment-manifest.json').write_text(json.dumps({'upstream_sha': sha, 'profile': args.profile, 'repack': args.repack}, indent=2) + '\n')


if __name__ == '__main__':
    main()
