# eitraining deployment

`eitraining` is an offline replay and training artifact pipeline. It consumes
experience exports from `eimemory`, the skill registry from `eiskills`, and emits
outcome reports plus training examples for later review or tuning.

## Canonical paths

| Purpose | Path |
| --- | --- |
| Source repository | `/dev-project/eitraining` |
| Immutable releases | `/opt/eitraining/releases/<commit>` |
| Active release | `/opt/eitraining/current` |
| Release virtual environment | `/opt/eitraining/current/.venv` |
| Runtime state | `/var/lib/eitraining` |
| Runtime configuration | `/etc/eitraining` |
| Logs | `/var/log/eitraining` |

## Release

```bash
/dev-project/eitraining/deploy/install_immutable_release.sh
```

The release script prepares `/var/lib/eitraining/inputs` and
`/var/lib/eitraining/outcomes`. It does not copy or mutate upstream memory or
skill registry files.

## Weekly pipeline

```bash
mkdir -p /home/darrow/.config/systemd/user
cp /dev-project/eitraining/deploy/systemd/eitraining-weekly.* /home/darrow/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now eitraining-weekly.timer
```

Default inputs:

```text
EITRAINING_EXPERIENCES=/var/lib/eimemory/exports/experiences.jsonl
EITRAINING_REGISTRY=/var/lib/eiskills/skills.jsonl
EITRAINING_OUTPUT_DIR=/var/lib/eitraining/outcomes
```

Override them in `/etc/eitraining/eitraining.env` when a run should use a
different export bundle.

## Manual run

```bash
/opt/eitraining/current/.venv/bin/eitraining run-loop \
  --experiences /var/lib/eimemory/exports/experiences.jsonl \
  --registry /var/lib/eiskills/skills.jsonl \
  --output-dir /var/lib/eitraining/outcomes
```

## Verification

```bash
/opt/eitraining/current/.venv/bin/eitraining build-examples \
  --experiences /var/lib/eimemory/exports/experiences.jsonl \
  --output /tmp/eitraining-examples.jsonl

systemctl --user start eitraining-weekly.service
journalctl --user -u eitraining-weekly.service -n 100 --no-pager
```
