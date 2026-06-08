#!/usr/bin/env python3
"""System checks for the Chinese history expert skill."""

from __future__ import annotations

import os
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from venv_utils import venv_executable  # noqa: E402


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
        import cnmaps_data  # noqa: F401
        print("✓ cnmaps-data 已安装")
    except ImportError:
        print("✗ cnmaps-data 未安装，请运行: ./setup_venv.sh")
        ok = False

    try:
        import opencc  # noqa: F401
        print("✓ opencc-python-reimplemented 已安装")
    except ImportError:
        print("✗ opencc-python-reimplemented 未安装，请运行: ./setup_venv.sh")
        ok = False

    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram')")
        print("✓ SQLite FTS5 trigram 可用")
    except sqlite3.DatabaseError as exc:
        print(f"✗ SQLite FTS5 trigram 不可用: {exc}")
        ok = False

    mdict_bin = venv_executable(ROOT, "mdict", must_exist=False)
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
        "scripts/dynasty_converter.py",
        "scripts/book_search.py",
        "scripts/place_resolver.py",
        "scripts/place_admin_resolver.py",
        "scripts/history_map_link.py",
        "scripts/shidian_link.py",
        "scripts/source_book_index.py",
        "scripts/update_history_map_index.py",
        "scripts/update_source_book_index.py",
        "scripts/run_in_venv.py",
        "scripts/venv_utils.py",
        "data/history_map_index.json",
        "data/source_book_index.sqlite",
        "setup_venv.py",
        "SKILL.md",
        "AGENTS.md",
        "CLAUDE.md",
        "install_global.py",
        "setup_venv.sh",
        "setup_venv.ps1",
        "install-global.sh",
        "install-global.ps1",
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

    removed_paths = [
        "scripts/fetch_dynasty_data.py",
        "data/dynasty",
    ]
    for file in removed_paths:
        path = ROOT / file
        if path.exists():
            print(f"✗ 已废弃的本地年表文件仍存在: {file}")
            all_exist = False
        else:
            print(f"✓ 已移除 {file}")

    return all_exist


def test_workflow_guardrails() -> bool:
    """Check documentation keeps mandatory workflow gates explicit."""
    print("\n测试3: 工作流强制门禁文档...")
    requirements = {
        "SKILL.md": [
            "单一真理源",
            "多人物/列表型答案",
            "不传 `--admin`",
            "needs_admin",
            "静默省略",
            "地点与地图核验",
            "place_admin_resolver.py",
            "反查历史地名",
            "识典原文链接交付",
            "正文出处行已交付",
            "正文首次出现或“地点与地图核验”已交付",
            "清单 C：被引史料说明",
            'venv/bin/mdict -q "史料书名"',
            "每部被引用史料",
        ],
        "README.md": [
            "多人物/列表型回答",
            "不传 `--admin`",
            "needs_admin",
            "静默省略",
            "逐条交付",
            "二次验证未通过",
            "不附左图右史链接",
            "place_admin_resolver.py",
            "反查历史地名",
            "必说明被引史料",
            "每部被引用史料都要有简介",
            "单一真理源",
        ],
        "CLAUDE.md": [
            "单一真理源",
            "SKILL.md",
            "venv/bin/mdict",
            "venv\\Scripts",
            "不要 `source",
            "test_system.py",
        ],
        "AGENTS.md": [
            "单一真理源",
            "SKILL.md",
            "venv/bin/mdict",
            "venv\\Scripts",
            "不要 `source",
            "test_system.py",
        ],
        "COMMON_MISTAKES.md": [
            "错误示例7",
            "错误示例8",
            "脚本跑了",
            "逐条交付结果",
            "history_map_link.py",
            "不传 --admin",
            "needs_admin",
            "错误示例10",
            "反查历史地名",
            "只给史料出处",
        ],
        ".claude/commands/history.md": [
            "scripts/run_in_venv.py",
            "查询被引用史料说明",
            "<史料书名>",
            "被引史料说明",
        ],
        ".claude/agents/history-fact-checker.md": [
            "被引史料说明核查",
            "<史料书名>",
            "缺少被引史料说明",
        ],
    }
    ok = True
    for filename, needles in requirements.items():
        text = (ROOT / filename).read_text(encoding="utf-8")
        missing = [needle for needle in needles if needle not in text]
        if missing:
            print(f"✗ {filename} 缺少门禁关键词: {', '.join(missing)}")
            ok = False
        else:
            print(f"✓ {filename} 已写明强制工作流门禁")
    return ok


