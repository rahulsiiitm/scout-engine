from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_labels
from .github_sync import GitHubClient
from .learning import learn_preferences
from .reports import write_weekly
from .source_stats import calculate_source_stats
from .state import OpportunityStore


def cmd_validate(_: argparse.Namespace) -> int:
    store = OpportunityStore()
    items = store.load()
    ids = [x.id for x in items]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate canonical opportunity IDs found")
    for item in items:
        if item.stage.value == "applied" and item.decision.value == "suppressed":
            raise SystemExit(f"{item.id}: applied opportunity cannot be suppressed")
    print(f"validated {len(items)} canonical opportunities")
    return 0


def cmd_weekly(_: argparse.Namespace) -> int:
    store = OpportunityStore()
    path = write_weekly(store.load())
    print(path)
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    store = OpportunityStore()
    stats = [s.to_dict() for s in calculate_source_stats(store.load())]
    path = Path("data/source-stats.json")
    path.write_text(json.dumps({"version": 1, "sources": stats}, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


def cmd_learn(_: argparse.Namespace) -> int:
    store = OpportunityStore()
    weights = learn_preferences(store.load())
    path = Path("data/preferences.json")
    path.write_text(json.dumps({"version":1,"note":"Bounded ranking nudges only; never bypass hard gates or alter fit score.","role_weights":weights.role_weights,"source_weights":weights.source_weights}, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


def cmd_labels(_: argparse.Namespace) -> int:
    client = GitHubClient.from_env()
    client.ensure_labels(load_labels())
    print("labels synchronized")
    return 0


def cmd_daily(_: argparse.Namespace) -> int:
    cmd_validate(argparse.Namespace())
    cmd_stats(argparse.Namespace())
    cmd_learn(argparse.Namespace())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scout-engine")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in {"validate":cmd_validate,"weekly":cmd_weekly,"stats":cmd_stats,"learn":cmd_learn,"labels":cmd_labels,"daily":cmd_daily}.items():
        sub.add_parser(name).set_defaults(handler=handler)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
