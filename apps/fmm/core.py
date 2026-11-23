"""Inventory, registry and conservative placement policy; Python standard library only."""
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

MAX_MODEL_BYTES = 100_000_000_000  # Policy uses decimal GB, not GiB.
STATES = {'Catalogued', 'Candidate', 'Approved candidate', 'Installed', 'Qualified',
          'Preferred', 'Restricted', 'Disabled', 'Retired'}
FIELDS = {'id', 'source', 'revision', 'license', 'filename', 'sha256', 'quantization',
          'task_classes', 'storage_path', 'memory', 'runtime_compatibility',
          'lifecycle', 'gateway_route', 'last_validation', 'enabled'}


def byte_count(value):
    return type(value) is int and value >= 0


def validate_registry(data):
    if not isinstance(data, dict) or set(data) != {'version', 'models'} or type(data['version']) is not int or data['version'] != 1 or not isinstance(data['models'], list):
        raise ValueError('expected version 1 registry with models array')
    ids = set()
    for model in data['models']:
        if not isinstance(model, dict) or set(model) != FIELDS:
            raise ValueError('manifest fields do not match schema')
        ident = model['id']
        if not isinstance(ident, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', ident) or ident in ids:
            raise ValueError('invalid or duplicate model id')
        ids.add(ident)
        for key in FIELDS - {'id', 'memory', 'task_classes', 'enabled', 'lifecycle'}:
            if model[key] is not None and (not isinstance(model[key], str) or not model[key]):
                raise ValueError(f'{key} must be a nonempty string or null (unknown)')
        if model['sha256'] is not None and not re.fullmatch('[0-9a-f]{64}', model['sha256']):
            raise ValueError('invalid SHA256')
        if not isinstance(model['lifecycle'], str) or model['lifecycle'] not in STATES or type(model['enabled']) is not bool:
            raise ValueError('invalid lifecycle or enabled flag')
        if not isinstance(model['task_classes'], list) or not all(isinstance(x, str) and x for x in model['task_classes']):
            raise ValueError('invalid task classes')
        memory = model['memory']
        if not isinstance(memory, dict) or set(memory) != {'estimated_total_bytes', 'measured_peak_bytes', 'gpu_bytes', 'assumptions'}:
            raise ValueError('invalid memory record')
        if not isinstance(memory['assumptions'], str):
            raise ValueError('memory assumptions required')
        for key in ('estimated_total_bytes', 'measured_peak_bytes', 'gpu_bytes'):
            if memory[key] is not None and not byte_count(memory[key]):
                raise ValueError('memory must be nonnegative integer bytes or null')
    return data


def load_registry(path):
    return validate_registry(json.loads(Path(path).read_text()))


def inventory(roots, hashes=False):
    """Read only regular files, deduplicate hardlinks and optional content hashes."""
    records, errors, seen = [], [], {}
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir() or root.is_symlink():
            errors.append({'root': str(root), 'error': 'unavailable or symlink root'})
            continue
        def onerror(error):
            errors.append({'root': str(root), 'error': type(error).__name__})
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
            for name in sorted(files):
                if not name.lower().endswith('.gguf'):
                    continue
                path = Path(directory) / name
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(fd, 'rb') as stream:
                        before = os.fstat(stream.fileno())
                        if not stat.S_ISREG(before.st_mode):
                            continue
                        if stream.read(4) != b'GGUF':
                            errors.append({'path': str(path), 'error': 'invalid GGUF magic'})
                            continue
                        key = (before.st_dev, before.st_ino)
                        digest = None
                        if hashes:
                            stream.seek(0)
                            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                            after = os.fstat(stream.fileno())
                            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                                raise ValueError('file changed during hashing')
                            key = digest
                        if key in seen:
                            seen[key]['aliases'].append(str(path))
                            continue
                        item = {'path': str(path), 'aliases': [], 'size_bytes': before.st_size,
                                'sha256': digest, 'observed_at': time.time(), 'format': 'GGUF'}
                        records.append(item)
                        seen[key] = item
                except (OSError, ValueError) as error:
                    errors.append({'path': str(path), 'error': type(error).__name__})
    return {'files': records, 'errors': errors, 'hashes_computed': hashes,
            'deduplication': 'sha256' if hashes else 'device/inode; separate copies may remain'}


def resources(proc=Path('/proc'), drm=Path('/sys/class/drm'), storage=Path('.')):
    result = {'observed_at': time.time(), 'ram_available_bytes': None, 'gpu': [],
              'storage_available_bytes': None, 'active_requests': None, 'errors': []}
    try:
        values = dict(line.split(':', 1) for line in (proc / 'meminfo').read_text().splitlines())
        result['ram_available_bytes'] = int(values['MemAvailable'].split()[0]) * 1024
    except (OSError, ValueError, KeyError, IndexError):
        result['errors'].append('RAM telemetry unavailable')
    for card in sorted(drm.glob('card[0-9]*')):
        if not re.fullmatch(r'card\d+', card.name):
            continue
        device = card / 'device'
        gpu = {'card': card.name}
        for pool in ('vram', 'gtt'):
            try:
                total = int((device / f'mem_info_{pool}_total').read_text())
                used = int((device / f'mem_info_{pool}_used').read_text())
                gpu[pool + '_available_bytes'] = total - used if 0 <= used <= total else None
            except (OSError, ValueError):
                gpu[pool + '_available_bytes'] = None
        try:
            gpu['busy_percent'] = int((device / 'gpu_busy_percent').read_text())
        except (OSError, ValueError):
            gpu['busy_percent'] = None
        result['gpu'].append(gpu)
    try:
        disk = os.statvfs(storage)
        result['storage_available_bytes'] = disk.f_bavail * disk.f_frsize
    except OSError:
        result['errors'].append('storage telemetry unavailable')
    return result


def podman_inventory():
    """Only local rootless queries; never inherit a remote socket destination."""
    if os.geteuid() == 0:
        return {'available': False, 'error': 'rootless user required'}
    env = {k: v for k, v in os.environ.items() if k not in
           {'CONTAINER_HOST', 'CONTAINER_CONNECTION', 'DOCKER_HOST'}}
    def query(args):
        completed = subprocess.run(['podman', '--remote=false', *args], env=env,
                                   capture_output=True, text=True, timeout=10, check=True)
        return json.loads(completed.stdout)
    try:
        info = query(['info', '--format', 'json'])
        if info.get('host', {}).get('security', {}).get('rootless') is not True:
            return {'available': False, 'error': 'rootless identity not verified'}
        containers = query(['ps', '--all', '--format', 'json'])
        stats = query(['stats', '--all', '--no-stream', '--format', 'json'])
        volumes = query(['volume', 'ls', '--format', 'json'])
        if not all(isinstance(x, list) for x in (containers, stats, volumes)):
            raise ValueError('unexpected Podman output')
        # Exclude command lines, labels, environment, and mount paths from responses.
        return {'available': True, 'version': info.get('version', {}).get('Version'),
                'containers': [{k: c.get(k) for k in ('Id', 'Names', 'Image', 'State', 'Ports')} for c in containers],
                'stats': [{k: c.get(k) for k in ('id', 'name', 'mem_usage', 'mem_percent', 'cpu_percent')} for c in stats],
                'volumes': [{'name': v.get('Name')} for v in volumes]}
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError, TypeError):
        return {'available': False, 'error': 'local Podman inventory unavailable; no remediation attempted'}