def test_cross_platform_installation() -> bool:
    """Check setup/install scripts avoid hard-coded platform paths."""
    print("\n测试4: 跨平台安装脚本...")
    from tempfile import TemporaryDirectory

    from install_global import install_global
    from venv_utils import display_venv_command

    ok = True
    windows_python = venv_executable(ROOT, "python", platform="nt", must_exist=False)
    windows_mdict = venv_executable(ROOT, "mdict", platform="nt", must_exist=False)
    posix_python = venv_executable(ROOT, "python", platform="posix", must_exist=False)
    if (
        windows_python.as_posix().endswith("venv/Scripts/python.exe")
        and windows_mdict.as_posix().endswith("venv/Scripts/mdict.exe")
        and posix_python.as_posix().endswith("venv/bin/python")
        and display_venv_command("python", platform="nt") == "venv\\Scripts\\python.exe"
    ):
        print("✓ venv 路径会按 Windows/POSIX 分别解析")
    else:
        print(
            "✗ venv 路径解析错误: "
            f"win_python={windows_python}, win_mdict={windows_mdict}, posix_python={posix_python}"
        )
        ok = False

    forbidden = "/Users/zhi.q/HistoryAgentSkills"
    checked_files = [
        "setup_venv.sh",
        "install-global.sh",
        "setup_venv.py",
        "install_global.py",
        "setup_venv.ps1",
        "install-global.ps1",
        ".claude/commands/history.md",
        ".claude/agents/history-fact-checker.md",
    ]
    for filename in checked_files:
        text = (ROOT / filename).read_text(encoding="utf-8")
        if forbidden in text:
            print(f"✗ {filename} 仍含旧的硬编码项目目录")
            ok = False
    if ok:
        print("✓ 安装入口和 Claude 模板不再硬编码本机项目目录")

    if "source venv/bin/activate" in (ROOT / "setup_venv.sh").read_text(encoding="utf-8"):
        print("✗ setup_venv.sh 仍依赖 POSIX activate 路径")
        ok = False
    else:
        print("✓ setup_venv.sh 不再依赖 source venv/bin/activate")

    with TemporaryDirectory() as tmpdir:
        outputs = install_global(project_root=ROOT, claude_dir=Path(tmpdir))
        skill_text = outputs["skill"].read_text(encoding="utf-8")
        command_text = outputs["command"].read_text(encoding="utf-8")
        agent_text = outputs["agent"].read_text(encoding="utf-8")
        if (
            str(ROOT) in skill_text
            and str(ROOT / "scripts" / "run_in_venv.py") in command_text
            and "全局安装信息" in agent_text
            and "__PROJECT_ROOT__" not in command_text
        ):
            print("✓ 全局安装会按当前项目目录生成 skill/command/agent")
        else:
            print("✗ 全局安装生成物缺少当前项目目录或 runner")
            ok = False

    return ok


