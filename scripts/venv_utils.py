"""Helpers for locating project virtualenv executables across platforms."""

from __future__ import annotations

import os
from pathlib import Path


def venv_bin_dir(project_root: str | Path, platform: str | None = None) -> Path:
    """Return the virtualenv script directory for the requested platform."""
    platform_name = platform or os.name
    subdir = "Scripts" if platform_name == "nt" else "bin"
    return Path(project_root) / "venv" / subdir


def executable_candidates(project_root: str | Path, name: str, platform: str | None = None) -> list[Path]:
    """Return likely virtualenv executable paths, ordered by preference."""
    platform_name = platform or os.name
    base = venv_bin_dir(project_root, platform_name)
    if platform_name != "nt":
        return [base / name]

    if name.lower() == "python":
        names = ["python.exe", "python"]
    else:
        names = [f"{name}.exe", f"{name}.cmd", f"{name}.bat", name]
    return [base / candidate for candidate in names]


def venv_executable(
    project_root: str | Path,
    name: str,
    platform: str | None = None,
    must_exist: bool = True,
) -> Path:
    """Locate an executable inside the project's virtualenv."""
    candidates = executable_candidates(project_root, name, platform)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    if must_exist:
        formatted = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"找不到虚拟环境可执行文件 {name}: {formatted}")
    return candidates[0]


def display_venv_command(name: str, platform: str | None = None) -> str:
    """Return a documentation-friendly relative command path."""
    platform_name = platform or os.name
    if platform_name == "nt":
        suffix = ".exe" if name.lower() in {"python", "mdict"} else ""
        return f"venv\\Scripts\\{name}{suffix}"
    return f"venv/bin/{name}"
