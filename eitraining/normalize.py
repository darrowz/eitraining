from __future__ import annotations

from typing import Any


def normalize_experience(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten eimemory record envelopes into a replay-friendly experience item."""
    if not isinstance(record, dict):
        return {}
    content = record.get("content") if isinstance(record.get("content"), dict) else {}
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
    payload_meta = content.get("meta") if isinstance(content.get("meta"), dict) else {}
    report_type = meta.get("report_type") or provenance.get("report_type") or record.get("report_type")

    normalized = dict(content) if report_type == "skill_trace" else dict(record)
    normalized["record_id"] = str(record.get("record_id") or normalized.get("record_id") or "")
    normalized["id"] = str(normalized.get("id") or normalized.get("trace_id") or record.get("record_id") or "")
    normalized["report_type"] = str(report_type or normalized.get("report_type") or "")
    normalized["meta"] = {**meta, **payload_meta}
    normalized["provenance"] = provenance
    normalized["summary"] = str(normalized.get("input_summary") or record.get("summary") or normalized.get("summary") or "")
    if not normalized.get("selected_skills") and meta.get("selected_skill_ids"):
        normalized["selected_skills"] = meta.get("selected_skill_ids")
    return normalized


def meaningful_skill_traces(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [normalize_experience(record) for record in records if isinstance(record, dict)]
    return [item for item in items if _is_meaningful_skill_trace(item)]


def _is_meaningful_skill_trace(item: dict[str, Any]) -> bool:
    if item.get("report_type") != "skill_trace":
        return False
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    if not (meta.get("write_policy_version") == "meaningful_event_v1" or meta.get("trace_reason")):
        return False
    return bool(item.get("id") and item.get("selected_skills"))


def selected_skill_ids(item: dict[str, Any]) -> list[str]:
    skills = item.get("selected_skills") or item.get("skill_ids") or []
    if not isinstance(skills, list):
        return []
    result: list[str] = []
    for skill in skills:
        if isinstance(skill, dict):
            value = skill.get("skill_id") or skill.get("id") or skill.get("name")
        else:
            value = skill
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def evidence_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("trace_id") or item.get("record_id") or "")
