"""Fetches available versions from GitHub API."""

import re
import requests
from typing import Any, Optional


def _version_sort_key(ver: str) -> tuple[Any, ...]:
    """Build a comparable tuple so newer versions sort higher. Suffixes (a, b, …) are newer than base: 1.2.0 < 1.2.0a < 1.2.0b < 1.2.1."""
    parts = re.split(r"[-.]", ver)
    key = []
    for p in parts:
        match = re.match(r"^(\d*)(.*)$", p)
        num_str = match.group(1) if match else ""
        suffix = match.group(2) if match else p
        num = int(num_str) if num_str else 0
        key.append((num, suffix))
    return tuple(key)


def _fetch_all_tags(owner: str, repo: str, headers: dict) -> list[dict]:
    """Fetch all tags from GitHub API (paginated). Returns list of tag objects."""
    tags = []
    page = 1
    per_page = 100
    while True:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/tags?per_page={per_page}&page={page}"
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                break
            chunk = response.json()
            if not chunk:
                break
            tags.extend(chunk)
            if len(chunk) < per_page:
                break
            page += 1
        except Exception:
            break
    return tags


def get_owner_repo(repo_url: str) -> tuple[str, str] | None:
    """Extract owner and repo from GitHub URL. Returns (owner, repo) or None."""
    if not repo_url or "github.com" not in repo_url:
        return None
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return None
    owner = parts[-2]
    repo = parts[-1].replace(".git", "")
    return (owner, repo)


def version_gt(a: str, b: str) -> bool:
    """Return True if version a is strictly newer than b (e.g. 1.2.1 > 1.2.0b)."""
    va = (a or "").lstrip("v").strip()
    vb = (b or "").lstrip("v").strip()
    if not va or not vb:
        return False
    return _version_sort_key(va) > _version_sort_key(vb)


def _get_releases_sorted(repo_url: str, token: str, limit: int = 50) -> list[dict]:
    """Fetch releases from GitHub API and return them sorted by version descending (newest first)."""
    parsed = get_owner_repo(repo_url)
    if not parsed:
        return []

    owner, repo = parsed
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    releases = []
    page = 1
    per_page = 30
    try:
        while len(releases) < limit:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page={per_page}&page={page}"
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                break
            chunk = response.json()
            if not chunk:
                break
            for r in chunk:
                ver = (r.get("tag_name") or "").lstrip("v")
                if ver:
                    releases.append({
                        "version": ver,
                        "prerelease": r.get("prerelease", False),
                    })
            if len(chunk) < per_page:
                break
            page += 1
    except Exception:
        pass

    releases.sort(key=lambda x: _version_sort_key(x["version"]), reverse=True)
    return releases[:limit]


def get_latest_version(repo_url: str, token: str, include_prerelease: bool = False) -> Optional[str]:
    """Get latest version from GitHub releases or tags. If include_prerelease is False, returns latest non-prerelease only."""
    parsed = get_owner_repo(repo_url)
    if not parsed:
        return None

    owner, repo = parsed
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    releases = _get_releases_sorted(repo_url, token)
    if releases:
        if include_prerelease:
            return releases[0]["version"]
        for r in releases:
            if not r["prerelease"]:
                return r["version"]
        return None

    # Fallback to tags (no prerelease info; treat all as release)
    try:
        tags = _fetch_all_tags(owner, repo, headers)
        if tags:
            sorted_tags = sorted(
                tags,
                key=lambda t: _version_sort_key((t.get("name") or "").lstrip("v")),
                reverse=True,
            )
            return sorted_tags[0].get("name", "").lstrip("v")
    except Exception:
        pass

    return None


def get_latest_stable_and_prerelease(repo_url: str, token: str) -> tuple[Optional[str], Optional[str]]:
    """Return (latest_stable_version, latest_prerelease_version). Either may be None."""
    releases = _get_releases_sorted(repo_url, token)
    if releases:
        latest_stable = next((r["version"] for r in releases if not r["prerelease"]), None)
        latest_prerelease = next((r["version"] for r in releases if r["prerelease"]), None)
        return (latest_stable, latest_prerelease)

    parsed = get_owner_repo(repo_url)
    if not parsed:
        return (None, None)
    owner, repo = parsed
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        tags = _fetch_all_tags(owner, repo, headers)
        if tags:
            sorted_tags = sorted(
                tags,
                key=lambda t: _version_sort_key((t.get("name") or "").lstrip("v")),
                reverse=True,
            )
            ver = sorted_tags[0].get("name", "").lstrip("v")
            return (ver, None)
    except Exception:
        pass
    return (None, None)


def get_available_versions(repo_url: str, token: str, limit: int = 10) -> list[dict]:
    """Get list of available versions from GitHub. Returns list of {version, name, published_at, prerelease}."""
    parsed = get_owner_repo(repo_url)
    if not parsed:
        return []

    owner, repo = parsed
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    versions = []

    # Try releases first
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            releases = response.json()
            for r in releases[:limit]:
                ver = r.get("tag_name", "").lstrip("v")
                if ver:
                    versions.append({
                        "version": ver,
                        "name": r.get("name", ver),
                        "published_at": r.get("published_at", ""),
                        "prerelease": r.get("prerelease", False),
                    })
    except Exception:
        pass

    # Fallback to tags: fetch all, sort by version (newest first), take limit
    if not versions:
        try:
            tags = _fetch_all_tags(owner, repo, headers)
            if tags:
                sorted_tags = sorted(
                    tags,
                    key=lambda t: _version_sort_key((t.get("name") or "").lstrip("v")),
                    reverse=True,
                )
                for t in sorted_tags[:limit]:
                    ver = t.get("name", "").lstrip("v")
                    if ver:
                        versions.append({
                            "version": ver,
                            "name": ver,
                            "published_at": "",
                            "prerelease": False,
                        })
        except Exception:
            pass

    # Sort by version descending so newest is first
    versions.sort(key=lambda x: _version_sort_key(x["version"]), reverse=True)
    return versions
