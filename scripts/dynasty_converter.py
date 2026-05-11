#!/usr/bin/env python3
"""Convert Chinese reign-year expressions to Gregorian years."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from fetch_dynasty_data import INDEX_PATH, DynastyDataError, load_index


ROOT = Path(__file__).resolve().parents[1]
YEAR_PATTERN = re.compile(r"(?P<era>[\u4e00-\u9fff·]+?)(?P<number>元|[零〇一二两三四五六七八九十百千\d]+)(?P<unit>年|载)")
CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}

# Known source-data boundary errata. Keep the raw downloaded JSON untouched and
# apply these only at conversion time so callers can still audit source values.
KNOWN_BOUNDARY_CORRECTIONS: Dict[str, Dict[str, Any]] = {
    # The local Shanghai Library row for 唐先天 currently gives 714-714, which
    # makes 先天二年 impossible. Standard chronology and the local dictionary's
    # 渤海/大祚荣 entries require 先天二年 = 713.
    "http://data.library.sh.cn/authority/temporal/5nyr6anqrz1zld77": {
        "begin": 712,
        "end": 713,
        "note": "本地校正：唐玄宗先天元年为712年，先天二年为713年。",
    },
    # The same boundary issue shifts 开元元年 to 714 in the source row; it began
    # in 713 after 先天二年.
    "http://data.library.sh.cn/authority/temporal/4ilyrfwurk4tysv8": {
        "begin": 713,
        "end": 741,
        "note": "本地校正：唐玄宗开元元年为713年。",
    },
    # The source rows for several short Five Dynasties eras are offset by one
    # Gregorian year. The dictionary entries and standard chronology require
    # 后唐同光元年 = 923 and 后唐清泰三年 = 936.
    "http://data.library.sh.cn/authority/temporal/kc511ful8w2f7sgk": {
        "begin": 923,
        "end": 926,
        "note": "本地校正：后唐同光元年为923年。",
    },
    "http://data.library.sh.cn/authority/temporal/7nx1agvmifneyc4c": {
        "begin": 934,
        "end": 936,
        "note": "本地校正：后唐清泰元年为934年，清泰三年为936年。",
    },
    "http://data.library.sh.cn/authority/temporal/4t699kyebyl4m2ng": {
        "begin": 936,
        "end": 944,
        "note": "本地校正：后晋天福元年为936年。",
    },
}


class EraConversionError(ValueError):
    """Raised when an era-year expression cannot be parsed or converted."""


def chinese_number_to_int(text: str) -> int:
    """Parse simple Chinese numerals used in reign years."""
    value = text.strip().replace("第", "")
    if value == "元":
        return 1
    if value.isdigit():
        number = int(value)
        if number < 1:
            raise EraConversionError(f"年序必须大于 0: {text!r}")
        return number
    if not value:
        raise EraConversionError("缺少年序")

    total = 0
    current = 0
    for char in value:
        if char in CHINESE_DIGITS:
            current = CHINESE_DIGITS[char]
        elif char in CHINESE_UNITS:
            unit = CHINESE_UNITS[char]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
        else:
            raise EraConversionError(f"无法解析中文数字: {text!r}")
    total += current
    if total < 1:
        raise EraConversionError(f"年序必须大于 0: {text!r}")
    return total


def _entry_aliases(entry: Mapping[str, Any]) -> List[str]:
    aliases: List[str] = []
    for title in entry.get("reignTitles") or []:
        if title and title not in aliases:
            aliases.append(str(title))
    title = str(entry.get("reignTitle") or "").strip()
    for part in title.replace("；", ";").split(";"):
        part = part.strip()
        if part and part != "NON" and part not in aliases:
            aliases.append(part)
    if not aliases:
        dynasty = str(entry.get("dynasty") or "").strip()
        if dynasty:
            aliases.append(dynasty)
    return aliases


def _format_gregorian(year: int) -> str:
    if year < 0:
        return f"公元前{abs(year)}年"
    return f"公元{year}年"


def _entry_bounds(entry: Mapping[str, Any]) -> Tuple[Any, Any, Optional[Mapping[str, Any]]]:
    correction = KNOWN_BOUNDARY_CORRECTIONS.get(str(entry.get("uri") or ""))
    if correction:
        return correction.get("begin"), correction.get("end"), correction
    return entry.get("begin"), entry.get("end"), None


def parse_era_expression(expression: str) -> Tuple[Optional[str], str, int]:
    """Return optional dynasty filter, era title, and year sequence."""
    query = expression.strip()
    if not query:
        raise EraConversionError("输入为空")

    dynasty_filter: Optional[str] = None
    parts = query.split()
    if len(parts) >= 2:
        possible_dynasty = parts[0].strip()
        if possible_dynasty:
            dynasty_filter = possible_dynasty
            query = "".join(parts[1:])

    match = YEAR_PATTERN.search(query)
    if not match:
        raise EraConversionError(f"无法识别年号纪年: {expression!r}")
    era = match.group("era").strip()
    year_number = chinese_number_to_int(match.group("number"))
    return dynasty_filter, era, year_number


def _matches_dynasty(entry: Mapping[str, Any], dynasty: Optional[str]) -> bool:
    if not dynasty:
        return True
    return dynasty in str(entry.get("dynasty") or "")


def convert_era_expression(
    expression: str,
    dynasty: Optional[str] = None,
    index: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Convert one reign-year expression, returning structured matches and errors."""
    parsed_dynasty, era, year_number = parse_era_expression(expression)
    dynasty_filter = dynasty or parsed_dynasty
    entries = index if index is not None else load_index()

    result: Dict[str, Any] = {
        "query": expression,
        "dynasty_filter": dynasty_filter,
        "era": era,
        "year_number": year_number,
        "matches": [],
        "errors": [],
    }

    candidates = [
        entry
        for entry in entries
        if _matches_dynasty(entry, dynasty_filter) and era in _entry_aliases(entry)
    ]
    if not candidates:
        result["errors"].append(f"未在本地年表索引中找到年号/纪年名: {era}")
        return result

    for entry in candidates:
        begin, end, correction = _entry_bounds(entry)
        if not isinstance(begin, int):
            result["errors"].append(f"{era} 的开始年份无效: {entry.get('uri')}")
            continue
        gregorian_year = begin + year_number - 1
        if isinstance(end, int) and gregorian_year > end:
            result["errors"].append(
                f"{entry.get('dynasty')}{entry.get('reignTitle') or entry.get('dynasty')}止于{_format_gregorian(end)}，"
                f"{expression}超出范围。"
            )
            continue
        result["matches"].append(
            {
                "expression": f"{era}{'元' if year_number == 1 else year_number}年",
                "gregorian_year": gregorian_year,
                "gregorian_label": _format_gregorian(gregorian_year),
                "dynasty": entry.get("dynasty") or "",
                "reignTitle": entry.get("reignTitle") or "",
                "monarch": entry.get("monarch") or "",
                "monarchName": entry.get("monarchName") or "",
                "begin": begin,
                "end": end,
                "uri": entry.get("uri") or "",
            }
        )
        if correction:
            result["matches"][-1].update(
                {
                    "corrected_boundary": True,
                    "source_begin": entry.get("begin"),
                    "source_end": entry.get("end"),
                    "correction_note": correction.get("note", ""),
                }
            )
    return result


