#!/usr/bin/env bash
# macOS/Linux wrapper for the cross-platform virtualenv setup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=python
else
  echo "❌ 未找到 Python，请先安装 Python 3"
  exit 1
fi

exec "$PYTHON_CMD" "$SCRIPT_DIR/setup_venv.py" "$@"
