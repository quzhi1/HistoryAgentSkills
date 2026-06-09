#!/usr/bin/env python3
"""Resolve map admins from modern-location clues without guessing.

This script is a guardrail helper for cases where a concrete place, such as a
temple or pass, is not directly resolved by TGAZ, but reliable sources give a
modern/later location. It verifies source-derived historical placename
candidates for the target year, checks that their modern location matches the
clue, then asks history_map_link.py to validate a same-period or transition map.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from history_map_link import (
    DEFAULT_INDEX_PATH,
    HistoryMapLinkError,
    STATUS_OVERVIEW as MAP_STATUS_OVERVIEW,
    label_core,
    load_index,
    normalize_text,
    pages_for_dynasty,
    pages_for_year,
    resolve_history_map_link,
    transition_map_pages,
)
from place_resolver import (
    MAX_PLACE_NAME_LENGTH,
    ModernBoundaryResolver,
    PlaceResolverError,
    STATUS_AMBIGUOUS as PLACE_STATUS_AMBIGUOUS,
    TgazClient,
    resolve_place,
    validate_place_name,
    validate_year as validate_tgaz_year,
)


MAX_HINT_LENGTH = 80
MAX_CANDIDATES = 12
MAX_LOOKUP_NAMES = 8
HINT_PATTERN = re.compile(r"^[\w\s\-\u4e00-\u9fff·'’().（）、，/]+$", re.UNICODE)
OVERVIEW_ADMIN_SUFFIXES = (
    "承宣布政使司",
    "布政使司",
    "布政司",
    "行中书省",
    "中书省",
    "行省",
    "刺史部",
    "宣慰司",
    "都司",
    "省",
    "道",
    "路",
    "诸郡",
)
PLACE_SUFFIX_PATTERN = (
    r"(?:承宣布政使司|布政使司|布政司|行中书省|中书省|行省|刺史部|"
    r"宣慰司|都司|县|州|郡|府|路|道|军|监|厅|卫|所|镇|关|城|寨|堡|邑)"
)
PLACE_NAME_PATTERN = rf"[\u4e00-\u9fff]{{1,10}}{PLACE_SUFFIX_PATTERN}"
DYNASTY_PREFIXES = (
    "西周",
    "东周",
    "西汉",
    "东汉",
    "曹魏",
    "蜀汉",
    "孙吴",
    "西晋",
    "东晋",
    "北魏",
    "东魏",
    "西魏",
    "北齐",
    "北周",
    "南朝",
    "北朝",
    "五代",
    "后梁",
    "后唐",
    "后晋",
    "后汉",
    "后周",
    "北宋",
    "南宋",
    "民国",
    "夏",
    "商",
    "周",
    "秦",
    "汉",
    "魏",
    "蜀",
    "吴",
    "晋",
    "隋",
    "唐",
    "宋",
    "辽",
    "金",
    "元",
    "明",
    "清",
)
DYNASTY_PREFIX_PATTERN = rf"(?:{'|'.join(DYNASTY_PREFIXES)})"
STATUS_RESOLVED = "resolved"
STATUS_OVERVIEW = "overview"
STATUS_NEEDS_CANDIDATES = "needs_candidates"
STATUS_NEEDS_ADMIN = "needs_admin"
STATUS_NOT_FOUND = "not_found"
STATUS_OUT_OF_RANGE = "out_of_range"
STATUS_INVALID = "invalid"


class PlaceAdminResolverError(ValueError):
    """Raised when reverse place-admin resolution inputs are invalid."""


def resolve_place_admin(
    place: str,
    year: int,
    dynasty: Optional[str] = None,
    modern_hint: Optional[str] = None,
    candidates: Optional[Sequence[str]] = None,
    lookup_names: Optional[Sequence[str]] = None,
    tgaz_client: Optional[TgazClient] = None,
    boundary_resolver: Optional[ModernBoundaryResolver] = None,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> Dict[str, Any]:
    """Resolve a validated map admin from a modern/later location clue."""

    checked_place = validate_place_name(place)
    checked_year = validate_tgaz_year(year)
    checked_dynasty = validate_optional_hint(dynasty, "朝代")
    checked_modern_hint = validate_optional_hint(modern_hint, "现代地点线索")
    checked_candidates = validate_name_list(candidates or [], "候选历史地名", MAX_CANDIDATES)
    checked_lookup_names = validate_name_list(lookup_names or [], "反查地名", MAX_LOOKUP_NAMES)

    result: Dict[str, Any] = {
        "query": {
            "place": checked_place,
            "year": checked_year,
            "dynasty": checked_dynasty,
            "modern_hint": checked_modern_hint,
            "candidates": checked_candidates,
            "lookup_names": checked_lookup_names,
        },
        "status": STATUS_NOT_FOUND,
        "historical_place": None,
        "modern_match": None,
        "derived_candidates": [],
        "candidate_results": [],
        "admin_candidates": [],
        "map_link": None,
        "reason": "",
        "warnings": [],
    }

    if checked_year is None:
        result["status"] = STATUS_OUT_OF_RANGE
        result["reason"] = "年份超出 TGAZ / 左图右史可验证范围"
        return result

    candidate_names = list(checked_candidates)
    for lookup_name in checked_lookup_names:
        lookup_result = resolve_place(
            lookup_name,
            year=None,
            tgaz_client=tgaz_client,
            boundary_resolver=boundary_resolver,
            max_candidates=8,
        )
        extracted = historical_names_from_lookup(lookup_name, lookup_result)
        result["derived_candidates"].extend(extracted)
        candidate_names.extend(item["name"] for item in extracted)

    if len(result["derived_candidates"]) > MAX_CANDIDATES:
        result["derived_candidates"] = result["derived_candidates"][:MAX_CANDIDATES]
    candidate_names = dedupe(candidate_names)
    if len(candidate_names) > MAX_CANDIDATES:
        result["warnings"].append(f"候选历史地名超过 {MAX_CANDIDATES} 个，已按来源顺序截断")
        candidate_names = candidate_names[:MAX_CANDIDATES]
    if not candidate_names:
        result["status"] = STATUS_NEEDS_CANDIDATES
        result["reason"] = "需要先从辞典/cnkgraph/TGAZ 沿革中取得目标年代候选历史地名"
        return result

    if not checked_modern_hint:
        result["warnings"].append("未提供现代地点线索；只能验证候选地名和地图，不能完成现代落点反查闭环")

    first_matched_place: Optional[Mapping[str, Any]] = None
    first_modern_match: Optional[Mapping[str, Any]] = None
    first_admin_candidates: List[Dict[str, Any]] = []

    for candidate_name in candidate_names:
        candidate_result = resolve_place(
            candidate_name,
            year=checked_year,
            tgaz_client=tgaz_client,
            boundary_resolver=boundary_resolver,
        )
        result["candidate_results"].append(summarize_candidate_result(candidate_name, candidate_result))

        for place_check in inspectable_place_results(candidate_result, checked_modern_hint, boundary_resolver):
            if not modern_hint_matches(checked_modern_hint, place_check):
                continue

            best_match = place_check.get("best_match") or {}
            modern_match = place_check.get("modern_administration")
            admin_candidates = derive_admin_candidates(best_match, checked_year, checked_dynasty, index_path=index_path)
            if first_matched_place is None:
                first_matched_place = best_match
                first_modern_match = modern_match
                first_admin_candidates = admin_candidates
            for admin_candidate in admin_candidates:
                map_link = resolve_history_map_link(
                    checked_place,
                    checked_year,
                    admin_candidate["admin"],
                    dynasty=checked_dynasty,
                    index_path=index_path,
                    allow_overview=can_use_overview_fallback(admin_candidate["admin"]),
                )
                admin_candidate["map_status"] = map_link.get("status")
                admin_candidate["map_reason"] = map_link.get("reason")
                if map_link.get("status") == STATUS_RESOLVED:
                    result["status"] = STATUS_RESOLVED
                    result["historical_place"] = best_match
                    result["modern_match"] = modern_match
                    result["admin_candidates"] = admin_candidates
                    result["map_link"] = map_link
                    result["reason"] = "已由现代地点线索反查到目标年份历史地名，并验证左图右史地图"
                    return result
                if map_link.get("status") == MAP_STATUS_OVERVIEW:
                    result["status"] = STATUS_OVERVIEW
                    result["historical_place"] = best_match
                    result["modern_match"] = modern_match
                    result["admin_candidates"] = admin_candidates
                    result["map_link"] = map_link
                    result["reason"] = "已匹配目标年份历史地名和现代地点线索；同代一级区划专题图缺失，已回退到同一时代总图"
                    return result

    if first_matched_place is not None:
        result["status"] = STATUS_NEEDS_ADMIN
        result["historical_place"] = first_matched_place
        result["modern_match"] = first_modern_match
        result["admin_candidates"] = first_admin_candidates
        result["reason"] = "已匹配目标年份历史地名和现代地点线索，但未验证到可用的一级区划地图"
        return result

    result["status"] = STATUS_NOT_FOUND
    result["reason"] = "候选历史地名未能在目标年份解析，或其现代落点与线索不符"
    return result


def inspectable_place_results(
    candidate_result: Mapping[str, Any],
    modern_hint: Optional[str],
    boundary_resolver: Optional[ModernBoundaryResolver],
) -> List[Dict[str, Any]]:
    """Return resolved-like records that are safe to check for admin labels."""

    if candidate_result.get("status") == STATUS_RESOLVED:
        return [dict(candidate_result)]
    if candidate_result.get("status") != PLACE_STATUS_AMBIGUOUS:
        return []

    # Ambiguous TGAZ results need a modern clue to choose between same-scored
    # historical names. Without that clue, continuing would be a guess.
    if not modern_hint:
        return []

    resolver = boundary_resolver or ModernBoundaryResolver.from_cnmaps_data()
    checks: List[Dict[str, Any]] = []
    for candidate in candidate_result.get("candidates") or []:
        if not isinstance(candidate, Mapping):
            continue
        longitude = candidate.get("longitude")
        latitude = candidate.get("latitude")
        if longitude is None or latitude is None:
            continue
        try:
            modern_administration = resolver.reverse_geocode(float(longitude), float(latitude))
        except (TypeError, ValueError):
            modern_administration = None
        checks.append(
            {
                "query": candidate_result.get("query"),
                "status": STATUS_RESOLVED,
                "best_match": dict(candidate),
                "candidates": candidate_result.get("candidates") or [],
                "modern_administration": modern_administration,
                "note": "TGAZ 歧义候选经现代地点线索逐一核验",
            }
        )
    return checks


def validate_optional_hint(value: Optional[str], label: str) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > MAX_HINT_LENGTH:
        raise PlaceAdminResolverError(f"{label}长度不能超过 {MAX_HINT_LENGTH} 字符")
    if not HINT_PATTERN.fullmatch(text):
        raise PlaceAdminResolverError(f"{label}包含不允许的字符")
    return text


def validate_name_list(values: Sequence[str], label: str, limit: int) -> List[str]:
    if len(values) > limit:
        raise PlaceAdminResolverError(f"{label}不能超过 {limit} 个")
    names: List[str] = []
    for value in values:
        if len(value.strip()) > MAX_PLACE_NAME_LENGTH:
            raise PlaceAdminResolverError(f"{label}长度不能超过 {MAX_PLACE_NAME_LENGTH} 字符")
        names.append(validate_place_name(value))
    return dedupe(names)


def historical_names_from_lookup(lookup_name: str, lookup_result: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Extract source-note historical placename candidates from a later-place lookup."""

    records: List[Mapping[str, Any]] = []
    best_match = lookup_result.get("best_match")
    if isinstance(best_match, Mapping):
        records.append(best_match)
    for item in lookup_result.get("candidates") or []:
        if isinstance(item, Mapping):
            records.append(item)

    derived: List[Dict[str, str]] = []
    for record in records:
        evidence_text = "；".join(
            text
            for text in (
                str(record.get("source_note") or ""),
                str(record.get("present_location") or ""),
                str(record.get("parent") or ""),
            )
            if text and not is_non_historical_note(text)
        )
        for name in extract_historical_place_names(evidence_text):
            name = clean_historical_place_name(name)
            if not name:
                continue
            record_names = [str(record.get("name") or ""), *list(record.get("names") or [])]
            if name == lookup_name or name in record_names:
                continue
            derived.append(
                {
                    "name": name,
                    "source": f"lookup_name:{lookup_name}",
                    "evidence": truncate(evidence_text, 180),
                }
            )
    return dedupe_derived_candidates(derived)


