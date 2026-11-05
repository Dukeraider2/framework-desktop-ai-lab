import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from apps.fmm.core import (DeploymentController, MAX_MODEL_BYTES, inventory,
                           plan, podman_inventory, resources, service_observations, validate_registry)
from apps.fmm.__main__ import Server


def model():
    return {'id': 'test', 'source': None, 'revision': None, 'license': None,
            'filename': 'test.gguf', 'sha256': None, 'quantization': None,
            'task_classes': ['coding'], 'storage_path': None,
            'memory': {'estimated_total_bytes': 10_000_000_000,
                       'measured_peak_bytes': None, 'gpu_bytes': 8_000_000_000,
                       'assumptions': 'fixture only; includes runtime and KV cache'},
            'runtime_compatibility': 'verified', 'lifecycle': 'Qualified',
            'gateway_route': None, 'last_validation': None, 'enabled': True}


def telemetry():
    return {'observed_at': time.time(), 'ram_available_bytes': 120_000_000_000,
            'gpu': [{'gtt_available_bytes': 60_000_000_000}]}


class RegistryTests(unittest.TestCase):
    def test_valid_and_unknown(self):
        entry = model()
        entry['memory']['estimated_total_bytes'] = None
        self.assertEqual(validate_registry({'version': 1, 'models': [entry]})['models'], [entry])

    def test_invalid(self):
        for key, value in [('sha256', 'invalid'), ('enabled', 1), ('id', '../path'),
                           ('lifecycle', 'running'), ('lifecycle', []), ('task_classes', 'coding')]:
            with self.subTest(key=key):
                entry = model()
                entry[key] = value
                with self.assertRaises(ValueError):
                    validate_registry({'version': 1, 'models': [entry]})
        entry = model()
        for value in (-1, True, float('nan'), '100'):
            entry['memory']['gpu_bytes'] = value
            with self.assertRaises(ValueError):
                validate_registry({'version': 1, 'models': [entry]})

    def test_duplicates_and_extra_fields(self):
        with self.assertRaises(ValueError):
            validate_registry({'version': 1, 'models': [model(), model()]})
        entry = model()
        entry['command'] = 'do not execute'
        with self.assertRaises(ValueError):
            validate_registry({'version': 1, 'models': [entry]})

    def test_schema_and_validator_fields_match(self):
        schema = json.loads(Path('docs/fmm/manifest.schema.json').read_text())
        self.assertEqual(set(schema['properties']['models']['items']['required']), set(model()))
        validate_registry(json.loads(Path('registry/fmm.json').read_text()))


