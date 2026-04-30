from __future__ import annotations

from typing import Any

from .normalize import evidence_id, meaningful_skill_traces, selected_skill_ids
from .replay import _trace_passed


def build_training_examples(experiences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for trace in meaningful_skill_traces(experiences):
        example_id = evidence_id(trace)
        examples.append(
            {
                "id": f"train:{example_id}",
                "source_experience_id": example_id,
                "task_type": str(trace.get("task_type") or ""),
                "input": str(trace.get("input_summary") or trace.get("summary") or ""),
                "target": {
                    "selected_skills": selected_skill_ids(trace),
                    "actions": list(trace.get("actions") or []) if isinstance(trace.get("actions"), list) else [],
                },
                "outcome": {
                    "passed": _trace_passed(trace),
                    "outcome": trace.get("outcome"),
                    "feedback": trace.get("feedback"),
                    "latency_ms": trace.get("latency_ms"),
                },
                "metadata": {
                    "trace_reason": (trace.get("meta") or {}).get("trace_reason") if isinstance(trace.get("meta"), dict) else None,
                    "write_policy_version": (trace.get("meta") or {}).get("write_policy_version") if isinstance(trace.get("meta"), dict) else None,
                },
            }
        )
    return examples
