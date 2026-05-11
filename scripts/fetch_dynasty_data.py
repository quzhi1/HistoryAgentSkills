#!/usr/bin/env python3
"""Download and normalize Shanghai Library Chinese dynasty chronology data."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import requests


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "dynasty"
RAW_DIR = DATA_DIR / "raw"
INDEX_PATH = DATA_DIR / "dynasty_index.json"
METADATA_PATH = DATA_DIR / "metadata.json"

SOURCE_URL = "https://data.library.sh.cn/dynasty/main"
SEARCH_URL = "https://data.library.sh.cn/dynasty/search"
SOURCE_CREDIT = "上海图书馆开放数据平台：中国历史纪年表（https://data.library.sh.cn/dynasty/main）"
SOURCE_LICENSE = "非特别注明，上海图书馆开放数据平台遵循 CC2.0：署名-非商业性使用-相同方式共享。"
TIMEOUT = 30

RDF_KEYS = {
    "label": "http://bibframe.org/vocab/label",
    "begin": "http://www.library.sh.cn/ontology/beginYear",
    "end": "http://www.library.sh.cn/ontology/endYear",
    "dynasty": "http://www.library.sh.cn/ontology/dynasty",
    "reignTitle": "http://www.library.sh.cn/ontology/reignTitle",
    "monarch": "http://www.library.sh.cn/ontology/monarch",
    "monarchName": "http://www.library.sh.cn/ontology/monarchName",
}


class DynastyDataError(RuntimeError):
    """Raised when remote or local dynasty data is malformed."""


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_year(value: Any) -> Optional[int]:
    if value in (None, "", "NON"):
        return None
    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise DynastyDataError(f"Invalid year value: {value!r}") from exc


def split_reign_titles(value: str) -> List[str]:
    """Split semicolon-delimited reign title aliases and drop placeholders."""
    if not value or value == "NON":
        return []
    titles: List[str] = []
    for part in value.replace("；", ";").split(";"):
        title = part.strip()
        if title and title != "NON" and title not in titles:
            titles.append(title)
    return titles


def _rdf_value(rdf_data: Mapping[str, Any], uri: str, field: str) -> str:
    if isinstance(rdf_data.get("rdfs"), list):
        for triple in rdf_data["rdfs"]:
            if (
                isinstance(triple, Mapping)
                and triple.get("s") == uri
                and triple.get("p") == RDF_KEYS[field]
            ):
                return str(triple.get("o", "")).strip()
        return ""

    subject = rdf_data.get(uri)
    if not isinstance(subject, Mapping):
        return ""
    values = subject.get(RDF_KEYS[field], [])
    if not values:
        return ""
    first = values[0]
    if isinstance(first, Mapping):
        return str(first.get("value", "")).strip()
    return ""


def _raw_filename(uri: str) -> str:
    identifier = uri.rstrip("/").rsplit("/", 1)[-1]
    if not identifier:
        raise DynastyDataError(f"Cannot derive raw filename from URI: {uri!r}")
    return f"{identifier}.json"


def _require_fields(item: Mapping[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if field not in item]
    if missing:
        raise DynastyDataError(f"Dynasty search item missing fields {missing}: {item!r}")


def normalize_item(item: Mapping[str, Any], rdf_data: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Normalize one /dynasty/search row plus optional RDF JSON."""
    _require_fields(item, ["dynasty", "reignTitle", "monarch", "monarchName", "begin", "end", "uri"])
    uri = str(item["uri"]).strip()
    if not uri:
        raise DynastyDataError(f"Dynasty item has empty URI: {item!r}")

    rdf_data = rdf_data or {}

    def choose(field: str) -> str:
        value = str(item.get(field, "") or "").strip()
        if value and value != "NON":
            return value
        return _rdf_value(rdf_data, uri, field)

    dynasty = choose("dynasty")
    reign_title = choose("reignTitle")
    monarch = choose("monarch")
    monarch_name = choose("monarchName")
    begin = _parse_year(choose("begin") or item.get("begin"))
    end = _parse_year(choose("end") or item.get("end"))

    if begin is None:
        raise DynastyDataError(f"Dynasty item has no begin year: {item!r}")

    return {
        "dynasty": dynasty,
        "reignTitle": reign_title,
        "reignTitles": split_reign_titles(reign_title),
        "monarch": monarch,
        "monarchName": monarch_name,
        "begin": begin,
        "end": end,
        "uri": uri,
        "raw_json": f"raw/{_raw_filename(uri)}",
    }


