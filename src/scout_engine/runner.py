from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import load_profile, load_yaml
from .discovery.registry import load_company_registry
from .engine import EngineConfig, evaluate
from .enrich import enrich_opportunity
from .github_sync import GitHubClient
from .models import Decision, Opportunity, Stage
from .sources import AshbyAdapter, CareerPageAdapter, GreenhouseAdapter, LeverAdapter, SmartRecruitersAdapter, WorkableAdapter
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
        candidate_graduation_year=int(profile.get("candidate", {}).get("graduation_year"))
        if profile.get("candidate", {}).get("graduation_year") is not None
        else None,
        max_years_without_override=float(
            constraints.get("max_years_experience_without_explicit_new_grad_override", 2)
        ),
        dedupe_threshold=float(
            source_cfg.get("dedupe", {}).get("fuzzy_company_title_threshold", 0.86)
        ),
    )


def configured_adapters() -> list[SourceAdapter]:
    boards = load_yaml("config/boards.yaml")
    source_cfg = load_yaml("config/sources.yaml")
    crawl_cfg = source_cfg.get("crawl", {})
    adapters: list[SourceAdapter] = []
    configured_companies: set[str] = set()

    for item in boards.get("greenhouse", []) or []:
        adapters.append(GreenhouseAdapter(item["company"], item["board"]))
        configured_companies.add(item["company"].lower())
    for item in boards.get("lever", []) or []:
        adapters.append(LeverAdapter(item["company"], item["site"]))
        configured_companies.add(item["company"].lower())
    for item in boards.get("ashby", []) or []:
        adapters.append(AshbyAdapter(item["company"], item["board"]))
        configured_companies.add(item["company"].lower())
    for item in boards.get("workable", []) or []:
        adapters.append(WorkableAdapter(item["company"], item["subdomain"]))
        configured_companies.add(item["company"].lower())
    for item in boards.get("smartrecruiters", []) or []:
        adapters.append(SmartRecruitersAdapter(item["company"], item["identifier"]))
        configured_companies.add(item["company"].lower())

    if crawl_cfg.get("enabled", True):
        default_max_pages = int(crawl_cfg.get("max_pages_per_company", 30))
        browser_fallback = bool(crawl_cfg.get("browser_fallback", True))
        timeout = int(crawl_cfg.get("request_timeout_seconds", 20))
        user_agent = str(
            crawl_cfg.get(
                "user_agent",
                "ScoutEngineBot/1.0 (+https://github.com/rahulsiiitm/scout-engine)",
            )
        )
        registry_path = str(crawl_cfg.get("registry", "config/companies.yaml"))
        for company in load_company_registry(registry_path):
            if company.name.lower() in configured_companies:
                continue
            adapters.append(
                CareerPageAdapter(
                    company.name,
                    company.domain,
                    careers_url=company.careers_url,
                    max_pages=company.max_pages or default_max_pages,
                    browser_fallback=browser_fallback,
                    timeout_seconds=timeout,
                    user_agent=user_agent,
                )
            )
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


def _mark_source_disappearances(
    by_id: dict[str, Opportunity],
    *,
    successful_keys: set[str],
    seen_by_key: dict[str, set[str]],
    miss_limit: int,
) -> int:
    changed = 0
    pre_application = {Stage.DISCOVERED, Stage.QUALIFIED, Stage.REVIEWING}
    for item in by_id.values():
        key = str(item.metadata.get("source_key") or "")
        if not key or key not in successful_keys:
            continue
        if item.id in seen_by_key.get(key, set()):
            if item.missing_successful_scans or item.source_status != "open":
                changed += 1
            item.missing_successful_scans = 0
            item.source_status = "open"
            continue
        item.missing_successful_scans += 1
        item.source_status = "possibly_closed" if item.missing_successful_scans < miss_limit else "closed"
        changed += 1
        if item.missing_successful_scans >= miss_limit and item.stage in pre_application:
            item.decision = Decision.EXPIRED
            if item.stage != Stage.EXPIRED:
                item.transition(Stage.EXPIRED)
    return changed


