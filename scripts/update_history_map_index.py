#!/usr/bin/env python3
"""Refresh the compact left-map/right-history route index."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlencode, urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "history_map_index.json"
BASE_URL = "https://history-map.osgeo.cn/"
TIMEOUT = 30
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HistoryAgentSkills/1.0; +https://history-map.osgeo.cn/)",
    "Accept": "text/html,application/javascript,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
}
APP_JS_PATTERN = re.compile(r'src="(?P<src>/assets/index\.[^"]+\.js)"')
DATA_JS_PATTERN = re.compile(r'assets/xx_all_html_data\.[A-Za-z0-9]+\.js')
PAGE_LABEL_PATTERN = re.compile(r'(?P<page>page\d+):\{to:"/page\d+",label:"(?P<label>(?:\\.|[^"])*)",tab_list:')
ROUTE_PATTERN = re.compile(
    r'to:\{query:\{ch:"(?P<ch>[^"]+)",sec:"(?P<sec>[^"]+)"\},path:"(?P<path>/page\d+/html)"\},label:"(?P<label>(?:\\.|[^"])*)"'
)


class HistoryMapIndexError(ValueError):
    """Raised when the remote route index cannot be refreshed safely."""


def fetch_text(url: str) -> str:
    if not url.startswith("https://history-map.osgeo.cn/"):
        raise HistoryMapIndexError("只允许读取左图右史 HTTPS 官方域名")
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=REQUEST_HEADERS)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise HistoryMapIndexError(f"请求超时: {url}") from exc
    except requests.exceptions.RequestException as exc:
        raise HistoryMapIndexError(f"请求失败: {url}: {exc}") from exc
    return response.text


def discover_data_asset() -> str:
    home = fetch_text(BASE_URL)
    app_match = APP_JS_PATTERN.search(home)
    if not app_match:
        raise HistoryMapIndexError("未能在首页发现 index JS")
    app_js = fetch_text(urljoin(BASE_URL, app_match.group("src")))
    data_match = DATA_JS_PATTERN.search(app_js)
    if not data_match:
        raise HistoryMapIndexError("未能在 index JS 中发现地图数据 chunk")
    return urljoin(BASE_URL, data_match.group(0))


def build_index(data_js: str, source_asset: str) -> Dict[str, Any]:
    page_labels = {
        match.group("page"): decode_js_string(match.group("label"))
        for match in PAGE_LABEL_PATTERN.finditer(data_js)
    }
    entries: List[Dict[str, str]] = []
    seen = set()
    for match in ROUTE_PATTERN.finditer(data_js):
        path = match.group("path")
        page_match = re.search(r"/(page\d+)/", path)
        page = page_match.group(1) if page_match else ""
        ch = match.group("ch")
        sec = match.group("sec")
        key = (path, ch, sec)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "page": page,
                "period": page_labels.get(page, ""),
                "path": path,
                "ch": ch,
                "sec": sec,
                "label": decode_js_string(match.group("label")),
                "url": build_share_url(path, ch, sec),
            }
        )
    if not entries:
        raise HistoryMapIndexError("未能从地图数据 chunk 提取任何 route")
    return {
        "source": BASE_URL.rstrip("/"),
        "generated_from": source_asset.replace(BASE_URL.rstrip("/"), ""),
        "entries": entries,
    }


def decode_js_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except ValueError as exc:
        raise HistoryMapIndexError("地图数据中存在无法解析的 JS 字符串") from exc


def build_share_url(path: str, ch: str, sec: str) -> str:
    """Return the browser-shareable hash route used by the history-map SPA."""

    route = path if path.startswith("/") else f"/{path}"
    return f"{BASE_URL.rstrip('/')}/#{route}?{urlencode({'ch': ch, 'sec': sec})}"


def main() -> int:
    parser = argparse.ArgumentParser(description="刷新 data/history_map_index.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true", help="只打印索引 JSON，不写文件")
    args = parser.parse_args()

    asset_url = discover_data_asset()
    index = build_index(fetch_text(asset_url), asset_url)
    if args.json:
        print(json.dumps(index, ensure_ascii=False, indent=2))
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"已写入 {args.output}，共 {len(index['entries'])} 条 route")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
