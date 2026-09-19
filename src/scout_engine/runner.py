from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import load_profile, load_yaml
from .engine import EngineConfig, evaluate
from .github_sync import GitHubClient
from .models import Decision, Opportunity, Stage
from .sources import AshbyAdapter, GreenhouseAdapter, LeverAdapter, WorkableAdapter
from .sources.base import SourceAdapter
from .state import OpportunityStore


IST = ZoneInfo("Asia/Kolkata")


def _engine_config() -> EngineConfig:
    source_cfg = load_yaml("config/sources.yaml")
    matching = source_cfg.get("matching", {})
    profile = load_profile()
    constraints = profile.get("constraints", {})
    return EngineConfig(
        minimum_score=float(matching.get("minimum_score", 6)),
        urgent_score_floor=float(matching.get("urgent_score_floor", 4)),
        urgent_deadline_days=float(matching.get("urgent_deadline_days", 5)),
        high_fit_score=float(matching.get("high_fit_score", 8)),
        confidence_floor=float(matching.get("confidence_floor", 0.55)),
        minimum_lpa_exclusive=float(constraints.get("full_time_min_lpa_exclusive", 10)),
        candidate_has_publications=bool(constraints.get("research_publications", False)),
        max_years_without_override=float(
            constraints.get("max_years_experience_without_explicit_new_grad_override", 2)
        ),
        dedupe_threshold=float(
            source_cfg.get("dedupe", {}).get("fuzzy_company_title_threshold", 0.86)
        ),
    )


def configured_adapters() -> list[SourceAdapter]:
    boards = load_yaml("config/boards.yaml")
    adapters: list[SourceAdapter] = []
    for item in boards.get("greenhouse", []) or []:
        adapters.append(GreenhouseAdapter(item["company"], item["board"]))
    for item in boards.get("lever", []) or []:
        adapters.append(LeverAdapter(item["company"], item["site"]))
    for item in boards.get("ashby", []) or []:
        adapters.append(AshbyAdapter(item["company"], item["board"]))
    for item in boards.get("workable", []) or []:
        adapters.append(WorkableAdapter(item["company"], item["subdomain"]))
    return adapters


def _append_run_log(source: str, result: str) -> None:
    path = Path("run-log.md")
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    line = f"| {timestamp} | {source} | {result.replace('|', '/')} |\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _append_suppression(opportunity: Opportunity) -> None:
    path = Path("data/suppressions.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": opportunity.id,
        "reason": opportunity.suppression_reason,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _issue_labels(opportunity: Opportunity, cfg: EngineConfig) -> list[str]:
    labels = ["hackathon" if opportunity.kind.value in {"competition", "hackathon"} else "job"]
    if (opportunity.fit_score or 0) >= cfg.high_fit_score:
        labels.append("high-fit")
    if bool(opportunity.metadata.get("urgent")):
        labels.append("urgent")
    if opportunity.decision == Decision.SUPPRESSED:
        labels.append("suppressed")
    else:
        labels.append(f"stage/{opportunity.stage.value}")
    return labels


def scan_structured_sources(*, sync_github: bool = True) -> dict[str, int]:
    profile = load_profile()
    cfg = _engine_config()
    store = OpportunityStore()
    existing = store.load()
    by_id = {item.id: item for item in existing}
    github = None
    if sync_github and os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPOSITORY"):
        github = GitHubClient.from_env()

    counters = {"fetched": 0, "surfaced": 0, "suppressed": 0, "errors": 0}
    for adapter in configured_adapters():
        try:
            fetched = adapter.fetch()
        except Exception as exc:
            counters["errors"] += 1
            _append_run_log(adapter.source_name, f"adapter error: {exc}")
            continue

        counters["fetched"] += len(fetched)
        for raw in fetched:
            old = by_id.get(raw.id)
            if old:
                raw.first_seen_utc = old.first_seen_utc
                raw.stage = old.stage
                raw.issue_number = old.issue_number
                raw.source_urls = old.source_urls
            raw.last_seen_utc = datetime.now(timezone.utc).isoformat()
            raw.last_verified_utc = raw.last_seen_utc
            evaluated = evaluate(
                raw,
                profile=profile,
                existing=list(by_id.values()),
                config=cfg,
            )
            by_id[evaluated.id] = evaluated

            if evaluated.decision == Decision.SURFACED:
                counters["surfaced"] += 1
                if github and evaluated.issue_number is None:
                    issue = github.create_issue_for(evaluated, _issue_labels(evaluated, cfg))
                    evaluated.issue_number = issue
            elif evaluated.decision == Decision.SUPPRESSED:
                counters["suppressed"] += 1
                if old is None:
                    _append_suppression(evaluated)

    store.save(list(by_id.values()))
    return counters


def push_github_issue_labels() -> int:
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPOSITORY"):
        return 0
    client = GitHubClient.from_env()
    cfg = _engine_config()
    changed = 0
    for item in OpportunityStore().load():
        if item.issue_number is None:
            continue
        client.sync_issue_labels(item.issue_number, _issue_labels(item, cfg))
        changed += 1
    return changed


def reconcile_github_stage_labels() -> int:
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPOSITORY"):
        return 0
    client = GitHubClient.from_env()
    issues = client.list_issues(state="all")
    stage_by_issue: dict[int, Stage] = {}
    for issue in issues:
        if "pull_request" in issue:
            continue
        stage_labels = [
            label["name"].split("/", 1)[1]
            for label in issue.get("labels", [])
            if str(label.get("name", "")).startswith("stage/")
        ]
        if len(stage_labels) != 1:
            continue
        try:
            stage_by_issue[int(issue["number"])] = Stage(stage_labels[0])
        except ValueError:
            continue

    store = OpportunityStore()
    items = store.load()
    changed = 0
    for item in items:
        if item.issue_number is None or item.issue_number not in stage_by_issue:
            continue
        desired = stage_by_issue[item.issue_number]
        if desired == item.stage:
            continue
        item.transition(desired)
        changed += 1
    if changed:
        store.save(items)
    return changed
