#!/usr/bin/env python3
"""Convert Chinese reign-year expressions through the cnkgraph Calendar API."""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Tuple
from urllib.parse import quote

import requests


API_BASE_URL = os.environ.get("CNKGRAPH_API_BASE", "https://open.cnkgraph.com/api").rstrip("/")
try:
    TIMEOUT = int(os.environ.get("CNKGRAPH_TIMEOUT", "30"))
except ValueError:
    TIMEOUT = 30
YEAR_PATTERN = re.compile(r"(?P<era>[\u4e00-\u9fff·]+?)(?P<number>元|[零〇一二两三四五六七八九十百千\d]+)(?P<unit>年|载)")
SCAN_PATTERN = re.compile(r"[\u4e00-\u9fff·]{2,12}(?:元|[零〇一二两三四五六七八九十百千\d]+)(?:年|载)")
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


class EraConversionError(ValueError):
    """Raised when an era-year expression cannot be parsed or converted."""


class CalendarClient(Protocol):
    """Small protocol for tests and alternate API clients."""

    def get_date(self, key: str) -> Mapping[str, Any]:
        """Return the JSON body from GET /api/Calendar/Date/{key}."""


class CnkgraphCalendarClient:
    """HTTP client for cnkgraph Calendar date parsing."""

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_date(self, key: str) -> Mapping[str, Any]:
        url = f"{self.base_url}/Calendar/Date/{quote(key, safe='')}"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout as exc:
            raise EraConversionError(f"cnkgraph Calendar API 请求超时: {key}") from exc
        except requests.exceptions.RequestException as exc:
            raise EraConversionError(f"cnkgraph Calendar API 请求失败: {exc}") from exc
        except ValueError as exc:
            raise EraConversionError("cnkgraph Calendar API 返回了非 JSON 响应") from exc
        if not isinstance(data, Mapping):
            raise EraConversionError("cnkgraph Calendar API 返回结构异常")
        return data


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


def parse_era_expression(expression: str) -> Tuple[Optional[str], str, int, str, str]:
    """Return optional dynasty filter, era title, year sequence, source number text, and unit."""
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
    number_text = match.group("number")
    unit = match.group("unit")
    year_number = chinese_number_to_int(number_text)
    return dynasty_filter, era, year_number, number_text, unit


def _format_gregorian(year: int) -> str:
    if year < 0:
        return f"公元前{abs(year)}年"
    return f"公元{year}年"


def _parse_gregorian_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    year = int(match.group(0))
    if "前" in text and year > 0:
        return -year
    return year


def _matches_dynasty(text: str, dynasty: Optional[str]) -> bool:
    if not dynasty:
        return True
    return dynasty in text or text in dynasty


def _matches_era(api_name: Any, primary_era: str, parsed_era: str) -> bool:
    name = str(api_name or "").strip()
    return bool(name) and (name == primary_era or name == parsed_era or name in parsed_era)


def _iter_relevant_eras(
    data: Mapping[str, Any],
    primary_era: str,
    parsed_era: str,
    dynasty_filter: Optional[str],
) -> Iterable[Dict[str, Any]]:
    for group in data.get("EraYears") or []:
        if not isinstance(group, Mapping):
            continue
        dynasty = str(group.get("Dynasty") or "")
        if dynasty_filter and not _matches_dynasty(dynasty, dynasty_filter):
            continue
        for king in group.get("Kings") or []:
            if not isinstance(king, Mapping):
                continue
            for era in king.get("EraYears") or []:
                if not isinstance(era, Mapping) or not _matches_era(era.get("Name"), primary_era, parsed_era):
                    continue
                yield {
                    "dynasty": dynasty,
                    "king": king,
                    "era": era,
                }


def _build_api_key(expression: str, dynasty_filter: Optional[str], parsed_dynasty: Optional[str]) -> str:
    compact = "".join(expression.strip().split())
    if dynasty_filter and dynasty_filter != parsed_dynasty:
        return f"{dynasty_filter}{compact}"
    return compact


