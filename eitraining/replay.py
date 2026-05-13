"""Replay artifact generation for `eiskills` promotion validation.

Boundary note:
- `eitraining` turns normalized experiences into this replay schema and writes it
  to disk as plain JSON.
- Downstream packages (currently `eiskills`) consume the resulting rows as opaque
  dictionaries to make promotion decisions, so the transport contract is schema
  based and avoids import-time coupling.
"""

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
    """Build replay rows for each registry skill asset.

    The output keys are intentionally aligned with `eiskills` replay-gate inputs
    (`passed`, `pass_rate`, `sample_count`, `regression_count`, `paired_summary`)
    so the two packages can exchange data via JSON only.
    """
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
        result = _result_for_skill(skill_id, asset, evidence_traces, min_samples=min_samples, min_pass_rate=min_pass_rate)
        result["evidence_ids"] = [evidence_id(trace) for trace in evidence_traces if evidence_id(trace)]
        result["details"]["asset_status"] = asset.get("status")
        result["details"]["asset_utility"] = asset.get("utility")
        results.append(result)
    return sorted(results, key=lambda item: item["skill_id"])


def _result_for_skill(skill_id: str, asset: dict[str, Any], traces: list[dict[str, Any]], *, min_samples: int, min_pass_rate: float) -> dict[str, Any]:
    sample_count = len(traces)
    pass_count = sum(1 for trace in traces if _trace_passed(trace))
    paired_cases = [_paired_case(skill_id, asset, trace) for trace in traces]
    paired_count = sum(1 for case in paired_cases if case["baseline_passed"] is not None)
    win_count = sum(1 for case in paired_cases if case["outcome"] == "win")
    loss_count = sum(1 for case in paired_cases if case["outcome"] == "loss")
    tie_count = sum(1 for case in paired_cases if case["outcome"] == "tie")
    regression_count = sum(
        1 for trace, case in zip(traces, paired_cases, strict=False) if _trace_failed(trace) or case["outcome"] == "loss"
    )
    pass_rate = round(pass_count / sample_count, 4) if sample_count else 0.0
    baseline_pass_rate = _baseline_pass_rate(paired_cases)
    score_delta = round(pass_rate - baseline_pass_rate, 4) if baseline_pass_rate is not None else None
    passed = sample_count >= min_samples and pass_rate >= min_pass_rate and regression_count == 0 and loss_count == 0 and (paired_count == 0 or win_count >= loss_count)
    report_id = _report_id(skill_id, traces, asset)
    baseline_version = _baseline_version(asset)
    candidate_version = str(asset.get("version") or asset.get("candidate_version") or "candidate")
    return {
        "skill_id": skill_id,
        "candidate_id": str(asset.get("candidate_id") or skill_id),
        "baseline_version": baseline_version,
        "candidate_version": candidate_version,
        "replay_mode": "paired_historical",
        "passed": passed,
        "pass_rate": pass_rate,
        "sample_count": sample_count,
        "regression_count": regression_count,
        "report_id": report_id,
        "paired_summary": {
            "paired_count": paired_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "tie_count": tie_count,
            "baseline_pass_rate": baseline_pass_rate,
            "score_delta": score_delta,
        },
        "cases": paired_cases,
        "details": {
            "min_samples": min_samples,
            "min_pass_rate": min_pass_rate,
            "pass_count": pass_count,
            "blocked_reasons": _blocked_reasons(sample_count, pass_rate, regression_count, min_samples, min_pass_rate, loss_count),
        },
    }


def _paired_case(skill_id: str, asset: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    candidate_passed = _trace_passed(trace)
    baseline_passed = _baseline_passed(trace)
    if baseline_passed is None:
        outcome = "unpaired"
    elif candidate_passed and not baseline_passed:
        outcome = "win"
    elif not candidate_passed and baseline_passed:
        outcome = "loss"
    else:
        outcome = "tie"
    trace_id = evidence_id(trace)
    return {
        "case_id": _case_id(skill_id, trace_id),
        "evidence_id": trace_id,
        "skill_id": skill_id,
        "baseline_version": _baseline_version(asset),
        "candidate_version": str(asset.get("version") or asset.get("candidate_version") or "candidate"),
        "candidate_passed": candidate_passed,
        "baseline_passed": baseline_passed,
        "outcome": outcome,
        "task_type": str(trace.get("task_type") or ""),
        "input_hash": _hash_text(str(trace.get("summary") or trace.get("input_summary") or "")),
        "failure_category": _failure_category(trace),
    }


def _baseline_passed(trace: dict[str, Any]) -> bool | None:
    meta = trace.get("meta") if isinstance(trace.get("meta"), dict) else {}
    value = trace.get("baseline_outcome") or trace.get("baseline_status") or meta.get("baseline_outcome") or meta.get("baseline_status")
    if value is None:
        return None
    normalized = str(value).lower()
    if normalized in SUCCESS_OUTCOMES or normalized in {"pass", "passed", "true"}:
        return True
    if normalized in FAILURE_OUTCOMES or normalized in {"fail", "false"}:
        return False
    return None


def _baseline_version(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    return str(asset.get("baseline_version") or metadata.get("baseline_version") or asset.get("rollback_to") or "current")


def _baseline_pass_rate(cases: list[dict[str, Any]]) -> float | None:
    paired = [case for case in cases if case["baseline_passed"] is not None]
    if not paired:
        return None
    return round(sum(1 for case in paired if case["baseline_passed"] is True) / len(paired), 4)


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


def _failure_category(trace: dict[str, Any]) -> str:
    meta = trace.get("meta") if isinstance(trace.get("meta"), dict) else {}
    return str(trace.get("failure_category") or meta.get("failure_category") or "")


def _blocked_reasons(sample_count: int, pass_rate: float, regression_count: int, min_samples: int, min_pass_rate: float, loss_count: int) -> list[str]:
    reasons: list[str] = []
    if sample_count < min_samples:
        reasons.append("sample_count_below_minimum")
    if pass_rate < min_pass_rate:
        reasons.append("pass_rate_below_threshold")
    if regression_count > 0:
        reasons.append("regressions_detected")
    if loss_count > 0:
        reasons.append("paired_replay_losses_detected")
    return reasons


def _report_id(skill_id: str, traces: list[dict[str, Any]], asset: dict[str, Any]) -> str:
    evidence = "|".join(sorted(evidence_id(trace) for trace in traces if evidence_id(trace)))
    digest = hashlib.sha256(f"{skill_id}:{_baseline_version(asset)}:{asset.get('version')}:{evidence}".encode("utf-8")).hexdigest()[:12]
    return f"replay:{digest}"


def _case_id(skill_id: str, trace_id: str) -> str:
    digest = hashlib.sha256(f"{skill_id}:{trace_id}".encode("utf-8")).hexdigest()[:12]
    return f"case:{digest}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else ""
