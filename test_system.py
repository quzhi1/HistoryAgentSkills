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
        "scripts/random_anecdote_seed.py",
        "scripts/update_history_map_index.py",
        "scripts/run_in_venv.py",
        "scripts/venv_utils.py",
        "data/history_map_index.json",
        "setup_venv.py",
        "SKILL.md",
        "random-history-anecdote/SKILL.md",
        "AGENTS.md",
        "CLAUDE.md",
        "install_codex.py",
        "setup_venv.sh",
        "setup_venv.ps1",
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
        "scripts/source_book_index.py",
        "scripts/update_source_book_index.py",
        "data/dynasty",
        "data/source_book_index.sqlite",
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
            "译文只翻译原文",
            "每个评价或比较结论",
            "朝代/时期总图",
            "--period-overview",
            "多人物/列表型答案",
            "不传 `--admin`",
            "needs_admin",
            "静默省略",
            "地点与地图核验",
            "place_admin_resolver.py",
            "反查历史地名",
            "--allow-overview",
            "overview",
            "admin_substitute",
            "合并/分置期",
            "时代总图",
            "识典检索链接交付",
            "识典检索 URL",
            "正文出处行已附 [识典检索](url)：是",
            "正文首次出现或“地点与地图核验”已交付",
            "清单 C：被引史料说明",
            'venv/bin/mdict -q "史料书名"',
            "每部被引用史料",
        ],
        "README.md": [
            "译文只翻译原文",
            "每个评价或比较结论",
            "朝代/时期总图",
            "--period-overview",
            "多人物/列表型回答",
            "不传 `--admin`",
            "needs_admin",
            "静默省略",
            "逐条交付",
            "识典检索链接",
            "不要手写或猜测识典书页链接",
            "不附左图右史链接",
            "place_admin_resolver.py",
            "反查历史地名",
            "--allow-overview",
            "overview",
            "admin_substitute",
            "合并/分置期",
            "时代总图",
            "必说明被引史料",
            "每部被引用史料都要有简介",
            "单一真理源",
            "install_codex.py",
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
            "译文里混入分析",
            "无证据比较结论",
            "朝代/时期总图",
            "错误示例7",
            "错误示例8",
            "脚本跑了",
            "逐条交付结果",
            "history_map_link.py",
            "不传 --admin",
            "needs_admin",
            "错误示例10",
            "反查历史地名",
            "overview",
            "admin_substitute",
            "合并/分置期",
            "时代总图",
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
        "random-history-anecdote/SKILL.md": [
            "随机历史小段子",
            "不输出识典",
            "不输出左图右史",
            "输出原文、译文和出处",
            "不另写“好玩处”",
            "不使用固定段子池",
            "scripts/random_anecdote_seed.py",
            "scripts/dynasty_converter.py",
            "scripts/place_resolver.py",
            "译文只翻译原文",
            "查不到可靠原文",
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
        "setup_venv.py",
        "install_codex.py",
        "setup_venv.ps1",
        "random-history-anecdote/SKILL.md",
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

    # 全局安装是符号链接（见 README「全局注册到 Claude Code」），被链接的文件
    # 必须自己能解析项目根目录，不能假设 cwd 已在项目内。
    resolver = 'realpath ~/.claude/skills/chinese-history-expert'
    for filename in (".claude/commands/history.md", ".claude/agents/history-fact-checker.md"):
        if resolver not in (ROOT / filename).read_text(encoding="utf-8"):
            print(f"✗ {filename} 缺少符号链接安装时的项目根目录解析步骤")
            ok = False
    anecdote_text = (ROOT / "random-history-anecdote" / "SKILL.md").read_text(encoding="utf-8")
    if "realpath ~/.claude/skills/random-history-anecdote" not in anecdote_text:
        print("✗ random-history-anecdote/SKILL.md 缺少符号链接安装时的项目根目录解析步骤")
        ok = False
    if ok:
        print("✓ 符号链接全局安装的入口文件都会自行解析项目根目录")

    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmpdir:
        from install_codex import install_codex

        outputs = install_codex(project_root=ROOT, agents_dir=Path(tmpdir))
        skill_text = outputs["skill"].read_text(encoding="utf-8")
        anecdote_skill_text = outputs["anecdote_skill"].read_text(encoding="utf-8")
        if (
            str(ROOT / "AGENTS.md") in skill_text
            and str(ROOT / "random-history-anecdote" / "SKILL.md") in anecdote_skill_text
            and "__PROJECT_ROOT__" not in skill_text
        ):
            print("✓ Codex 全局安装会按当前项目目录生成 skill/anecdote skill")
        else:
            print("✗ Codex 全局安装生成物缺少当前项目目录")
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
        "scripts/random_anecdote_seed.py",
        "scripts/update_history_map_index.py",
        "scripts/run_in_venv.py",
        "scripts/venv_utils.py",
        "setup_venv.py",
        "install_codex.py",
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


def test_random_anecdote_seed() -> bool:
    """Check random anecdote discovery helpers without network access."""
    print("\n测试6: 随机历史段子发现...")
    from random_anecdote_seed import extract_candidates, random_probe, result_page_count, score_candidate

    ok = True

    result = subprocess.run(
        [str(venv_executable(ROOT, "python")), "scripts/random_anecdote_seed.py", "--sample-probe", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode == 0:
        payload = json.loads(result.stdout)
        if payload.get("status") == "ok" and payload.get("strategy") == "sample_probe_only" and payload.get("keyword"):
            print("✓ 可离线生成随机全库检索探针")
        else:
            print(f"✗ 随机探针输出结构不符合预期: {payload}")
            ok = False
    else:
        print(f"✗ 随机探针脚本失败: {result.stderr or result.stdout}")
        ok = False

    probe = random_probe()
    if isinstance(probe, str) and 1 <= len(probe) <= 6:
        print("✓ 随机探针来自运行时生成，不依赖段子清单")
    else:
        print(f"✗ 随机探针不符合预期: {probe!r}")
        ok = False

    fixture = {
        "Count": 250,
        "PageSize": 100,
        "Result": [
            {
                "Books": [
                    {
                        "Book": "世说新语-刘宋-刘义庆",
                        "BookId": "KR3l0002",
                        "Volumes": [
                            {
                                "Volume": "卷六",
                                "VolumeId": "KR3l0002_006",
                                "Pages": [
                                    {
                                        "Page": "6-43a",
                                        "PreviousText": "王蓝田性急，尝食鸡子，",
                                        "MatchedText": "以箸刺之",
                                        "LaterText": "不得，便大怒，举以掷地。",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ],
    }
    if result_page_count(fixture) == 3:
        print("✓ 会按 Count/PageSize 计算随机跳页范围")
    else:
        print("✗ 随机跳页范围计算错误")
        ok = False

    candidates = extract_candidates(fixture, "以")
    if candidates and candidates[0].book.startswith("世说新语") and "王蓝田性急" in candidates[0].text:
        print("✓ 能从 cnkgraph 结构中提取叙事候选")
    else:
        print(f"✗ 叙事候选提取失败: {candidates}")
        ok = False

    long_story = (
        "王公与客坐，客问曰：今日何以处事。公笑曰：事急则缓，言多则乱。"
        "俄而吏持牍至，众皆失色，公乃顾左右曰：先饭后判。客问其故，"
        "公曰：饥者易怒，怒者易误。遂命取案，逐条问答，吏不能欺。"
    ) * 4
    long_score = score_candidate("世说新语-刘宋-刘义庆", "卷一", long_story, "KR3l0002")
    if 300 < len(long_story) < 1000 and long_score >= 8:
        print("✓ 数百字叙事候选不会被旧的 180 字限制误伤")
    else:
        print(f"✗ 数百字叙事候选评分过低: length={len(long_story)}, score={long_score}")
        ok = False

    return ok


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
    print("\n测试7: 年号换算...")
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
    print("\n测试8: EPUB 全文检索...")
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
            "黄州": [
                _tgaz_payload(
                    "hvd_13",
                    "黄州",
                    758,
                    1276,
                    20,
                    20,
                    present_location="今别处",
                    source_note="唐乾元元年改齐安郡置，属淮南道。",
                ),
                _tgaz_payload(
                    "hvd_14",
                    "黄州",
                    885,
                    1276,
                    2,
                    2,
                    present_location="今测试县",
                    source_note=(
                        "北宋太平兴国元年(976年)属淮南西路。至道三年(997年)属淮南路。"
                        "熙宁五年(1072年)属淮南西路。元丰元年(1078年)属淮南路，"
                        "八年(1085年)属淮南西路。治今测试县。"
                    ),
                ),
            ],
            "州治": [
                _tgaz_payload(
                    "hvd_15",
                    "州治",
                    700,
                    800,
                    2,
                    2,
                    parent="测试州",
                    present_location="今测试县",
                    source_note="唐属测试州，治今测试县。",
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
    print("\n测试9: 古地名现代行政区划映射...")
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
    print("\n测试10: 左图右史同代一级区划链接...")
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

    huainan = resolve_history_map_link("黄州", 1080, "淮南路", dynasty="宋")
    if (
        huainan["status"] == "resolved"
        and huainan["coverage"] == "admin_substitute"
        and huainan["matched_admin"] == "淮南东路"
        and huainan["url"].endswith("sec=sec08_huainan-dong")
    ):
        print("✓ 宋代淮南路合并期可显式匹配左图右史淮南东路专题页")
    else:
        print(f"✗ 淮南路合并期专题页匹配失败: {huainan}")
        ok = False

    huainan_west = resolve_history_map_link("黄州", 1080, "淮南西路", dynasty="宋")
    if huainan_west["status"] == "not_found":
        print("✓ 淮南西路不会因共享词干误匹配到淮南东路")
    else:
        print(f"✗ 淮南西路误匹配地图: {huainan_west}")
        ok = False

    guangnan_west = resolve_history_map_link("桂州", 1080, "广南西路", dynasty="宋", allow_overview=True)
    if (
        guangnan_west["status"] == "overview"
        and guangnan_west["coverage"] == "period_overview"
        and guangnan_west["url"].endswith("sec=sec01_bei-song")
    ):
        print("✓ 已核实 admin 但缺专题图时仍可回退到同代时代总图")
    else:
        print(f"✗ 总图 fallback 失败: {guangnan_west}")
        ok = False

    tang_overview = resolve_history_map_link("唐朝", 750, None, dynasty="唐", period_overview=True)
    if (
        tang_overview["status"] == "overview"
        and tang_overview["coverage"] == "period_overview"
        and tang_overview["url"].endswith("sec=sec02_tang741")
    ):
        print("✓ 朝代/时期整体问题可显式返回左图右史总图")
    else:
        print(f"✗ 朝代/时期总图失败: {tang_overview}")
        ok = False

    return ok


def test_place_admin_resolver() -> bool:
    """Test reverse modern-location to historical admin resolution offline."""
    print("\n测试11: 现代地点线索反查历史地名与地图区划...")
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

    huangzhou = resolve_place_admin(
        "黄州",
        1080,
        dynasty="宋",
        modern_hint="测试县",
        candidates=["黄州"],
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    huangzhou_admins = {item["admin"]: item.get("map_status") for item in huangzhou.get("admin_candidates", [])}
    if (
        huangzhou["status"] == "resolved"
        and huangzhou["historical_place"]["name"] == "黄州"
        and huangzhou.get("modern_match", {}).get("district") == "测试县"
        and huangzhou.get("admin_candidates", [{}])[0].get("admin") == "淮南路"
        and "淮南路" in huangzhou_admins
        and huangzhou_admins["淮南路"] == "resolved"
        and huangzhou["map_link"]["coverage"] == "admin_substitute"
        and huangzhou["map_link"]["url"].endswith("sec=sec08_huainan-dong")
    ):
        print("✓ TGAZ 同名歧义候选可用现代线索筛出，并验证淮南路合并期专题页")
    else:
        print(f"✗ 黄州歧义候选反查处理失败: {huangzhou}")
        ok = False

    local_prefecture = resolve_place_admin(
        "州治",
        750,
        dynasty="唐",
        modern_hint="测试县",
        candidates=["州治"],
        tgaz_client=client,
        boundary_resolver=boundary_resolver,
    )
    local_statuses = {item["admin"]: item.get("map_status") for item in local_prefecture.get("admin_candidates", [])}
    if local_prefecture["status"] == "needs_admin" and local_statuses.get("测试州") == "not_found":
        print("✓ 自动反查不会把州级候选回退成同代总图")
    else:
        print(f"✗ 州级候选不应触发总图 fallback: {local_prefecture}")
        ok = False

    return ok


def test_shidian_link() -> bool:
    """Test Shidian Guji search URL generation offline."""
    print("\n测试12: 识典古籍检索链接生成...")
    from shidian_link import build_search_url

    ok = True

    simple_url = build_search_url("崔浩")
    if simple_url == "https://www.shidianguji.com/search/%E5%B4%94%E6%B5%A9":
        print("✓ 识典检索 URL 会按关键词编码")
    else:
        print(f"✗ 识典关键词编码失败: {simple_url}")
        ok = False

    quote_result = subprocess.run(
        [
            str(venv_executable(ROOT, "python")),
            "scripts/shidian_link.py",
            "--source",
            "《魏书》卷三五《崔浩传》",
            "--quote",
            "崔浩字伯渊清河人也",
            "--keyword",
            "崔浩字伯渊清河人也",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if quote_result.returncode == 0:
        payload = json.loads(quote_result.stdout)
        if (
            payload["status"] == "search"
            and payload["search_term"] == "崔浩字伯渊清河人也"
            and payload["url"] == build_search_url("崔浩字伯渊清河人也")
        ):
            print("✓ CLI JSON 输出交付 search 状态、检索词和 URL")
        else:
            print(f"✗ CLI JSON 输出字段错误: {payload}")
            ok = False
    else:
        print(f"✗ 识典 CLI 调用失败: {quote_result.stderr}")
        ok = False

    fallback_result = subprocess.run(
        [
            str(venv_executable(ROOT, "python")),
            "scripts/shidian_link.py",
            "--source",
            "《魏书》卷三五《崔浩传》",
            "--quote",
            "崔浩字伯渊清河人也",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if fallback_result.returncode == 0:
        payload = json.loads(fallback_result.stdout)
        if payload["search_term"] == "崔浩字伯渊清河人也":
            print("✓ 未传 keyword 时回退使用 quote")
        else:
            print(f"✗ quote fallback 错误: {payload}")
            ok = False
    else:
        print(f"✗ quote fallback 调用失败: {fallback_result.stderr}")
        ok = False

    error_result = subprocess.run(
        [str(venv_executable(ROOT, "python")), "scripts/shidian_link.py", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if error_result.returncode != 0:
        payload = json.loads(error_result.stdout)
        if payload["status"] == "error" and payload["reason"] == "no search term provided":
            print("✓ 无 source/quote/keyword 时 fail closed")
        else:
            print(f"✗ 无检索词错误输出不符合预期: {payload}")
            ok = False
    else:
        print("✗ 无检索词时没有失败")
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
        ("随机历史段子候选", test_random_anecdote_seed),
        ("年号换算", test_dynasty_converter),
        ("EPUB检索", test_epub_search),
        ("古地名映射", test_place_resolver),
        ("左图右史链接", test_history_map_link),
        ("现代地点反查历史区划", test_place_admin_resolver),
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
