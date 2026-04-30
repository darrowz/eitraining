from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .io import read_json_items, write_json, write_jsonl
from .pipeline import run_training_loop
from .replay import build_replay_results
from .training_examples import build_training_examples


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
    except Exception as exc:
        _emit({"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}})
        return 1
    _emit(payload)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eitraining")
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("build-replay", help="Build replay results from experiences and a skill registry.")
    replay.add_argument("--experiences", required=True)
    replay.add_argument("--registry", required=True)
    replay.add_argument("--output", required=True)
    replay.add_argument("--min-samples", type=int, default=2)
    replay.add_argument("--min-pass-rate", type=float, default=0.8)
    replay.set_defaults(handler=_handle_build_replay)

    examples = sub.add_parser("build-examples", help="Build training examples from experiences.")
    examples.add_argument("--experiences", required=True)
    examples.add_argument("--output", required=True)
    examples.set_defaults(handler=_handle_build_examples)

    loop = sub.add_parser("run-loop", help="Build replay, outcome, and training artifacts.")
    loop.add_argument("--experiences", required=True)
    loop.add_argument("--registry", required=True)
    loop.add_argument("--output-dir", required=True)
    loop.add_argument("--min-samples", type=int, default=2)
    loop.add_argument("--min-pass-rate", type=float, default=0.8)
    loop.set_defaults(handler=_handle_run_loop)
    return parser


def _handle_build_replay(args: argparse.Namespace) -> dict[str, Any]:
    experiences = read_json_items(args.experiences)
    assets = read_json_items(args.registry)
    replay_results = build_replay_results(
        experiences=experiences,
        registry_assets=assets,
        min_samples=args.min_samples,
        min_pass_rate=args.min_pass_rate,
    )
    payload = {"ok": True, "replay_results": replay_results, "replay_result_count": len(replay_results)}
    write_json(args.output, payload)
    return payload


def _handle_build_examples(args: argparse.Namespace) -> dict[str, Any]:
    examples = build_training_examples(read_json_items(args.experiences))
    write_jsonl(args.output, examples)
    return {"ok": True, "training_example_count": len(examples), "output": args.output}


def _handle_run_loop(args: argparse.Namespace) -> dict[str, Any]:
    return run_training_loop(
        experiences=read_json_items(args.experiences),
        registry_assets=read_json_items(args.registry),
        output_dir=args.output_dir,
        min_samples=args.min_samples,
        min_pass_rate=args.min_pass_rate,
    )


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
