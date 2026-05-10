#!/usr/bin/env python3
"""Full-text search for local EPUB books about Chinese historical sources."""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
CACHE_DIR = ROOT / ".cache"
INDEX_PATH = CACHE_DIR / "book_search.sqlite3"
GUIDANCE_NOTE = "检索结果只用于判断史料搜集方向；最终史实仍需辞典与 cnkgraph 原文核验。"

CONTAINER_NS = {"ocf": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NS = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
XHTML_MEDIA_TYPES = {"application/xhtml+xml", "text/html"}


class BookSearchError(RuntimeError):
    """Raised when EPUB indexing or searching fails."""


class TextExtractor(HTMLParser):
    """Minimal HTML/XHTML text extractor based on the Python standard library."""

    BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
    HEADING_TAGS = {"h1", "h2", "h3"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.heading_parts: List[str] = []
        self._capture_heading = False
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._ignore_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag in self.HEADING_TAGS and not self.heading_parts:
            self._capture_heading = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self._ignore_depth:
            self._ignore_depth -= 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag in self.HEADING_TAGS:
            self._capture_heading = False

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        text = html.unescape(data)
        self.parts.append(text)
        if self._capture_heading:
            self.heading_parts.append(text)

    def text(self) -> str:
        lines = []
        for line in "".join(self.parts).splitlines():
            clean = re.sub(r"\s+", " ", line).strip()
            if clean:
                lines.append(clean)
        return "\n".join(lines)

    def heading(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.heading_parts)).strip()


def _book_files() -> List[Path]:
    if not BOOKS_DIR.exists():
        raise BookSearchError(f"books directory not found: {BOOKS_DIR}")
    files = sorted(BOOKS_DIR.glob("*.epub"))
    if not files:
        raise BookSearchError(f"No EPUB files found in {BOOKS_DIR}")
    return files


def _fingerprint(files: Iterable[Path]) -> str:
    parts = []
    for path in files:
        stat = path.stat()
        parts.append(f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}")
    return "|".join(parts)


def _rootfile_path(zf: zipfile.ZipFile) -> PurePosixPath:
    try:
        container = zf.read("META-INF/container.xml")
    except KeyError as exc:
        raise BookSearchError("EPUB missing META-INF/container.xml") from exc
    root = ET.fromstring(container)
    rootfile = root.find(".//ocf:rootfile", CONTAINER_NS)
    if rootfile is None:
        raise BookSearchError("EPUB container has no rootfile")
    full_path = rootfile.attrib.get("full-path")
    if not full_path:
        raise BookSearchError("EPUB rootfile missing full-path")
    return PurePosixPath(full_path)


def _metadata_text(opf_root: ET.Element, name: str) -> str:
    node = opf_root.find(f".//dc:{name}", OPF_NS)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _spine_hrefs(opf_root: ET.Element) -> List[str]:
    manifest: Dict[str, Tuple[str, str]] = {}
    for item in opf_root.findall(".//opf:manifest/opf:item", OPF_NS):
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        media_type = item.attrib.get("media-type", "")
        if item_id and href:
            manifest[item_id] = (href, media_type)

    hrefs: List[str] = []
    for itemref in opf_root.findall(".//opf:spine/opf:itemref", OPF_NS):
        idref = itemref.attrib.get("idref")
        if not idref or idref not in manifest:
            continue
        href, media_type = manifest[idref]
        if media_type in XHTML_MEDIA_TYPES:
            hrefs.append(href)
    return hrefs


def _clean_zip_path(opf_path: PurePosixPath, href: str) -> str:
    return str(opf_path.parent.joinpath(PurePosixPath(href))).replace("\\", "/").lstrip("./")


def iter_epub_documents(epub_path: Path) -> Iterable[Dict[str, str]]:
    """Yield text documents from an EPUB spine."""
    with zipfile.ZipFile(epub_path) as zf:
        opf_path = _rootfile_path(zf)
        opf_root = ET.fromstring(zf.read(str(opf_path)))
        title = _metadata_text(opf_root, "title") or epub_path.stem
        author = _metadata_text(opf_root, "creator")

        for href in _spine_hrefs(opf_root):
            zip_path = _clean_zip_path(opf_path, href)
            try:
                raw = zf.read(zip_path)
            except KeyError:
                continue
            text_source = raw.decode("utf-8", errors="replace")
            extractor = TextExtractor()
            extractor.feed(text_source)
            body_text = extractor.text()
            if not body_text:
                continue
            yield {
                "book_path": str(epub_path.relative_to(ROOT)),
                "book_title": title,
                "author": author,
                "href": zip_path,
                "section": extractor.heading() or zip_path,
                "text": body_text,
            }


def _connect() -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(INDEX_PATH)
    con.row_factory = sqlite3.Row
    return con


def _create_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        DROP TABLE IF EXISTS meta;
        DROP TABLE IF EXISTS passages;
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE VIRTUAL TABLE passages USING fts5(
            book_path UNINDEXED,
            book_title,
            author,
            href UNINDEXED,
            section,
            text,
            tokenize='trigram'
        );
        """
    )


def build_index(rebuild: bool = False) -> Dict[str, Any]:
    """Build or reuse the local SQLite FTS index."""
    books = _book_files()
    fingerprint = _fingerprint(books)
    if rebuild and INDEX_PATH.exists():
        INDEX_PATH.unlink()

    if INDEX_PATH.exists():
        try:
            with _connect() as con:
                row = con.execute("SELECT value FROM meta WHERE key = 'fingerprint'").fetchone()
                count = con.execute("SELECT count(*) AS count FROM passages").fetchone()["count"]
                if row and row["value"] == fingerprint and count:
                    return {"index_path": str(INDEX_PATH), "documents": count, "rebuilt": False}
        except sqlite3.DatabaseError:
            INDEX_PATH.unlink(missing_ok=True)

    with _connect() as con:
        _create_schema(con)
        inserted = 0
        for book in books:
            for doc in iter_epub_documents(book):
                con.execute(
                    """
                    INSERT INTO passages (book_path, book_title, author, href, section, text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc["book_path"],
                        doc["book_title"],
                        doc["author"],
                        doc["href"],
                        doc["section"],
                        doc["text"],
                    ),
                )
                inserted += 1
        con.execute("INSERT INTO meta (key, value) VALUES ('fingerprint', ?)", (fingerprint,))
        con.execute("INSERT INTO meta (key, value) VALUES ('guidance_note', ?)", (GUIDANCE_NOTE,))
        con.commit()
    return {"index_path": str(INDEX_PATH), "documents": inserted, "rebuilt": True}


