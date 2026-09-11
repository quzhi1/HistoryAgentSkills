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
import random
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

SONG = '"Songti SC", "STSong", serif'
HEI = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
LAN = '"Lantinghei SC", "PingFang SC", sans-serif'
YUAN = '"Yuanti SC", "PingFang SC", sans-serif'
KAI = '"Kaiti SC", "STKaiti", serif'
LIBIAN = '"Libian SC", "Songti SC", serif'

# 每套主题 = 配色 + 字体 + 版式。默认每次随机换一套，避免所有帖子长一个样。
# scale 是整体字号倍率，每卡字数预算按 1/scale² 联动（面积固定，字大则字少）。
THEMES = {
    "xuan": dict(  # 宣纸暖白：经典款，左对齐宋体大标题
        bg="#F7F3EA", ink="#1F1B16", accent="#9E2B25", muted="#6B6055",
        rule="#D8CEBB", mark="#EDD9BE", title_font=SONG, body_font=HEI,
        quote_font=SONG, heading="rule-left", cover="left", cover_style="plain",
        deco="none", footer="rule", scale=1.00),
    "mo": dict(  # 墨夜：深底暖金，封面粗线压顶，页脚无框
        bg="#15171B", ink="#EDE8E0", accent="#E0A458", muted="#9A9186",
        rule="#33373E", mark="#4A3A22", title_font=SONG, body_font=SONG,
        quote_font=SONG, heading="rule-top", cover="center", cover_style="rule",
        deco="none", footer="bare", scale=1.00),
    "qing": dict(  # 青瓷：标题压在色块上反白，小标题徽章
        bg="#E9EFEA", ink="#17241F", accent="#2E6B57", muted="#5C6B64",
        rule="#BFCFC5", mark="#C8DCD0", title_font=LAN, body_font=HEI,
        quote_font=SONG, heading="badge", cover="left", cover_style="block",
        deco="none", footer="bare", scale=0.94),
    "zhu": dict(  # 朱白：冷白圆体，右上角色块，字号偏大
        bg="#FCFBF8", ink="#14110E", accent="#C8372A", muted="#6E675E",
        rule="#E3DDD2", mark="#F6D5CD", title_font=YUAN, body_font=HEI,
        quote_font=KAI, heading="underline", cover="center", cover_style="plain",
        deco="corner", footer="rule", scale=1.06),
    "lan": dict(  # 靛青：深蓝底，顶部色带，页码做成胶囊
        bg="#0F1A2B", ink="#E6ECF5", accent="#6FA8DC", muted="#94A3B8",
        rule="#26344A", mark="#24405F", title_font=HEI, body_font=HEI,
        quote_font=SONG, heading="rule-left", cover="left", cover_style="plain",
        deco="band", footer="pill", scale=0.98),
    "jian": dict(  # 简牍：土黄隶书，细边框
        bg="#EFE7D6", ink="#2B2418", accent="#7A5C2E", muted="#6D6350",
        rule="#CDBE9E", mark="#DFC99B", title_font=LIBIAN, body_font=HEI,
        quote_font=KAI, heading="rule-top", cover="center", cover_style="rule",
        deco="frame", footer="bare", scale=1.00),
}

# 基准预算按 xuan 主题（正文 52px、原文 48px）实测得来，其余主题按字号折算。
BUDGET_BASE = {"cover": 40, "body": 150, "quote": 170}

HEADING_CSS = {
    "rule-left": "padding-left: 28px; border-left: 10px solid {accent};",
    "rule-top": ("display: inline-block; padding-top: 26px;"
                 " border-top: 7px solid {accent};"),
    "underline": ("display: inline-block; padding-bottom: 10px;"
                  " box-shadow: inset 0 -16px 0 {mark};"),
    "badge": ("display: inline-block; background: {accent}; color: {bg};"
              " padding: 12px 30px 16px; border-radius: 8px;"),
}


# 卡面装饰。绝对定位盖到出血边，所以 .card 要 position: relative。
DECO_CSS = {
    "none": "",
    "band": (".card::before{{content:'';position:absolute;top:0;left:0;right:0;"
             "height:16px;background:{accent};}}"),
    "corner": (".card::before{{content:'';position:absolute;top:0;right:0;"
               "width:230px;height:230px;background:{mark};}}"),
    "frame": (".card::before{{content:'';position:absolute;top:44px;left:44px;"
              "right:44px;bottom:44px;border:3px solid {rule};}}"),
}