def plan(model, telemetry, safety_bytes=8_000_000_000):
    reasons = []
    if not byte_count(safety_bytes):
        raise ValueError('invalid safety margin')
    memory = model['memory']
    totals = [memory[k] for k in ('estimated_total_bytes', 'measured_peak_bytes') if memory[k] is not None]
    total = max(totals) if totals else None
    if total is None:
        reasons.append('complete deployment memory unknown')
    elif total > MAX_MODEL_BYTES:
        reasons.append('100 GB deployment ceiling exceeded')
    available = telemetry.get('ram_available_bytes')
    stamp = telemetry.get('observed_at')
    if not isinstance(stamp, (int, float)) or not 0 <= time.time() - stamp <= 10:
        reasons.append('telemetry missing or stale')
    if not byte_count(available) or total is not None and total + safety_bytes > available:
        reasons.append('insufficient or unknown RAM headroom')
    gpu_bytes = memory['gpu_bytes']
    if gpu_bytes is None:
        reasons.append('GPU requirement unknown')
    elif gpu_bytes:
        # On Strix Halo GTT shares RAM. Never add GPU capacity to MemAvailable.
        headrooms = [g.get('gtt_available_bytes') for g in telemetry.get('gpu', [])]
        if not any(byte_count(n) and gpu_bytes + safety_bytes <= n for n in headrooms):
            reasons.append('insufficient or unknown GPU GTT headroom')
    if total is not None and gpu_bytes is not None and gpu_bytes > total:
        reasons.append('GPU allocation exceeds complete deployment budget')
    if model['lifecycle'] not in {'Qualified', 'Preferred'} or not model['enabled']:
        reasons.append('deployment not qualified and user enabled')
    if model['runtime_compatibility'] != 'verified':
        reasons.append('runtime compatibility not verified')
    return {'model_id': model['id'], 'dry_run': True, 'memory_eligible': not reasons,
            'total_bytes': total, 'safety_bytes': safety_bytes, 'reasons': reasons,
            'executable': False, 'authority': 'Hermes',
            'controller': 'disabled; explicit user authorization and session drain required'}