def extract_historical_place_names(text: str) -> List[str]:
    if not text:
        return []
    candidates: List[str] = []
    patterns = [
        rf"(?:旧名|旧曰|古曰|本名|本曰|本为|原名|原曰|改曰|改名|改为|更名|更曰|复名|复为|置|改置|析置|升为|降为|省入|废入|属|隶)[^。；，、]{{0,12}}?({PLACE_NAME_PATTERN})",
        rf"({PLACE_NAME_PATTERN})(?:改置|改名|复名|省入|废入|属|隶|治|故城)",
        rf"{DYNASTY_PREFIX_PATTERN}({PLACE_NAME_PATTERN})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1).strip()
            if 2 <= len(name) <= 16:
                candidates.append(name)
    return dedupe(candidates)


def clean_historical_place_name(name: str) -> str:
    text = name.strip()
    for marker in (
        "改为",
        "改曰",
        "改名",
        "更名",
        "更曰",
        "复名",
        "复为",
        "旧名",
        "旧曰",
        "本名",
        "本曰",
        "本为",
        "原名",
        "原曰",
        "省入",
        "废入",
        "分置",
        "析置",
        "置",
        "改",
        "更",
        "为",
        "属",
        "隶",
    ):
        if marker in text:
            text = text.rsplit(marker, 1)[-1].strip()
    text = re.sub(r"^(?:为|曰|名|改为|复为|属|隶|旧|新|今|后|古|原)+", "", text)
    text = re.sub(r"^(?:又|复|以|领|治|在|改|置|省|入|分|废)+", "", text)
    for prefix in sorted(DYNASTY_PREFIXES, key=len, reverse=True):
        if text.startswith(prefix):
            stripped = text[len(prefix):]
            if is_valid_extracted_place_name(stripped, require_two_char_stem=True):
                text = stripped
                break
    if re.search(r"(年|月|日|数据|地图|投影|精度|关系|位置|参照|聚落|河流|之间|相对|依据)", text):
        return ""
    if text.startswith("的") or re.search(r"(县县|州州|府府|郡郡|路路|道道)$", text):
        return ""
    if text.count("府") == 1 and not text.endswith("府"):
        text = text.rsplit("府", 1)[-1]
    if text in {"州县", "郡县", "府县", "诸县", "本县", "郡县城", "州府"}:
        return ""
    if not is_valid_extracted_place_name(text):
        return ""
    return text


def is_non_historical_note(text: str) -> bool:
    lowered = text.lower()
    return "<html" in lowered or "<body" in lowered or "chgis项目" in text or "数据依据" in text


def is_valid_extracted_place_name(name: str, require_two_char_stem: bool = False) -> bool:
    if not re.fullmatch(PLACE_NAME_PATTERN, name):
        return False
    suffix = matched_place_suffix(name)
    if not suffix:
        return False
    stem = name[: -len(suffix)]
    if require_two_char_stem and len(stem) < 2:
        return False
    return bool(stem)


def matched_place_suffix(name: str) -> str:
    suffixes = re.findall(PLACE_SUFFIX_PATTERN, name)
    return suffixes[-1] if suffixes else ""


def derive_admin_candidates(
    best_match: Mapping[str, Any],
    year: int,
    dynasty: Optional[str],
    index_path: Path = DEFAULT_INDEX_PATH,
) -> List[Dict[str, Any]]:
    """Derive possible map admin labels, leaving final validation to history_map_link."""

    raw_admins: List[str] = []
    raw_admins.extend(extract_admins_from_note(str(best_match.get("source_note") or ""), year=year))
    raw_admins.extend(split_parent_admins(str(best_match.get("parent") or "")))
    raw_admins = dedupe(raw_admins)

    candidates: List[Dict[str, Any]] = []
    for admin in raw_admins:
        candidates.extend(index_admin_variants(admin, year, dynasty, index_path))
        candidates.append(
            {
                "admin": admin,
                "source_admin": admin,
                "reason": "由 TGAZ parent/source_note 抽取，仍需 history_map_link.py 验证是否为可用地图标签",
            }
        )
    return dedupe_admin_candidates(candidates)


def split_parent_admins(text: str) -> List[str]:
    values: List[str] = []
    for part in re.split(r"[/／、,，;；\s]+", text):
        part = part.strip()
        if 2 <= len(part) <= 12 and re.search(r"(州|郡|道|路|府|省|布政司|行省|都司)$", part):
            values.append(part)
    return values


def can_use_overview_fallback(admin: str) -> bool:
    return any(admin.endswith(suffix) for suffix in OVERVIEW_ADMIN_SUFFIXES)


def extract_admins_from_note(text: str, year: Optional[int] = None) -> List[str]:
    clean = re.sub(r"<[^>]+>", "；", text or "")
    mentions: List[Tuple[str, Optional[int], int]] = []
    pattern = r"(?:属|隶|为|置为|改为)([\u4e00-\u9fff]{2,12}(?:州|郡|道|路|府|省|布政司|行省|都司))"
    for match in re.finditer(pattern, clean):
        mentions.append((match.group(1), nearest_preceding_year(clean, match.start()), match.start()))

    if year is not None:
        dated = [(admin, admin_year, pos) for admin, admin_year, pos in mentions if admin_year is not None and admin_year <= year]
        if dated:
            latest_year = max(admin_year for _, admin_year, _ in dated if admin_year is not None)
            return dedupe(admin for admin, admin_year, _ in dated if admin_year == latest_year)

    return dedupe(admin for admin, _, _ in mentions)


def nearest_preceding_year(text: str, position: int) -> Optional[int]:
    window = text[max(0, position - 96) : position]
    years = [int(match.group(1)) for match in re.finditer(r"(?<!\d)(-?\d{1,4})\s*年", window)]
    return years[-1] if years else None


def index_admin_variants(admin: str, year: int, dynasty: Optional[str], index_path: Path) -> List[Dict[str, Any]]:
    """Find suffix-compatible map labels from the current year/dynasty index pages."""

    suffix = matched_admin_suffix(admin)
    if suffix != "郡":
        return []
    stem = admin[: -len(suffix)]
    if len(stem) < 2:
        return []

    allowed_pages = context_pages_for_map_index(year, dynasty)
    if not allowed_pages:
        return []

    index = load_index(index_path)
    variants: List[Dict[str, Any]] = []
    stem_norm = normalize_text(stem)
    for entry in index.get("entries") or []:
        if entry.get("page") not in allowed_pages:
            continue
        core = label_core(str(entry.get("label") or ""))
        core_norm = normalize_text(core)
        if core == admin:
            continue
        if stem_norm in core_norm and "郡" in core_norm:
            variants.append(
                {
                    "admin": core,
                    "source_admin": admin,
                    "reason": "由左图右史索引在目标年份/过渡期可用页面中找到同名郡类地图标签，仍需 history_map_link.py 验证",
                }
            )
    return dedupe_admin_candidates(variants)


def matched_admin_suffix(admin: str) -> str:
    for suffix in (
        "承宣布政使司",
        "布政使司",
        "布政司",
        "行中书省",
        "中书省",
        "行省",
        "刺史部",
        "宣慰司",
        "都司",
        "省",
        "道",
        "路",
        "府",
        "州",
        "郡",
        "县",
    ):
        if admin.endswith(suffix):
            return suffix
    return ""


def context_pages_for_map_index(year: int, dynasty: Optional[str]) -> List[str]:
    year_pages = set(pages_for_year(year))
    dynasty_pages = set(pages_for_dynasty(dynasty)) if dynasty else set()
    transition_pages = set(transition_map_pages(year, dynasty))
    pages: List[str] = []
    if dynasty_pages:
        overlap = year_pages & dynasty_pages
        pages.extend(sorted(overlap or set()))
    else:
        pages.extend(sorted(year_pages))
    pages.extend(page for page in sorted(transition_pages) if page not in pages)
    return pages


def modern_hint_matches(modern_hint: Optional[str], candidate_result: Mapping[str, Any]) -> bool:
    if not modern_hint:
        return True
    needle = normalize_for_match(modern_hint)
    if not needle:
        return False
    for text in modern_texts(candidate_result):
        haystack = normalize_for_match(text)
        if not haystack:
            continue
        if needle in haystack or haystack in needle:
            return True
    return False


def modern_texts(candidate_result: Mapping[str, Any]) -> Iterable[str]:
    best_match = candidate_result.get("best_match") or {}
    yield str(best_match.get("present_location") or "")
    yield from modern_snippets_from_note(str(best_match.get("source_note") or ""))
    admin = candidate_result.get("modern_administration") or {}
    if isinstance(admin, Mapping):
        yield "".join(str(admin.get(key) or "") for key in ("province", "city", "district"))
        yield str(admin.get("matched_name") or "")


def modern_snippets_from_note(text: str) -> Iterable[str]:
    if not text:
        return []
    clean = re.sub(r"<[^>]+>", "；", text)
    pattern = r"(?:即今|治今|在今|移治于今|治所约在今|今)([\u4e00-\u9fff]{2,24}?)(?=[，。、；\s()（）]|$)"
    return [match.group(1) for match in re.finditer(pattern, clean)]


def summarize_candidate_result(candidate_name: str, result: Mapping[str, Any]) -> Dict[str, Any]:
    best_match = result.get("best_match") or {}
    return {
        "candidate": candidate_name,
        "status": result.get("status"),
        "matched_name": best_match.get("name"),
        "present_location": best_match.get("present_location"),
        "parent": best_match.get("parent"),
        "modern_administration": result.get("modern_administration"),
        "note": result.get("note"),
    }


def dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def dedupe_derived_candidates(candidates: Iterable[Mapping[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    result: List[Dict[str, str]] = []
    for candidate in candidates:
        name = candidate.get("name") or ""
        if name and name not in seen:
            seen.add(name)
            result.append(dict(candidate))
    return result


def dedupe_admin_candidates(candidates: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for candidate in candidates:
        admin = str(candidate.get("admin") or "")
        if admin and admin not in seen:
            seen.add(admin)
            result.append(dict(candidate))
    return result


def normalize_for_match(text: str) -> str:
    text = re.sub(r"[\s,，、.。:：;；()（）《》〈〉\[\]【】\-_/]+", "", text.strip())
    text = re.sub(r"^(今|治今|约在今|在今|治所约在今)", "", text)
    for suffix in ("特别行政区", "自治州", "自治县", "地区", "省", "市", "区", "县", "旗"):
        text = text.replace(suffix, "")
    return text


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def format_text(result: Mapping[str, Any]) -> str:
    if result.get("status") == STATUS_RESOLVED:
        historical_place = result.get("historical_place") or {}
        map_link = result.get("map_link") or {}
        return f"{historical_place.get('name')}: {map_link.get('map_label')} {map_link.get('url')}"
    if result.get("status") == STATUS_OVERVIEW:
        historical_place = result.get("historical_place") or {}
        map_link = result.get("map_link") or {}
        return f"{historical_place.get('name')}: {map_link.get('map_label')}（时代总图） {map_link.get('url')}"
    return f"{result.get('status')}: {result.get('reason')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="由现代地点线索反查目标年份历史地名并验证左图右史 admin")
    parser.add_argument("--place", required=True, help="最终回答保留的地点，如 少林寺")
    parser.add_argument("--year", required=True, type=int, help="公元年份，如 625")
    parser.add_argument("--dynasty", help="可选朝代提示，如 唐")
    parser.add_argument("--modern", help="辞典/cnkgraph 给出的现代地点线索，如 河南登封")
    parser.add_argument("--candidate", action="append", default=[], help="来源已验证的目标年代候选历史地名，可多次传入")
    parser.add_argument("--lookup-name", action="append", default=[], help="后世/现代地名，用其沿革抽取候选历史地名，可多次传入")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH, help="左图右史索引 JSON")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    try:
        result = resolve_place_admin(
            args.place,
            args.year,
            dynasty=args.dynasty,
            modern_hint=args.modern,
            candidates=args.candidate,
            lookup_names=args.lookup_name,
            index_path=args.index,
        )
    except (PlaceAdminResolverError, PlaceResolverError, HistoryMapLinkError) as exc:
        result = {
            "query": {
                "place": args.place,
                "year": args.year,
                "dynasty": args.dynasty,
                "modern_hint": args.modern,
                "candidates": args.candidate,
                "lookup_names": args.lookup_name,
            },
            "status": STATUS_INVALID,
            "historical_place": None,
            "modern_match": None,
            "derived_candidates": [],
            "candidate_results": [],
            "admin_candidates": [],
            "map_link": None,
            "reason": str(exc),
            "warnings": [],
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result))
    return 0 if result.get("status") in {STATUS_RESOLVED, STATUS_OVERVIEW} else 1


if __name__ == "__main__":
    raise SystemExit(main())