def test_scripts_compile() -> bool:
    """Check Python scripts compile."""
    print("\n测试5: 检查脚本语法...")
    scripts = [
        "dict/scripts/query_dict.py",
        "cnkgraph/scripts/query_api.py",
        "scripts/history_query.py",
        "scripts/dynasty_converter.py",
        "scripts/book_search.py",
        "scripts/place_resolver.py",
        "scripts/place_admin_resolver.py",
        "scripts/history_map_link.py",
        "scripts/shidian_link.py",
        "scripts/source_book_index.py",
        "scripts/update_history_map_index.py",
        "scripts/update_source_book_index.py",
        "scripts/run_in_venv.py",
        "scripts/venv_utils.py",
        "setup_venv.py",
        "install_global.py",
    ]
    result = subprocess.run(
        [str(venv_executable(ROOT, "python")), "-m", "py_compile", *scripts],
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


class FakeCalendarClient:
    """Offline fixture for cnkgraph Calendar API tests."""

    def __init__(self):
        self.payloads = {
            "天宝三载": _calendar_payload(744, "天宝", "续唐", "李隆基", "742年", "756年七月", "三年"),
            "吴越天宝三载": _calendar_payload(910, "天宝", "吴越", "钱镠", "908年", "912年", "三年"),
            "天宝十四载": _calendar_payload(755, "天宝", "续唐", "李隆基", "742年", "756年七月", "十四年"),
            "康熙六十一年": _calendar_payload(1722, "康熙", "清朝", "玄烨", "1662年", "1722年", "六十一年"),
            "民国元年": _calendar_payload(1912, None, "民国", None, "1912年", "1949年", "元年", era_name="民国"),
            "先天二年": _calendar_payload(713, "先天", "续唐", "李隆基", "712年八月", "713年十一月", "二年"),
            "后唐同光元年": _calendar_payload(923, "同光", "后唐", "李存勖", "923年四月", "926年四月", "元年"),
            "后唐清泰三年": _calendar_payload(936, "清泰", "后唐", "李从珂", "934年四月", "936年闰十一月", "三年"),
            "后晋天福元年": _calendar_payload(936, "天福", "后晋", "石敬瑭", "936年十一月", "947年十二月", "元年"),
            "清泰三年": _multi_calendar_payload(
                936,
                "清泰",
                [
                    ("后唐", "李从珂", "934年四月", "936年闰十一月", "三年"),
                    ("吴越", "钱元瓘", "934年四月", "936年闰十一月", "三年"),
                ],
            ),
        }

    def get_date(self, key: str):
        from dynasty_converter import EraConversionError

        if key not in self.payloads:
            raise EraConversionError(f"fixture missing Calendar/Date payload: {key}")
        return self.payloads[key]


def _calendar_payload(
    year: int,
    date_era_name: str | None,
    dynasty: str,
    king_name: str | None,
    begin: str,
    end: str,
    calculated_year: str,
    era_name: str | None = None,
):
    return _multi_calendar_payload(
        year,
        date_era_name,
        [(dynasty, king_name, begin, end, calculated_year)],
        era_name=era_name or date_era_name,
    )


def _multi_calendar_payload(year: int, date_era_name: str | None, rows, era_name: str | None = None):
    return {
        "Date": {
            "Year": str(year),
            "YearGanZhi": "",
            "EraName": date_era_name,
            "EraId": 1 if date_era_name else 0,
        },
        "EraYears": [
            {
                "Dynasty": dynasty,
                "Kings": [
                    {
                        "Id": index + 1,
                        "Name": king_name,
                        "EraYears": [
                            {
                                "Id": index + 100,
                                "Name": era_name or date_era_name,
                                "BeginYear": begin,
                                "EndYear": end,
                                "CalculatedYear": calculated_year,
                            }
                        ],
                    }
                ],
            }
            for index, (dynasty, king_name, begin, end, calculated_year) in enumerate(rows)
        ],
        "Links": {"Count": 0},
    }


def test_dynasty_converter() -> bool:
    """Test reign-year conversion with fixtures."""
    print("\n测试6: 年号换算...")
    from dynasty_converter import convert_era_expression

    ok = True
    client = FakeCalendarClient()

    checks = [
        ("天宝三载", [744]),
        ("吴越 天宝三载", [910]),
        ("天宝十四载", [755]),
        ("康熙六十一年", [1722]),
        ("民国元年", [1912]),
        ("先天二年", [713]),
        ("后唐 同光元年", [923]),
        ("后唐 清泰三年", [936]),
        ("后晋 天福元年", [936]),
    ]
    for expression, years in checks:
        result = convert_era_expression(expression, api_client=client)
        got = sorted(item["gregorian_year"] for item in result["matches"])
        if got == sorted(years):
            print(f"✓ {expression} -> {got}")
        else:
            print(f"✗ {expression} 预期 {years}，实际 {got}，错误 {result['errors']}")
            ok = False

    ambiguous = convert_era_expression("清泰三年", api_client=client)
    if len(ambiguous["matches"]) == 2:
        print("✓ API 多政权候选会保留为多条匹配")
    else:
        print("✗ API 多政权候选未保留")
        ok = False

    return ok


def test_epub_search() -> bool:
    """Test local EPUB indexing and searching."""
    print("\n测试7: EPUB 全文检索...")
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


class FakeTgazPlaceClient:
    """Offline fixture for CHGIS/TGAZ placename tests."""

    def __init__(self):
        self.search_payloads = {
            "古城": [_tgaz_payload("hvd_1", "古城", 700, 800)],
            "同名": [
                _tgaz_payload("hvd_2", "同名", 700, 800, 2, 2),
                _tgaz_payload("hvd_3", "同名", 900, 1000, 7, 7),
            ],
            "两城": [
                _tgaz_payload("hvd_4", "两城", 700, 800, 2, 2),
                _tgaz_payload("hvd_5", "两城", 700, 800, 4, 4),
            ],
            "无坐标": [_tgaz_payload("hvd_6", "无坐标", 700, 800)],
            "海外": [_tgaz_payload("hvd_7", "海外", 700, 800, 20, 20)],
            "省内": [_tgaz_payload("hvd_8", "省内", 700, 800, 9, 9)],
            "登封": [
                _tgaz_payload(
                    "hvd_9",
                    "登封县",
                    696,
                    1911,
                    2,
                    2,
                    present_location="今测试县",
                    source_note="旧唐书：河南府登封县，隋嵩阳县。",
                )
            ],
            "嵩阳县": [
                _tgaz_payload(
                    "hvd_10",
                    "嵩阳县",
                    605,
                    642,
                    2,
                    2,
                    parent="豫州 / 河南郡 / 洛州",
                    present_location="今测试县",
                    source_note="隋大业元年置，属豫州，三年属河南郡；唐属洛州。治今测试县。",
                )
            ],
            "历城": [
                _tgaz_payload(
                    "hvd_11",
                    "历城县",
                    900,
                    1911,
                    2,
                    2,
                    present_location="今测试县",
                    source_note="明洪武九年改齐州为济南府，治今测试县。",
                )
            ],
            "济南府": [
                _tgaz_payload(
                    "hvd_12",
                    "济南府",
                    1369,
                    1911,
                    2,
                    2,
                    parent="山东布政司",
                    present_location="今测试县",
                    source_note="明属山东布政司，治今测试县。",
                )
            ],
        }
        self.detail_payloads = {
            "hvd_1": _tgaz_payload("hvd_1", "古城", 700, 800, 2, 2),
        }

    def search(self, name: str, year: int | None = None, feature_type: str | None = None):
        return self.search_payloads.get(name, [])

    def get_by_id(self, sys_id: str):
        return self.detail_payloads.get(sys_id, {})


def _tgaz_payload(
    sys_id: str,
    name: str,
    begin: int,
    end: int,
    lon: float | None = None,
    lat: float | None = None,
    parent: str = "测试州",
    present_location: str = "",
    source_note: str = "",
):
    parent_items = [{"name": item.strip()} for item in parent.split("/") if item.strip()]
    payload = {
        "sys_id": sys_id,
        "spellings": [{"simplified Chinese": name}, {"transcribed in Pinyin": f"{name} Pinyin"}],
        "feature_type": {"name": "县", "English": "county"},
        "temporal": {"begin year": str(begin), "end year": str(end)},
        "historical_context": {"part of": parent_items},
        "data source": "CHGIS",
        "source note": source_note,
    }
    if lon is not None and lat is not None:
        payload["spatial"] = {"longitude": str(lon), "latitude": str(lat)}
        if present_location:
            payload["spatial"]["present_location"] = [{"text": present_location}]
    return payload


def _square(min_x: float, min_y: float, max_x: float, max_y: float):
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_x, min_y],
                [max_x, min_y],
                [max_x, max_y],
                [min_x, max_y],
                [min_x, min_y],
            ]
        ],
    }


