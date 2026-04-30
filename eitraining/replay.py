from __future__ import annotations

import hashlib
from typing import Any

from .normalize import evidence_id, meaningful_skill_traces, selected_skill_ids

SUCCESS_OUTCOMES = {"planned", "success", "succeeded", "accepted", "ok", "completed"}
FAILURE_OUTCOMES = {"failed", "failure", "error", "rejected", "regression"}
NEGATIVE_FEEDBACK = {"failed", "failure", "rejected", "bad", "regression"}


def build_replay_results(
    *,
    experiences: list[dict[str, Any]],
    registry_assets: list[dict[str, Any]],
    min_samples: int = 2,
    min_pass_rate: float = 0.8,
) -> list[dict[str, Any]]:
    traces = meaningful_skill_traces(experiences)
    traces_by_id = {evidence_id(trace): trace for trace in traces if evidence_id(trace)}
    results: list[dict[str, Any]] = []
    for asset in registry_assets:
        if not isinstance(asset, dict):
            continue
        skill_id = str(asset.get("skill_id") or asset.get("id") or "").strip()
        if not skill_id:
            continue
        evidence_ids = [str(item) for item in asset.get("evidence_ids", []) if str(item)] if isinstance(asset.get("evidence_ids"), list) else []
        evidence_traces = [traces_by_id[item] for item in evidence_ids if item in traces_by_id]
        if not evidence_traces:
            evidence_traces = [trace for trace in traces if skill_id in selected_skill_ids(trace)]
        result = _result_for_skill(skill_id, evidence_traces, min_samples=min_samples, min_pass_rate=min_pass_rate)
        result["evidence_ids"] = [evidence_id(trace) for trace in evidence_traces if evidence_id(trace)]
        result["details"]["asset_status"] = asset.get("status")
        result["details"]["asset_utility"] = asset.get("utility")
        results.append(result)
    return sorted(results, key=lambda item: item["skill_id"])


def _result_for_skill(skill_id: str, traces: list[dict[str, Any]], *, min_samples: int, min_pass_rate: float) -> dict[str, Any]:
    sample_count = len(traces)
    pass_count = sum(1 for trace in traces if _trace_passed(trace))
    regression_count = sum(1 for trace in traces if _trace_failed(trace))
    pass_rate = round(pass_count / sample_count, 4) if sample_count else 0.0
    passed = sample_count >= min_samples and pass_rate >= min_pass_rate and regression_count == 0
    report_id = _report_id(skill_id, traces)
    return {
        "skill_id": skill_id,
        "passed": passed,
        "pass_rate": pass_rate,
        "sample_count": sample_count,
        "regression_count": regression_count,
        "report_id": report_id,
        "details": {
            "min_samples": min_samples,
            "min_pass_rate": min_pass_rate,
            "pass_count": pass_count,
            "blocked_reasons": _blocked_reasons(sample_count, pass_rate, regression_count, min_samples, min_pass_rate),
        },
    }


def _trace_passed(trace: dict[str, Any]) -> bool:
    outcome = str(trace.get("outcome") or "").lower()
    feedback = str(trace.get("feedback") or "").lower()
    if outcome in FAILURE_OUTCOMES or feedback in NEGATIVE_FEEDBACK:
        return False
    return outcome in SUCCESS_OUTCOMES


def _trace_failed(trace: dict[str, Any]) -> bool:
    outcome = str(trace.get("outcome") or "").lower()
    feedback = str(trace.get("feedback") or "").lower()
    return outcome in FAILURE_OUTCOMES or feedback in NEGATIVE_FEEDBACK


def _blocked_reasons(sample_count: int, pass_rate: float, regression_count: int, min_samples: int, min_pass_rate: float) -> list[str]:
    reasons: list[str] = []
    if sample_count < min_samples:
        reasons.append("sample_count_below_minimum")
    if pass_rate < min_pass_rate:
        reasons.append("pass_rate_below_threshold")
    if regression_count > 0:
        reasons.append("regressions_detected")
    return reasons


def _report_id(skill_id: str, traces: list[dict[str, Any]]) -> str:
    evidence = "|".join(sorted(evidence_id(trace) for trace in traces if evidence_id(trace)))
    digest = hashlib.sha256(f"{skill_id}:{evidence}".encode("utf-8")).hexdigest()[:12]
    return f"replay:{digest}"
