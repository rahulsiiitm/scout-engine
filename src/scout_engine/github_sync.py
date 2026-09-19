from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import Opportunity, Stage


@dataclass(slots=True)
class GitHubClient:
    repository: str
    token: str

    @classmethod
    def from_env(cls) -> "GitHubClient":
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")
        if not repo or not token:
            raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
        return cls(repo, token)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"https://api.github.com/repos/{self.repository}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "scout-engine",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"GitHub API {exc.code}: {body}") from exc

    def list_labels(self) -> list[dict[str, Any]]:
        return self._request("GET", "/labels?per_page=100")

    def ensure_labels(self, labels: list[dict[str, str]]) -> None:
        existing = {item["name"] for item in self.list_labels()}
        for label in labels:
            if label["name"] in existing:
                continue
            self._request(
                "POST",
                "/labels",
                {
                    "name": label["name"],
                    "description": label.get("description", ""),
                    "color": label.get("color", "ededed"),
                },
            )

    def update_issue_stage_label(self, issue_number: int, stage: Stage) -> None:
        issue = self._request("GET", f"/issues/{issue_number}")
        labels = [x["name"] for x in issue.get("labels", []) if not x["name"].startswith("stage/")]
        labels.append(f"stage/{stage.value}")
        self._request("PATCH", f"/issues/{issue_number}", {"labels": labels})

    def create_issue_for(self, opportunity: Opportunity, labels: list[str]) -> int:
        title = f"[Score {opportunity.fit_score or 0:.1f}/10] {opportunity.company} — {opportunity.title}"
        body = [
            f"**Source:** {opportunity.canonical_url}",
            f"**Fit:** {opportunity.fit_score or 0:.1f}/10",
            f"**Confidence:** {(opportunity.confidence_score or 0):.0%}",
            f"**Priority:** {opportunity.priority_score or 0:.1f}/10",
            "",
            "### Evidence",
        ]
        if opportunity.evidence:
            for skill, entries in opportunity.evidence.items():
                body.append(f"- **{skill}**: " + "; ".join(entries[:3]))
        else:
            body.append("- No structured evidence extracted.")

        if opportunity.missing_requirements:
            body.extend(["", "### Missing / weak evidence"])
            body.extend(f"- {item}" for item in opportunity.missing_requirements)

        body.extend(
            [
                "",
                f"**Stable ID:** `{opportunity.id}`",
                "",
                "The canonical lifecycle state lives in `data/opportunities.json`.",
            ]
        )
        result = self._request(
            "POST",
            "/issues",
            {"title": title, "body": "\n".join(body), "labels": labels},
        )
        return int(result["number"])
