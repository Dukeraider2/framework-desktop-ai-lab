"""Repository-scoped, read-only GitHub App client (REST API v2022-11-28)."""

from __future__ import annotations

import base64
import http.client
import json
import os
import re
import socket
import ssl
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote, urlsplit

from .evidence import Evidence, utc_now


API_HOST = "api.github.com"
REPOSITORY = "Dukeraider2/framework-desktop-ai-lab"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 100
MAX_FILE_BYTES = 512 * 1024
_VALID_REF = re.compile(r"^[A-Za-z0-9._/-]{1,128}$")


def _repository_url(value: Any) -> str | None:
    """Accept links only to this repository's canonical GitHub web pages."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.port not in {None, 443}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or not parsed.path.startswith(f"/{REPOSITORY}")):
            return None
    except ValueError:
        return None
    return value


class GitHubProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubSettings:
    app_id: str
    installation_id: str
    private_key_credential: str
    proxy_socket: str
    repository: str = REPOSITORY

    def __post_init__(self) -> None:
        if self.repository != REPOSITORY:
            raise ValueError("GitHub provider is pinned to the approved repository")
        if not self.app_id.isdigit() or not self.installation_id.isdigit():
            raise ValueError("GitHub App identifiers must be numeric")


class UnixConnectHTTPS:
    """TLS client tunneled through a local CONNECT proxy; never opens Internet sockets itself."""

    def __init__(self, proxy_socket: str, timeout: float = 12.0):
        self.proxy_socket = proxy_socket
        self.timeout = timeout

    def request(self, method: str, path: str, headers: dict[str, str], body: bytes | None = None) -> tuple[int, dict[str, str], bytes]:
        if method not in {"GET", "POST"} or not path.startswith("/") or "\r" in path or "\n" in path:
            raise GitHubProviderError("invalid GitHub API request")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self.proxy_socket)
            sock.sendall(f"CONNECT {API_HOST}:443 HTTP/1.1\r\nHost: {API_HOST}:443\r\n\r\n".encode("ascii"))
            response = bytearray()
            while b"\r\n\r\n" not in response and len(response) < 8192:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response.extend(chunk)
            if b"\r\n\r\n" not in response or not bytes(response).startswith(b"HTTP/1.1 200 "):
                raise GitHubProviderError("GitHub egress proxy refused the fixed API destination")
            # The proxy may have sent bytes after its CONNECT headers; a conforming proxy does
            # not, and treating unexpected bytes as TLS data would weaken framing assumptions.
            if bytes(response).split(b"\r\n\r\n", 1)[1]:
                raise GitHubProviderError("unexpected bytes from GitHub egress proxy")
            tls = ssl.create_default_context().wrap_socket(sock, server_hostname=API_HOST)
            # HTTPSConnection cannot adopt an established AF_UNIX tunnel; send the request and
            # parse the HTTP response directly on the verified TLS stream instead.
            request_headers = {**headers, "Host": API_HOST, "Connection": "close", "Accept-Encoding": "identity"}
            request_line = f"{method} {path} HTTP/1.1\r\n".encode("ascii")
            header_block = b"".join(f"{key}: {value}\r\n".encode("ascii") for key, value in request_headers.items())
            tls.sendall(request_line + header_block + b"\r\n" + (body or b""))
            response_obj = http.client.HTTPResponse(tls)
            response_obj.begin()
            length = response_obj.getheader("Content-Length")
            if length and int(length) > MAX_RESPONSE_BYTES:
                raise GitHubProviderError("GitHub response exceeded the size limit")
            content = response_obj.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise GitHubProviderError("GitHub response exceeded the size limit")
            return response_obj.status, {k.lower(): v for k, v in response_obj.getheaders()}, content
        except (OSError, ssl.SSLError, http.client.HTTPException, ValueError) as exc:
            if isinstance(exc, GitHubProviderError):
                raise
            raise GitHubProviderError("GitHub API transport failed") from exc
        finally:
            try:
                sock.close()
            except OSError:
                pass


class GitHubAppToken:
    """Mint and cache one-hour repository installation tokens; never log token material."""

    def __init__(self, settings: GitHubSettings, transport: Any, *, clock: Callable[[], float] = time.time):
        self.settings, self.transport, self.clock = settings, transport, clock
        self._token: str | None = None
        self._expires = 0.0

    def _app_jwt(self) -> str:
        now = int(self.clock())
        header = _b64url(b'{"alg":"RS256","typ":"JWT"}')
        payload = _b64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": self.settings.app_id},
                                    separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header}.{payload}".encode("ascii")
        key_path = self.settings.private_key_credential
        if not os.path.isabs(key_path) or ".." in key_path.split("/"):
            raise GitHubProviderError("GitHub App credential path is invalid")
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa
            with open(key_path, "rb") as key_file:
                key_data = key_file.read(64 * 1024 + 1)
            if len(key_data) > 64 * 1024:
                raise ValueError("credential is too large")
            private_key = serialization.load_pem_private_key(key_data, password=None)
            if not isinstance(private_key, rsa.RSAPrivateKey) or private_key.key_size < 2048:
                raise ValueError("credential is not a supported RSA key")
            signed = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        except Exception as exc:
            raise GitHubProviderError("GitHub App signing operation failed") from exc
        return f"{header}.{payload}.{_b64url(signed)}"

    def get(self) -> str:
        if self._token and self.clock() < self._expires - 120:
            return self._token
        path = f"/app/installations/{self.settings.installation_id}/access_tokens"
        status, _, body = self.transport.request(
            "POST", path,
            {"Authorization": f"Bearer {self._app_jwt()}", "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
            b"{}",
        )
        if status not in {200, 201}:
            raise GitHubProviderError(f"GitHub App token request failed with HTTP {status}")
        try:
            data = json.loads(body)
            token = data["token"]
            # Token expiry is normally a GitHub RFC3339 timestamp. Cache conservatively for
            # 45 minutes; a delayed or malformed clock must not extend credential lifetime.
            if not isinstance(token, str) or not token:
                raise ValueError("missing token")
        except (ValueError, KeyError, TypeError) as exc:
            raise GitHubProviderError("GitHub App token response was malformed") from exc
        self._token, self._expires = token, self.clock() + 2700
        return token


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class GitHubProvider:
    """Fixed-operation reader for one repository. Caller input cannot select a host or method."""

    def __init__(self, settings: GitHubSettings, transport: Any | None = None):
        self.settings = settings
        self.transport = transport or UnixConnectHTTPS(settings.proxy_socket)
        self.auth = GitHubAppToken(settings, self.transport)
        owner, name = settings.repository.split("/", 1)
        self._base = f"/repos/{owner}/{name}"

    def _get(self, path: str) -> tuple[dict[str, Any], dict[str, str]]:
        status, headers, body = self.transport.request(
            "GET", path,
            {"Authorization": f"Bearer {self.auth.get()}", "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "frameworklab-project-awareness"},
        )
        if status != 200:
            raise GitHubProviderError(f"GitHub read failed with HTTP {status}")
        try:
            data = json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubProviderError("GitHub returned malformed JSON") from exc
        if not isinstance(data, (dict, list)):
            raise GitHubProviderError("GitHub returned an unexpected response shape")
        return data, headers

    def call(self, operation: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        args = args or {}
        if not isinstance(args, dict):
            raise GitHubProviderError("tool arguments must be an object")
        if operation == "repository_summary":
            data, _ = self._get(self._base)
            result = {key: data.get(key) for key in ("full_name", "description", "default_branch", "visibility", "updated_at")}
            result["html_url"] = _repository_url(data.get("html_url"))
            return self._result(operation, [result], source_url=result["html_url"])
        if operation == "read_document":
            path = args.get("path")
            ref = args.get("ref", "")
            if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/") or len(path) > 240:
                raise GitHubProviderError("repository path is invalid")
            if ref and (not isinstance(ref, str) or not _VALID_REF.fullmatch(ref)):
                raise GitHubProviderError("repository ref is invalid")
            api_path = f"{self._base}/contents/{quote(path, safe='/')}" + (f"?ref={quote(ref, safe='')}" if ref else "")
            data, _ = self._get(api_path)
            if not isinstance(data, dict) or data.get("type") != "file" or not isinstance(data.get("content"), str):
                raise GitHubProviderError("requested repository entry is not a file")
            content = base64.b64decode(data["content"], validate=False)
            if len(content) > MAX_FILE_BYTES:
                raise GitHubProviderError("repository file exceeds the read limit")
            import codecs
            text = codecs.decode(content, "utf-8", errors="replace")
            page_url = _repository_url(data.get("html_url"))
            return self._result(operation, [{"path": path, "ref": ref or "default branch",
                                             "content": text, "html_url": page_url,
                                             "blob_sha": data.get("sha")}], source_url=page_url)
        if operation == "branches":
            data, headers = self._get(f"{self._base}/branches?per_page={MAX_ITEMS}")
            return self._result(operation, self._bounded_list(data), partial=self._next_page(headers), source_url=f"https://github.com/{REPOSITORY}/branches")
        if operation == "recent_commits":
            limit = _bounded_int(args.get("limit", 10), 1, 30)
            branch = args.get("branch", "")
            if branch and (not isinstance(branch, str) or not _VALID_REF.fullmatch(branch)):
                raise GitHubProviderError("branch name is invalid")
            path = f"{self._base}/commits?per_page={limit}" + (f"&sha={quote(branch, safe='')}" if branch else "")
            data, headers = self._get(path)
            return self._result(operation, [
                {"sha": row.get("sha"), "html_url": _repository_url(row.get("html_url")),
                 "message": ((row.get("commit") or {}).get("message") or "").splitlines()[0][:500],
                 "date": ((row.get("commit") or {}).get("author") or {}).get("date")}
                for row in self._bounded_list(data)
            ], partial=self._next_page(headers), source_url=f"https://github.com/{REPOSITORY}/commits/{quote(branch or 'main', safe='')}")
        if operation in {"issues", "pull_requests"}:
            state = args.get("state", "open")
            if state not in {"open", "closed", "all"}:
                raise GitHubProviderError("state must be open, closed, or all")
            endpoint = "issues" if operation == "issues" else "pulls"
            data, headers = self._get(f"{self._base}/{endpoint}?state={state}&per_page={MAX_ITEMS}&sort=updated&direction=desc")
            rows = self._bounded_list(data)
            if operation == "issues":
                rows = [row for row in rows if "pull_request" not in row]
            safe_rows = []
            for row in rows:
                safe_rows.append({key: (_repository_url(row.get(key)) if key == "html_url" else row.get(key))
                                  for key in ("number", "title", "state", "state_reason", "html_url", "updated_at", "closed_at", "labels", "draft", "merged_at") if key in row})
            listing = "issues" if operation == "issues" else "pulls"
            return self._result(f"{operation}_{state}", safe_rows, partial=self._next_page(headers), source_url=f"https://github.com/{REPOSITORY}/{listing}?q=is%3A{state}")
        if operation == "pull_request_reviews":
            number = _bounded_int(args.get("number"), 1, 2**31 - 1)
            data, headers = self._get(f"{self._base}/pulls/{number}/reviews?per_page={MAX_ITEMS}")
            reviews = [{key: (_repository_url(row.get(key)) if key == "html_url" else row.get(key))
                        for key in ("state", "submitted_at", "commit_id", "html_url") if key in row} for row in self._bounded_list(data)]
            result = self._result(f"pull_request_reviews_{number}", reviews, partial=self._next_page(headers), source_url=f"https://github.com/{REPOSITORY}/pull/{number}/reviews")
            result["subject"] = number
            return result
        if operation == "tree":
            ref = args.get("ref", "")
            if not isinstance(ref, str) or not _VALID_REF.fullmatch(ref):
                raise GitHubProviderError("tree ref is invalid")
            data, _ = self._get(f"{self._base}/git/trees/{quote(ref, safe='')}?recursive=1")
            if data.get("truncated"):
                raise GitHubProviderError("Git tree was truncated; refusing incomplete inventory")
            rows = self._bounded_list(data.get("tree"))
            return self._result(operation, [{"path": row.get("path"), "type": row.get("type"), "sha": row.get("sha")} for row in rows], source_url=f"https://github.com/{REPOSITORY}/tree/{quote(ref, safe='')}")
        raise GitHubProviderError("unknown read-only GitHub operation")

    @staticmethod
    def _bounded_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list) or len(value) > MAX_ITEMS:
            raise GitHubProviderError("GitHub list is malformed or exceeded the item limit")
        if any(not isinstance(row, dict) for row in value):
            raise GitHubProviderError("GitHub list contains malformed records")
        return value

    @staticmethod
    def _next_page(headers: dict[str, str]) -> str | None:
        link = headers.get("link", "")
        if 'rel="next"' in link:
            # Return a boolean marker only; the report never follows caller-selected URLs.
            return "additional pages exist; result set is partial"
        return None

    @staticmethod
    def _result(operation: str, records: list[dict[str, Any]], *, partial: str | None = None,
                source_url: str | None = None) -> dict[str, Any]:
        now = utc_now()
        evidence = Evidence(evidence_id=f"github:{operation}:{now}", provider="github",
                            kind=operation, observed_at=now,
                            summary=f"GitHub returned {len(records)} record(s) for {operation}.",
                            source_url=source_url or f"https://github.com/{REPOSITORY}", source_ref=operation)
        return {"provider_id": "github", "schema_version": "1.0", "observed_at": now,
                "status": "partial" if partial else "ok", "coverage": [operation],
                "records": records, "partial_reason": partial, "evidence": [evidence.as_dict()]}


def _bounded_int(value: Any, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise GitHubProviderError("numeric input is outside its permitted range")
    return value
