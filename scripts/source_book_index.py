#!/usr/bin/env python3
"""Load and query local book-title indexes for source-link validation."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

from opencc import OpenCC


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_PATH = ROOT / "data" / "source_book_index.sqlite"
LEGACY_JSON_INDEX_PATH = ROOT / "data" / "source_book_index.json"
SCRIPT_NORMALIZER = OpenCC("t2s")
TITLE_SUFFIX_RE = re.compile(r"\s*(?:全文原文及译文|全文原文及譯文|全文及译文|全文及譯文|全文原文|原文|全文)\s*$")
TITLE_NOISE_RE = re.compile(r"[\s,，、.。:：;；!?！？()（）《》〈〉\[\]【】\"'“”‘’\-_/·]+")


class SQLiteSourceBookIndex:
    """Small SQLite-backed lookup wrapper for the source book index."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def lookup_title_entries(
        self,
        title: str,
        *,
        sources: Sequence[str] = ("shidian", "cnkgraph"),
        include_prefix: bool = True,
    ) -> List[Mapping[str, Any]]:
        title_norm = normalize_title(title)
        if not title_norm:
            return []

        matches: List[Mapping[str, Any]] = []
        seen = set()
        for source, book in self.lookup_crosswalk_books(title_norm, sources=sources):
            key = _entry_key(source, book)
            if key not in seen:
                seen.add(key)
                matches.append(book)

        for source in sources:
            for book in self._lookup_raw_books(source, title_norm, include_prefix=include_prefix):
                key = _entry_key(source, book)
                if key not in seen:
                    seen.add(key)
                    matches.append(book)
        return matches

    def lookup_crosswalk_books(
        self,
        normalized_title: str,
        *,
        sources: Sequence[str] = ("shidian", "cnkgraph"),
    ) -> List[tuple[str, Mapping[str, Any]]]:
        wanted = set(sources)
        matches: List[tuple[str, Mapping[str, Any]]] = []
        if "shidian" in wanted:
            rows = self.conn.execute(
                """
                SELECT b.title, b.normalized_title, b.url, b.book_id
                FROM crosswalk_shidian x
                JOIN shidian_books b ON b.url = x.shidian_url
                WHERE x.normalized_title = ?
                ORDER BY b.title, b.url
                """,
                (normalized_title,),
            ).fetchall()
            matches.extend(("shidian", _row_to_dict(row)) for row in rows)
        if "cnkgraph" in wanted:
            rows = self.conn.execute(
                """
                SELECT b.id, b.title, b.normalized_title, b.author, b.dynasty, b.api_url
                FROM crosswalk_cnkgraph x
                JOIN cnkgraph_books b ON b.id = x.cnkgraph_id
                WHERE x.normalized_title = ?
                ORDER BY b.title, b.id
                """,
                (normalized_title,),
            ).fetchall()
            matches.extend(("cnkgraph", _cnkgraph_row_to_dict(row)) for row in rows)
        return matches

    def find_shidian_book_by_url(self, url: str) -> Optional[Mapping[str, Any]]:
        book_url = shidian_book_url_from_any(url)
        if not book_url:
            return None
        canonical_url = _canonical_shidian_book_url(book_url)
        row = self.conn.execute(
            """
            SELECT title, normalized_title, url, book_id
            FROM shidian_books
            WHERE url = ?
            LIMIT 1
            """,
            (canonical_url,),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def _lookup_raw_books(self, source: str, title_norm: str, *, include_prefix: bool) -> List[Mapping[str, Any]]:
        if source == "shidian":
            params: tuple[Any, ...]
            where = "normalized_title = ?"
            params = (title_norm,)
            if include_prefix:
                where = "(normalized_title = ? OR normalized_title LIKE ?)"
                params = (title_norm, f"{title_norm}%")
            rows = self.conn.execute(
                f"""
                SELECT title, normalized_title, url, book_id
                FROM shidian_books
                WHERE {where}
                ORDER BY CASE WHEN normalized_title = ? THEN 0 ELSE 1 END, title, url
                """,
                (*params, title_norm),
            ).fetchall()
            return [_row_to_dict(row) for row in rows]
        if source == "cnkgraph":
            params = (title_norm,)
            where = "normalized_title = ?"
            if include_prefix:
                where = "(normalized_title = ? OR normalized_title LIKE ?)"
                params = (title_norm, f"{title_norm}%")
            rows = self.conn.execute(
                f"""
                SELECT id, title, normalized_title, author, dynasty, api_url
                FROM cnkgraph_books
                WHERE {where}
                ORDER BY CASE WHEN normalized_title = ? THEN 0 ELSE 1 END, title, id
                """,
                (*params, title_norm),
            ).fetchall()
            return [_cnkgraph_row_to_dict(row) for row in rows]
        return []


def load_source_book_index(path: Path | str = DEFAULT_INDEX_PATH) -> Any:
    """Load the generated Shidian/cnkgraph book index.

    The default is SQLite for fast point lookups. Legacy JSON is still accepted
    for tests and one-time migrations.
    """

    return _load_source_book_index(str(Path(path)))


@lru_cache(maxsize=4)
def _load_source_book_index(path_str: str) -> Any:
    index_path = Path(path_str)
    if index_path.exists() and index_path.suffix in {".sqlite", ".db"}:
        return SQLiteSourceBookIndex(index_path)
    if not index_path.exists() and index_path == DEFAULT_INDEX_PATH and LEGACY_JSON_INDEX_PATH.exists():
        index_path = LEGACY_JSON_INDEX_PATH
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


def source_books(index: Optional[Any], source: str) -> List[Mapping[str, Any]]:
    if isinstance(index, SQLiteSourceBookIndex):
        return index._lookup_raw_books(source, "", include_prefix=False)
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
    index: Optional[Any] = None,
    sources: Sequence[str] = ("shidian", "cnkgraph"),
    include_prefix: bool = True,
) -> List[Mapping[str, Any]]:
    """Find book entries whose normalized title matches or extends ``title``."""

    data = index or load_source_book_index()
    if isinstance(data, SQLiteSourceBookIndex):
        return data.lookup_title_entries(title, sources=sources, include_prefix=include_prefix)

    title_norm = normalize_title(title)
    if not title_norm:
        return []
    matches: List[Mapping[str, Any]] = []
    seen = set()
    for source, book in lookup_crosswalk_books(title_norm, data, sources=sources):
        key = _entry_key(source, book)
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
                key = _entry_key(source, book)
                if key not in seen:
                    seen.add(key)
                    matches.append(book)
    return matches


