#!/usr/bin/env python3
"""Find verified Shidian Guji chapter links for cited source passages."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence
from urllib.parse import quote, urljoin

import requests
from opencc import OpenCC

from source_book_index import find_shidian_book_by_url, load_source_book_index, lookup_title_entries, lookup_title_variants

BASE_URL = "https://www.shidianguji.com"
SEARCH_BASE = f"{BASE_URL}/zh/search"
TIMEOUT = 30
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HistoryAgentSkills/1.0; +https://www.shidianguji.com/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
}
MAX_KEYWORD_LENGTH = 64
MAX_SOURCE_LENGTH = 160
MAX_QUOTE_LENGTH = 500
STATUS_RESOLVED = "resolved"
STATUS_NOT_FOUND = "not_found"
STATUS_INVALID = "invalid"
CHAPTER_HREF_PATTERN = re.compile(r"^/(?:(?:zh|ens)/)?book/[^/\s]+/chapter/[^?\s#]+")
SCRIPT_NORMALIZER = OpenCC("t2s")
DIRECT_CHAPTER_BOOK_ID_RE = re.compile(r"^(?:LS|SK|SBCK|NA)\d+$")
CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "两": 2,
    "兩": 2,
}
CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}
SOURCE_TITLE_ALIASES = {
    "诗经": ("毛诗", "诗三百", "毛诗郑笺", "诗经集传"),
    "毛诗": ("诗经", "诗三百", "毛诗郑笺", "诗经集传"),
    "庄子": ("南华经", "南华真经", "南华真经注疏", "庄子注", "庄子集释"),
    "南华经": ("庄子", "南华真经", "南华真经注疏", "庄子注", "庄子集释"),
    "南华真经": ("庄子", "南华经", "南华真经注疏", "庄子注", "庄子集释"),
    "史记": ("太史公书", "史记集解", "史记索隐", "史记正义", "史记三家注"),
    "汉书": ("前汉书", "汉书补注"),
    "全唐文": ("钦定全唐文",),
    "钦定全唐文": ("全唐文",),
}


class ShidianLinkError(ValueError):
    """Raised for invalid inputs or Shidian fetch problems."""


class HttpGetter(Protocol):
    """Small protocol for tests and alternate HTTP fetchers."""

    def __call__(self, url: str, **kwargs: Any) -> Any:
        """Return a response-like object with text/status methods."""


class ShidianSearchParser(HTMLParser):
    """Extract Shidian chapter anchors and their visible search-result text."""

    def __init__(self) -> None:
        super().__init__()
        self.results: List[Dict[str, str]] = []
        self._current: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        href = ""
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value.strip()
                break
        if CHAPTER_HREF_PATTERN.match(href):
            self._current = {"href": href, "text": []}

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current is None:
            return
        href = str(self._current["href"])
        text = " ".join(part.strip() for part in self._current["text"] if part.strip())
        if href and text:
            self.results.append({"href": href, "text": text})
        self._current = None


def find_shidian_link(
    quote_text: str,
    source: str,
    keyword: Optional[str] = None,
    html: Optional[str] = None,
    http_get: Optional[HttpGetter] = None,
) -> Dict[str, Any]:
    """Return a verified Shidian chapter link or a clearly unverified fallback."""

    quote_checked = validate_text(quote_text, "原文短引", MAX_QUOTE_LENGTH)
    source_checked = validate_text(source, "出处", MAX_SOURCE_LENGTH)
    keyword_checked = validate_keyword(keyword or derive_keyword(quote_checked, source_checked))
    search_url = build_search_url(keyword_checked)

    if html is None:
        direct = find_direct_source_chapter_link(quote_checked, source_checked, http_get=http_get)
        if direct:
            direct["search_url"] = search_url
            return direct
        html = fetch_search_html(search_url, http_get=http_get)
    candidates = parse_search_results(html)
    scored = score_candidates(candidates, quote_checked, source_checked)

    if (
        scored
        and scored[0]["score"] >= 70
        and scored[0]["quote_score"] >= 45
        and scored[0]["primary_source_score"] >= 35
    ):
        best = scored[0]
        return {
            "status": STATUS_RESOLVED,
            "url": best["url"],
            "search_url": search_url,
            "matched_source": best["text"],
            "reason": "识典搜索结果中的章节链接与引文/出处达到验证阈值",
        }

    return {
        "status": STATUS_NOT_FOUND,
        "url": None,
        "search_url": search_url,
        "matched_source": scored[0]["text"] if scored else None,
        "reason": "未能验证识典章节链接与该原文短引/出处相符",
    }


def find_direct_source_chapter_link(
    quote_text: str,
    source: str,
    *,
    http_get: Optional[HttpGetter] = None,
) -> Optional[Dict[str, Any]]:
    """Verify predictable Shidian chapter URLs for known source books.

    Shidian's global search only returns a small top-N candidate set. For
    canonical series with numeric chapter IDs, such as LS0016_1 for
    《旧唐书》卷一, the cited original chapter may be present on Shidian but
    absent from global search results. This fallback uses the local book index
    plus the cited volume number to check the original book directly.
    """

    source_terms = extract_source_terms(source)
    if not source_terms:
        return None
    volume_number = extract_volume_number(source)
    if volume_number is None:
        return None

    index = load_source_book_index()
    source_title = source_terms[0]
    candidate_books: List[Mapping[str, Any]] = []
    seen_books: set[str] = set()
    for lookup_title in source_lookup_titles(source_title):
        for book in lookup_title_entries(lookup_title, index=index, sources=("shidian",), include_prefix=True):
            key = str(book.get("url") or book.get("book_id") or book.get("title") or "")
            if key and key not in seen_books:
                seen_books.add(key)
                candidate_books.append(book)
    getter = http_get or requests.get
    seen_urls: set[str] = set()
    for book in candidate_books:
        book_id = str(book.get("book_id") or "").strip()
        title = str(book.get("title") or source_title)
        if not DIRECT_CHAPTER_BOOK_ID_RE.match(book_id):
            continue
        for url in direct_chapter_urls(book_id, volume_number):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            html = fetch_optional_html(url, getter)
            if html is None:
                continue
            quote_score = text_overlap_score(quote_text, visible_text(html))
            if quote_score >= 85:
                return {
                    "status": STATUS_RESOLVED,
                    "url": url,
                    "matched_source": f"直接校验识典《{title}》卷{volume_number}章节页，quote_score={quote_score}",
                    "reason": "本地书目索引定位原书后，直接章节页与引文匹配",
                }
    return None


def direct_chapter_urls(book_id: str, volume_number: int) -> List[str]:
    chapter_id = f"{book_id}_{volume_number}"
    return [
        f"{BASE_URL}/book/{book_id}/chapter/{chapter_id}",
        f"{BASE_URL}/zh/book/{book_id}/chapter/{chapter_id}",
    ]


def fetch_optional_html(url: str, getter: HttpGetter) -> Optional[str]:
    try:
        response = getter(url, timeout=TIMEOUT, headers=REQUEST_HEADERS)
        if getattr(response, "status_code", 200) == 404:
            return None
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    return str(response.text)


def visible_text(html: str) -> str:
    return collapse_space(re.sub(r"<[^>]+>", " ", html))


def extract_volume_number(source: str) -> Optional[int]:
    match = re.search(r"卷\s*([0-9]+|[零〇一二三四五六七八九十百千两兩]+)", source)
    if not match:
        return None
    token = match.group(1)
    if token.isdigit():
        return int(token)
    return parse_chinese_number(token)


def parse_chinese_number(token: str) -> Optional[int]:
    if not token:
        return None
    if all(char in CHINESE_DIGITS for char in token) and len(token) > 1:
        return int("".join(str(CHINESE_DIGITS[char]) for char in token))
    if all(char in CHINESE_DIGITS for char in token):
        return CHINESE_DIGITS[token]

    total = 0
    current = 0
    used_unit = False
    for char in token:
        if char in CHINESE_DIGITS:
            current = CHINESE_DIGITS[char]
        elif char in CHINESE_UNITS:
            unit = CHINESE_UNITS[char]
            total += (current or 1) * unit
            current = 0
            used_unit = True
        else:
            return None
    if used_unit:
        return total + current
    return None


def validate_text(value: str, label: str, max_length: int) -> str:
    text = value.strip()
    if not text:
        raise ShidianLinkError(f"{label}不能为空")
    if len(text) > max_length:
        raise ShidianLinkError(f"{label}长度不能超过 {max_length} 字符")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
        raise ShidianLinkError(f"{label}包含控制字符")
    return text


def validate_keyword(value: str) -> str:
    text = validate_text(value, "关键词", MAX_KEYWORD_LENGTH)
    if any(char in text for char in "<>{}\\"):
        raise ShidianLinkError("关键词包含不允许的字符")
    return text


def derive_keyword(quote_text: str, source: str) -> str:
    chars = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", quote_text)
    if chars:
        return chars[0][:10]
    titles = extract_source_terms(source)
    if titles:
        return titles[0][:MAX_KEYWORD_LENGTH]
    return quote_text[:MAX_KEYWORD_LENGTH]


def build_search_url(keyword: str) -> str:
    return f"{SEARCH_BASE}/{quote(keyword, safe='')}"


def fetch_search_html(search_url: str, http_get: Optional[HttpGetter] = None) -> str:
    if not search_url.startswith(f"{BASE_URL}/"):
        raise ShidianLinkError("识典检索 URL 必须使用 HTTPS 官方域名")
    getter = http_get or requests.get
    try:
        response = getter(search_url, timeout=TIMEOUT, headers=REQUEST_HEADERS)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise ShidianLinkError("识典古籍检索超时") from exc
    except requests.exceptions.RequestException as exc:
        raise ShidianLinkError(f"识典古籍检索失败: {exc}") from exc
    return str(response.text)


def parse_search_results(html: str) -> List[Dict[str, str]]:
    parser = ShidianSearchParser()
    parser.feed(html)
    seen = set()
    results: List[Dict[str, str]] = []
    source_index = load_source_book_index()
    for item in parser.results:
        href = item["href"]
        if href in seen:
            continue
        seen.add(href)
        url = urljoin(BASE_URL, href)
        result = {
            "url": url,
            "text": collapse_space(item["text"]),
        }
        indexed_book = find_shidian_book_by_url(url, index=source_index)
        if indexed_book:
            result["book_title"] = str(indexed_book.get("title") or "")
            result["book_url"] = str(indexed_book.get("url") or "")
        results.append(
            result
        )
    return results


def score_candidates(candidates: Iterable[Mapping[str, str]], quote_text: str, source: str) -> List[Dict[str, Any]]:
    source_terms = extract_source_terms(source)
    scored: List[Dict[str, Any]] = []
    for candidate in candidates:
        text = candidate.get("text") or ""
        quote_score = text_overlap_score(quote_text, text)
        primary_source_score = primary_source_match_score(source_terms, text, candidate.get("book_title"))
        source_score = source_match_score(source_terms, text)
        total = quote_score + primary_source_score + min(source_score, 20)
        if quote_score >= 45 or primary_source_score > 0 or source_score > 0:
            scored.append(
                {
                    "url": candidate.get("url"),
                    "text": text,
                    "book_title": candidate.get("book_title"),
                    "book_url": candidate.get("book_url"),
                    "score": total,
                    "quote_score": quote_score,
                    "primary_source_score": primary_source_score,
                    "source_score": source_score,
                }
            )
    scored.sort(
        key=lambda item: (
            item["primary_source_score"],
            item["score"],
            item["quote_score"],
            item["source_score"],
        ),
        reverse=True,
    )
    return scored


def text_overlap_score(quote_text: str, haystack: str) -> int:
    quote_norm = normalize_for_match(quote_text)
    haystack_norm = normalize_for_match(haystack)
    if not quote_norm or not haystack_norm:
        return 0
    if quote_norm in haystack_norm:
        return 100
    quote_counter = Counter(quote_norm)
    haystack_counter = Counter(haystack_norm)
    overlap = sum(min(count, haystack_counter.get(char, 0)) for char, count in quote_counter.items())
    return int(100 * overlap / max(len(quote_norm), 1))


def source_match_score(source_terms: Sequence[str], text: str) -> int:
    text_norm = normalize_for_match(text)
    score = 0
    for term in source_terms:
        term_norm = normalize_for_match(term)
        if term_norm and term_norm in text_norm:
            score = max(score, 35 if len(term_norm) >= 2 else 10)
    return score


def primary_source_match_score(source_terms: Sequence[str], text: str, indexed_book_title: Optional[str] = None) -> int:
    """Prefer the chapter whose owning book matches the cited primary source.

    Shidian search can return later anthologies or reference works that quote the
    same sentence. Those are useful clues, but they must not be surfaced as the
    original source link.
    """

    if not source_terms:
        return 0
    accepted_titles = source_title_variants(source_terms[0])
    candidate_titles = []
    if indexed_book_title:
        candidate_titles.append(indexed_book_title)
    candidate_titles.extend(extract_source_terms(text))
    if candidate_titles:
        for title in candidate_titles:
            candidate_norm = normalize_for_match(title)
            candidate_variants = source_title_variants(title)
            if accepted_titles.intersection(candidate_variants):
                return 70
            if any(
                candidate_norm == accepted or (len(accepted) >= 2 and candidate_norm.startswith(accepted))
                for accepted in accepted_titles
            ):
                return 70
        return 0

    text_norm = normalize_for_match(text)
    if any(accepted in text_norm for accepted in accepted_titles):
        return 45
    return 0


def source_title_variants(title: str) -> set[str]:
    normalized_title = normalize_for_match(title)
    variants = {normalized_title}
    variants.update(lookup_title_variants(title))
    for canonical, aliases in SOURCE_TITLE_ALIASES.items():
        normalized_group = {normalize_for_match(canonical)}
        normalized_group.update(normalize_for_match(alias) for alias in aliases)
        if normalized_title in normalized_group:
            variants.update(normalized_group)
    return {variant for variant in variants if variant}


def source_lookup_titles(title: str) -> List[str]:
    """Return source title strings worth trying against the local book index."""

    titles = [title]
    normalized_title = normalize_for_match(title)
    for canonical, aliases in SOURCE_TITLE_ALIASES.items():
        normalized_group = {normalize_for_match(canonical)}
        normalized_group.update(normalize_for_match(alias) for alias in aliases)
        if normalized_title in normalized_group:
            titles.append(canonical)
            titles.extend(aliases)
    return list(dict.fromkeys(item for item in titles if item))


def extract_source_terms(source: str) -> List[str]:
    terms = re.findall(r"《([^》]+)》", source)
    if not terms:
        terms = re.findall(r"[\u4e00-\u9fff]{2,8}", source)
    return list(dict.fromkeys(term.strip() for term in terms if term.strip()))


def normalize_for_match(text: str) -> str:
    normalized = SCRIPT_NORMALIZER.convert(unicodedata.normalize("NFKC", text))
    return re.sub(r"[\s,，、.。:：;；!?！？()（）《》〈〉\[\]【】\"'“”‘’\-_/·]+", "", normalized)


def collapse_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def format_text(result: Mapping[str, Any]) -> str:
    if result.get("status") == STATUS_RESOLVED:
        return f"识典原文: {result['url']}"
    return f"{result.get('status')}: {result.get('reason')}；检索页: {result.get('search_url')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="验证并生成识典古籍原文章节链接")
    parser.add_argument("--quote", required=True, help="最终回答中准备引用的原文短引")
    parser.add_argument("--source", required=True, help="书名+卷章出处，如 《魏书》卷三五《崔浩传》")
    parser.add_argument("--keyword", help="识典检索关键词；缺省时从出处或引文中派生")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    try:
        result = find_shidian_link(args.quote, args.source, args.keyword)
    except ShidianLinkError as exc:
        keyword = (args.keyword or args.source[:MAX_KEYWORD_LENGTH]).strip()
        search_url = build_search_url(keyword) if keyword else None
        result = {
            "status": STATUS_INVALID,
            "url": None,
            "search_url": search_url,
            "matched_source": None,
            "reason": str(exc),
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result))
    return 0 if result.get("status") == STATUS_RESOLVED else 1


if __name__ == "__main__":
    raise SystemExit(main())
