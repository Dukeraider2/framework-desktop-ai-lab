"""Non-destructive protocol and upstream failure regression checks; no sockets."""
from collections import deque
import http.client
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from apps.fmm.__main__ import Handler
from apps.fmm.core import DeploymentController, service_observations
from test_fmm import model


class MemoryConnection:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()

    def makefile(self, *args):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


class ProtocolTests(unittest.TestCase):
    def request(self, body=b'', auth=True, path='/v1/plan', method='POST', headers=()):
        self.server = SimpleNamespace(token='x' * 40, registry={'models': [model()]},
                                      roots=[], safety_bytes=8_000_000_000,
                                      controller=DeploymentController(), audit=deque(maxlen=1000))
        lines = [f'{method} {path} HTTP/1.0', 'Content-Type: application/json',
                 f'Content-Length: {len(body)}']
        if auth:
            lines.append('Authorization: Bearer ' + self.server.token)
        lines.extend(headers)
        connection = MemoryConnection(('\r\n'.join(lines) + '\r\n\r\n').encode() + body)
        Handler(connection, ('127.0.0.1', 12345), self.server)
        head, payload = bytes(connection.output).split(b'\r\n\r\n', 1)
        return int(head.split()[1]), json.loads(payload)

    def test_deep_json_is_rejected_and_audited(self):
        status, _ = self.request(b'[' * 1500 + b'0' + b']' * 1500)
        self.assertEqual(status, 400)
        self.assertEqual(self.server.audit[-1]['status'], 400)

    def test_auth_and_disabled_lifecycle(self):
        self.assertEqual(self.request(auth=False, method='GET', path='/health')[0], 401)
        self.assertEqual(self.request(method='GET', path='/health')[0], 200)
        self.assertEqual(self.request(method='GET', path='/health', headers=['Origin: http://example.com'])[0], 403)
        for operation in ('load', 'unload', 'switch'):
            status, payload = self.request(b'{"model_id":"test"}', path='/v1/' + operation)
            self.assertEqual(status, 409)
            self.assertFalse(payload['accepted'])

    def test_json_size_and_framing(self):
        for body, headers, expected in [(b'{', [], 400), (b'x' * 4097, [], 413),
                                         (b'{}', ['Content-Length: 2'], 400),
                                         (b'{}', ['Transfer-Encoding: chunked'], 400)]:
            with self.subTest(expected=expected, headers=headers):
                self.assertEqual(self.request(body, headers=headers)[0], expected)


class UpstreamFailureTests(unittest.TestCase):
    @patch('urllib.request.build_opener')
    def test_http_protocol_failure_does_not_abort_other_probes(self, build):
        response = build.return_value.open.return_value.__enter__.return_value
        response.status = 200
        response.read.side_effect = [http.client.IncompleteRead(b'private')]+[b'{}'] * 10
        result = service_observations()
        self.assertFalse(result['services']['ollama_models']['available'])
        self.assertTrue(result['services']['llama_health']['available'])
        self.assertEqual(build.return_value.open.call_count, 11)
        self.assertNotIn('private', json.dumps(result))

    @patch('urllib.request.build_opener')
    def test_deep_upstream_json_does_not_abort_other_probes(self, build):
        response = build.return_value.open.return_value.__enter__.return_value
        response.status = 200
        response.read.side_effect = [b'[' * 1500 + b'0' + b']' * 1500] + [b'{}'] * 10
        result = service_observations()
        self.assertFalse(result['services']['ollama_models']['available'])
        self.assertTrue(result['services']['llama_health']['available'])
        self.assertEqual(build.return_value.open.call_count, 11)
