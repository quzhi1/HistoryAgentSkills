#!/usr/bin/env python3
"""Refresh Shidian and cnkgraph book-title/link indexes."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests

from source_book_index import DEFAULT_INDEX_PATH, clean_title, normalize_title, short_title


SHIDIAN_BASE_URL = "https://www.shidianguji.com"
SHIDIAN_SITEMAP_PATH = "/sitemap-book"
SHIDIAN_SITEMAP_RE = re.compile(r"^/sitemap-book(?:-\d+(?:-\d+)*)?$")
SHIDIAN_BOOK_RE = re.compile(r"^/(?:zh/)?book/[^/?#]+$")
CNKGRAPH_API_BASE = "https://open.cnkgraph.com/api"
CNKGRAPH_SITE_BASE = "https://cnkgraph.com"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HistoryAgentSkills/1.0; +https://www.shidianguji.com/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.5",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
}
DEFAULT_TIMEOUT = 30


class AnchorParser(HTMLParser):
    """Collect anchor href/text pairs from sitemap HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: List[Dict[str, str]] = []
        self._current: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        href = ""
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value.strip()
                break
        if href:
            self._current = {"href": href, "text": []}

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current is None:
            return
        text = " ".join(part.strip() for part in self._current["text"] if part.strip())
        self.anchors.append({"href": str(self._current["href"]), "text": text})
        self._current = None


