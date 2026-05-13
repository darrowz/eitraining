# eitraining

`eitraining` closes the first production loop between eibrain, eimemory, and eiskills.

It consumes eimemory experience exports, evaluates eiskills candidates against their evidence,
and emits replay/outcome/training artifacts that eiskills can use as an automatic promotion gate.

Current scope:

- Normalize eimemory JSON/JSONL experience exports.
- Extract meaningful skill traces and evidence records.
- Build candidate replay results from candidate evidence IDs.
- Emit training examples for future policy/model tuning.
- Produce an outcome report for weekly audit.

Boundary:

- eibrain owns exploration and event capture.
- eimemory owns durable experience/world knowledge records.
- eiskills owns skill registry, promotion, rollback, and routing.
- eitraining owns evaluation artifacts and training datasets.

## Memory Scoring Contract

`eitraining` reads memory quality from `meta.scoring.memory_score_v1` when it is
present and falls back to legacy `meta.quality` for older exports.

Expected tiers:

- `rejected`: ignored for replay/training inputs
- `candidate`: retained but lower-confidence memory
- `confirmed`: normal reusable memory
- `core`: highest-salience reusable memory

Compatibility rules:

- `meta.scoring.memory_score_v1.tier` is the preferred tier signal.
- Legacy `meta.quality.quality_tier` remains accepted.
- Legacy `meta.quality.capture_decision="reject"` is still honored even though
  older records may keep `quality_tier="candidate"`.
- Replay artifacts now record included evidence-tier counts under
  `details.memory_tier_counts` for downstream auditing.
