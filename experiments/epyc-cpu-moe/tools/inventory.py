#!/usr/bin/env python3
"""Read-only host topology inventory; excludes network details and user data."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess


def safe_run(command: list[str]) -> dict:
    if not shutil.which(command[0]):
        return {'available': False, 'error': f'{command[0]} absent'}
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
        return {'available': True, 'returncode': done.returncode, 'stdout': done.stdout[:25000], 'stderr': done.stderr[:2000]}
    except (OSError, subprocess.TimeoutExpired) as err:
        return {'available': True, 'error': str(err)}


def read_file(path: str, cap=8000) -> str | None:
    try:
        return Path(path).read_text(errors='replace')[:cap]
    except OSError:
        return None


def inventory() -> dict:
    files = {
        'kernel_cmdline': '/proc/cmdline',
        'numa_auto_balancing': '/proc/sys/kernel/numa_balancing',
        'thp_enabled': '/sys/kernel/mm/transparent_hugepage/enabled',
        'thp_defrag': '/sys/kernel/mm/transparent_hugepage/defrag',
        'cpu_online': '/sys/devices/system/cpu/online',
        'memory_total': '/proc/meminfo',
        'kernel_release': '/proc/sys/kernel/osrelease',
        'cpu_driver_0': '/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver',
        'cpu_governor_0': '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor',
    }
    # kernel_cmdline may reveal root UUIDs; exclude from shared artifacts.
    files.pop('kernel_cmdline')
    return {
        'captured_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'platform': platform.platform(),
        'architecture': platform.machine(),
        'kernel': platform.release(),
        'commands': {
            'lscpu_extended': safe_run(['lscpu', '-e=CPU,CORE,SOCKET,NODE,ONLINE']),
            'numactl_hardware': safe_run(['numactl', '--hardware']),
            'lscpu_summary': safe_run(['lscpu', '--json']),
        },
        'sysfs': {name: read_file(path) for name, path in files.items()},
        'kernel_config_presence': {
            'proc_config_gz': Path('/proc/config.gz').exists(),
            'boot_config': Path('/boot/config-' + platform.release()).exists(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Write JSON to this file. Default prints JSON.')
    args = parser.parse_args()
    data = json.dumps(inventory(), indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data)
        print(f'Wrote read-only inventory: {args.out}')
    else:
        print(data, end='')


if __name__ == '__main__':
    main()