def fetch_shidian_books(
    session: requests.Session,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    sleep_seconds: float = 0.05,
    max_pages: Optional[int] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Crawl Shidian sitemap pages and extract book title -> URL mappings."""

    queue = deque([SHIDIAN_SITEMAP_PATH])
    queued = {SHIDIAN_SITEMAP_PATH}
    visited: set[str] = set()
    books_by_url: Dict[str, Dict[str, Any]] = {}

    while queue:
        path = queue.popleft()
        queued.discard(path)
        if path in visited:
            continue
        if max_pages is not None and len(visited) >= max_pages:
            break
        visited.add(path)
        html = fetch_text(session, f"{SHIDIAN_BASE_URL}{path}", timeout=timeout)
        parsed = parse_shidian_sitemap(html, sitemap_path=path)

        for next_path in parsed["sitemap_paths"]:
            if next_path not in visited and next_path not in queued:
                queue.append(next_path)
                queued.add(next_path)
        for book in parsed["books"]:
            books_by_url.setdefault(book["url"], book)
        if verbose:
            print(
                f"shidian page {len(visited)}: {path} "
                f"books={len(books_by_url)} queue={len(queue)}",
                file=sys.stderr,
                flush=True,
            )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    books = sorted(books_by_url.values(), key=lambda item: (item["normalized_title"], item["url"]))
    return {
        "base_url": SHIDIAN_BASE_URL,
        "sitemap_url": f"{SHIDIAN_BASE_URL}{SHIDIAN_SITEMAP_PATH}",
        "sitemap_pages_crawled": len(visited),
        "book_count": len(books),
        "books": books,
    }


def parse_shidian_sitemap(html: str, *, sitemap_path: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse a Shidian sitemap page into child sitemap paths and book links."""

    parser = AnchorParser()
    parser.feed(html)
    sitemap_paths: set[str] = set()
    books: List[Dict[str, str]] = []
    seen_books: set[str] = set()

    for anchor in parser.anchors:
        href = anchor["href"]
        text = anchor.get("text") or ""
        path = shidian_sitemap_path(href)
        if path:
            sitemap_paths.add(path)
        book_url = shidian_book_target_url(href)
        if not book_url or book_url in seen_books:
            continue
        title = clean_title(text)
        if not title:
            continue
        seen_books.add(book_url)
        books.append(
            {
                "title": title,
                "normalized_title": normalize_title(title),
                "url": book_url,
                "book_id": book_url.rstrip("/").rsplit("/", 1)[-1],
                "sitemap_path": sitemap_path,
            }
        )

    for path in re.findall(r"/sitemap-book(?:-\d+(?:-\d+)*)?", html):
        if SHIDIAN_SITEMAP_RE.match(path):
            sitemap_paths.add(path)

    return {
        "sitemap_paths": sorted(sitemap_paths),
        "books": books,
    }


def shidian_sitemap_path(href: str) -> Optional[str]:
    absolute = urljoin(SHIDIAN_BASE_URL, href)
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or parsed.netloc != "www.shidianguji.com":
        return None
    return parsed.path if SHIDIAN_SITEMAP_RE.match(parsed.path) else None


def shidian_book_target_url(href: str) -> Optional[str]:
    """Extract official Shidian book URL from direct or security redirect hrefs."""

    parsed = urlparse(href)
    candidate = href
    if parsed.netloc == "security.zijieapi.com":
        target = parse_qs(parsed.query).get("targetUrl", [None])[0]
        if not target:
            return None
        candidate = target

    absolute = urljoin(SHIDIAN_BASE_URL, candidate)
    book = urlparse(absolute)
    if book.scheme != "https" or book.netloc != "www.shidianguji.com":
        return None
    if not SHIDIAN_BOOK_RE.match(book.path):
        return None
    return f"https://www.shidianguji.com{book.path}"


def fetch_cnkgraph_books(
    session: requests.Session,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    sleep_seconds: float = 0.05,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Fetch cnkgraph book overview and expand every category/group."""

    overview_url = f"{CNKGRAPH_API_BASE}/Book"
    overview = fetch_json(session, overview_url, timeout=timeout)
    categories = overview.get("Categories") if isinstance(overview, Mapping) else None
    if not isinstance(categories, list):
        raise ValueError("cnkgraph /Book overview missing Categories")

    books_by_id: Dict[str, Dict[str, Any]] = {}
    normalized_categories: List[Dict[str, Any]] = []

    for category_index, category in enumerate(categories, 1):
        if not isinstance(category, Mapping):
            continue
        category_name = str(category.get("Name") or "").strip()
        groups = category.get("Groups")
        if not category_name or not isinstance(groups, list):
            continue
        category_groups: List[Dict[str, Any]] = []
        for group_index, group in enumerate(groups, 1):
            if not isinstance(group, Mapping):
                continue
            group_name = str(group.get("Name") or "").strip()
            if not group_name:
                continue
            group_payload = fetch_cnkgraph_group(session, category_name, group_name, timeout=timeout)
            group_books = group_payload.get("Books") if isinstance(group_payload, Mapping) else None
            if not isinstance(group_books, list):
                raise ValueError(f"cnkgraph group missing Books: {category_name}/{group_name}")
            category_groups.append({"name": group_name, "count": int(group.get("Count") or len(group_books))})
            for raw_book in group_books:
                if not isinstance(raw_book, Mapping):
                    continue
                book = normalize_cnkgraph_book(raw_book, category_name, group_name)
                existing = books_by_id.get(book["id"])
                if existing:
                    existing.setdefault("categories", []).append({"category": category_name, "group": group_name})
                else:
                    books_by_id[book["id"]] = book
            if verbose:
                print(
                    f"cnkgraph {category_index}/{len(categories)} "
                    f"{category_name}/{group_name} ({group_index}/{len(groups)}) "
                    f"group_books={len(group_books)} total_books={len(books_by_id)}",
                    file=sys.stderr,
                    flush=True,
                )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        normalized_categories.append({"name": category_name, "groups": category_groups})

    books = sorted(books_by_id.values(), key=lambda item: (item["normalized_title"], item["id"]))
    return {
        "base_api_url": CNKGRAPH_API_BASE,
        "overview_url": overview_url,
        "reported_total": int(overview.get("Total") or len(books)),
        "book_count": len(books),
        "categories": normalized_categories,
        "books": books,
    }


def fetch_cnkgraph_group(
    session: requests.Session,
    category_name: str,
    group_name: str,
    *,
    timeout: int,
) -> Dict[str, Any]:
    path = f"/Book/{quote(category_name, safe='')}/{quote(group_name, safe='')}"
    return fetch_json(session, f"{CNKGRAPH_API_BASE}{path}", timeout=timeout)


def normalize_cnkgraph_book(raw_book: Mapping[str, Any], category: str, group: str) -> Dict[str, Any]:
    raw_id = raw_book.get("Id")
    if raw_id is None:
        raise ValueError(f"cnkgraph book missing Id: {raw_book}")
    book_id = str(raw_id)
    title = clean_title(str(raw_book.get("Name") or ""))
    if not title:
        raise ValueError(f"cnkgraph book missing Name: {raw_book}")
    api_url = f"{CNKGRAPH_API_BASE}/Book/{quote(book_id, safe='')}"
    return {
        "id": book_id,
        "title": title,
        "normalized_title": normalize_title(title),
        "author": raw_book.get("Author"),
        "dynasty": raw_book.get("Dynasty"),
        "api_url": api_url,
        "site_url": f"{CNKGRAPH_SITE_BASE}/Book/{quote(book_id, safe='')}",
        "categories": [{"category": category, "group": group}],
    }


def normalize_existing_sources(sources: Mapping[str, Any]) -> Dict[str, Any]:
    """Recompute normalized titles for already-crawled source payloads."""

    normalized: Dict[str, Any] = {}
    for source_name, payload in sources.items():
        if not isinstance(payload, Mapping):
            continue
        source_payload = dict(payload)
        books = payload.get("books")
        if isinstance(books, list):
            normalized_books = []
            for book in books:
                if not isinstance(book, Mapping):
                    continue
                normalized_book = dict(book)
                normalized_book["title"] = clean_title(str(normalized_book.get("title") or ""))
                normalized_book["normalized_title"] = normalize_title(str(normalized_book.get("title") or ""))
                normalized_books.append(normalized_book)
            source_payload["books"] = normalized_books
            source_payload["book_count"] = len(normalized_books)
        normalized[source_name] = source_payload
    return normalized


def build_crosswalk(sources: Mapping[str, Any]) -> Dict[str, Any]:
    """Build explicit Shidian <-> cnkgraph title correspondence groups."""

    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for source_name in ("shidian", "cnkgraph"):
        payload = sources.get(source_name)
        if not isinstance(payload, Mapping):
            continue
        books = payload.get("books")
        if not isinstance(books, list):
            continue
        for book in books:
            if not isinstance(book, Mapping):
                continue
            title = str(book.get("title") or "")
            normalized_title = normalize_title(short_title(title))
            if not normalized_title:
                continue
            grouped.setdefault(normalized_title, {"shidian": [], "cnkgraph": []})[source_name].append(
                crosswalk_book_ref(source_name, book)
            )

    entries: List[Dict[str, Any]] = []
    for normalized_title, source_books in sorted(grouped.items()):
        shidian_books = _dedupe_crosswalk_books(source_books["shidian"])
        cnkgraph_books = _dedupe_crosswalk_books(source_books["cnkgraph"])
        if not shidian_books or not cnkgraph_books:
            continue
        titles = sorted(
            {
                str(book.get("title") or "")
                for book in [*shidian_books, *cnkgraph_books]
                if str(book.get("title") or "")
            }
        )
        entries.append(
            {
                "normalized_title": normalized_title,
                "match_type": "exact_normalized_title",
                "titles": titles,
                "shidian": shidian_books,
                "cnkgraph": cnkgraph_books,
            }
        )

    return {
        "strategy": "same normalized title after script conversion, punctuation cleanup, and display-suffix removal",
        "entry_count": len(entries),
        "entries": entries,
    }


def crosswalk_book_ref(source_name: str, book: Mapping[str, Any]) -> Dict[str, Any]:
    """Keep crosswalk entries compact but directly usable."""

    if source_name == "shidian":
        return {
            "title": book.get("title"),
            "url": book.get("url"),
            "book_id": book.get("book_id"),
        }
    return {
        "title": book.get("title"),
        "id": book.get("id"),
        "api_url": book.get("api_url"),
        "site_url": book.get("site_url"),
        "author": book.get("author"),
        "dynasty": book.get("dynasty"),
        "categories": book.get("categories"),
    }


def _dedupe_crosswalk_books(books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for book in books:
        key = str(book.get("url") or book.get("api_url") or book.get("id") or book.get("book_id") or book.get("title"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(book)
    return deduped


def read_existing_sources(path: Path) -> Dict[str, Any]:
    if path.suffix in {".sqlite", ".db"}:
        return read_sqlite_sources(path)
    with path.open("r", encoding="utf-8") as file:
        existing = json.load(file)
    if isinstance(existing, Mapping) and isinstance(existing.get("sources"), Mapping):
        return dict(existing["sources"])
    return {}


def read_sqlite_sources(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        shidian_books = [
            {
                "title": row["title"],
                "normalized_title": row["normalized_title"],
                "url": row["url"],
                "book_id": row["book_id"],
            }
            for row in conn.execute(
                "SELECT title, normalized_title, url, book_id FROM shidian_books ORDER BY normalized_title, url"
            )
        ]
        cnkgraph_books = []
        for row in conn.execute(
            """
            SELECT id, title, normalized_title, author, dynasty, api_url
            FROM cnkgraph_books
            ORDER BY normalized_title, id
            """
        ):
            cnkgraph_books.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "normalized_title": row["normalized_title"],
                    "author": row["author"],
                    "dynasty": row["dynasty"],
                    "api_url": row["api_url"],
                }
            )
    finally:
        conn.close()
    sources: Dict[str, Any] = {}
    if shidian_books:
        sources["shidian"] = {
            "base_url": SHIDIAN_BASE_URL,
            "sitemap_url": f"{SHIDIAN_BASE_URL}{SHIDIAN_SITEMAP_PATH}",
            "book_count": len(shidian_books),
            "books": shidian_books,
        }
    if cnkgraph_books:
        sources["cnkgraph"] = {
            "base_api_url": CNKGRAPH_API_BASE,
            "overview_url": f"{CNKGRAPH_API_BASE}/Book",
            "book_count": len(cnkgraph_books),
            "books": cnkgraph_books,
        }
    return sources


def build_index(args: argparse.Namespace) -> Dict[str, Any]:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    sources: Dict[str, Any] = {}
    if args.input_json:
        sources.update(read_existing_sources(args.input_json))
    elif (args.merge_existing or args.from_existing) and args.output.exists():
        sources.update(read_existing_sources(args.output))

    if args.from_existing:
        sources = normalize_existing_sources(sources)
    elif args.source in ("all", "shidian"):
        sources["shidian"] = fetch_shidian_books(
            session,
            timeout=args.timeout,
            sleep_seconds=args.sleep,
            max_pages=args.max_shidian_pages,
            verbose=args.verbose,
        )
    if not args.from_existing and args.source in ("all", "cnkgraph"):
        sources["cnkgraph"] = fetch_cnkgraph_books(
            session,
            timeout=args.timeout,
            sleep_seconds=args.sleep,
            verbose=args.verbose,
        )
    sources = normalize_existing_sources(sources)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sources": sources,
        "crosswalk": build_crosswalk(sources),
    }


def fetch_text(session: requests.Session, url: str, *, timeout: int) -> str:
    assert_official_url(url)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return str(response.text)


def fetch_json(session: requests.Session, url: str, *, timeout: int) -> Dict[str, Any]:
    assert_official_url(url)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def assert_official_url(url: str) -> None:
    parsed = urlparse(url)
    allowed = {
        ("https", "www.shidianguji.com"),
        ("https", "open.cnkgraph.com"),
    }
    if (parsed.scheme, parsed.netloc) not in allowed:
        raise ValueError(f"refusing non-official URL: {url}")


def write_index(index: Mapping[str, Any], output_path: Path, *, pretty: bool) -> None:
    if output_path.suffix in {".sqlite", ".db"}:
        write_sqlite_index(index, output_path)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(index, file, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
        file.write("\n")


def write_sqlite_index(index: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    conn = sqlite3.connect(output_path)
    try:
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        create_sqlite_schema(conn)
        sources = index.get("sources") if isinstance(index.get("sources"), Mapping) else {}
        shidian_books = (sources.get("shidian") or {}).get("books", []) if isinstance(sources, Mapping) else []
        cnkgraph_books = (sources.get("cnkgraph") or {}).get("books", []) if isinstance(sources, Mapping) else []

        shidian_rows = {}
        for book in shidian_books:
            if not isinstance(book, Mapping) or not book.get("url"):
                continue
            canonical_url = canonical_shidian_book_url(str(book.get("url") or ""))
            title = str(book.get("title") or "")
            existing = shidian_rows.get(canonical_url)
            if existing and len(str(existing[0])) <= len(title):
                continue
            shidian_rows[canonical_url] = (
                title,
                book.get("normalized_title") or normalize_title(title),
                canonical_url,
                book.get("book_id") or canonical_url.rstrip("/").rsplit("/", 1)[-1],
            )
        conn.executemany(
            """
            INSERT INTO shidian_books(title, normalized_title, url, book_id)
            VALUES (?, ?, ?, ?)
            """,
            list(shidian_rows.values()),
        )
        conn.executemany(
            """
            INSERT INTO cnkgraph_books(id, title, normalized_title, author, dynasty, api_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    book.get("id"),
                    book.get("title"),
                    book.get("normalized_title"),
                    book.get("author"),
                    book.get("dynasty"),
                    book.get("api_url"),
                )
                for book in cnkgraph_books
                if isinstance(book, Mapping) and book.get("id")
            ],
        )

        crosswalk = index.get("crosswalk") if isinstance(index.get("crosswalk"), Mapping) else {}
        entries = crosswalk.get("entries", []) if isinstance(crosswalk, Mapping) else []
        conn.executemany(
            "INSERT INTO crosswalk(normalized_title, match_type, titles_json) VALUES (?, ?, ?)",
            [
                (
                    entry.get("normalized_title"),
                    entry.get("match_type"),
                    json.dumps(entry.get("titles") or [], ensure_ascii=False, separators=(",", ":")),
                )
                for entry in entries
                if isinstance(entry, Mapping) and entry.get("normalized_title")
            ],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO crosswalk_shidian(normalized_title, shidian_url) VALUES (?, ?)",
            [
                (entry.get("normalized_title"), canonical_shidian_book_url(str(book.get("url") or "")))
                for entry in entries
                if isinstance(entry, Mapping)
                for book in (entry.get("shidian") or [])
                if isinstance(book, Mapping) and book.get("url")
            ],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO crosswalk_cnkgraph(normalized_title, cnkgraph_id) VALUES (?, ?)",
            [
                (entry.get("normalized_title"), str(book.get("id")))
                for entry in entries
                if isinstance(entry, Mapping)
                for book in (entry.get("cnkgraph") or [])
                if isinstance(book, Mapping) and book.get("id") is not None
            ],
        )

        metadata = {
            "schema_version": str(index.get("schema_version") or 1),
            "generated_at": str(index.get("generated_at") or ""),
            "shidian_book_count": str(len(shidian_rows)),
            "cnkgraph_book_count": str(len([book for book in cnkgraph_books if isinstance(book, Mapping)])),
            "crosswalk_entry_count": str(crosswalk.get("entry_count") or len(entries)),
            "crosswalk_strategy": str(crosswalk.get("strategy") or ""),
        }
        conn.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()


