#!/usr/bin/env python3
"""Dry-run-first, allowlisted, reversible Linux sysctl/sysfs experiments."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / 'configs' / 'tuning'
DEFAULT_STATE = Path('/var/lib/epyc-moe-experimental/runtime-tune.json')
ALLOWED = {
    '/proc/sys/kernel/numa_balancing': {'0', '1'},
    '/sys/kernel/mm/transparent_hugepage/enabled': {'always', 'madvise', 'never'},
    '/sys/kernel/mm/transparent_hugepage/defrag': {'always', 'defer', 'defer+madvise', 'madvise', 'never'},
}


def parse_selected(raw: str) -> str:
    match = re.search(r'\[([^\]]+)\]', raw)
    return match.group(1) if match else raw.strip()


def validate_changes(changes: dict) -> None:
    if not isinstance(changes, dict):
        raise ValueError('profile changes must be an object')
    for path, value in changes.items():
        if path not in ALLOWED or str(value) not in ALLOWED[path]:
            raise ValueError(f'not allowlisted: {path}={value}')


def read_profile(name: str) -> dict:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name):
        raise ValueError('invalid profile name')
    data = json.loads((PROFILES / f'{name}.json').read_text())
    changes = data['changes']
    validate_changes(changes)
    return changes


def read_current(path: str) -> str:
    return parse_selected(Path(path).read_text())


def atomic_state_save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f'state exists, restore first: {path}')
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w') as writer:
            json.dump(state, writer, indent=2)
            writer.write('\n')
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def write_change(path: str, value: str) -> None:
    with Path(path).open('w') as handle:
        handle.write(value + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='baseline')
    parser.add_argument('--state', type=Path, default=DEFAULT_STATE)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--restore', action='store_true')
    parser.add_argument('--acknowledge', action='store_true', help='Required with apply/restore')
    args = parser.parse_args()
    try:
        if args.restore:
            if not args.state.exists():
                raise FileNotFoundError(f'no state to restore: {args.state}')
            state = json.loads(args.state.read_text())
            changes = state['original']
            validate_changes(changes)
        else:
            changes = read_profile(args.profile)
        plan = []
        for path, value in changes.items():
            current = read_current(path) if Path(path).exists() else None
            if current is None:
                raise FileNotFoundError(f'unsupported tuning path on this kernel: {path}')
            plan.append({'path': path, 'current': current, 'desired': str(value)})
        print(json.dumps({'action': 'restore' if args.restore else 'apply' if args.apply else 'dry-run', 'plan': plan}, indent=2))
        if not (args.apply or args.restore):
            print('DRY RUN: no host settings changed')
            return
        if not args.acknowledge or os.geteuid() != 0:
            raise PermissionError('host changes require root AND --acknowledge')
        if args.apply and not plan:
            print('Empty profile: nothing to apply')
            return
        if args.apply:
            state = {'profile': args.profile, 'original': {row['path']: row['current'] for row in plan}}
            atomic_state_save(args.state, state)
        applied = []
        try:
            for row in plan:
                write_change(row['path'], row['desired'])
                applied.append(row)
        except BaseException:
            if args.apply:
                for row in reversed(applied):
                    write_change(row['path'], row['current'])
                args.state.unlink(missing_ok=True)
            raise
        if args.restore:
            args.state.unlink()
        print('Applied. Restore as soon as the dedicated experiment completes.' if args.apply else 'Restored original settings.')
    except (OSError, ValueError, KeyError, PermissionError) as exc:
        parser.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