def test_place_resolver() -> bool:
    """Test historical placename to modern administration resolution offline."""
    print("\n测试8: 古地名现代行政区划映射...")
    from place_resolver import BoundaryRecord, ModernBoundaryResolver, resolve_place

    boundary_resolver = ModernBoundaryResolver(
        [
            BoundaryRecord(
                name="测试省",
                level="省",
                province="测试省",
                adcode="100000",
                source="fixture",
                geometry=_square(0, 0, 10, 10),
            ),
            BoundaryRecord(
                name="测试市",
                level="市",
                province="测试省",
                city="测试市",
                adcode="100100",
                source="fixture",
                geometry=_square(0, 0, 8, 8),
            ),
            BoundaryRecord(
                name="测试县",
                level="区县",
                province="测试省",
                city="测试市",
                district="测试县",
                adcode="100101",
                source="fixture",
                geometry=_square(1, 1, 5, 5),
            ),
        ]
    )
    client = FakeTgazPlaceClient()
    ok = True

    resolved = resolve_place("古城", year=750, tgaz_client=client, boundary_resolver=boundary_resolver)
    if resolved["status"] == "resolved" and resolved["modern_administration"]["district"] == "测试县":
        print("✓ TGAZ 详情坐标 + 县级现代边界反查通过")
    else:
        print(f"✗ 精确地名解析失败: {resolved}")
        ok = False

    active = resolve_place("同名", year=750, tgaz_client=client, boundary_resolver=boundary_resolver)
    if active["status"] == "resolved" and active["best_match"]["id"] == "hvd_2":
        print("✓ 年份过滤会排除非活动候选")
    else:
        print(f"✗ 年份过滤失败: {active}")
        ok = False

    ambiguous = resolve_place("两城", year=750, tgaz_client=client, boundary_resolver=boundary_resolver)
    if ambiguous["status"] == "ambiguous" and len(ambiguous["candidates"]) == 2:
        print("✓ 多候选歧义会保留候选列表")
    else:
        print(f"✗ 歧义处理失败: {ambiguous}")
        ok = False

    no_coordinate = resolve_place("无坐标", year=750, tgaz_client=client, boundary_resolver=boundary_resolver)
    if no_coordinate["status"] == "no_coordinate":
        print("✓ 无坐标候选返回 no_coordinate")
    else:
        print(f"✗ 无坐标处理失败: {no_coordinate}")
        ok = False

    out_of_range = resolve_place("古城", year=2000, tgaz_client=client, boundary_resolver=boundary_resolver)
    if out_of_range["status"] == "out_of_range":
        print("✓ 超出 TGAZ 年份范围返回 out_of_range")
    else:
        print(f"✗ 年份范围校验失败: {out_of_range}")
        ok = False

    outside = resolve_place("海外", year=750, tgaz_client=client, boundary_resolver=boundary_resolver)
    if outside["status"] == "resolved" and outside["modern_administration"] is None:
        print("✓ 坐标在现代边界外时不编造行政区划")
    else:
        print(f"✗ 边界外处理失败: {outside}")
        ok = False

    province_only = resolve_place("省内", year=750, tgaz_client=client, boundary_resolver=boundary_resolver)
    admin = province_only.get("modern_administration") or {}
    if province_only["status"] == "resolved" and admin.get("province") == "测试省" and admin.get("city") is None:
        print("✓ 只命中上级边界时只输出可确认层级")
    else:
        print(f"✗ 上级边界处理失败: {province_only}")
        ok = False

    required_keys = {"query", "status", "best_match", "candidates", "modern_administration", "note"}
    if required_keys.issubset(resolved):
        print("✓ JSON 输出顶层字段稳定")
    else:
        print(f"✗ JSON 输出字段缺失: {resolved.keys()}")
        ok = False

    return ok


