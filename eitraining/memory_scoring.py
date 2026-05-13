from __future__ import annotations

from typing import Any


_VALID_TIERS = {"rejected", "candidate", "confirmed", "core"}
_VALID_CAPTURE_DECISIONS = {"accept", "reject"}


def extract_memory_scoring(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    payload = meta if isinstance(meta, dict) else {}
    scoring = payload.get("scoring") if isinstance(payload.get("scoring"), dict) else {}
    score = scoring.get("memory_score_v1") if isinstance(scoring.get("memory_score_v1"), dict) else {}
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}

    schema_version = str(score.get("schema_version") or "").strip()
    tier = _normalized_tier(score.get("tier")) or _normalized_tier(quality.get("quality_tier"))
    capture_decision = _normalized_capture_decision(quality.get("capture_decision"))
    if not capture_decision and tier:
        capture_decision = "reject" if tier == "rejected" else "accept"
    final_score = _to_float_or_none(score.get("final_score"))

    if not schema_version and tier is None and capture_decision is None and final_score is None:
        return None

    result: dict[str, Any] = {}
    if schema_version:
        result["schema_version"] = schema_version
    if tier is not None:
        result["tier"] = tier
    if capture_decision is not None:
        result["capture_decision"] = capture_decision
    if final_score is not None:
        result["final_score"] = final_score
    return result


def is_rejected_memory(meta: dict[str, Any] | None) -> bool:
    scoring = extract_memory_scoring(meta)
    if not scoring:
        return False
    if scoring.get("capture_decision") == "reject":
        return True
    return scoring.get("tier") == "rejected"


def _normalized_tier(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in _VALID_TIERS else None


def _normalized_capture_decision(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in _VALID_CAPTURE_DECISIONS else None


def _to_float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
