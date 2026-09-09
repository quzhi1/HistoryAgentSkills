#!/usr/bin/env python3
"""把一段文字渲染成小红书图文卡片（1080×1440，3:4 竖版）。

用法：
    venv/bin/python scripts/xhs_cards.py cards.json --outdir outputs/xhs/某段子

输入 JSON 结构见 xiaohongshu-cards/SKILL.md。渲染靠本机 Chrome 无头截图，
不引入 Node / Playwright / Pillow 等任何新依赖。
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 小红书规范：3:4 竖版，一篇笔记最多 18 张，且必须统一比例。
WIDTH, HEIGHT = 1080, 1440
MAX_CARDS = 18

# 安全区：上方被头像昵称压住、下方被点赞收藏栏压住、左右可能被整屏裁切。
PAD_TOP, PAD_BOTTOM, PAD_SIDE = 160, 210, 88

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "chromium",
]

# 小红书通行做法：每张 ≤150 字、字号往大了给，而不是塞满小字。
# ponytail: 用字数估算是否溢出，只警告不自动分页。真需要自动分页再换成
# Chrome --dump-dom 读 scrollHeight。
BUDGET = {"cover": 40, "body": 150, "quote": 170}

CSS = f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {WIDTH}px; height: {HEIGHT}px; overflow: hidden; }}
body {{
  background: #F7F3EA;
  color: #1F1B16;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
}}
.card {{
  width: {WIDTH}px; height: {HEIGHT}px;
  padding: {PAD_TOP}px {PAD_SIDE}px {PAD_BOTTOM}px;
  display: flex; flex-direction: column;
}}
.main {{ flex: 1; min-height: 0; display: flex; flex-direction: column; }}
.main.center {{ justify-content: center; }}
.main.cover {{ justify-content: center; padding-bottom: 150px; }}
.eyebrow {{
  font-size: 32px; letter-spacing: .22em; color: #9E2B25;
  font-weight: 600; margin-bottom: 52px;
}}
.title {{
  font-family: "Songti SC", "STSong", serif;
  font-size: 128px; line-height: 1.26; font-weight: 700;
  letter-spacing: .02em; white-space: pre-line;
}}
.sub {{
  margin-top: 56px; font-size: 54px; line-height: 1.58;
  color: #5A5148; white-space: pre-line;
}}
.heading {{
  font-family: "Songti SC", "STSong", serif;
  font-size: 68px; font-weight: 700; line-height: 1.3;
  margin-bottom: 52px; padding-left: 28px; border-left: 10px solid #9E2B25;
}}
.body-text {{ font-size: 52px; line-height: 1.76; }}
.body-text p + p {{ margin-top: 38px; }}
.quote-text {{
  font-family: "Songti SC", "STSong", serif;
  font-size: 48px; line-height: 1.8; color: #2A241C;
}}
.quote-text p + p {{ margin-top: 32px; }}
em {{
  font-style: normal; font-weight: 600; color: #9E2B25;
  background: linear-gradient(transparent 60%, #EDD9BE 60%);
}}
.note {{ margin-top: 48px; font-size: 34px; line-height: 1.65; color: #6B6055; }}
.footer {{
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 32px; color: #8A7F72; letter-spacing: .06em;
  border-top: 2px solid #D8CEBB; padding-top: 30px;
}}
"""


def _inline(text):
    """转义后再把 **重点** 变成朱红标注。"""
    return re.sub(r"\*\*(.+?)\*\*", r"<em>\1</em>", html.escape(str(text)))


def _paras(text):
    out = []
    for block in str(text).split("\n\n"):
        block = block.strip()
        if block:
            out.append("<p>" + _inline(block).replace("\n", "<br>") + "</p>")
    return "".join(out)