def create_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE shidian_books (
            url TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            book_id TEXT
        );
        CREATE INDEX idx_shidian_books_normalized_title ON shidian_books(normalized_title);

        CREATE TABLE cnkgraph_books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            author TEXT,
            dynasty TEXT,
            api_url TEXT NOT NULL
        );
        CREATE INDEX idx_cnkgraph_books_normalized_title ON cnkgraph_books(normalized_title);

        CREATE TABLE crosswalk (
            normalized_title TEXT PRIMARY KEY,
            match_type TEXT NOT NULL,
            titles_json TEXT
        );
        CREATE TABLE crosswalk_shidian (
            normalized_title TEXT NOT NULL,
            shidian_url TEXT NOT NULL,
            PRIMARY KEY (normalized_title, shidian_url)
        );
        CREATE INDEX idx_crosswalk_shidian_url ON crosswalk_shidian(shidian_url);
        CREATE TABLE crosswalk_cnkgraph (
            normalized_title TEXT NOT NULL,
            cnkgraph_id TEXT NOT NULL,
            PRIMARY KEY (normalized_title, cnkgraph_id)
        );
        CREATE INDEX idx_crosswalk_cnkgraph_id ON crosswalk_cnkgraph(cnkgraph_id);
        """
    )


def canonical_shidian_book_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc == "www.shidianguji.com":
        match = re.match(r"^(/(?:zh/)?book/[^/?#]+)", parsed.path)
        if match:
            return f"https://www.shidianguji.com{match.group(1)}".replace("/zh/book/", "/book/", 1).rstrip("/")
    return url.replace("/zh/book/", "/book/", 1).rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description="刷新识典/cnkgraph 书名链接索引")
    parser.add_argument("--output", type=Path, default=DEFAULT_INDEX_PATH, help="输出路径（默认 SQLite；.json 后缀则输出 JSON）")
    parser.add_argument("--input-json", type=Path, help="从已有 JSON sources 迁移/重建索引")
    parser.add_argument("--source", choices=("all", "shidian", "cnkgraph"), default="all", help="刷新哪个来源")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP 超时时间（秒）")
    parser.add_argument("--sleep", type=float, default=0.05, help="请求间隔（秒）")
    parser.add_argument("--max-shidian-pages", type=int, help="调试用：最多抓取多少个识典 sitemap 页面")
    parser.add_argument("--pretty", action="store_true", help="用缩进格式输出 JSON")
    parser.add_argument("--merge-existing", action="store_true", help="分源刷新时保留输出文件中的其他来源")
    parser.add_argument("--from-existing", action="store_true", help="不联网，使用输出文件中已有 sources 重建 normalized_title 和 crosswalk")
    parser.add_argument("--verbose", action="store_true", help="输出抓取进度到 stderr")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    if args.sleep < 0:
        parser.error("--sleep 不能为负数")
    if args.max_shidian_pages is not None and args.max_shidian_pages <= 0:
        parser.error("--max-shidian-pages 必须大于 0")
    if args.from_existing and not args.output.exists() and not args.input_json:
        parser.error("--from-existing 需要已有输出文件或 --input-json")

    index = build_index(args)
    write_index(index, args.output, pretty=args.pretty)
    counts = {
        source: payload.get("book_count")
        for source, payload in index.get("sources", {}).items()
        if isinstance(payload, Mapping)
    }
    print(json.dumps({"output": str(args.output), "counts": counts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