def _write_scan_snapshot(counters: dict[str, int], reasons: Counter[str]) -> None:
    now = datetime.now(IST)
    path = Path("daily") / f"{now.date().isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    source_cfg = load_yaml("config/sources.yaml")
    target = int(source_cfg.get("discovery_targets", {}).get("actionable_career_opportunities_per_day", 10))
    lines = [
        f"# Daily Scout Snapshot — {now.date().isoformat()}",
        "",
        "Generated by Scout Engine V3 from canonical source scans.",
        "",
        f"- New qualified career opportunities: **{counters.get('new_qualified', 0)}/{target}**",
        f"- New explicit PPO/conversion internships: **{counters.get('new_conversion', 0)}**",
        f"- Raw postings fetched: **{counters.get('fetched', 0)}**",
        f"- Duplicates/history matches: **{counters.get('duplicates', 0)}**",
        f"- Suppressed: **{counters.get('suppressed', 0)}**",
        f"- Sources succeeded/attempted: **{counters.get('sources_succeeded', 0)}/{counters.get('sources_attempted', 0)}**",
        f"- Source errors: **{counters.get('errors', 0)}**",
        f"- Stale-state updates: **{counters.get('stale_updates', 0)}**",
        "",
        "## Suppression reasons",
        "",
    ]
    if reasons:
        lines.extend(f"- {reason}: **{count}**" for reason, count in reasons.most_common())
    else:
        lines.append("- None")
    if counters.get("new_qualified", 0) < target:
        lines.extend(
            [
                "",
                "## Yield note",
                "",
                "The quality target was not filled. Hard gates were not lowered.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan_structured_sources(*, sync_github: bool = True) -> dict[str, int]:
    profile = load_profile()
    cfg = _engine_config()
    source_cfg = load_yaml("config/sources.yaml")
    miss_limit = int(source_cfg.get("crawl", {}).get("stale_after_successful_misses", 2))
    store = OpportunityStore()
    existing = store.load()
    by_id = {item.id: item for item in existing}
    github = None
    if sync_github and os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPOSITORY"):
        github = GitHubClient.from_env()

    counters = {
        "sources_attempted": 0,
        "sources_succeeded": 0,
        "fetched": 0,
        "surfaced": 0,
        "new_qualified": 0,
        "new_conversion": 0,
        "suppressed": 0,
        "duplicates": 0,
        "errors": 0,
        "stale_updates": 0,
    }
    suppression_reasons: Counter[str] = Counter()
    successful_keys: set[str] = set()
    seen_by_key: dict[str, set[str]] = defaultdict(set)

    for adapter in configured_adapters():
        counters["sources_attempted"] += 1
        try:
            fetched = adapter.fetch()
            if not isinstance(fetched, list):
                raise TypeError(f"adapter returned {type(fetched).__name__}, expected list")
        except Exception as exc:
            counters["errors"] += 1
            _append_run_log(adapter.source_key, f"adapter error: {exc}")
            continue

        counters["sources_succeeded"] += 1
        successful_keys.update(adapter.effective_source_keys())
        counters["fetched"] += len(fetched)
        for raw in fetched:
            try:
                raw = enrich_opportunity(raw)
            except Exception as exc:
                counters["errors"] += 1
                _append_run_log(adapter.source_key, f"enrichment error for {getattr(raw, 'id', 'unknown')}: {exc}")
                continue
            source_key = str(raw.metadata.get("source_key") or adapter.source_key)
            raw.metadata["source_key"] = source_key
            successful_keys.add(source_key)
            seen_by_key[source_key].add(raw.id)

            old = by_id.get(raw.id)
            if old:
                raw.first_seen_utc = old.first_seen_utc
                raw.stage = old.stage
                raw.issue_number = old.issue_number
                raw.source_urls = sorted(set(old.source_urls + raw.source_urls + [raw.canonical_url]))
                # Funnel history is authoritative. Re-discovery may refresh evidence,
                # but must never demote an already-actioned opportunity into suppression.
                if old.stage in {Stage.APPLIED, Stage.OA, Stage.INTERVIEW, Stage.OFFER, Stage.OFFER_ACCEPTED}:
                    raw.decision = old.decision
                    raw.suppression_reason = old.suppression_reason
            raw.last_seen_utc = datetime.now(timezone.utc).isoformat()
            raw.last_verified_utc = raw.last_verified_utc or raw.last_seen_utc
            evaluated = evaluate(
                raw,
                profile=profile,
                existing=list(by_id.values()),
                config=cfg,
            )
            if old and old.stage in {Stage.APPLIED, Stage.OA, Stage.INTERVIEW, Stage.OFFER, Stage.OFFER_ACCEPTED}:
                evaluated.stage = old.stage
                evaluated.decision = Decision.SURFACED
                evaluated.suppression_reason = None
            if evaluated.id != raw.id:
                counters["duplicates"] += 1
                seen_by_key[source_key].add(evaluated.id)
            discovered_via = str(raw.metadata.get("discovered_via") or "")
            if discovered_via:
                successful_keys.add(discovered_via)
                seen_by_key[discovered_via].add(evaluated.id)
            is_new = old is None and evaluated.id == raw.id
            by_id[evaluated.id] = evaluated

            if evaluated.kind.value in {"competition", "hackathon"}:
                # Competitions remain outside the production career-opportunity lane.
                evaluated.decision = Decision.SUPPRESSED
                evaluated.suppression_reason = "competition excluded from career production lane"

            if evaluated.decision == Decision.SURFACED:
                counters["surfaced"] += 1
                if is_new and evaluated.kind.value in {"full_time", "internship", "contract"}:
                    counters["new_qualified"] += 1
                    if evaluated.kind.value == "internship" and evaluated.conversion_signal == "explicit":
                        counters["new_conversion"] += 1
                if github and evaluated.issue_number is None:
                    issue = github.create_issue_for(evaluated, _issue_labels(evaluated, cfg))
                    evaluated.issue_number = issue
            elif evaluated.decision == Decision.SUPPRESSED:
                counters["suppressed"] += 1
                suppression_reasons[evaluated.suppression_reason or "unknown"] += 1
                if is_new:
                    _append_suppression(evaluated)

    counters["stale_updates"] = _mark_source_disappearances(
        by_id,
        successful_keys=successful_keys,
        seen_by_key=seen_by_key,
        miss_limit=max(2, miss_limit),
    )
    store.save(list(by_id.values()))
    _write_scan_snapshot(counters, suppression_reasons)
    Path("data/scan-stats.json").write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "counters": counters,
                "suppression_reasons": dict(suppression_reasons),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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
