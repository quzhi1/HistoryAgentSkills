#!/usr/bin/env python3
"""System checks for the Chinese history expert skill."""

from __future__ import annotations

import os
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def test_imports() -> bool:
    """Check Python and command dependencies."""
    print("测试1: 检查依赖...")
    ok = True

    try:
        import requests  # noqa: F401
        print("✓ requests 已安装")
    except ImportError:
        print("✗ requests 未安装，请运行: ./setup_venv.sh")
        ok = False

    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram')")
        print("✓ SQLite FTS5 trigram 可用")
    except sqlite3.DatabaseError as exc:
        print(f"✗ SQLite FTS5 trigram 不可用: {exc}")
        ok = False

    mdict_bin = ROOT / "venv" / "bin" / "mdict"
    if not mdict_bin.exists():
        print(f"✗ mdict 不存在: {mdict_bin}，请运行 ./setup_venv.sh")
        return False
    result = subprocess.run([str(mdict_bin), "--version"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✓ mdict-utils 已安装")
    else:
        print("✗ mdict-utils 可能未正确安装")
        ok = False

    return ok


def test_files() -> bool:
    """Check required project files."""
    print("\n测试2: 检查文件...")
    required_files = [
        "dict/历史辞典4合1.mdx",
        "dict/scripts/query_dict.py",
        "cnkgraph/scripts/query_api.py",
        "scripts/history_query.py",
        "scripts/fetch_dynasty_data.py",
        "scripts/dynasty_converter.py",
        "scripts/book_search.py",
        "data/dynasty/dynasty_index.json",
        "data/dynasty/metadata.json",
        "SKILL.md",
        "dict/SKILL.md",
        "cnkgraph/SKILL.md",
    ]
    all_exist = True
    for file in required_files:
        path = ROOT / file
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 不存在")
            all_exist = False

    raw_dir = ROOT / "data" / "dynasty" / "raw"
    raw_count = len(list(raw_dir.glob("*.json"))) if raw_dir.exists() else 0
    metadata_path = ROOT / "data" / "dynasty" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    expected_count = metadata.get("index_count", 879)
    if raw_count == expected_count == metadata.get("raw_count"):
        print(f"✓ data/dynasty/raw 包含 {raw_count} 个 JSON 文件")
    else:
        print(f"✗ 年表 JSON 数量不一致: raw={raw_count}, metadata={metadata}")
        all_exist = False

    return all_exist


def test_scripts_compile() -> bool:
    """Check Python scripts compile."""
    print("\n测试3: 检查脚本语法...")
    scripts = [
        "dict/scripts/query_dict.py",
        "cnkgraph/scripts/query_api.py",
        "scripts/history_query.py",
        "scripts/fetch_dynasty_data.py",
        "scripts/dynasty_converter.py",
        "scripts/book_search.py",
    ]
    result = subprocess.run(
        [str(ROOT / "venv" / "bin" / "python"), "-m", "py_compile", *scripts],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode == 0:
        print("✓ 所有 Python 脚本语法通过")
        return True
    print(result.stderr)
    return False


def _fixture_index():
    return [
        {
            "dynasty": "唐",
            "reignTitle": "天宝",
            "reignTitles": ["天宝"],
            "monarch": "玄宗",
            "monarchName": "李隆基",
            "begin": 742,
            "end": 756,
            "uri": "fixture://tang-tianbao",
            "source_credit": "fixture",
        },
        {
            "dynasty": "吴越",
            "reignTitle": "天宝",
            "reignTitles": ["天宝"],
            "monarch": "",
            "monarchName": "钱镠",
            "begin": 908,
            "end": 912,
            "uri": "fixture://wuyue-tianbao",
            "source_credit": "fixture",
        },
        {
            "dynasty": "清",
            "reignTitle": "康熙",
            "reignTitles": ["康熙"],
            "monarch": "圣祖",
            "monarchName": "爱新觉罗玄烨",
            "begin": 1662,
            "end": 1722,
            "uri": "fixture://qing-kangxi",
            "source_credit": "fixture",
        },
        {
            "dynasty": "民国",
            "reignTitle": "",
            "reignTitles": [],
            "monarch": "",
            "monarchName": "",
            "begin": 1912,
            "end": 1949,
            "uri": "fixture://minguo",
            "source_credit": "fixture",
        },
    ]


def test_dynasty_converter() -> bool:
    """Test reign-year conversion with fixtures."""
    print("\n测试4: 年号换算...")
    from dynasty_converter import convert_era_expression

    ok = True
    index = _fixture_index()

    checks = [
        ("天宝三载", [744, 910]),
        ("天宝十四载", [755]),
        ("康熙六十一年", [1722]),
        ("民国元年", [1912]),
    ]
    for expression, years in checks:
        result = convert_era_expression(expression, index=index)
        got = sorted(item["gregorian_year"] for item in result["matches"])
        if got == sorted(years):
            print(f"✓ {expression} -> {got}")
        else:
            print(f"✗ {expression} 预期 {years}，实际 {got}，错误 {result['errors']}")
            ok = False

    ambiguous = convert_era_expression("天宝三载", index=index)
    if len(ambiguous["matches"]) == 2:
        print("✓ 同名年号默认返回全部匹配")
    else:
        print("✗ 同名年号未返回全部匹配")
        ok = False

    return ok


def test_fetch_normalization() -> bool:
    """Test dynasty fetcher normalization and fail-closed validation."""
    print("\n测试5: 年表数据规范化...")
    from fetch_dynasty_data import DynastyDataError, normalize_item

    item = {
        "dynasty": "唐",
        "reignTitle": "天宝",
        "monarch": "玄宗",
        "monarchName": "李隆基",
        "begin": "742",
        "end": "756",
        "uri": "http://data.library.sh.cn/authority/temporal/fixture",
    }
    normalized = normalize_item(item, {})
    if normalized["begin"] == 742 and normalized["end"] == 756 and normalized["reignTitles"] == ["天宝"]:
        print("✓ 年表字段规范化通过")
    else:
        print(f"✗ 年表字段规范化异常: {normalized}")
        return False

    bad_item = dict(item)
    bad_item.pop("begin")
    try:
        normalize_item(bad_item, {})
    except DynastyDataError:
        print("✓ 字段缺失会失败闭合")
        return True
    print("✗ 字段缺失未失败")
    return False


def test_epub_search() -> bool:
    """Test local EPUB indexing and searching."""
    print("\n测试6: EPUB 全文检索...")
    from book_search import search_books

    try:
        results = search_books("甲骨文", limit=1, rebuild=True)
    except Exception as exc:
        print(f"✗ EPUB 检索失败: {exc}")
        return False
    if not results:
        print("✗ 未检索到“甲骨文”")
        return False
    item = results[0]
    required = ["book_title", "author", "href", "section", "snippet"]
    if all(key in item for key in required):
        print(f"✓ EPUB 检索命中: {item['book_title']} / {item['section']}")
        return True
    print(f"✗ EPUB 检索结果缺字段: {item}")
    return False


def main() -> int:
    os.chdir(ROOT)
    print("=" * 60)
    print("中国历史专家系统 - 系统测试")
    print("=" * 60)

    tests = [
        ("依赖", test_imports),
        ("文件完整性", test_files),
        ("脚本语法", test_scripts_compile),
        ("年号换算", test_dynasty_converter),
        ("年表规范化", test_fetch_normalization),
        ("EPUB检索", test_epub_search),
    ]

    results = []
    for name, func in tests:
        try:
            results.append((name, func()))
        except Exception as exc:
            print(f"✗ {name} 测试异常: {exc}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    for name, result in results:
        print(f"{name}: {'✓ 通过' if result else '✗ 失败'}")
    print(f"\n总计: {passed}/{len(results)} 测试通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
