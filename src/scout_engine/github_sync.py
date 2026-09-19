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

    def _list_paginated(self, path: str, *, per_page: int = 100) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            batch = self._request(
                "GET",
                f"{path}{separator}per_page={per_page}&page={page}",
            )
            if not isinstance(batch, list):
                raise RuntimeError(f"GitHub list endpoint returned non-list payload for {path}")
            items.extend(batch)
            if len(batch) < per_page:
                return items
            page += 1

    def list_labels(self) -> list[dict[str, Any]]:
        return self._list_paginated("/labels")

    def list_issues(self, state: str = "all") -> list[dict[str, Any]]:
        return self._list_paginated(f"/issues?state={state}")

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

    def sync_issue_labels(self, issue_number: int, desired: list[str]) -> None:
        issue = self._request("GET", f"/issues/{issue_number}")
        managed = {"job", "hackathon", "urgent", "high-fit", "suppressed"}
        labels = [
            x["name"]
            for x in issue.get("labels", [])
            if x["name"] not in managed and not x["name"].startswith("stage/")
        ]
        labels.extend(desired)
        self._request("PATCH", f"/issues/{issue_number}", {"labels": sorted(set(labels))})

    def update_issue_stage_label(self, issue_number: int, stage: Stage) -> None:
        issue = self._request("GET", f"/issues/{issue_number}")
        labels = [x["name"] for x in issue.get("labels", []) if not x["name"].startswith("stage/")]
        labels.append(f"stage/{stage.value}")
        self._request("PATCH", f"/issues/{issue_number}", {"labels": labels})

    def create_issue_for(self, opportunity: Opportunity, labels: list[str]) -> int:
        title = f"[Score {opportunity.fit_score or 0:.1f}/10] {opportunity.company} — {opportunity.title}"
        body = [
            f"**Source:** {opportunity.canonical_url}",
            f"**Apply:** {opportunity.application_url or opportunity.canonical_url}",
            f"**Type:** {opportunity.kind.value}",
            f"**Location:** {opportunity.location or 'Unknown'}",
            f"**Fit:** {opportunity.fit_score or 0:.1f}/10",
            f"**Confidence:** {(opportunity.confidence_score or 0):.0%}",
            f"**Priority:** {opportunity.priority_score or 0:.1f}/10",
            f"**Extraction:** {opportunity.extraction_method or opportunity.source} ({opportunity.source_confidence:.0%} source trust)",
        ]
        if opportunity.posted_at_utc:
            body.append(f"**Posted:** {opportunity.posted_at_utc}")
        if opportunity.deadline_utc:
            body.append(f"**Deadline:** {opportunity.deadline_utc}")
        if opportunity.compensation and opportunity.compensation.verified:
            comp = opportunity.compensation
            raw = f"{comp.currency} {comp.min_annual:,.0f}" if comp.min_annual is not None else comp.currency
            if comp.max_annual is not None:
                raw += f"–{comp.max_annual:,.0f}"
            body.append(f"**Compensation:** {raw} ({comp.source or 'verified source'})")
            if comp.min_lpa_inr is not None and comp.currency.upper() != "INR":
                body.append(
                    f"**INR floor:** ₹{comp.min_lpa_inr:.2f} LPA via ECB {comp.fx_rate_date or 'rate'}"
                )
        if opportunity.kind.value == "internship":
            if opportunity.internship_duration_months is not None:
                body.append(f"**Internship duration:** {opportunity.internship_duration_months:g} months")
            body.append(f"**PPO / conversion:** {opportunity.conversion_signal}")
            if opportunity.conversion_evidence:
                body.append(f"**Conversion evidence:** {opportunity.conversion_evidence[0]}")
        body.extend(["", "### Evidence"])
        if opportunity.evidence:
            for skill, entries in opportunity.evidence.items():
                body.append(f"- **{skill}**: " + "; ".join(entries[:3]))
        else:
            body.append("- No structured evidence extracted.")
        if opportunity.missing_requirements:
            body.extend(["", "### Missing / weak evidence"])
            body.extend(f"- {item}" for item in opportunity.missing_requirements)
        if opportunity.field_provenance:
            body.extend(["", "### Provenance"])
            body.extend(
                f"- `{field}` ← {source}"
                for field, source in sorted(opportunity.field_provenance.items())
            )
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
