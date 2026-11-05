"""CLI and authenticated loopback HTTP interface for the read-only prototype."""
import argparse
from collections import deque
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import time

from .core import DeploymentController, inventory, load_registry, plan, podman_inventory, resources, service_observations


class Server(HTTPServer):
    def __init__(self, address, registry, roots, token, safety_bytes=8_000_000_000):
        if address[0] != '127.0.0.1':
            raise ValueError('FMM binds only to IPv4 loopback')
        if not isinstance(token, str) or len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError('supply a non-whitespace ASCII bearer token of at least 32 characters')
        self.registry, self.roots, self.token = registry, roots, token
        self.safety_bytes = safety_bytes
        self.audit = deque(maxlen=1000)
        self.controller = DeploymentController()
        super().__init__(address, Handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


class Handler(BaseHTTPRequestHandler):
    server_version = 'FMM/0.1'
    sys_version = ''

    def log_message(self, *_args):
        pass  # Do not log request bodies, paths or authorization headers.

    def respond(self, status, payload):
        body = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        auth = self.headers.get('Authorization', '')
        return auth.isascii() and hmac.compare_digest(auth, 'Bearer ' + self.server.token)

    def dispatch(self):
        status, payload = 500, {'error': 'internal error'}
        try:
            if not self.authorized():
                status, payload = 401, {'error': 'bearer authentication required'}
            elif self.headers.get('Origin') is not None:
                status, payload = 403, {'error': 'browser origins prohibited'}
            else:
                status, payload = self.route()
        except (ValueError, UnicodeError, json.JSONDecodeError):
            status, payload = 400, {'error': 'invalid request'}
        except OSError:
            status, payload = 503, {'error': 'observation unavailable'}
        # Bounded process-local audit; no secrets or client-supplied values retained.
        self.server.audit.append({'at': time.time(), 'method': self.command,
                                  'status': status, 'operation': getattr(self, 'operation', 'unknown')})
        self.respond(status, payload)

    def route(self):
        server = self.server
        if self.command == 'GET':
            self.operation = {'/health': 'health', '/v1/registry': 'registry',
                              '/v1/inventory': 'inventory', '/v1/status': 'status',
                              '/v1/audit': 'audit', '/v1/services': 'services'}.get(self.path, 'unknown')
            if self.path == '/health':
                return 200, {'status': 'ok', 'mode': 'read-only', 'controller_enabled': False}
            if self.path == '/v1/registry':
                return 200, server.registry
            if self.path == '/v1/inventory':
                return 200, inventory(server.roots)
            if self.path == '/v1/status':
                return 200, {'resources': resources(), 'podman': podman_inventory()}
            if self.path == '/v1/services':
                return 200, service_observations()
            if self.path == '/v1/audit':
                return 200, {'events': list(server.audit), 'persistent': False, 'capacity': 1000}
            return 404, {'error': 'unknown endpoint'}
        if self.path not in {'/v1/plan', '/v1/load', '/v1/unload', '/v1/switch'}:
            return 404, {'error': 'unknown endpoint'}
        self.operation = self.path.rsplit('/', 1)[-1]
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != 'application/json':
            return 400, {'error': 'JSON Content-Length request required'}
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) != 1:
            return 400, {'error': 'one Content-Length required'}
        length = int(lengths[0])
        if not 0 < length <= 4096:
            return 413, {'error': 'request size limit 4096 bytes'}
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict) or set(body) != {'model_id'} or not isinstance(body['model_id'], str):
            return 400, {'error': 'expected model_id only'}
        model = next((m for m in server.registry['models'] if m['id'] == body['model_id']), None)
        if model is None:
            return 404, {'error': 'unknown model'}
        if self.path == '/v1/plan':
            return 200, plan(model, resources(), server.safety_bytes)
        return 409, server.controller.request(self.operation, model['id'])

    do_GET = dispatch
    do_POST = dispatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=Path('registry/fmm.json'))
    parser.add_argument('--root', type=Path, action='append', default=[])
    parser.add_argument('--safety-bytes', type=int, default=8_000_000_000)
    parser.add_argument('command', choices=['validate', 'inventory', 'status', 'services', 'serve'])
    parser.add_argument('--hashes', action='store_true', help='opt-in full-file SHA256 for CLI inventory')
    parser.add_argument('--port', type=int, default=18090)
    args = parser.parse_args()
    if args.safety_bytes < 0:
        parser.error('safety margin must be nonnegative')
    try:
        registry = load_registry(args.registry)
        if args.command == 'validate':
            output = {'valid': True, 'models': len(registry['models'])}
        elif args.command == 'inventory':
            output = inventory(args.root, args.hashes)
        elif args.command == 'services':
            output = service_observations()
        elif args.command == 'status':
            output = {'resources': resources(), 'podman': podman_inventory()}
        else:
            with Server(('127.0.0.1', args.port), registry, args.root,
                        os.environ.get('FMM_API_TOKEN'), args.safety_bytes) as server:
                server.serve_forever()
            return
        print(json.dumps(output, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'FMM: {type(error).__name__}; check registry, permissions and token configuration\n')


if __name__ == '__main__':
    main()
