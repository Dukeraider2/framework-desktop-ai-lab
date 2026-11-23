"""Generate a reviewed systemd allowlist from GitHub's public meta endpoint.

The script only prints a drop-in. It never installs files, creates a marker,
starts a service, reads credentials, or edits firewall/systemd state.
"""

from __future__ import annotations

import ipaddress
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


META_URL = "https://api.github.com/meta"
MAX_META_BYTES = 1024 * 1024
MAX_CIDRS = 512


class PolicyError(RuntimeError):
    pass


def parse_api_networks(payload: bytes) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    if not isinstance(payload, bytes) or len(payload) > MAX_META_BYTES:
        raise PolicyError("GitHub meta response is absent or too large")
    try:
        parsed: Any = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PolicyError("GitHub meta response is malformed") from exc
    values = parsed.get("api") if isinstance(parsed, dict) else None
    if not isinstance(values, list) or not values or len(values) > MAX_CIDRS:
        raise PolicyError("GitHub meta response has no bounded API CIDR list")
    networks = set()
    for value in values:
        if not isinstance(value, str) or len(value) > 64:
            raise PolicyError("GitHub API CIDR entry is invalid")
        try:
            network = ipaddress.ip_network(value, strict=True)
        except ValueError as exc:
            raise PolicyError("GitHub API CIDR entry is invalid") from exc
        if not network.network_address.is_global or network.prefixlen == 0:
            raise PolicyError("GitHub API CIDR is not a globally routed narrow range")
        networks.add(network)
    return sorted(networks, key=lambda net: (net.version, int(net.network_address), net.prefixlen))


def parse_resolvers(text: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    result = set()
    for line in text.splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) == 2 and fields[0] == "nameserver":
            try:
                result.add(ipaddress.ip_address(fields[1]))
            except ValueError as exc:
                raise PolicyError("resolver address in resolv.conf is not a literal IP") from exc
    if not result:
        raise PolicyError("no DNS resolver is configured")
    return sorted(result, key=lambda addr: (addr.version, int(addr)))


def render_dropin(networks: list[ipaddress._BaseNetwork], resolvers: list[ipaddress._BaseAddress]) -> str:
    rows = [
        "# Generated from the GitHub REST meta API and this host's resolv.conf.",
        "# Review current values before installing; this file is a manually refreshed snapshot.",
        "[Service]",
        "IPAddressDeny=any",
    ]
    for network in networks:
        rows.append(f"IPAddressAllow={network.with_prefixlen}")
    for resolver in resolvers:
        prefix = 32 if resolver.version == 4 else 128
        rows.append(f"IPAddressAllow={resolver}/{prefix}")
    return "\n".join(rows) + "\n"


def fetch_meta() -> bytes:
    request = urllib.request.Request(META_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "frameworklab-github-egress-policy/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise PolicyError("GitHub meta endpoint returned a non-success status")
            payload = response.read(MAX_META_BYTES + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise PolicyError("GitHub meta endpoint could not be retrieved") from exc
    if len(payload) > MAX_META_BYTES:
        raise PolicyError("GitHub meta response is too large")
    return payload


def main() -> int:
    try:
        networks = parse_api_networks(fetch_meta())
        resolvers = parse_resolvers(Path("/etc/resolv.conf").read_text(encoding="ascii"))
        sys.stdout.write(render_dropin(networks, resolvers))
        return 0
    except (OSError, PolicyError) as exc:
        print(f"egress policy generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