COVER_CSS = {
    "plain": "",
    "block": (".cover .title{{background:{accent};color:{bg};"
              "padding:26px 34px;width:fit-content;}}"),
    "rule": ".cover .title{{padding-top:42px;border-top:12px solid {accent};}}",
}

FOOTER_CSS = {
    "rule": "",
    "bare": ".footer{{border-top:none;opacity:.8;}}",
    "pill": (".footer span:last-child{{background:{accent};color:{bg};"
             "padding:8px 22px;border-radius:999px;}}"),
}


def css_for(t):
    s = t["scale"]
    px = lambda n: round(n * s)  # noqa: E731
    head = HEADING_CSS[t["heading"]].format(**t)
    align = "flex-start" if t["cover"] == "left" else "center"
    extra = "".join(d[t[k]].format(**t) for k, d in
                    (("deco", DECO_CSS), ("cover_style", COVER_CSS), ("footer", FOOTER_CSS)))
    return f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {WIDTH}px; height: {HEIGHT}px; overflow: hidden; }}
body {{
  background: {t['bg']};
  color: {t['ink']};
  font-family: {t['body_font']};
  -webkit-font-smoothing: antialiased;
}}
.card {{
  width: {WIDTH}px; height: {HEIGHT}px;
  padding: {PAD_TOP}px {PAD_SIDE}px {PAD_BOTTOM}px;
  display: flex; flex-direction: column; position: relative;
}}
.main, .footer {{ position: relative; z-index: 1; }}
.main {{
  flex: 1; min-height: 0; overflow: hidden;
  display: flex; flex-direction: column;
}}
.fit {{ width: 100%; }}
.main.center {{ justify-content: center; align-items: flex-start; }}
.main.cover {{
  justify-content: center; padding-bottom: 150px;
  align-items: {align}; text-align: {t['cover']};
}}
.eyebrow {{
  font-size: {px(32)}px; letter-spacing: .22em; color: {t['accent']};
  font-weight: 600; margin-bottom: {px(52)}px;
}}
.title {{
  font-family: {t['title_font']};
  font-size: {px(128)}px; line-height: 1.26; font-weight: 700;
  letter-spacing: .02em; white-space: pre-line;
}}
.sub {{
  margin-top: {px(56)}px; font-size: {px(54)}px; line-height: 1.58;
  color: {t['muted']}; white-space: pre-line;
}}
.heading {{
  font-family: {t['title_font']};
  font-size: {px(68)}px; font-weight: 700; line-height: 1.3;
  margin-bottom: {px(52)}px; {head}
}}
.body-text {{ font-size: {px(52)}px; line-height: 1.76; }}
.body-text p + p {{ margin-top: {px(38)}px; }}
.quote-text {{
  font-family: {t['quote_font']};
  font-size: {px(48)}px; line-height: 1.8;
}}
.quote-text p + p {{ margin-top: {px(32)}px; }}
em {{
  font-style: normal; font-weight: 600; color: {t['accent']};
  background: linear-gradient(transparent 60%, {t['mark']} 60%);
}}
.note {{
  margin-top: {px(48)}px; font-size: {px(34)}px; line-height: 1.65;
  color: {t['muted']};
}}
.footer {{
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: {px(32)}px; color: {t['muted']}; letter-spacing: .06em;
  border-top: 2px solid {t['rule']}; padding-top: {px(30)}px;
}}
{extra}
"""


# 字太多时整体缩到放得下为止。zoom 会重排（transform 不会），所以行宽依然铺满。
# ponytail: 3% 一档、下限 62%，比二分查找长不了几毫秒，省得写边界。
FIT_JS = """
(function(){
  var m=document.querySelector('.main'), f=m&&m.querySelector('.fit'), z=1;
  if(!f) return;
  while(f.getBoundingClientRect().height > m.clientHeight && z > 0.62){
    z -= 0.03; f.style.zoom = z;
  }
})();
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


def render_html(card, idx, total, footer_left, theme="xuan"):
    t = THEMES[theme]
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
        f"<style>{css_for(t)}</style></head><body><div class='card'>"
        f"<div class='{wrap}'><div class='fit'>{inner}</div></div>"
        f'<div class="footer"><span>{html.escape(footer_left)}</span>'
        f"<span>{foot_right}</span></div></div>"
        f"<script>{FIT_JS}</script></body></html>"
    )


def budget(kind, theme="xuan"):
    """该主题下一张卡放得下多少字：面积固定，字号翻倍则容量掉到 1/4。"""
    return round(BUDGET_BASE.get(kind, BUDGET_BASE["body"]) / THEMES[theme]["scale"] ** 2)


