from __future__ import annotations

from eitraining.replay import build_replay_results
from eitraining.training_examples import build_training_examples


def _trace(trace_id: str, *, outcome: str = "planned", feedback: str = "accepted") -> dict:
    return {
        "record_id": f"rec-{trace_id}",
        "content": {
            "trace_id": trace_id,
            "task_type": "brain.respond",
            "input_summary": "记住我喜欢简短回复",
            "selected_skills": ["reply.default"],
            "actions": ["play_speech_action"],
            "outcome": outcome,
            "feedback": feedback,
            "latency_ms": 12,
            "meta": {"write_policy_version": "meaningful_event_v1", "trace_reason": "explicit_remember"},
        },
        "meta": {"report_type": "skill_trace"},
        "provenance": {"report_type": "skill_trace", "trace_id": trace_id},
    }


def test_build_replay_results_from_candidate_evidence_ids() -> None:
    experiences = [_trace("t1"), _trace("t2")]
    assets = [{"skill_id": "candidate.reply", "status": "candidate", "utility": 0.9, "evidence_ids": ["t1", "t2"]}]

    results = build_replay_results(experiences=experiences, registry_assets=assets, min_samples=2)

    assert results == [
        {
            "skill_id": "candidate.reply",
            "passed": True,
            "pass_rate": 1.0,
            "sample_count": 2,
            "regression_count": 0,
            "report_id": results[0]["report_id"],
            "evidence_ids": ["t1", "t2"],
            "details": {
                "min_samples": 2,
                "min_pass_rate": 0.8,
                "pass_count": 2,
                "blocked_reasons": [],
                "asset_status": "candidate",
                "asset_utility": 0.9,
            },
        }
    ]


def test_build_replay_results_blocks_regression() -> None:
    experiences = [_trace("t1"), _trace("t2", outcome="failed", feedback="rejected")]
    assets = [{"skill_id": "candidate.reply", "status": "candidate", "evidence_ids": ["t1", "t2"]}]

    result = build_replay_results(experiences=experiences, registry_assets=assets)[0]

    assert result["passed"] is False
    assert result["regression_count"] == 1
    assert "regressions_detected" in result["details"]["blocked_reasons"]


def test_training_examples_use_only_meaningful_traces() -> None:
    examples = build_training_examples([_trace("t1"), {"record_id": "noise", "kind": "memory"}])

    assert len(examples) == 1
    assert examples[0]["source_experience_id"] == "t1"
    assert examples[0]["target"]["selected_skills"] == ["reply.default"]