def convert_era_expression(
    expression: str,
    dynasty: Optional[str] = None,
    api_client: Optional[CalendarClient] = None,
) -> Dict[str, Any]:
    """Convert one reign-year expression via cnkgraph, returning structured matches and errors."""
    parsed_dynasty, parsed_era, year_number, number_text, unit = parse_era_expression(expression)
    dynasty_filter = dynasty or parsed_dynasty
    api_key = _build_api_key(expression, dynasty_filter, parsed_dynasty)
    client = api_client or CnkgraphCalendarClient()

    result: Dict[str, Any] = {
        "query": expression,
        "dynasty_filter": dynasty_filter,
        "era": parsed_era,
        "year_number": year_number,
        "api_query": api_key,
        "api_endpoint": f"{API_BASE_URL}/Calendar/Date/{quote(api_key, safe='')}",
        "matches": [],
        "errors": [],
    }

    data = client.get_date(api_key)
    date_info = data.get("Date") if isinstance(data.get("Date"), Mapping) else {}
    gregorian_year = _parse_gregorian_year(date_info.get("Year"))
    if gregorian_year is None:
        result["errors"].append(f"cnkgraph 未能把 {expression} 解析为公元年份")
        return result

    primary_era = str(date_info.get("EraName") or parsed_era).strip()
    result["era"] = primary_era or parsed_era
    result["year_ganzhi"] = date_info.get("YearGanZhi")
    result["links_count"] = (data.get("Links") or {}).get("Count") if isinstance(data.get("Links"), Mapping) else None

    for item in _iter_relevant_eras(data, primary_era or parsed_era, parsed_era, dynasty_filter):
        king = item["king"]
        era = item["era"]
        result["matches"].append(
            {
                "expression": f"{primary_era or parsed_era}{number_text}{unit}",
                "gregorian_year": gregorian_year,
                "gregorian_label": _format_gregorian(gregorian_year),
                "dynasty": item["dynasty"],
                "reignTitle": era.get("Name") or "",
                "monarch": king.get("Name") or "",
                "monarchName": king.get("Name") or "",
                "begin": era.get("BeginYear") or "",
                "end": era.get("EndYear") or "",
                "eraId": era.get("Id"),
                "kingId": king.get("Id"),
                "calculatedYear": era.get("CalculatedYear") or "",
                "comment": era.get("Comment") or "",
                "source_api": "open.cnkgraph.com Calendar API",
            }
        )

    if not result["matches"]:
        result["matches"].append(
            {
                "expression": f"{primary_era or parsed_era}{number_text}{unit}",
                "gregorian_year": gregorian_year,
                "gregorian_label": _format_gregorian(gregorian_year),
                "dynasty": "",
                "reignTitle": primary_era or parsed_era,
                "monarch": "",
                "monarchName": "",
                "begin": "",
                "end": "",
                "source_api": "open.cnkgraph.com Calendar API",
            }
        )
    return result


def scan_text(text: str, api_client: Optional[CalendarClient] = None) -> List[Dict[str, Any]]:
    """Find and convert recognizable reign-year expressions in arbitrary text."""
    found: List[Dict[str, Any]] = []
    seen = set()
    for match in SCAN_PATTERN.finditer(text):
        expression = match.group(0)
        if expression.startswith(("公元", "西元")):
            continue
        key = (match.start(), expression)
        if key in seen:
            continue
        seen.add(key)
        try:
            converted = convert_era_expression(expression, api_client=api_client)
        except EraConversionError:
            continue
        converted["start"] = match.start()
        converted["end"] = match.end()
        found.append(converted)
    return found


def _print_human(result: Mapping[str, Any]) -> None:
    print(f"查询：{result['query']}")
    if result.get("dynasty_filter"):
        print(f"朝代/政权限定：{result['dynasty_filter']}")

    matches = result.get("matches") or []
    if matches:
        print("\n换算结果：")
        for item in matches:
            reign = item.get("reignTitle") or result.get("era")
            monarch_text = f"，{item.get('monarch')}" if item.get("monarch") else ""
            dynasty_text = item.get("dynasty") or ""
            calculated = f"（{item.get('calculatedYear')}）" if item.get("calculatedYear") else ""
            print(f"- {dynasty_text}{reign}{calculated}{monarch_text}：{item['gregorian_label']}")

    errors = result.get("errors") or []
    if errors:
        print("\n提示：")
        for error in errors:
            print(f"- {error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Chinese reign-year expressions to Gregorian years through cnkgraph."
    )
    parser.add_argument("expression", help='Year expression, e.g. "天宝十四载" or "唐 天宝三载".')
    parser.add_argument("--dynasty", help="Optional dynasty or regime filter, e.g. 唐, 吴越, 后唐.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    args = parser.parse_args()

    try:
        result = convert_era_expression(args.expression, dynasty=args.dynasty)
    except EraConversionError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
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
