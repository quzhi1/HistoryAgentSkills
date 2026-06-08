#!/usr/bin/env python3
"""Run project commands through the local virtualenv without activation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from venv_utils import venv_executable


ROOT = Path(__file__).resolve().parents[1]


def _usage() -> None:
    print("用法: python scripts/run_in_venv.py <script.py|mdict|python> [args...]")
    print('示例: python scripts/run_in_venv.py scripts/history_query.py "李白"')
    print('示例: python scripts/run_in_venv.py mdict -q "李白" dict/历史辞典4合1.mdx')


def build_command(argv: list[str]) -> list[str]:
    if not argv:
        raise ValueError("缺少要运行的命令")

    target, *args = argv
    if target in {"python", "python.exe"}:
        return [str(venv_executable(ROOT, "python")), *args]
    if target == "mdict":
        return [str(venv_executable(ROOT, "mdict")), *args]

    target_path = (ROOT / target).resolve()
    try:
        target_path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"命令必须位于项目目录内: {target}") from exc
    if not target_path.exists():
        raise FileNotFoundError(f"找不到项目命令: {target}")
    if target_path.suffix.lower() == ".py":
        return [str(venv_executable(ROOT, "python")), str(target_path), *args]
    return [str(target_path), *args]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        _usage()
        return 0 if argv else 2

    try:
        command = build_command(argv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        print("请先在项目根目录运行 setup_venv.py / setup_venv.sh / setup_venv.ps1。", file=sys.stderr)
        return 1

    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
