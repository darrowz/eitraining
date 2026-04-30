from __future__ import annotations

import json

from eitraining.cli import main


def _trace(trace_id: str) -> dict:
    return {
        "record_id": f"rec-{trace_id}",
        "content": {
            "trace_id": trace_id,
            "task_type": "brain.respond",
            "input_summary": "记住我喜欢简短回复",
            "selected_skills": ["reply.default"],
            "actions": ["play_speech_action"],
            "outcome": "planned",
            "feedback": "accepted",
            "latency_ms": 12,
            "meta": {"write_policy_version": "meaningful_event_v1", "trace_reason": "explicit_remember"},
        },
        "meta": {"report_type": "skill_trace"},
        "provenance": {"report_type": "skill_trace", "trace_id": trace_id},
    }


def run_cli(args: list[str], capsys) -> tuple[int, dict]:
    exit_code = main(args)
    output = capsys.readouterr().out
    return exit_code, json.loads(output)


def test_run_loop_writes_artifacts(tmp_path, capsys) -> None:
    experiences = tmp_path / "experiences.jsonl"
    registry = tmp_path / "registry.jsonl"
    output_dir = tmp_path / "out"
    experiences.write_text("\n".join(json.dumps(_trace(item)) for item in ["t1", "t2"]) + "\n", encoding="utf-8")
    registry.write_text(json.dumps({"skill_id": "candidate.reply", "status": "candidate", "evidence_ids": ["t1", "t2"]}) + "\n", encoding="utf-8")

    exit_code, payload = run_cli([
        "run-loop",
        "--experiences", str(experiences),
        "--registry", str(registry),
        "--output-dir", str(output_dir),
    ], capsys)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["replay_result_count"] == 1
    assert payload["passed_replay_count"] == 1
    assert (output_dir / "replay-results.json").exists()
    assert (output_dir / "training-examples.jsonl").exists()
    assert (output_dir / "outcome-report.json").exists()