def fetch_search_rows(session: requests.Session, page_size: int = 1000) -> List[Dict[str, Any]]:
    """Fetch all rows from the Shanghai Library chronology search endpoint."""
    rows: List[Dict[str, Any]] = []
    seen = set()
    page = 1
    page_count = 1

    while page <= page_count:
        response = session.post(
            SEARCH_URL,
            data={"pageth": str(page), "iflimit": "1", "pageSize": str(page_size), "firstChar": "全部"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise DynastyDataError("Search endpoint returned a non-object payload")
        detail = payload.get("detail")
        pager = payload.get("pager", {})
        if not isinstance(detail, list):
            raise DynastyDataError("Search endpoint payload missing detail list")
        if isinstance(pager, Mapping):
            page_count = int(pager.get("pageCount", page_count))

        for item in detail:
            if not isinstance(item, Mapping):
                raise DynastyDataError(f"Search endpoint item is not an object: {item!r}")
            uri = str(item.get("uri", "")).strip()
            if not uri or uri in seen:
                continue
            rows.append(dict(item))
            seen.add(uri)

        page += 1

    return rows


def fetch_raw_json(session: requests.Session, uri: str) -> Dict[str, Any]:
    """Fetch one RDF JSON document for a chronology entity URI."""
    last_error: Optional[BaseException] = None
    for attempt in range(1, 4):
        try:
            response = session.get(f"{uri}.json", timeout=TIMEOUT, allow_redirects=True)
            if response.status_code == 403:
                # A small number of authority IDs trip the site's WAF when placed in
                # the path. The page itself retrieves the same RDF through this form
                # endpoint, so use it as a transparent fallback.
                response = session.post(
                    "https://data.library.sh.cn/dynasty/getRdf",
                    data={"dataUri": uri},
                    timeout=TIMEOUT,
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise DynastyDataError(f"Raw JSON for {uri} is not an object")
            return dict(payload)
        except (requests.RequestException, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(0.8 * attempt)
    raise DynastyDataError(f"Failed to fetch raw JSON for {uri}: {last_error}") from last_error


def _fetch_normalized_entry(position: int, item: Mapping[str, Any]) -> Dict[str, Any]:
    uri = str(item["uri"]).strip()
    raw_path = RAW_DIR / _raw_filename(uri)
    if raw_path.exists():
        try:
            raw = _read_json(raw_path)
        except (OSError, json.JSONDecodeError):
            with requests.Session() as session:
                raw = fetch_raw_json(session, uri)
            _write_json(raw_path, raw)
    else:
        with requests.Session() as session:
            raw = fetch_raw_json(session, uri)
        _write_json(raw_path, raw)
    entry = normalize_item(item, raw)
    entry["position"] = position
    return entry


def build_dataset(rebuild: bool = False, page_size: int = 1000, workers: int = 12, progress: bool = False) -> Dict[str, Any]:
    """Download raw chronology JSON files and write the normalized index."""
    if rebuild and DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    rows = fetch_search_rows(session, page_size=page_size)
    normalized: List[Dict[str, Any]] = []

    worker_count = max(1, workers)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_fetch_normalized_entry, position, item): position
            for position, item in enumerate(rows, 1)
        }
        completed = 0
        for future in as_completed(futures):
            normalized.append(future.result())
            completed += 1
            if progress and (completed == len(rows) or completed % 50 == 0):
                print(f"已下载 {completed}/{len(rows)} 条 RDF JSON", flush=True)

    normalized.sort(key=lambda entry: entry["position"])

    metadata = {
        "source_url": SOURCE_URL,
        "search_url": SEARCH_URL,
        "source_credit": SOURCE_CREDIT,
        "source_license": SOURCE_LICENSE,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "raw_count": len(list(RAW_DIR.glob("*.json"))),
        "index_count": len(normalized),
    }

    _write_json(INDEX_PATH, normalized)
    _write_json(METADATA_PATH, metadata)
    return metadata


def load_index() -> List[Dict[str, Any]]:
    if not INDEX_PATH.exists():
        raise DynastyDataError(
            f"Missing dynasty index: {INDEX_PATH}. Run `venv/bin/python scripts/fetch_dynasty_data.py --rebuild`."
        )
    data = _read_json(INDEX_PATH)
    if not isinstance(data, list):
        raise DynastyDataError(f"Dynasty index is not a list: {INDEX_PATH}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download Shanghai Library Chinese dynasty chronology JSON data."
    )
    parser.add_argument("--rebuild", action="store_true", help="Delete existing downloaded chronology data first.")
    parser.add_argument("--page-size", type=int, default=1000, help="Page size for /dynasty/search.")
    parser.add_argument("--workers", type=int, default=12, help="Concurrent workers for raw RDF JSON downloads.")
    args = parser.parse_args()

    try:
        metadata = build_dataset(rebuild=args.rebuild, page_size=args.page_size, workers=args.workers, progress=True)
    except (requests.RequestException, DynastyDataError, json.JSONDecodeError) as exc:
        print(f"下载失败: {exc}")
        return 1

    print("上海图书馆中国历史纪年表数据下载完成")
    print(f"Index: {INDEX_PATH}")
    print(f"Raw JSON files: {metadata['raw_count']}")
    print(f"Normalized entries: {metadata['index_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