def test_history_map_link() -> bool:
    """Test left-map/right-history route matching with the static index."""
    print("\n测试9: 左图右史同代一级区划链接...")
    from history_map_link import resolve_history_map_link, transition_map_pages

    ok = True

    ming_shandong = resolve_history_map_link("济南", 1582, "山东布政司", dynasty="明")
    if (
        ming_shandong["status"] == "resolved"
        and ming_shandong["url"] == "https://history-map.osgeo.cn/#/page20/html?ch=ch20_ming&sec=sec07_shandong"
    ):
        print("✓ 明代山东布政司匹配明朝山东地图")
    else:
        print(f"✗ 明代山东匹配失败: {ming_shandong}")
        ok = False

    qing_henan = resolve_history_map_link("开封", 1820, "河南省", dynasty="清")
    if (
        qing_henan["status"] == "resolved"
        and qing_henan["url"] == "https://history-map.osgeo.cn/#/page21/html?ch=ch21_qing&sec=sec12_henan"
    ):
        print("✓ 清代河南省匹配清朝河南省地图")
    else:
        print(f"✗ 清代河南匹配失败: {qing_henan}")
        ok = False

    wude_henan = resolve_history_map_link("汜水", 621, "河南诸郡", dynasty="唐")
    if (
        wude_henan["status"] == "resolved"
        and wude_henan["period"] == "隋"
        and wude_henan["url"] == "https://history-map.osgeo.cn/#/page14/html?ch=ch14_sui&sec=sec05_henan"
    ):
        print("✓ 唐武德过渡期可匹配隋朝河南诸郡地图")
    else:
        print(f"✗ 唐武德过渡期地图匹配失败: {wude_henan}")
        ok = False

    zhenguan_henan = resolve_history_map_link("汜水", 627, "河南诸郡", dynasty="唐")
    if zhenguan_henan["status"] == "not_found":
        print("✓ 过渡期规则不会套用到贞观以后")
    else:
        print(f"✗ 过渡期规则范围过宽: {zhenguan_henan}")
        ok = False

    transition_tang = transition_map_pages(621, "唐")
    transition_sui = transition_map_pages(621, "隋")
    transition_song = transition_map_pages(621, "宋")
    transition_post_wude = transition_map_pages(627, "唐")
    if (
        transition_tang == ["page14"]
        and transition_sui == ["page14"]
        and transition_song == []
        and transition_post_wude == []
    ):
        print("✓ 过渡期地图页由相邻时代边界通用推导")
    else:
        print(
            "✗ 过渡期地图页推导失败: "
            f"唐621={transition_tang}, 隋621={transition_sui}, "
            f"宋621={transition_song}, 唐627={transition_post_wude}"
        )
        ok = False

    with (ROOT / "data" / "history_map_index.json").open("r", encoding="utf-8") as f:
        index = json.load(f)
    bad_urls = [
        entry.get("url", "")
        for entry in index.get("entries", [])
        if "https://history-map.osgeo.cn/#/" not in entry.get("url", "")
    ]
    if not bad_urls:
        print("✓ 左图右史索引使用可分享 hash route，避免直连 404")
    else:
        print(f"✗ 左图右史索引存在非 hash route: {bad_urls[:3]}")
        ok = False

    needs_admin = resolve_history_map_link("济南", 1582, None, dynasty="明")
    if needs_admin["status"] == "needs_admin":
        print("✓ 缺少一级行政区时不会用现代省份反推")
    else:
        print(f"✗ 缺少 admin 未 fail-closed: {needs_admin}")
        ok = False

    mismatch = resolve_history_map_link("济南", 1582, "山东", dynasty="清")
    if mismatch["status"] == "period_mismatch":
        print("✓ 年份与朝代提示冲突时拒绝链接")
    else:
        print(f"✗ 时代冲突未拒绝: {mismatch}")
        ok = False

    missing_admin = resolve_history_map_link("济南", 1582, "不存在道", dynasty="明")
    if missing_admin["status"] == "not_found":
        print("✓ 一级区划标签不匹配时不猜地图")
    else:
        print(f"✗ 不存在区划未拒绝: {missing_admin}")
        ok = False

    shanxi = resolve_history_map_link("太原", 1582, "山西", dynasty="明")
    shaanxi = resolve_history_map_link("西安", 1582, "陕西", dynasty="明")
    if (
        shanxi["status"] == "resolved"
        and shanxi["url"].endswith("sec=sec09_shanxi")
        and shaanxi["status"] == "resolved"
        and shaanxi["url"].endswith("sec=sec12_shanxi")
        and shanxi["url"] != shaanxi["url"]
    ):
        print("✓ 山西/陕西不会因拼音 sec 同名而混淆")
    else:
        print(f"✗ 山西/陕西区分失败: 山西={shanxi} 陕西={shaanxi}")
        ok = False

    return ok


