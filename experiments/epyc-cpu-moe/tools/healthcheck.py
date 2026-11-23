#!/usr/bin/env python3
"""Read-only loopback health check of an eventually deployed llama-server."""
from __future__ import annotations
import json
import urllib.request


def main():
    url = 'http://127.0.0.1:8088/health'
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            print(json.dumps({'url': url, 'http_status': response.status,
                              'body': response.read(2048).decode('utf-8', 'replace')}, indent=2))
    except Exception as exc:
        print(f'No confirmed local inference server: {exc}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
