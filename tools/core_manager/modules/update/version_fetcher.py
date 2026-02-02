"""Fetches available versions from GitHub API."""

import re
import requests
from typing import Any, Optional


def _version_sort_key(ver: str) -> tuple[Any, ...]:
    """Build a comparable tuple so newer versions sort higher (e.g. 1.1.0-2beta > 1.0.3 > 1.0.2c-13)."""
    parts = re.split(r"[-.]", ver)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((1, int(p)))
        else:
            key.append((0, p))
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


def get_latest_version(repo_url: str, token: str) -> Optional[str]:
    """Get latest version from GitHub releases or tags."""
    parsed = get_owner_repo(repo_url)
    if not parsed:
        return None

    owner, repo = parsed
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    # Try releases/latest first
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            tag = data.get("tag_name")
            return tag.lstrip("v") if tag else None
    except Exception:
        pass

    # Fallback to tags: fetch all, sort by version (newest first)
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

    return versions
