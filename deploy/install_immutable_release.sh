#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/dev-project/eitraining}"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/eitraining}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STATE_ROOT="${EITRAINING_STATE_DIR:-/var/lib/eitraining}"
COMMIT="${1:-$(git -C "$REPO_DIR" rev-parse --short HEAD)}"
RELEASE_DIR="$INSTALL_ROOT/releases/$COMMIT"
CURRENT_LINK="$INSTALL_ROOT/current"

if ! git -C "$REPO_DIR" rev-parse --verify "$COMMIT^{commit}" >/dev/null 2>&1; then
  echo "Unknown commit: $COMMIT" >&2
  exit 2
fi

mkdir -p "$INSTALL_ROOT/releases" "$INSTALL_ROOT/run" "$INSTALL_ROOT/logs" "$STATE_ROOT/inputs" "$STATE_ROOT/outcomes" /var/log/eitraining /etc/eitraining

if [ ! -d "$RELEASE_DIR" ]; then
  mkdir -p "$RELEASE_DIR"
  git -C "$REPO_DIR" archive "$COMMIT" | tar -C "$RELEASE_DIR" -xf -
fi

if [ ! -x "$RELEASE_DIR/.venv/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$RELEASE_DIR/.venv"
fi

"$RELEASE_DIR/.venv/bin/python" -m pip install --upgrade pip
"$RELEASE_DIR/.venv/bin/python" -m pip install "$RELEASE_DIR"

ln -sfn "$RELEASE_DIR" "$CURRENT_LINK.next"
mv -Tf "$CURRENT_LINK.next" "$CURRENT_LINK"

echo "release=$RELEASE_DIR"
echo "current=$CURRENT_LINK"
echo "commit=$COMMIT"
echo "state=$STATE_ROOT"