def width(text):
    """按「汉字宽」估占位：ASCII 半角算半个字，否则英文数字多的卡会被虚报超标。"""
    return sum(0.5 if ord(c) < 128 else 1 for c in str(text))


def over_budget(card, theme="xuan"):
    """返回超出的字数（0 表示没超）。只是估算，见下方 ponytail 注释。"""
    # ponytail: 用字数估算是否溢出，只警告不自动分页。真需要自动分页再换成
    # Chrome --dump-dom 读 scrollHeight。
    kind = card.get("kind", "body")
    n = width(card.get("title", "")) + width(card.get("sub", ""))
    n += width(card.get("heading", "")) * 2  # 标题字号大，按两倍占位算
    n += width(card.get("text", "")) + width(card.get("note", ""))
    return max(0, round(n - budget(kind, theme)))


def pick_theme(cards):
    """随机换主题，但避开明显装不下这批文字的——大字号主题被缩一堆卡就不好看了。
    做法：按总溢出排序，在较宽松的一半里随机挑，既有变化又不会卡卡都缩。"""
    ranked = sorted(THEMES, key=lambda t: sum(over_budget(c, t) for c in cards))
    return random.choice(ranked[: max(1, len(ranked) // 2)])


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
    ap.add_argument("--theme", default="random",
                    help="配色/字体/版式主题：" + "、".join(THEMES) + "，默认随机")
    ap.add_argument("--html-only", action="store_true", help="只出 HTML，不调 Chrome")
    ap.add_argument("--selftest", action="store_true", help="跑自检后退出")
    args = ap.parse_args(argv)

    if args.selftest:
        assert over_budget({"kind": "body", "text": "字" * 100}) == 0
        assert over_budget({"kind": "body", "text": "字" * 300}) == 150
        assert over_budget({"kind": "body", "text": "x" * 300}) == 0  # 半角算半个字
        assert budget("body", "zhu") < budget("body", "xuan") < budget("body", "qing")
        h = render_html({"kind": "cover", "title": "甲\n乙"}, 1, 3, "出处")
        assert "1/3" in h and "1080px" in h and "甲\n乙" in h
        long_deck = [{"kind": "body", "text": "字" * 200}] * 5
        assert "zhu" not in [pick_theme(long_deck) for _ in range(30)]  # 字最大的先被排除
        h2 = render_html({"kind": "body", "text": "一段\n\n两段"}, 2, 3, "x")
        assert h2.count("<p>") == 2 and "main center" in h2
        assert "class='fit'" in h2 and "getBoundingClientRect" in h2  # 自动缩放兜底
        assert "<em>重点</em>" in render_html(
            {"kind": "body", "text": "**重点**"}, 1, 1, "")
        assert "&lt;script&gt;" in render_html({"kind": "body", "text": "<script>"}, 1, 1, "")
        for name in THEMES:  # 每套主题都要能渲染出完整 CSS
            css = css_for(THEMES[name])
            assert THEMES[name]["bg"] in css and not re.search(r"\{(accent|mark|bg)\}", css)
            assert THEMES[name]["accent"] in render_html(
                {"kind": "body", "heading": "标题", "text": "x"}, 1, 1, "", name)
        print("selftest ok")
        return 0

    if args.theme != "random" and args.theme not in THEMES:
        sys.exit(f"没有这套主题：{args.theme}；可选 {'、'.join(THEMES)}")

    raw = Path(args.cards_json).read_text("utf-8") if args.cards_json else sys.stdin.read()
    doc = json.loads(raw)
    cards = doc["cards"]
    if len(cards) > MAX_CARDS:
        sys.exit(f"小红书一篇最多 {MAX_CARDS} 张，当前 {len(cards)} 张")
    footer_left = doc.get("footer", "")

    theme = args.theme if args.theme != "random" else pick_theme(cards)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"主题：{theme}（正文预算 {budget('body', theme)} 字/张）", file=sys.stderr)
    for i, card in enumerate(cards, 1):
        over = over_budget(card, theme)
        if over:
            print(f"  ⚠ 第 {i} 张约超出 {over} 字，会被自动缩小；想保住字号就拆卡", file=sys.stderr)

    chrome = None if args.html_only else find_chrome()
    if not args.html_only and not chrome:
        sys.exit("没找到 Chrome/Chromium/Edge，可用 --html-only 只出 HTML")

    written = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, card in enumerate(cards, 1):
            name = f"{i:02d}-{card.get('kind', 'body')}"
            page = render_html(card, i, len(cards), footer_left, theme)
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
    print(f"\n共 {len(written)} 张（主题 {theme}），都在：{outdir.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
