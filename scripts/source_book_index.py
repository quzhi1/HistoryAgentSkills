#!/usr/bin/env python3
"""Load and query local book-title indexes for source-link validation."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

from opencc import OpenCC


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = ROOT / "data" / "source_book_index.json"
SCRIPT_NORMALIZER = OpenCC("t2s")
TITLE_SUFFIX_RE = re.compile(r"\s*(?:全文原文及译文|全文原文及譯文|全文及译文|全文及譯文|全文原文|原文|全文)\s*$")
TITLE_NOISE_RE = re.compile(r"[\s,，、.。:：;；!?！？()（）《》〈〉\[\]【】\"'“”‘’\-_/·]+")


@lru_cache(maxsize=4)
def load_source_book_index(path: Path | str = DEFAULT_INDEX_PATH) -> Dict[str, Any]:
    """Load the generated Shidian/cnkgraph book index.

    Missing indexes are treated as empty so validators can fail closed without
    blocking a history answer; the refresh script is responsible for creating it.
    """

    index_path = Path(path)
    if not index_path.exists():
        return {"schema_version": 1, "sources": {}}
    with index_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        return {"schema_version": 1, "sources": {}}
    return data


def normalize_title(title: str) -> str:
    """Normalize title text for exact-ish cross-source matching."""

    simplified = SCRIPT_NORMALIZER.convert(unicodedata.normalize("NFKC", clean_title(title)))
    return TITLE_NOISE_RE.sub("", simplified)


def clean_title(title: str) -> str:
    """Remove sitemap display suffixes without changing the real title."""

    return TITLE_SUFFIX_RE.sub("", collapse_space(title)).strip()


def collapse_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def source_books(index: Optional[Mapping[str, Any]], source: str) -> List[Mapping[str, Any]]:
    if not index:
        return []
    sources = index.get("sources") if isinstance(index, Mapping) else None
    if not isinstance(sources, Mapping):
        return []
    payload = sources.get(source)
    if not isinstance(payload, Mapping):
        return []
    books = payload.get("books")
    if not isinstance(books, list):
        return []
    return [book for book in books if isinstance(book, Mapping)]


def lookup_title_entries(
    title: str,
    *,
    index: Optional[Mapping[str, Any]] = None,
    sources: Sequence[str] = ("shidian", "cnkgraph"),
    include_prefix: bool = True,
) -> List[Mapping[str, Any]]:
    """Find book entries whose normalized title matches or extends ``title``."""

    title_norm = normalize_title(title)
    if not title_norm:
        return []
    data = index or load_source_book_index()
    matches: List[Mapping[str, Any]] = []
    seen = set()
    for source, book in lookup_crosswalk_books(title_norm, data, sources=sources):
        key = (source, str(book.get("id") or book.get("book_id") or book.get("url") or book.get("api_url")))
        if key not in seen:
            seen.add(key)
            matches.append(book)
    for source in sources:
        for book in source_books(data, source):
            book_norm = str(book.get("normalized_title") or normalize_title(str(book.get("title") or "")))
            short_norm = normalize_title(short_title(str(book.get("title") or "")))
            if _title_norm_matches(title_norm, book_norm, include_prefix=include_prefix) or _title_norm_matches(
                title_norm,
                short_norm,
                include_prefix=include_prefix,
            ):
                key = (source, str(book.get("id") or book.get("book_id") or book.get("url") or book.get("api_url")))
                if key not in seen:
                    seen.add(key)
                    matches.append(book)
    return matches


def lookup_title_variants(
    title: str,
    *,
    index: Optional[Mapping[str, Any]] = None,
    sources: Sequence[str] = ("shidian", "cnkgraph"),
) -> set[str]:
    """Return normalized title variants present in the local source index."""

    variants = {normalize_title(title)}
    for entry in lookup_title_entries(title, index=index, sources=sources, include_prefix=False):
        entry_title = str(entry.get("title") or "")
        variants.add(normalize_title(entry_title))
        variants.add(normalize_title(short_title(entry_title)))
    return {variant for variant in variants if variant}


def lookup_crosswalk_books(
    normalized_title: str,
    index: Mapping[str, Any],
    *,
    sources: Sequence[str] = ("shidian", "cnkgraph"),
) -> List[tuple[str, Mapping[str, Any]]]:
    """Return source-tagged books from the explicit crosswalk, if present."""

    crosswalk = index.get("crosswalk") if isinstance(index, Mapping) else None
    if not isinstance(crosswalk, Mapping):
        return []
    entries = crosswalk.get("entries")
    if not isinstance(entries, list):
        return []
    wanted = set(sources)
    matches: List[tuple[str, Mapping[str, Any]]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("normalized_title") != normalized_title:
            continue
        for source in ("shidian", "cnkgraph"):
            if source not in wanted:
                continue
            books = entry.get(source)
            if isinstance(books, list):
                matches.extend((source, book) for book in books if isinstance(book, Mapping))
    return matches


def short_title(title: str) -> str:
    """Strip cnkgraph-style author/dynasty suffixes from display titles."""

    cleaned = clean_title(title)
    if "-" in cleaned:
        return cleaned.split("-", 1)[0].strip()
    if "：" in cleaned:
        return cleaned.split("：", 1)[0].strip()
    return cleaned


def find_shidian_book_by_url(
    url: str,
    *,
    index: Optional[Mapping[str, Any]] = None,
) -> Optional[Mapping[str, Any]]:
    """Return a Shidian book entry matching a book or chapter URL."""

    book_url = shidian_book_url_from_any(url)
    if not book_url:
        return None
    data = index or load_source_book_index()
    accepted = {_canonical_shidian_book_url(book_url)}
    parsed = urlparse(book_url)
    if parsed.path.startswith("/zh/book/"):
        accepted.add(_canonical_shidian_book_url(book_url.replace("/zh/book/", "/book/", 1)))
    elif parsed.path.startswith("/book/"):
        accepted.add(_canonical_shidian_book_url(book_url.replace("/book/", "/zh/book/", 1)))
    for book in source_books(data, "shidian"):
        candidate = str(book.get("url") or "")
        if _canonical_shidian_book_url(candidate) in accepted:
            return book
    return None


def shidian_book_url_from_any(url: str) -> Optional[str]:
    """Extract the stable Shidian book URL from a book or chapter URL."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.shidianguji.com":
        return None
    match = re.match(r"^(/(?:zh/)?book/[^/?#]+)", parsed.path)
    if not match:
        return None
    return f"https://www.shidianguji.com{match.group(1)}"


def iter_title_norms(entries: Iterable[Mapping[str, Any]]) -> Iterable[str]:
    for entry in entries:
        title = str(entry.get("title") or "")
        yield normalize_title(title)
        yield normalize_title(short_title(title))


def _title_norm_matches(query_norm: str, book_norm: str, *, include_prefix: bool = True) -> bool:
    if not query_norm or not book_norm:
        return False
    if query_norm == book_norm:
        return True
    return include_prefix and len(query_norm) >= 2 and book_norm.startswith(query_norm)


def _canonical_shidian_book_url(url: str) -> str:
    return (shidian_book_url_from_any(url) or url).replace("/zh/book/", "/book/", 1).rstrip("/")
