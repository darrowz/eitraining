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
