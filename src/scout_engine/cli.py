from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_labels
from .github_sync import GitHubClient
from .learning import learn_preferences
from .reports import write_weekly
from .runner import push_github_issue_labels, reconcile_github_stage_labels, scan_structured_sources
from .source_stats import calculate_source_stats
from .state import OpportunityStore


def cmd_validate(_: argparse.Namespace) -> int:
    items = OpportunityStore().load()
    ids = [x.id for x in items]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate canonical opportunity IDs found")
    for item in items:
        if item.stage.value == "applied" and item.decision.value == "suppressed":
            raise SystemExit(f"{item.id}: applied opportunity cannot be suppressed")
    print(f"validated {len(items)} canonical opportunities")
    return 0


def cmd_weekly(_: argparse.Namespace) -> int:
    path = write_weekly(OpportunityStore().load())
    print(path)
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    stats = [s.to_dict() for s in calculate_source_stats(OpportunityStore().load())]
    path = Path("data/source-stats.json")
    path.write_text(json.dumps({"version": 1, "sources": stats}, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


def cmd_learn(_: argparse.Namespace) -> int:
    weights = learn_preferences(OpportunityStore().load())
    path = Path("data/preferences.json")
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "note": "Bounded ranking nudges only; never bypass hard gates or alter fit score.",
                "role_weights": weights.role_weights,
                "source_weights": weights.source_weights,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(path)
    return 0


def cmd_labels(_: argparse.Namespace) -> int:
    GitHubClient.from_env().ensure_labels(load_labels())
    print("labels synchronized")
    return 0


def cmd_push_stages(_: argparse.Namespace) -> int:
    changed = push_github_issue_labels()
    print(f"synchronized labels on {changed} tracked issues")
    return 0


def cmd_scan(_: argparse.Namespace) -> int:
    result = scan_structured_sources(sync_github=True)
    print(json.dumps(result, sort_keys=True))
    return 0


def cmd_reconcile(_: argparse.Namespace) -> int:
    changed = reconcile_github_stage_labels()
    print(f"reconciled {changed} lifecycle updates")
    return 0


def cmd_daily(_: argparse.Namespace) -> int:
    cmd_validate(argparse.Namespace())
    cmd_reconcile(argparse.Namespace())
    cmd_scan(argparse.Namespace())
    cmd_push_stages(argparse.Namespace())
    cmd_stats(argparse.Namespace())
    cmd_learn(argparse.Namespace())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scout-engine")
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {
        "validate": cmd_validate,
        "weekly": cmd_weekly,
        "stats": cmd_stats,
        "learn": cmd_learn,
        "labels": cmd_labels,
        "push-stages": cmd_push_stages,
        "scan": cmd_scan,
        "reconcile": cmd_reconcile,
        "daily": cmd_daily,
    }
    for name, handler in commands.items():
        sub.add_parser(name).set_defaults(handler=handler)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
