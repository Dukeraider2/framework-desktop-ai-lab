"""Read-only builder capability check. Never installs or changes host settings."""
import argparse
import json
import platform
import shutil
import sys


def inspect(system=None, which=shutil.which):
    system = system or platform.system()
    required = ('mkosi', 'podman', 'qemu-system-x86_64', 'qemu-img',
                'cmake', 'ninja', 'cc', 'git', 'zstd')
    available = {name: which(name) is not None for name in required}
    blockers = []
    if system != 'Linux':
        blockers.append('A dedicated Linux builder is required; this process is running on ' + system)
    blockers.extend('Missing executable: ' + name for name, found in available.items() if not found)
    return {'status': 'blocked' if blockers else 'capabilities-present',
            'system': system, 'executables': available, 'blockers': blockers,
            'not_validated': ['tool versions and Ubuntu release compatibility',
                              'OVMF firmware and virtualization access',
                              'resource budget and network access',
                              'source/package signature verification',
                              'image build and UEFI boot']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = inspect()
    print(json.dumps(result, indent=2))
    return 2 if result['blockers'] else 0


if __name__ == '__main__':
    sys.exit(main())