def test_place_admin_resolver() -> bool:
    """Test reverse modern-location to historical admin resolution offline."""
    print("\n测试10: 现代地点线索反查历史地名与地图区划...")
    from place_admin_resolver import resolve_place_admin
    from place_resolver import BoundaryRecord, ModernBoundaryResolver

    boundary_resolver = ModernBoundaryResolver(
        [
            BoundaryRecord(
                name="测试省",
                level="省",
                province="测试省",
                adcode="100000",
                source="fixture",
                geometry=_square(0, 0, 10, 10),
            ),
            BoundaryRecord(
                name="测试市",
                level="市",
                province="测试省",
                city="测试市",
                adcode="100100",
                source="fixture",
                geometry=_square(0, 0, 8, 8),
            ),
            BoundaryRecord(
                name="测试县",
                level="区县",
                province="测试省",
                city="测试市",
                district="测试县",
                adcode="100101",
                source="fixture",
                geometry=_square(1, 1, 5, 5),
            ),
        ]
    )
    client = FakeTgazPlaceClient()
    ok = True

    resolved = resolve_place_admin(
        "少林寺",
        625,
        dynasty="唐",
        modern_hint="测试县",
        lookup_names=["登封"],
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    derived_names = {item["name"] for item in resolved.get("derived_candidates", [])}
    if (
        resolved["status"] == "resolved"
        and resolved["historical_place"]["name"] == "嵩阳县"
        and "嵩阳县" in derived_names
        and resolved["map_link"]["admin"] == "河南诸郡"
        and resolved["map_link"]["period"] == "隋"
    ):
        print("✓ 可从现代/后世地名沿革反查目标年份历史地名，并验证过渡期前朝地图")
    else:
        print(f"✗ 现代地点反查历史区划失败: {resolved}")
        ok = False

    explicit = resolve_place_admin(
        "少林寺",
        625,
        dynasty="唐",
        modern_hint="测试省测试市测试县",
        candidates=["嵩阳县"],
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    if explicit["status"] == "resolved" and explicit["map_link"]["admin"] == "河南诸郡":
        print("✓ 手工给出的来源候选历史地名也可闭环验证")
    else:
        print(f"✗ 来源候选验证失败: {explicit}")
        ok = False

    ming = resolve_place_admin(
        "济南府",
        1582,
        dynasty="明",
        modern_hint="测试县",
        lookup_names=["历城"],
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    ming_derived = {item["name"] for item in ming.get("derived_candidates", [])}
    if (
        ming["status"] == "resolved"
        and ming["historical_place"]["name"] == "济南府"
        and "济南府" in ming_derived
        and ming["map_link"]["admin"] == "山东布政司"
        and ming["map_link"]["period"] == "明"
    ):
        print("✓ 非隋唐沿革也可反查历史地名，并按同代一级区划验证地图")
    else:
        print(f"✗ 非隋唐反查失败: {ming}")
        ok = False

    missing_candidates = resolve_place_admin(
        "少林寺",
        625,
        dynasty="唐",
        modern_hint="测试县",
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    if missing_candidates["status"] == "needs_candidates":
        print("✓ 缺少来源候选时不会从现代地名凭空猜历史地名")
    else:
        print(f"✗ 缺少候选未 fail-closed: {missing_candidates}")
        ok = False

    mismatch = resolve_place_admin(
        "少林寺",
        625,
        dynasty="唐",
        modern_hint="不存在地",
        candidates=["嵩阳县"],
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    if mismatch["status"] == "not_found":
        print("✓ 现代地点线索不匹配时拒绝继续推导地图")
    else:
        print(f"✗ 现代地点不匹配仍继续推导: {mismatch}")
        ok = False

    return ok


def test_source_book_index() -> bool:
    """Test source book index parsing and lookup offline."""
    print("\n测试11: 识典/cnkgraph 书目索引...")
    from tempfile import TemporaryDirectory

    from source_book_index import find_shidian_book_by_url, load_source_book_index, lookup_title_entries, lookup_title_variants
    from update_source_book_index import build_crosswalk, normalize_cnkgraph_book, normalize_existing_sources, parse_shidian_sitemap, write_index

    fixture_html = """
    <html><body>
      <a href="/sitemap-book-1">1</a>
      <a href="https://security.zijieapi.com/api/link?targetUrl=https%3A%2F%2Fwww.shidianguji.com%2Fzh%2Fbook%2FNA0001">
        毛詩 全文原文及譯文
      </a>
      <a href="/ens/book/QDTW0001">
        全唐文（欽定全唐文）全文原文
      </a>
      <a href="https://security.zijieapi.com/api/link?targetUrl=https%3A%2F%2Fevil.example%2Fbook%2Fbad">
        不应保存
      </a>
    </body></html>
    """
    ok = True
    parsed = parse_shidian_sitemap(fixture_html, sitemap_path="/sitemap-book")
    if parsed["sitemap_paths"] == ["/sitemap-book-1"] and len(parsed["books"]) == 2:
        book = next((item for item in parsed["books"] if item["title"] == "毛詩"), None)
        qdtw_book = next((item for item in parsed["books"] if item["title"] == "全唐文（欽定全唐文）"), None)
        if (
            book
            and qdtw_book
            and book["url"] == "https://www.shidianguji.com/book/NA0001"
            and qdtw_book["url"] == "https://www.shidianguji.com/book/QDTW0001"
        ):
            print("✓ 识典 sitemap 安全跳转可还原为官方书页")
        else:
            print(f"✗ 识典书页解析字段错误: books={parsed['books']}")
            ok = False
    else:
        print(f"✗ 识典 sitemap 解析失败: {parsed}")
        ok = False

    cnkgraph_book = normalize_cnkgraph_book(
        {"Id": 7337, "Name": "毛诗", "Author": "毛亨传", "Dynasty": "汉"},
        "经部",
        "诗类",
    )
    if cnkgraph_book["api_url"] == "https://open.cnkgraph.com/api/Book/7337" and cnkgraph_book["title"] == "毛诗":
        print("✓ cnkgraph 分组书目归一化为可验证 API 链接")
    else:
        print(f"✗ cnkgraph 书目归一化失败: {cnkgraph_book}")
        ok = False

    sources = normalize_existing_sources(
        {
            "shidian": {"books": parsed["books"]},
            "cnkgraph": {"books": [cnkgraph_book]},
        }
    )
    crosswalk = build_crosswalk(sources)
    sample_index = {
        "crosswalk": crosswalk,
        "sources": {
            "shidian": sources["shidian"],
            "cnkgraph": sources["cnkgraph"],
        }
    }
    found = find_shidian_book_by_url("https://www.shidianguji.com/zh/book/NA0001/chapter/abc", index=sample_index)
    ens_found = find_shidian_book_by_url("https://www.shidianguji.com/ens/book/NA0001/chapter/abc", index=sample_index)
    if found and ens_found and found["title"] == "毛詩" and ens_found["title"] == "毛詩":
        print("✓ 可从识典章节 URL 反查本地书目索引")
    else:
        print(f"✗ 章节 URL 反查书目失败: found={found}, ens_found={ens_found}")
        ok = False

    crosswalk_entries = crosswalk["entries"]
    if (
        crosswalk["entry_count"] == 1
        and crosswalk_entries[0]["normalized_title"] == "毛诗"
        and crosswalk_entries[0]["shidian"][0]["url"] == "https://www.shidianguji.com/book/NA0001"
        and crosswalk_entries[0]["cnkgraph"][0]["api_url"] == "https://open.cnkgraph.com/api/Book/7337"
    ):
        print("✓ crosswalk 可显式关联识典书页和 cnkgraph 书目")
    else:
        print(f"✗ crosswalk 生成失败: {crosswalk}")
        ok = False

    variants = lookup_title_variants("毛诗", index=sample_index)
    entries = lookup_title_entries("毛诗", index=sample_index)
    if "毛诗" in variants and entries and {entry.get("title") for entry in entries} == {"毛詩", "毛诗"}:
        print("✓ 书名优先通过 crosswalk 查到两边来源链接")
    else:
        print(f"✗ 本地书名索引查找失败: variants={variants}, entries={entries}")
        ok = False

    qdtw_entries = lookup_title_entries("钦定全唐文", index=sample_index, sources=("shidian",))
    if qdtw_entries and qdtw_entries[0]["title"] == "全唐文（欽定全唐文）":
        print("✓ 较长别名可匹配识典括注题名")
    else:
        print(f"✗ 识典括注题名匹配失败: {qdtw_entries}")
        ok = False

    with TemporaryDirectory() as tmpdir:
        sqlite_path = Path(tmpdir) / "source_book_index.sqlite"
        write_index(
            {"schema_version": 1, "generated_at": "fixture", "sources": sources, "crosswalk": crosswalk},
            sqlite_path,
            pretty=False,
        )
        sqlite_index = load_source_book_index(sqlite_path)
        sqlite_entries = lookup_title_entries("毛诗", index=sqlite_index)
        sqlite_qdtw_entries = lookup_title_entries("钦定全唐文", index=sqlite_index, sources=("shidian",))
        sqlite_found = find_shidian_book_by_url(
            "https://www.shidianguji.com/zh/book/NA0001/chapter/abc",
            index=sqlite_index,
        )
        sqlite_ens_found = find_shidian_book_by_url(
            "https://www.shidianguji.com/ens/book/NA0001/chapter/abc",
            index=sqlite_index,
        )
        if (
            sqlite_found
            and sqlite_ens_found
            and sqlite_found["url"] == "https://www.shidianguji.com/book/NA0001"
            and sqlite_ens_found["url"] == "https://www.shidianguji.com/book/NA0001"
            and sqlite_entries
            and sqlite_qdtw_entries
            and sqlite_qdtw_entries[0]["url"] == "https://www.shidianguji.com/book/QDTW0001"
        ):
            print("✓ SQLite 书目索引可点查书名与识典章节 URL")
        else:
            print(
                f"✗ SQLite 书目索引查询失败: found={sqlite_found}, "
                f"ens_found={sqlite_ens_found}, entries={sqlite_entries}, qdtw_entries={sqlite_qdtw_entries}"
            )
            ok = False

    return ok


def test_shidian_link() -> bool:
    """Test Shidian Guji result parsing and verification offline."""
    print("\n测试12: 识典古籍原文链接验证...")
    from shidian_link import ShidianLinkError, find_shidian_link, source_lookup_titles

    fixture_html = """
    <html><body>
      <a href="/zh/book/WEI001/chapter/cuihao">
        崔浩字伯渊清河人也 白马公玄伯之长子 《魏书》 卷三五 崔浩传
      </a>
      <a href="/zh/book/SONG001/chapter/other">
        王安石临川人 《宋史》 卷三二七 王安石传
      </a>
    </body></html>
    """
    ok = True

    qdtw_titles = source_lookup_titles("钦定全唐文")
    if "全唐文" in qdtw_titles:
        print("✓ 识典链接脚本知道《钦定全唐文》与《全唐文》可互查")
    else:
        print(f"✗ 全唐文异名未进入链接脚本查找集合: {qdtw_titles}")
        ok = False

    resolved = find_shidian_link(
        "崔浩字伯渊清河人也",
        "《魏书》卷三五《崔浩传》",
        keyword="崔浩",
        html=fixture_html,
    )
    if resolved["status"] == "resolved" and resolved["url"] == "https://www.shidianguji.com/zh/book/WEI001/chapter/cuihao":
        print("✓ HTML fixture 中的引文/出处匹配到精确章节链接")
    else:
        print(f"✗ 识典精确链接匹配失败: {resolved}")
        ok = False

    not_found = find_shidian_link(
        "魏主大怒诏浩诛之",
        "《魏书》卷三五《崔浩传》",
        keyword="崔浩",
        html=fixture_html,
    )
    if not_found["status"] == "not_found" and not_found["url"] is None and not_found["search_url"].endswith("/%E5%B4%94%E6%B5%A9"):
        print("✓ 未验证时只给检索页 fallback，不标为原文链接")
    else:
        print(f"✗ 识典未验证 fallback 失败: {not_found}")
        ok = False

    indirect_quote_html = """
    <html><body>
      <a href="/zh/book/ZHENGYANG/chapter/fanli">
        史货殖传：范蠡既雪会稽之耻，乃乘扁舟浮于江湖。 《正杨》 正杨卷二
      </a>
    </body></html>
    """
    indirect = find_shidian_link(
        "乃乘扁舟浮于江湖",
        "《史记》卷一百二十九《货殖列传》",
        keyword="浮于江湖",
        html=indirect_quote_html,
    )
    if indirect["status"] == "not_found" and indirect["url"] is None:
        print("✓ 后代类书转引不会冒充原书识典链接")
    else:
        print(f"✗ 转引误判为原文链接: {indirect}")
        ok = False

    direct_shiji_html = """
    <html><body>
      <a href="/zh/book/SHIJI/chapter/huozhi">
        乃乘扁舟，浮於江湖，變名易姓，適齊，爲鴟夷子皮。 《史記》 史記一百二十九
      </a>
    </body></html>
    """
    shiji = find_shidian_link(
        "乃乘扁舟浮于江湖变名易姓",
        "《史记》卷一百二十九《货殖列传》",
        keyword="乘扁舟浮于江湖",
        html=direct_shiji_html,
    )
    if shiji["status"] == "resolved" and shiji["url"] == "https://www.shidianguji.com/zh/book/SHIJI/chapter/huozhi":
        print("✓ 原书名匹配时可验证正史章节链接")
    else:
        print(f"✗ 正史原书章节链接匹配失败: {shiji}")
        ok = False

    class FakeResponse:
        def __init__(self, text: str, status_code: int = 200) -> None:
            self.text = text
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(str(self.status_code))

    def fake_direct_get(url: str, **_: object) -> FakeResponse:
        if url.endswith("/book/LS0016/chapter/LS0016_1"):
            return FakeResponse("五月己未秦王大破窦建德之众于武牢擒建德河北悉平")
        return FakeResponse("", 404)

    direct_jiutangshu = find_shidian_link(
        "秦王大破窦建德之众于武牢擒建德河北悉平",
        "《旧唐书》卷一《高祖本纪》",
        keyword="大破窦建德",
        http_get=fake_direct_get,
    )
    if direct_jiutangshu["status"] == "resolved" and direct_jiutangshu["url"].endswith("/LS0016_1"):
        print("✓ 可用本地书目索引直接校验识典原书章节")
    else:
        print(f"✗ 识典原书章节直接校验失败: {direct_jiutangshu}")
        ok = False

    try:
        find_shidian_link("短引", "《魏书》卷三五《崔浩传》", keyword="x" * 65, html=fixture_html)
    except ShidianLinkError:
        print("✓ 过长关键词会被拒绝")
    else:
        print("✗ 过长关键词未被拒绝")
        ok = False

    return ok


def main() -> int:
    os.chdir(ROOT)
    print("=" * 60)
    print("中国历史专家系统 - 系统测试")
    print("=" * 60)

    tests = [
        ("依赖", test_imports),
        ("文件完整性", test_files),
        ("工作流强制门禁", test_workflow_guardrails),
        ("跨平台安装", test_cross_platform_installation),
        ("脚本语法", test_scripts_compile),
        ("年号换算", test_dynasty_converter),
        ("EPUB检索", test_epub_search),
        ("古地名映射", test_place_resolver),
        ("左图右史链接", test_history_map_link),
        ("现代地点反查历史区划", test_place_admin_resolver),
        ("书目索引", test_source_book_index),
        ("识典链接", test_shidian_link),
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
