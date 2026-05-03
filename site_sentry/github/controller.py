# site_sentry/github/controller.py
"""
Complete GitHub controller for Site-Sentry.
Uses GitHub REST API v3 to create branches, commit files, and open PRs.
"""
from __future__ import annotations
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
import structlog

logger = structlog.get_logger()


class GitHubError(Exception):
    """GitHub API error with status code."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _response_error_message(r: requests.Response) -> str:
    try:
        data = r.json()
        if isinstance(data, dict) and "message" in data:
            return str(data["message"])
    except Exception:
        pass
    return r.text or f"HTTP {r.status_code}"


class GitHubController:
    """Full GitHub integration for creating fix branches and PRs."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        if not token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN in .env")
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        logger.info("GitHub controller initialized", repo=f"{repo_owner}/{repo_name}")

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}/repos/{self.repo_owner}/{self.repo_name}{path}"

    @staticmethod
    def _encode_content_path(file_path: str) -> str:
        return "/".join(quote(segment, safe="") for segment in file_path.split("/"))

    def _get(self, path: str) -> Dict:
        r = requests.get(self._url(path), headers=self._headers, timeout=60)
        if not r.ok:
            raise GitHubError(
                f"GET {path} failed: {_response_error_message(r)}", r.status_code
            )
        return r.json()

    def _post(self, path: str, payload: Dict) -> Dict:
        r = requests.post(
            self._url(path), json=payload, headers=self._headers, timeout=60
        )
        if not r.ok:
            raise GitHubError(
                f"POST {path} failed: {_response_error_message(r)}", r.status_code
            )
        return r.json()

    def _put(self, path: str, payload: Dict) -> Dict:
        r = requests.put(
            self._url(path), json=payload, headers=self._headers, timeout=60
        )
        if not r.ok:
            raise GitHubError(
                f"PUT {path} failed: {_response_error_message(r)}", r.status_code
            )
        return r.json()

    def get_default_branch_sha(self, branch: str) -> str:
        data = self._get(f"/git/refs/heads/{quote(branch, safe='')}")
        return data["object"]["sha"]

    def create_branch(self, branch_name: str, base_branch: str = "main") -> Dict:
        try:
            base_sha = self.get_default_branch_sha(base_branch)
            result = self._post(
                "/git/refs",
                {"ref": f"refs/heads/{branch_name}", "sha": base_sha},
            )
            logger.info("Branch created", branch=branch_name, from_branch=base_branch)
            return {"branch": branch_name, "sha": result["object"]["sha"]}
        except GitHubError as e:
            if e.status_code == 422:
                logger.warning("Branch already exists", branch=branch_name)
                return {"branch": branch_name, "already_exists": True}
            raise

    def get_file(self, file_path: str, branch: str) -> Optional[Dict]:
        enc = self._encode_content_path(file_path)
        try:
            data = self._get(f"/contents/{enc}?ref={quote(branch, safe='')}")
            content = base64.b64decode(data["content"]).decode("utf-8")
            return {"content": content, "sha": data["sha"], "path": file_path}
        except GitHubError as e:
            if e.status_code == 404:
                return None
            raise

    def commit_file(
        self,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        existing_sha: Optional[str] = None,
    ) -> Dict:
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload: Dict[str, Any] = {
            "message": commit_message,
            "content": encoded,
            "branch": branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha

        enc = self._encode_content_path(file_path)
        result = self._put(f"/contents/{enc}", payload)
        logger.info("File committed", path=file_path, branch=branch)
        return {
            "path": file_path,
            "branch": branch,
            "commit_sha": result["commit"]["sha"],
        }

    def commit_files(
        self,
        changes: List[Dict[str, str]],
        branch: str,
        commit_message_prefix: str = "fix",
    ) -> List[Dict]:
        results = []
        for change in changes:
            path = change["path"]
            content = change["content"]
            existing = self.get_file(path, branch)
            existing_sha = existing["sha"] if existing else None
            commit_msg = f"{commit_message_prefix}: update {path}"
            result = self.commit_file(
                file_path=path,
                content=content,
                branch=branch,
                commit_message=commit_msg,
                existing_sha=existing_sha,
            )
            results.append(result)
        return results

    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str = "",
        base_branch: str = "main",
        labels: Optional[List[str]] = None,
        draft: bool = False,
    ) -> Dict:
        payload = {
            "title": title,
            "head": branch_name,
            "base": base_branch,
            "body": body,
            "draft": draft,
        }
        result = self._post("/pulls", payload)
        pr_number = result["number"]
        pr_url = result["html_url"]

        if labels:
            try:
                lr = requests.post(
                    self._url(f"/issues/{pr_number}/labels"),
                    json={"labels": labels},
                    headers=self._headers,
                    timeout=60,
                )
                if not lr.ok:
                    logger.warning(
                        "Failed to add PR labels",
                        status=lr.status_code,
                        detail=_response_error_message(lr),
                    )
            except Exception as ex:
                logger.warning("Labels request failed", error=str(ex))

        logger.info("Pull request created", pr=pr_number, url=pr_url)
        return {
            "pr_number": pr_number,
            "url": pr_url,
            "title": title,
            "branch": branch_name,
            "base": base_branch,
        }

    def branch_exists(self, branch_name: str) -> bool:
        try:
            self.get_default_branch_sha(branch_name)
            return True
        except GitHubError:
            return False

    @staticmethod
    def generate_branch_name(prefix: str = "sentry/fix") -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{prefix}-{timestamp}"
