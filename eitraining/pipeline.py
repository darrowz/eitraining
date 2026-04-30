from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import write_json, write_jsonl
from .replay import build_replay_results
from .training_examples import build_training_examples


def run_training_loop(
    *,
    experiences: list[dict[str, Any]],
    registry_assets: list[dict[str, Any]],
    output_dir: str | Path,
    min_samples: int = 2,
    min_pass_rate: float = 0.8,
) -> dict[str, Any]:
    target = Path(output_dir)
    replay_results = build_replay_results(
        experiences=experiences,
        registry_assets=registry_assets,
        min_samples=min_samples,
        min_pass_rate=min_pass_rate,
    )
    training_examples = build_training_examples(experiences)
    report = {
        "ok": True,
        "experience_count": len(experiences),
        "registry_asset_count": len(registry_assets),
        "replay_result_count": len(replay_results),
        "training_example_count": len(training_examples),
        "passed_replay_count": sum(1 for item in replay_results if item.get("passed") is True),
        "failed_replay_count": sum(1 for item in replay_results if item.get("passed") is False),
        "min_samples": min_samples,
        "min_pass_rate": min_pass_rate,
    }
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "replay-results.json", {"ok": True, "replay_results": replay_results})
    write_jsonl(target / "training-examples.jsonl", training_examples)
    write_json(target / "outcome-report.json", report)
    return {**report, "output_dir": str(target), "replay_results": replay_results}
