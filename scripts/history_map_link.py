#!/usr/bin/env python3
"""Resolve same-period first-level history-map links for historical places."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = ROOT / "data" / "history_map_index.json"
BASE_URL = "https://history-map.osgeo.cn"
MIN_YEAR = -3000
MAX_YEAR = 1911
MAX_ADMIN_LENGTH = 64
MAX_PLACE_LENGTH = 64
ADMIN_PATTERN = re.compile(r"^[\w\s\-\u4e00-\u9fff·'’().（）/、]+$", re.UNICODE)
STATUS_RESOLVED = "resolved"
STATUS_NEEDS_ADMIN = "needs_admin"
STATUS_NOT_FOUND = "not_found"
STATUS_PERIOD_MISMATCH = "period_mismatch"
STATUS_OUT_OF_RANGE = "out_of_range"
STATUS_INVALID = "invalid"


class HistoryMapLinkError(ValueError):
    """Raised when map-link inputs or index data are invalid."""


# Page ranges are intentionally broad enough for period gating. The actual map
# link still requires a matching first-level historical administration label.
PAGE_RANGES: Mapping[str, Tuple[int, int]] = {
    "page02": (-2070, -1600),
    "page03": (-1600, -1046),
    "page04": (-1046, -771),
    "page05": (-770, -476),
    "page06": (-475, -221),
    "page07": (-221, -206),
    "page08": (-206, 8),
    "page09": (25, 220),
    "page10": (220, 280),
    "page11": (265, 316),
    "page12": (317, 420),
    "page13": (420, 589),
    "page14": (581, 618),
    "page15": (618, 907),
    "page16": (907, 960),
    "page17": (960, 1127),
    "page18": (1127, 1279),
    "page19": (1271, 1368),
    "page20": (1368, 1644),
    "page21": (1644, 1911),
}

DYNASTY_PAGES: Mapping[str, Sequence[str]] = {
    "夏": ("page02",),
    "商": ("page03",),
    "殷": ("page03",),
    "西周": ("page04",),
    "周": ("page04",),
    "春秋": ("page05",),
    "战国": ("page06",),
    "秦": ("page07",),
    "西汉": ("page08",),
    "前汉": ("page08",),
    "汉": ("page08", "page09"),
    "东汉": ("page09",),
    "后汉": ("page09", "page16"),
    "三国": ("page10",),
    "曹魏": ("page10",),
    "蜀汉": ("page10",),
    "孙吴": ("page10",),
    "西晋": ("page11",),
    "东晋": ("page12",),
    "十六国": ("page12",),
    "南北朝": ("page13",),
    "南朝": ("page13",),
    "北朝": ("page13",),
    "北魏": ("page13",),
    "东魏": ("page13",),
    "西魏": ("page13",),
    "北齐": ("page13",),
    "北周": ("page13",),
    "隋": ("page14",),
    "唐": ("page15",),
    "五代": ("page16",),
    "后梁": ("page16",),
    "后唐": ("page16",),
    "后晋": ("page16",),
    "后周": ("page16",),
    "吴越": ("page16",),
    "南唐": ("page16",),
    "北宋": ("page17",),
    "辽": ("page17",),
    "南宋": ("page18",),
    "金": ("page18",),
    "元": ("page19",),
    "明": ("page20",),
    "清": ("page21",),
}

ADMIN_SUFFIXES = (
    "承宣布政使司",
    "布政使司",
    "布政司",
    "行中书省",
    "中书省",
    "行省",
    "刺史部",
    "都司",
    "宣慰司",
    "省",
    "道",
    "路",
    "府",
)


def resolve_history_map_link(
    place: str,
    year: int,
    admin: Optional[str],
    dynasty: Optional[str] = None,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> Dict[str, Any]:
    """Return a verified left-map/right-history route for one historical admin."""

    checked_place = validate_text(place, "地名", MAX_PLACE_LENGTH)
    checked_year = validate_year(year)
    checked_dynasty = validate_optional_text(dynasty, "朝代", MAX_ADMIN_LENGTH)
    result: Dict[str, Any] = {
        "query": {
            "place": checked_place,
            "year": checked_year,
            "dynasty": checked_dynasty,
            "admin": admin.strip() if admin else None,
        },
        "status": STATUS_NOT_FOUND,
        "url": None,
        "map_label": None,
        "period": None,
        "admin": admin.strip() if admin else None,
        "reason": "",
    }

    if checked_year is None:
        result["status"] = STATUS_OUT_OF_RANGE
        result["reason"] = f"左图右史索引只用于 {MIN_YEAR} 至 {MAX_YEAR} 年范围内的中国历史地图"
        return result
    if not admin or not admin.strip():
        result["status"] = STATUS_NEEDS_ADMIN
        result["reason"] = "必须先根据辞典/原文确认同时代一级行政区，不能用现代省份反推"
        return result

    checked_admin = validate_text(admin, "一级行政区", MAX_ADMIN_LENGTH)
    result["query"]["admin"] = checked_admin
    result["admin"] = checked_admin

    index = load_index(index_path)
    entries = list(index.get("entries") or [])
    year_pages = set(pages_for_year(checked_year))
    dynasty_pages = set(pages_for_dynasty(checked_dynasty)) if checked_dynasty else set()
    allowed_pages = year_pages
    if dynasty_pages:
        overlap = year_pages & dynasty_pages
        if not overlap:
            result["status"] = STATUS_PERIOD_MISMATCH
            result["reason"] = "公元年份与朝代提示无法落在同一左图右史时代页"
            return result
        allowed_pages = overlap

    if not allowed_pages:
        result["status"] = STATUS_NOT_FOUND
        result["reason"] = "没有与该年份对应的左图右史时代页"
        return result

    aliases = admin_aliases(checked_admin)
    scored: List[Tuple[int, Mapping[str, Any]]] = []
    for entry in entries:
        if entry.get("page") not in allowed_pages:
            continue
        score = score_entry(entry, aliases)
        if score > 0:
            scored.append((score, entry))

    if not scored:
        result["status"] = STATUS_NOT_FOUND
        result["reason"] = "未找到同一时代且一级行政区标签相符的地图"
        return result

    scored.sort(key=lambda item: (item[0], -len(str(item[1].get("label") or ""))), reverse=True)
    best_score, best = scored[0]
    if best_score < 70:
        result["status"] = STATUS_NOT_FOUND
        result["reason"] = "候选地图与一级行政区匹配度不足，已按 fail-closed 处理"
        return result

    result["status"] = STATUS_RESOLVED
    result["url"] = str(best.get("url") or "")
    result["map_label"] = str(best.get("label") or "")
    result["period"] = str(best.get("period") or "")
    result["reason"] = "已匹配同一时代且一级行政区标签相符的左图右史页面"
    return result


def validate_text(value: str, label: str, max_length: int) -> str:
    text = value.strip()
    if not text:
        raise HistoryMapLinkError(f"{label}不能为空")
    if len(text) > max_length:
        raise HistoryMapLinkError(f"{label}长度不能超过 {max_length} 字符")
    if not ADMIN_PATTERN.fullmatch(text):
        raise HistoryMapLinkError(f"{label}包含不允许的字符")
    return text


def validate_optional_text(value: Optional[str], label: str, max_length: int) -> Optional[str]:
    if value is None:
        return None
    return validate_text(value, label, max_length)


def validate_year(value: int) -> Optional[int]:
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise HistoryMapLinkError("年份必须是整数") from None
    if MIN_YEAR <= year <= MAX_YEAR:
        return year
    return None


def load_index(path: Path = DEFAULT_INDEX_PATH) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise HistoryMapLinkError(f"无法读取左图右史索引: {path}") from exc
    except ValueError as exc:
        raise HistoryMapLinkError("左图右史索引不是有效 JSON") from exc
    if not isinstance(data, Mapping) or not isinstance(data.get("entries"), list):
        raise HistoryMapLinkError("左图右史索引缺少 entries")
    return data


def pages_for_year(year: int) -> List[str]:
    pages: List[str] = []
    for page, (begin, end) in PAGE_RANGES.items():
        if begin <= year <= end:
            pages.append(page)
    return pages


def pages_for_dynasty(dynasty: Optional[str]) -> List[str]:
    if not dynasty:
        return []
    normalized = normalize_text(dynasty)
    pages: List[str] = []
    for key, value in DYNASTY_PAGES.items():
        if normalize_text(key) in normalized or normalized in normalize_text(key):
            pages.extend(value)
    return list(dict.fromkeys(pages))


def admin_aliases(admin: str) -> List[str]:
    normalized = normalize_text(admin)
    aliases = {normalized}
    changed = True
    while changed:
        changed = False
        for suffix in ADMIN_SUFFIXES:
            suffix_norm = normalize_text(suffix)
            for alias in list(aliases):
                if alias.endswith(suffix_norm) and len(alias) > len(suffix_norm) + 1:
                    trimmed = alias[: -len(suffix_norm)]
                    if len(trimmed) >= 2 and trimmed not in aliases:
                        aliases.add(trimmed)
                        changed = True
    return sorted(aliases, key=len, reverse=True)


def score_entry(entry: Mapping[str, Any], aliases: Sequence[str]) -> int:
    label = str(entry.get("label") or "")
    label_norm = normalize_text(label)
    core = label_core(label)
    best = 0
    for alias in aliases:
        if not alias:
            continue
        if core == alias:
            best = max(best, 120 + len(alias))
        elif core.startswith(alias) and len(core) > len(alias):
            best = max(best, 80 + len(alias))
        elif alias in label_norm:
            best = max(best, 70 + len(alias))
    return best


def label_core(label: str) -> str:
    text = normalize_text(label)
    for phrase in (
        "历史地图",
        "历史全图",
        "地图",
        "时期",
        "朝",
        "代",
        "附近",
        "全图",
        "公元",
        "年",
        "的",
    ):
        text = text.replace(normalize_text(phrase), "")
    for period in ("史前", "西周", "春秋", "战国", "西汉", "东汉", "三国", "西晋", "东晋", "南北朝", "北宋", "南宋", "五代", "夏", "商", "秦", "隋", "唐", "元", "明", "清", "辽", "金"):
        text = text.replace(normalize_text(period), "")
    text = re.sub(r"\d+", "", text)
    return text


def normalize_text(text: str) -> str:
    return re.sub(r"[\s,，、.。:：;；()（）《》〈〉\[\]【】\-_/]+", "", text.strip())


def format_text(result: Mapping[str, Any]) -> str:
    if result.get("status") == STATUS_RESOLVED:
        return f"{result['map_label']}: {result['url']}"
    return f"{result.get('status')}: {result.get('reason')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成同代同一级行政区的左图右史链接")
    parser.add_argument("--place", required=True, help="古地名，如 长安")
    parser.add_argument("--year", required=True, type=int, help="公元年份，如 755")
    parser.add_argument("--admin", help="从辞典/原文确认的同时代一级行政区，如 京畿道")
    parser.add_argument("--dynasty", help="可选朝代提示，如 唐")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH, help="左图右史索引 JSON")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    try:
        result = resolve_history_map_link(args.place, args.year, args.admin, args.dynasty, args.index)
    except HistoryMapLinkError as exc:
        result = {
            "status": STATUS_INVALID,
            "url": None,
            "map_label": None,
            "period": None,
            "admin": args.admin,
            "reason": str(exc),
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result))
    return 0 if result.get("status") == STATUS_RESOLVED else 1


if __name__ == "__main__":
    raise SystemExit(main())