def lookup_title_variants(
    title: str,
    *,
    index: Optional[Any] = None,
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
    index: Any,
    *,
    sources: Sequence[str] = ("shidian", "cnkgraph"),
) -> List[tuple[str, Mapping[str, Any]]]:
    """Return source-tagged books from the explicit crosswalk, if present."""

    if isinstance(index, SQLiteSourceBookIndex):
        return index.lookup_crosswalk_books(normalized_title, sources=sources)
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
    index: Optional[Any] = None,
) -> Optional[Mapping[str, Any]]:
    """Return a Shidian book entry matching a book or chapter URL."""

    data = index or load_source_book_index()
    if isinstance(data, SQLiteSourceBookIndex):
        return data.find_shidian_book_by_url(url)

    book_url = shidian_book_url_from_any(url)
    if not book_url:
        return None
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


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


def _cnkgraph_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    item = dict(row)
    categories = item.pop("categories_json", None)
    item.setdefault("site_url", None)
    try:
        item["categories"] = json.loads(categories) if categories else []
    except json.JSONDecodeError:
        item["categories"] = []
    return item


def _entry_key(source: str, entry: Mapping[str, Any]) -> tuple[str, str]:
    return (source, str(entry.get("id") or entry.get("book_id") or entry.get("url") or entry.get("api_url")))


def _title_norm_matches(query_norm: str, book_norm: str, *, include_prefix: bool = True) -> bool:
    if not query_norm or not book_norm:
        return False
    if query_norm == book_norm:
        return True
    return include_prefix and len(query_norm) >= 2 and book_norm.startswith(query_norm)


def _canonical_shidian_book_url(url: str) -> str:
    return (shidian_book_url_from_any(url) or url).replace("/zh/book/", "/book/", 1).rstrip("/")
