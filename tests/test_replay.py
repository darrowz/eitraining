from __future__ import annotations

from eitraining.replay import build_replay_results
from eitraining.training_examples import build_training_examples


def _trace(
    trace_id: str,
    *,
    outcome: str = "planned",
    feedback: str = "accepted",
    baseline_outcome: str | None = None,
    memory_score: dict | None = None,
    quality: dict | None = None,
) -> dict:
    meta = {"write_policy_version": "meaningful_event_v1", "trace_reason": "explicit_remember"}
    if baseline_outcome is not None:
        meta["baseline_outcome"] = baseline_outcome
    if memory_score is not None:
        meta["scoring"] = {"memory_score_v1": memory_score}
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
            "meta": meta,
        },
        "meta": {
            "report_type": "skill_trace",
            **({"quality": quality} if quality is not None else {}),
        },
        "provenance": {"report_type": "skill_trace", "trace_id": trace_id},
    }


def test_build_replay_results_from_candidate_evidence_ids() -> None:
    experiences = [_trace("t1"), _trace("t2")]
    assets = [{"skill_id": "candidate.reply", "status": "candidate", "version": "1.1.0", "utility": 0.9, "evidence_ids": ["t1", "t2"]}]

    result = build_replay_results(experiences=experiences, registry_assets=assets, min_samples=2)[0]

    assert result["skill_id"] == "candidate.reply"
    assert result["candidate_id"] == "candidate.reply"
    assert result["candidate_version"] == "1.1.0"
    assert result["baseline_version"] == "current"
    assert result["passed"] is True
    assert result["pass_rate"] == 1.0
    assert result["sample_count"] == 2
    assert result["regression_count"] == 0
    assert result["evidence_ids"] == ["t1", "t2"]
    assert result["paired_summary"] == {
        "paired_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "tie_count": 0,
        "baseline_pass_rate": None,
        "score_delta": None,
    }
    assert len(result["cases"]) == 2
    assert result["details"]["blocked_reasons"] == []
    assert result["details"]["asset_status"] == "candidate"
    assert result["details"]["asset_utility"] == 0.9


def test_build_replay_results_blocks_regression() -> None:
    experiences = [_trace("t1"), _trace("t2", outcome="failed", feedback="rejected")]
    assets = [{"skill_id": "candidate.reply", "status": "candidate", "evidence_ids": ["t1", "t2"]}]

    result = build_replay_results(experiences=experiences, registry_assets=assets)[0]

    assert result["passed"] is False
    assert result["regression_count"] == 1
    assert "regressions_detected" in result["details"]["blocked_reasons"]


def test_build_replay_results_records_paired_win_loss_and_versions() -> None:
    experiences = [
        _trace("t1", outcome="success", baseline_outcome="failed"),
        _trace("t2", outcome="failed", feedback="rejected", baseline_outcome="success"),
    ]
    assets = [
        {
            "skill_id": "candidate.reply",
            "status": "candidate",
            "version": "1.2.0-candidate",
            "baseline_version": "1.1.0",
            "evidence_ids": ["t1", "t2"],
        }
    ]

    result = build_replay_results(experiences=experiences, registry_assets=assets, min_samples=2)[0]

    assert result["baseline_version"] == "1.1.0"
    assert result["candidate_version"] == "1.2.0-candidate"
    assert result["paired_summary"]["paired_count"] == 2
    assert result["paired_summary"]["win_count"] == 1
    assert result["paired_summary"]["loss_count"] == 1
    assert result["passed"] is False
    assert result["regression_count"] == 1
    assert "paired_replay_losses_detected" in result["details"]["blocked_reasons"]
    assert {case["outcome"] for case in result["cases"]} == {"win", "loss"}


def test_build_replay_results_ignores_rejected_memory_scores_and_counts_supported_tiers() -> None:
    experiences = [
        _trace(
            "t1",
            memory_score={"schema_version": "memory_score.v1", "final_score": 0.12, "tier": "rejected"},
        ),
        _trace(
            "t2",
            quality={"quality_tier": "confirmed", "capture_decision": "accept"},
        ),
        _trace(
            "t3",
            memory_score={"schema_version": "memory_score.v1", "final_score": 0.88, "tier": "core"},
        ),
    ]
    assets = [{"skill_id": "candidate.reply", "status": "candidate", "evidence_ids": ["t1", "t2", "t3"]}]

    result = build_replay_results(experiences=experiences, registry_assets=assets, min_samples=2)[0]

    assert result["sample_count"] == 2
    assert result["evidence_ids"] == ["t2", "t3"]
    assert result["details"]["memory_tier_counts"] == {"confirmed": 1, "core": 1}
    assert [case["memory_tier"] for case in result["cases"]] == ["confirmed", "core"]


def test_training_examples_use_only_meaningful_traces() -> None:
    examples = build_training_examples([_trace("t1"), {"record_id": "noise", "kind": "memory"}])

    assert len(examples) == 1
    assert examples[0]["source_experience_id"] == "t1"
    assert examples[0]["target"]["selected_skills"] == ["reply.default"]
