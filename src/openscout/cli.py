"""Command-line interface for openscout.

Commands
--------
``openscout list-sports``
    List every sport plugin currently discoverable (built-in + third-party),
    along with the metrics each one exposes.

``openscout analyze --sport SPORT --metric METRIC --input PATH``
    Load a JSON or CSV file of box-score-like data and compute one metric
    from it, printing the result.

``openscout demo --sport SPORT [--metric METRIC]``
    Run a metric against freshly generated, clearly-fabricated sample data,
    with no input file required. Great for a quick sanity check or a
    README screenshot.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .data import (
    load_input,
    synthetic_basketball_boxscore,
    synthetic_basketball_game,
    synthetic_soccer_passes,
    synthetic_soccer_shots,
)
from .plugins import SportNotFoundError, UnknownMetricError, get_sport, list_sports

_DEFAULT_DEMO_METRIC = {
    "basketball": "ts_pct",
    "soccer": "xg",
}


def _print_result(result: Any) -> None:
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2))
    else:
        print(result)


def _cmd_list_sports(args: argparse.Namespace) -> int:
    names = list_sports()
    if not names:
        print("No sport plugins are registered.")
        return 0
    for name in names:
        sport = get_sport(name)
        metrics = ", ".join(sport.list_metrics())
        print(f"{name}: {metrics}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    try:
        sport = get_sport(args.sport)
    except SportNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        data = load_input(args.input)
    except (OSError, ValueError) as exc:
        print(f"error: could not load input {args.input!r}: {exc}", file=sys.stderr)
        return 1

    try:
        result = sport.compute(args.metric, data)
    except UnknownMetricError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    return 0


def _demo_data_for(sport_name: str, metric: str) -> Any:
    if sport_name == "basketball":
        if metric == "four_factors":
            return synthetic_basketball_game(seed=42)
        return synthetic_basketball_boxscore(seed=42)
    if sport_name == "soccer":
        if metric == "pass_pct":
            return synthetic_soccer_passes(seed=42)
        if metric == "xt_added":
            return synthetic_soccer_passes(seed=42)
        return synthetic_soccer_shots(seed=42)
    raise SportNotFoundError(
        f"no built-in demo data for {sport_name!r}; try --input with your own data instead"
    )


def _cmd_demo(args: argparse.Namespace) -> int:
    try:
        sport = get_sport(args.sport)
    except SportNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    metric = args.metric or _DEFAULT_DEMO_METRIC.get(args.sport, sport.list_metrics()[0])

    try:
        data = _demo_data_for(args.sport, metric)
    except SportNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"# openscout demo -- sport={args.sport} metric={metric}")
    print("# input data is synthetic/fabricated -- see openscout.data")
    print(json.dumps(data, indent=2))
    print()

    try:
        result = sport.compute(metric, data)
    except UnknownMetricError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"# {metric} result:")
    _print_result(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openscout",
        description="A pluggable sports analytics CLI (basketball, soccer, and beyond).",
    )
    parser.add_argument("--version", action="version", version=f"openscout {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list-sports", help="list every registered sport plugin and its metrics"
    )
    list_parser.set_defaults(func=_cmd_list_sports)

    analyze_parser = subparsers.add_parser(
        "analyze", help="compute a metric from a user-supplied JSON/CSV data file"
    )
    analyze_parser.add_argument("--sport", required=True, help="sport plugin name, e.g. basketball")
    analyze_parser.add_argument("--metric", required=True, help="metric name, e.g. ts_pct")
    analyze_parser.add_argument("--input", required=True, help="path to a .json or .csv data file")
    analyze_parser.set_defaults(func=_cmd_analyze)

    demo_parser = subparsers.add_parser(
        "demo", help="run a metric against freshly generated synthetic sample data"
    )
    demo_parser.add_argument("--sport", required=True, help="sport plugin name, e.g. soccer")
    demo_parser.add_argument(
        "--metric", required=False, default=None, help="metric name (defaults to a sensible one)"
    )
    demo_parser.set_defaults(func=_cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
