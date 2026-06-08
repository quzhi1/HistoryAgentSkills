#!/usr/bin/env python3
"""Cross-platform virtualenv setup for the Chinese history skill."""

from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from venv_utils import display_venv_command, venv_executable  # noqa: E402


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / "venv"
REQUIREMENTS = ROOT / "requirements.txt"


def run(command: list[str], description: str) -> None:
    print(f"• {description}...")
    subprocess.check_call(command, cwd=ROOT)


def create_venv(clear: bool = False) -> None:
    if VENV_DIR.exists() and not clear:
        print("✓ 虚拟环境已存在，跳过创建")
        return
    print("• 创建虚拟环境...")
    builder = venv.EnvBuilder(with_pip=True, clear=clear)
    builder.create(VENV_DIR)
    print("✓ 虚拟环境创建成功")


def check_import(venv_python: Path, module: str, label: str) -> bool:
    result = subprocess.run(
        [str(venv_python), "-c", f"import {module}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"✓ {label} 已安装")
        return True
    print(f"✗ {label} 安装失败")
    return False


def validate_install() -> bool:
    venv_python = venv_executable(ROOT, "python")
    ok = True
    ok &= check_import(venv_python, "requests", "requests")
    ok &= check_import(venv_python, "cnmaps_data", "cnmaps-data")
    ok &= check_import(venv_python, "opencc", "opencc-python-reimplemented")

    try:
        mdict_bin = venv_executable(ROOT, "mdict")
    except FileNotFoundError as exc:
        print(f"✗ mdict-utils 未生成可执行文件: {exc}")
        return False

    result = subprocess.run([str(mdict_bin), "--version"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ mdict-utils 已安装")
    else:
        print("✗ mdict-utils 可能未正确安装")
        ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="创建虚拟环境并安装项目依赖")
    parser.add_argument("--clear", action="store_true", help="重建已有 venv")
    args = parser.parse_args()

    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║          中国历史专家系统 - 环境设置                              ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print("")
    print(f"项目目录: {ROOT}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print("")

    create_venv(clear=args.clear)
    venv_python = venv_executable(ROOT, "python")
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "-q"], "升级 pip")
    run([str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS)], "安装项目依赖")

    print("")
    print("🧪 测试安装...")
    ok = validate_install()

    print("")
    if ok:
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║          ✅ 环境设置完成！                                         ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")
        print("")
        print("下一步：")
        print(f"  1. 测试系统: {display_venv_command('python')} test_system.py")
        print(f"  2. 查询辞典: {display_venv_command('mdict')} -q \"李白\" dict/历史辞典4合1.mdx")
        print("  3. 全局安装: ./install-global.sh 或 .\\install-global.ps1")
        print("")
        print("后续命令可直接调用 venv 内的可执行文件，不需要激活虚拟环境。")
        return 0

    print("❌ 环境设置未完全通过，请检查上面的错误后重试。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
