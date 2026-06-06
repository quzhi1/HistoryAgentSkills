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
        import cnmaps_data  # noqa: F401
        print("✓ cnmaps-data 已安装")
    except ImportError:
        print("✗ cnmaps-data 未安装，请运行: ./setup_venv.sh")
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
        "scripts/dynasty_converter.py",
        "scripts/book_search.py",
        "scripts/place_resolver.py",
        "scripts/history_map_link.py",
        "scripts/shidian_link.py",
        "scripts/update_history_map_index.py",
        "data/history_map_index.json",
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


def test_scripts_compile() -> bool:
    """Check Python scripts compile."""
    print("\n测试3: 检查脚本语法...")
    scripts = [
        "dict/scripts/query_dict.py",
        "cnkgraph/scripts/query_api.py",
        "scripts/history_query.py",
        "scripts/dynasty_converter.py",
        "scripts/book_search.py",
        "scripts/place_resolver.py",
        "scripts/history_map_link.py",
        "scripts/shidian_link.py",
        "scripts/update_history_map_index.py",
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
    print("\n测试4: 年号换算...")
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
    print("\n测试5: EPUB 全文检索...")
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
):
    payload = {
        "sys_id": sys_id,
        "spellings": [{"simplified Chinese": name}, {"transcribed in Pinyin": f"{name} Pinyin"}],
        "feature_type": {"name": "县", "English": "county"},
        "temporal": {"begin year": str(begin), "end year": str(end)},
        "historical_context": {"part of": [{"name": "测试州"}]},
        "data source": "CHGIS",
    }
    if lon is not None and lat is not None:
        payload["spatial"] = {"longitude": str(lon), "latitude": str(lat)}
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
    print("\n测试6: 古地名现代行政区划映射...")
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
    print("\n测试7: 左图右史同代一级区划链接...")
    from history_map_link import resolve_history_map_link

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


def test_shidian_link() -> bool:
    """Test Shidian Guji result parsing and verification offline."""
    print("\n测试8: 识典古籍原文链接验证...")
    from shidian_link import ShidianLinkError, find_shidian_link

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
        ("脚本语法", test_scripts_compile),
        ("年号换算", test_dynasty_converter),
        ("EPUB检索", test_epub_search),
        ("古地名映射", test_place_resolver),
        ("左图右史链接", test_history_map_link),
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
