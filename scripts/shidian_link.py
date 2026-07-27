#!/usr/bin/env python3
"""Build Shidian Guji search URLs for manual source verification."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import quote

SEARCH_BASE = "https://www.shidianguji.com/search"


def build_search_url(keyword: str) -> str:
    return f"{SEARCH_BASE}/{quote(keyword, safe='')}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a Shidian search URL for manual citation verification."
    )
    parser.add_argument("--source", default="", help="Source citation (book + chapter)")
    parser.add_argument("--quote", default="", help="Original text excerpt to search for")
    parser.add_argument("--keyword", default="", help="Search keyword (preferred)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    search_term = (args.keyword or args.quote or args.source).strip()
    if not search_term:
        if args.json:
            print(json.dumps({"status": "error", "reason": "no search term provided"}, ensure_ascii=False))
        else:
            print("Error: provide --keyword, --quote, or --source", file=sys.stderr)
        sys.exit(1)

    url = build_search_url(search_term)
    result = {
        "status": "search_link_generated",
        "url": url,
        "search_term": search_term,
        "verification": "manual_required",
        "verified": False,
        "note": "Search URL generation does not verify that Shidian contains or attributes the passage correctly.",
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(url)


if __name__ == "__main__":
    main()