def render_html(card, idx, total, footer_left):
    kind = card.get("kind", "body")
    foot_right = f"{idx}/{total}"
    if kind == "cover":
        inner = (
            f'<div class="eyebrow">{html.escape(card.get("eyebrow", ""))}</div>'
            f'<div class="title">{html.escape(card.get("title", ""))}</div>'
            f'<div class="sub">{_inline(card.get("sub", ""))}</div>'
        )
        wrap = "main cover"
    else:
        cls = "quote-text" if kind == "quote" else "body-text"
        head = card.get("heading", "")
        note = card.get("note", "")
        inner = (
            (f'<div class="heading">{html.escape(head)}</div>' if head else "")
            + f'<div class="{cls}">{_paras(card.get("text", ""))}</div>'
            + (f'<div class="note">{html.escape(note)}</div>' if note else "")
        )
        wrap = "main center"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body><div class='card'>"
        f"<div class='{wrap}'>{inner}</div>"
        f'<div class="footer"><span>{html.escape(footer_left)}</span>'
        f"<span>{foot_right}</span></div></div></body></html>"
    )


def over_budget(card):
    """返回超出的字数（0 表示没超）。只是估算，见上方 ponytail 注释。"""
    kind = card.get("kind", "body")
    n = len(card.get("title", "")) + len(card.get("sub", ""))
    n += len(card.get("heading", "")) * 2  # 标题字号大，按两倍占位算
    n += len(card.get("text", "")) + len(card.get("note", ""))
    return max(0, n - BUDGET.get(kind, BUDGET["body"]))


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成小红书 1080×1440 图文卡片")
    ap.add_argument("cards_json", nargs="?", help="卡片 JSON；省略则读 stdin")
    ap.add_argument("--outdir", required=True, help="PNG 输出目录")
    ap.add_argument("--html-only", action="store_true", help="只出 HTML，不调 Chrome")
    ap.add_argument("--selftest", action="store_true", help="跑自检后退出")
    args = ap.parse_args(argv)

    if args.selftest:
        assert over_budget({"kind": "body", "text": "字" * 100}) == 0
        assert over_budget({"kind": "body", "text": "字" * 300}) == 150
        h = render_html({"kind": "cover", "title": "甲\n乙"}, 1, 3, "出处")
        assert "1/3" in h and "1080px" in h and "甲\n乙" in h
        h2 = render_html({"kind": "body", "text": "一段\n\n两段"}, 2, 3, "x")
        assert h2.count("<p>") == 2 and "main center" in h2
        assert "<em>重点</em>" in render_html(
            {"kind": "body", "text": "**重点**"}, 1, 1, "")
        assert "&lt;script&gt;" in render_html({"kind": "body", "text": "<script>"}, 1, 1, "")
        print("selftest ok")
        return 0

    raw = Path(args.cards_json).read_text("utf-8") if args.cards_json else sys.stdin.read()
    doc = json.loads(raw)
    cards = doc["cards"]
    if len(cards) > MAX_CARDS:
        sys.exit(f"小红书一篇最多 {MAX_CARDS} 张，当前 {len(cards)} 张")
    footer_left = doc.get("footer", "")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for i, card in enumerate(cards, 1):
        over = over_budget(card)
        if over:
            print(f"  ⚠ 第 {i} 张约超出 {over} 字，可能顶到安全区外，建议拆卡", file=sys.stderr)

    chrome = None if args.html_only else find_chrome()
    if not args.html_only and not chrome:
        sys.exit("没找到 Chrome/Chromium/Edge，可用 --html-only 只出 HTML")

    written = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, card in enumerate(cards, 1):
            name = f"{i:02d}-{card.get('kind', 'body')}"
            page = render_html(card, i, len(cards), footer_left)
            html_path = (outdir if args.html_only else Path(tmp)) / f"{name}.html"
            html_path.write_text(page, "utf-8")
            if args.html_only:
                written.append(html_path)
                continue
            png = outdir / f"{name}.png"
            subprocess.run(
                [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                 f"--screenshot={png}", f"--window-size={WIDTH},{HEIGHT}",
                 "--virtual-time-budget=3000", html_path.as_uri()],
                check=True, capture_output=True,
            )
            written.append(png)

    for p in written:
        print(p)
    print(f"\n共 {len(written)} 张，都在：{outdir.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