class DeploymentController:
    """No enable switch in this deliverable; future adapters require independent review."""
    enabled = False

    def request(self, operation, model_id):
        if operation not in {'load', 'unload', 'switch'}:
            raise ValueError('unknown deployment operation')
        return {'accepted': False, 'operation': operation, 'model_id': model_id,
                'authority': 'Hermes', 'reason': 'deployment controller disabled'}


def service_observations():
    """Fixed read-only endpoints; no proxy environment or redirects, no inference."""
    import urllib.error
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    endpoints = {
        'ollama_models': 'http://127.0.0.1:11434/api/tags',
        'ollama_loaded': 'http://127.0.0.1:11434/api/ps',
        'llama_health': 'http://127.0.0.1:18080/health',
        'llama_models': 'http://127.0.0.1:18080/v1/models',
        'coder_health': 'http://127.0.0.1:18081/health',
        'coder_models': 'http://127.0.0.1:18081/v1/models',
        'gateway_ollama': 'http://127.0.0.1:11435/api/tags',
        'gateway_llama': 'http://127.0.0.1:11435/llama/health',
        'gateway_coder': 'http://127.0.0.1:11435/llama-coder/health',
        'comfy_health': 'http://127.0.0.1:8188/system_stats',
        'gateway_comfy': 'http://127.0.0.1:11436/system_stats',
    }
    observed = {}
    for name, url in endpoints.items():
        try:
            with opener.open(url, timeout=2) as response:
                raw = response.read(1_048_577)
                if len(raw) > 1_048_576:
                    raise ValueError('response too large')
                data = json.loads(raw)
                item = {'available': True, 'http_status': response.status}
                if name in {'ollama_models', 'ollama_loaded'}:
                    item['model_ids'] = [m['name'] for m in data['models']]
                elif name in {'llama_models', 'coder_models'}:
                    item['model_ids'] = [m['id'] for m in data['data']]
                observed[name] = item
        except (OSError, HTTPException, ValueError, KeyError, TypeError):
            observed[name] = {'available': False, 'http_status': None}
    return {'observed_at': time.time(), 'services': observed, 'active_sessions': None}