def _snippet(text: str, query: str, radius: int = 70) -> str:
    position = text.find(query)
    if position < 0:
        return text[: radius * 2].replace("\n", " ")
    start = max(0, position - radius)
    end = min(len(text), position + len(query) + radius)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return (prefix + text[start:end] + suffix).replace("\n", " ")


def _like_search(con: sqlite3.Connection, query: str, limit: int) -> List[Dict[str, Any]]:
    rows = con.execute(
        """
        SELECT rowid, book_path, book_title, author, href, section, text
        FROM passages
        WHERE text LIKE ?
        LIMIT ?
        """,
        (f"%{query}%", limit),
    ).fetchall()
    return [
        {
            "book_path": row["book_path"],
            "book_title": row["book_title"],
            "author": row["author"],
            "href": row["href"],
            "section": row["section"],
            "snippet": _snippet(row["text"], query),
            "guidance_note": GUIDANCE_NOTE,
        }
        for row in rows
    ]


def search_books(query: str, limit: int = 5, rebuild: bool = False) -> List[Dict[str, Any]]:
    """Search indexed EPUB text and return source-direction snippets."""
    clean_query = query.strip()
    if not clean_query:
        raise BookSearchError("查询词不能为空")
    if limit < 1:
        raise BookSearchError("limit 必须大于 0")

    build_index(rebuild=rebuild)
    with _connect() as con:
        if len(clean_query) < 3:
            return _like_search(con, clean_query, limit)
        fts_query = '"' + clean_query.replace('"', '""') + '"'
        try:
            rows = con.execute(
                """
                SELECT book_path, book_title, author, href, section,
                       snippet(passages, 5, '[', ']', '...', 70) AS snippet,
                       bm25(passages) AS rank
                FROM passages
                WHERE passages MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return _like_search(con, clean_query, limit)
        if not rows:
            return _like_search(con, clean_query, limit)
        return [
            {
                "book_path": row["book_path"],
                "book_title": row["book_title"],
                "author": row["author"],
                "href": row["href"],
                "section": row["section"],
                "snippet": re.sub(r"\s+", " ", row["snippet"]).strip(),
                "guidance_note": GUIDANCE_NOTE,
            }
            for row in rows
        ]


def _print_human(query: str, results: Sequence[Mapping[str, Any]]) -> None:
    print(f"EPUB 检索：{query}")
    print(GUIDANCE_NOTE)
    if not results:
        print("未找到匹配片段。")
        return
    for idx, item in enumerate(results, 1):
        author = f" / {item['author']}" if item.get("author") else ""
        print(f"\n【{idx}】{item['book_title']}{author}")
        print(f"章节：{item['section']}")
        print(f"位置：{item['book_path']}#{item['href']}")
        print(f"片段：{item['snippet']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search local EPUB books in books/ for source-collection guidance. "
            + GUIDANCE_NOTE
        )
    )
    parser.add_argument("query", help="Search keyword or phrase.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of snippets.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the local SQLite FTS index first.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    args = parser.parse_args()

    try:
        results = search_books(args.query, limit=args.limit, rebuild=args.rebuild)
    except (BookSearchError, sqlite3.DatabaseError, zipfile.BadZipFile, ET.ParseError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "index_path": str(INDEX_PATH)}, ensure_ascii=False, indent=2))
        else:
            print(f"EPUB 检索失败: {exc}")
        return 1

    if args.json:
        print(json.dumps({"query": args.query, "results": results, "guidance_note": GUIDANCE_NOTE}, ensure_ascii=False, indent=2))
    else:
        _print_human(args.query, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