class InventoryTests(unittest.TestCase):
    def test_regular_hardlink_symlink_and_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'model.gguf'
            file.write_bytes(b'GGUFpayload')
            os.link(file, root / 'alias.gguf')
            (root / 'link.gguf').symlink_to(file)
            (root / 'bad.gguf').write_bytes(b'bad')
            (root / 'ignored.bin').write_bytes(b'GGUF')
            before = file.stat()
            result = inventory([root])
            self.assertEqual(len(result['files']), 1)
            self.assertEqual(len(result['files'][0]['aliases']), 1)
            self.assertEqual(file.read_bytes(), b'GGUFpayload')
            self.assertEqual(file.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(len(result['errors']), 2)

    def test_hash_deduplicates_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('one.gguf', 'two.gguf'):
                (root / name).write_bytes(b'GGUFsame')
            self.assertEqual(len(inventory([root])['files']), 2)
            result = inventory([root], hashes=True)
            self.assertEqual(len(result['files']), 1)
            self.assertEqual(len(result['files'][0]['sha256']), 64)

    def test_missing_and_symlink_root(self):
        self.assertTrue(inventory(['/does/not/exist'])['errors'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'link').symlink_to(root, target_is_directory=True)
            self.assertTrue(inventory([root / 'link'])['errors'])


class PolicyTests(unittest.TestCase):
    def test_eligible_is_never_executable(self):
        result = plan(model(), telemetry())
        self.assertTrue(result['memory_eligible'])
        self.assertFalse(result['executable'])

    def test_decimal_ceiling_and_measured_peak(self):
        entry = model()
        entry['memory']['estimated_total_bytes'] = MAX_MODEL_BYTES
        self.assertTrue(plan(entry, telemetry())['memory_eligible'])
        entry['memory']['measured_peak_bytes'] = MAX_MODEL_BYTES + 1
        self.assertIn('100 GB deployment ceiling exceeded', plan(entry, telemetry())['reasons'])

    def test_unknown_stale_and_headroom(self):
        for change in ({'observed_at': 0}, {'observed_at': time.time() + 30},
                       {'ram_available_bytes': None}, {'ram_available_bytes': 10_000_000_000},
                       {'gpu': []}):
            sample = telemetry()
            sample.update(change)
            self.assertFalse(plan(model(), sample)['memory_eligible'])
        entry = model()
        entry['memory']['estimated_total_bytes'] = None
        self.assertFalse(plan(entry, telemetry())['memory_eligible'])

    def test_activation_and_compatibility(self):
        for field, value in [('enabled', False), ('lifecycle', 'Installed'),
                             ('runtime_compatibility', 'unverified')]:
            entry = model()
            entry[field] = value
            self.assertFalse(plan(entry, telemetry())['memory_eligible'])

    def test_controller_cannot_be_enabled(self):
        for operation in ('load', 'unload', 'switch'):
            self.assertFalse(DeploymentController().request(operation, 'test')['accepted'])
        with self.assertRaises(ValueError):
            DeploymentController().request('exec', 'test')


class TelemetryTests(unittest.TestCase):
    def test_ram_gpu_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'meminfo').write_text('MemAvailable: 123 kB\n')
            device = root / 'card0/device'
            device.mkdir(parents=True)
            for name, value in [('gtt_total', 100), ('gtt_used', 25), ('vram_total', 10), ('vram_used', 2)]:
                (device / ('mem_info_' + name)).write_text(str(value))
            result = resources(root, root, root)
            self.assertEqual(result['ram_available_bytes'], 123 * 1024)
            self.assertEqual(result['gpu'][0]['gtt_available_bytes'], 75)
            self.assertIsNone(result['active_requests'])
            self.assertIsNone(resources(root / 'missing', root)['ram_available_bytes'])

    @patch('apps.fmm.core.os.geteuid', return_value=1000)
    @patch('apps.fmm.core.subprocess.run')
    def test_podman_allowlist_and_redaction(self, run, uid):
        values = [{'host': {'security': {'rootless': True}}},
                  [{'Names': ['model'], 'Command': ['secret'], 'State': 'running'}],
                  [{'name': 'model', 'mem_usage': '1GB'}], [{'Name': 'volume'}]]
        run.side_effect = [type('Result', (), {'stdout': json.dumps(v)}) for v in values]
        with patch.dict(os.environ, {'CONTAINER_HOST': 'secret', 'DOCKER_HOST': 'secret'}):
            result = podman_inventory()
        self.assertTrue(result['available'])
        self.assertNotIn('Command', result['containers'][0])
        for call in run.call_args_list:
            self.assertNotIn('CONTAINER_HOST', call.kwargs['env'])
            self.assertEqual(call.args[0][:2], ['podman', '--remote=false'])
            self.assertNotIn('shell', call.kwargs)

    @patch('apps.fmm.core.os.geteuid', return_value=1000)
    @patch('apps.fmm.core.subprocess.run', side_effect=FileNotFoundError)
    def test_podman_unavailable(self, run, uid):
        self.assertFalse(podman_inventory()['available'])


class ServiceTests(unittest.TestCase):
    @patch('urllib.request.build_opener')
    def test_fixed_gets_without_raw_payload(self, build):
        response = build.return_value.open.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = b'{"models": [], "data": [], "private": "redact"}'
        result = service_observations()
        self.assertTrue(all(item['available'] for item in result['services'].values()))
        self.assertNotIn('redact', json.dumps(result))
        for call in build.return_value.open.call_args_list:
            self.assertTrue(call.args[0].startswith('http://127.0.0.1:'))
            self.assertEqual(call.kwargs['timeout'], 2)

    @patch('urllib.request.build_opener')
    def test_unavailable_is_unknown(self, build):
        build.return_value.open.side_effect = OSError
        result = service_observations()
        self.assertFalse(any(item['available'] for item in result['services'].values()))
        self.assertIsNone(result['active_sessions'])


class APITests(unittest.TestCase):
    def setUp(self):
        self.token = 'x' * 40
        self.server = Server(('127.0.0.1', 0), {'version': 1, 'models': [model()]}, [], self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, auth=True, extra=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers['Authorization'] = 'Bearer ' + self.token
        headers.update(extra or {})
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        status, payload = response.status, json.loads(response.read())
        connection.close()
        return status, payload

    def test_auth_health_and_origin(self):
        self.assertEqual(self.request('GET', '/health', auth=False)[0], 401)
        self.assertEqual(self.request('GET', '/health')[0], 200)
        self.assertEqual(self.request('GET', '/health', extra={'Origin': 'http://example.com'})[0], 403)
        self.assertEqual(self.request('GET', '/v1/registry')[1]['models'][0]['id'], 'test')

    def test_disabled_operations_and_unknown(self):
        for op in ('load', 'unload', 'switch'):
            status, body = self.request('POST', '/v1/' + op, json.dumps({'model_id': 'test'}))
            self.assertEqual(status, 409)
            self.assertFalse(body['accepted'])
        self.assertEqual(self.request('POST', '/v1/plan', '{')[0], 400)
        self.assertEqual(self.request('POST', '/v1/plan', '{"model_id":"missing"}')[0], 404)
        self.assertEqual(self.request('GET', '/unknown')[0], 404)
        self.assertEqual(self.request('POST', '/v1/plan', 'x' * 4097)[0], 413)

    def test_plan_and_audit(self):
        with patch('apps.fmm.__main__.resources', return_value=telemetry()):
            status, body = self.request('POST', '/v1/plan', '{"model_id":"test"}')
        self.assertEqual(status, 200)
        self.assertFalse(body['executable'])
        audit = self.request('GET', '/v1/audit')[1]
        self.assertFalse(audit['persistent'])
        self.assertNotIn(self.token, json.dumps(audit))

    def test_bind_and_token_validation(self):
        for address, token in [(('0.0.0.0', 0), self.token), (('127.0.0.1', 0), ''),
                               (('127.0.0.1', 0), 'é' * 40)]:
            with self.assertRaises(ValueError):
                Server(address, {}, [], token)


if __name__ == '__main__':
    unittest.main()