def scan_text(text: str, index: Optional[Sequence[Mapping[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Find and convert recognizable reign-year expressions in arbitrary text."""
    entries = index if index is not None else load_index()
    aliases = sorted({alias for entry in entries for alias in _entry_aliases(entry)}, key=len, reverse=True)
    found: List[Dict[str, Any]] = []
    seen = set()
    for alias in aliases:
        if not alias:
            continue
        pattern = re.compile(re.escape(alias) + r"(元|[零〇一二两三四五六七八九十百千\d]+)(年|载)")
        for match in pattern.finditer(text):
            expression = match.group(0)
            key = (match.start(), expression)
            if key in seen:
                continue
            seen.add(key)
            converted = convert_era_expression(expression, index=entries)
            converted["start"] = match.start()
            converted["end"] = match.end()
            found.append(converted)
    return sorted(found, key=lambda item: item["start"])


def _print_human(result: Mapping[str, Any]) -> None:
    print(f"查询：{result['query']}")
    if result.get("dynasty_filter"):
        print(f"朝代限定：{result['dynasty_filter']}")

    matches = result.get("matches") or []
    if matches:
        print("\n换算结果：")
        for item in matches:
            reign = item.get("reignTitle") or item.get("dynasty")
            monarch_bits = " ".join(bit for bit in [item.get("monarch"), item.get("monarchName")] if bit)
            monarch_text = f"，{monarch_bits}" if monarch_bits else ""
            print(
                f"- {item.get('dynasty')}{reign}{result['year_number']}年"
                f"{monarch_text}：{item['gregorian_label']}"
            )

    errors = result.get("errors") or []
    if errors:
        print("\n提示：")
        for error in errors:
            print(f"- {error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Chinese reign-year expressions to Gregorian years."
    )
    parser.add_argument("expression", help='Year expression, e.g. "天宝三载" or "唐 天宝三载".')
    parser.add_argument("--dynasty", help="Optional dynasty filter, e.g. 唐.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    args = parser.parse_args()

    try:
        result = convert_era_expression(args.expression, dynasty=args.dynasty)
    except (DynastyDataError, EraConversionError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "index_path": str(INDEX_PATH)}, ensure_ascii=False, indent=2))
        else:
            print(f"换算失败: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result.get("matches") else 1


if __name__ == "__main__":
    raise SystemExit(main())
