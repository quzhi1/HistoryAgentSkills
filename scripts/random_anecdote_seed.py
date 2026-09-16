#!/usr/bin/env python3
"""Discover random anecdote candidates from cnkgraph instead of a fixed story pool."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import secrets
import sys
from dataclasses import dataclass
from typing import Any

import requests


API_BASE_URL = "https://open.cnkgraph.com/api"
TIMEOUT = 30
DEFAULT_ATTEMPTS = 15
DEFAULT_CANDIDATES = 5
MAX_KEYWORD_LENGTH = 6
# Score is a quality floor, not a ranking: everything above it is shuffled (see discover_candidates).
MIN_CANDIDATE_SCORE = 12

# These are ingredients for random corpus probes, not a finite topic/story list.
# The script still searches the full corpus and randomly jumps result pages.
PROBE_SINGLE_CHARS = "曰云谓问答笑怒惊拜呼梦食饮刺杀救逃顾盗醉讼赂诈匿窃赌哭骂偿赎劾"
PROBE_PREFIXES = "因乃遂便即忽俄既公帝王君客人妇僧道贾吏卒儿翁媪"
PROBE_CORES = "曰云谓问笑怒惊拜呼顾见闻食饮杀救逃盗窃醉诈匿骂争夺弃卖买藏"
# Speech markers alone kept dragging the same famous dialogue pages back up, so
# probes are drawn from several unrelated families instead of one.
PROBE_SPEECH_PHRASES = (
    "问曰",
    "答曰",
    "谓曰",
    "笑曰",
    "怒曰",
    "惊曰",
    "顾曰",
    "呼曰",
    "因曰",
    "乃曰",
    "遂曰",
    "曰吾",
    "曰君",
    "曰汝",
)
PROBE_ACTION_PHRASES = (
    "窃取",
    "阴使",
    "伪为",
    "阳为",
    "诈称",
    "匿于",
    "夺之",
    "掷地",
    "殴之",
    "缚之",
    "遁去",
    "亡去",
    "跳出",
    "堕水",
    "失火",
    "夜半",
    "大醉",
    "被酒",
    "剧饮",
    "赌钱",
    "博塞",
)
PROBE_REACTION_PHRASES = (
    "大惭",
    "大窘",
    "失色",
    "拊掌",
    "绝倒",
    "始悟",
    "乃悟",
    "方知",
    "不觉失",
    "相顾愕",
    "众皆笑",
    "举座",
)
PROBE_WORLD_PHRASES = (
    "市中",
    "邻人",
    "老妪",
    "村民",
    "贾人",
    "牙侩",
    "小吏",
    "驿卒",
    "船人",
    "医者",
    "巫者",
    "屠者",
    "乞儿",
    "鬻药",
    "质钱",
    "负债",
    "讼于",
    "对簿",
    "鞫之",
    "验之",
    "发棺",
    "改葬",
)
PROBE_PHRASES = (
    PROBE_SPEECH_PHRASES + PROBE_ACTION_PHRASES + PROBE_REACTION_PHRASES + PROBE_WORLD_PHRASES
)

NARRATIVE_MARKERS = (
    "曰",
    "云",
    "谓",
    "问",
    "答",
    "笑",
    "怒",
    "喜",
    "惊",
    "惧",
    "泣",
    "哭",
    "拜",
    "呼",
    "语",
    "告",
    "梦",
    "食",
    "饮",
    "投",
    "掷",
    "刺",
    "杀",
    "救",
    "逃",
)

NOISY_SOURCE_MARKERS = (
    "目录",
    "凡例",
    "提要",
    "序",
    "跋",
    "总闻",
    "集注",
    "注疏",
    "义疏",
    "正义",
    "音义",
    "韵府",
    "类函",
    "字锦",
    "骈字",
)

GOOD_ANECDOTE_SOURCE_MARKERS = (
    "世说新语",
    "太平广记",
    "唐语林",
    "朝野佥载",
    "酉阳杂俎",
    "因话录",
    "明皇杂录",
    "北梦琐言",
    "归田录",
    "梦溪笔谈",
    "容斋随笔",
    "涑水记闻",
    "东轩笔录",
    "续世说",
    "说郛",
)

COMPILATION_SOURCE_MARKERS = (
    "古今图书集成",
    "经籍典",
    "理学汇编",
    "方舆汇编",
    "明伦汇编",
)

SCHOLARLY_SOURCE_MARKERS = (
    "语类",
    "讲义",
    "大全",
    "全书",
)

REFERENCE_SOURCE_MARKERS = (
    "韵府",
    "字锦",
    "骈字",
    "广韵",
    "集韵",
    "说文",
    "玉篇",
    "切韵",
)

POETRY_SOURCE_MARKERS = (
    "全唐诗",
    "御选唐诗",
    "唐诗",
    "宋诗",
    "全金诗",
    "诗选",
    "诗钞",
    "词选",
)

RELIGIOUS_COMMENTARY_SOURCE_MARKERS = (
    "阿毗",
    "毗婆沙",
    "俱舍",
    "瑜伽",
    "大智度",
    "成实",
    "摄论",
    "法苑",
    "金刚经",
    "法华经",
    "楞严",
    "圆觉",
    "般若",
    "华严",
    "维摩",
    "阿弥陀",
    "大藏",
    "禅",
    "经注",
    "补注",
    "注解",
)

COMMENTARY_TEXT_MARKERS = (
    "总闻曰",
    "案曰",
    "按曰",
    "疏曰",
    "注曰",
    "笺曰",
    "传曰",
    "解曰",
    "释曰",
    "正义曰",
    "韵藻",
    "颂曰",
    "偈言",
    "禅师云",
    "法师曰",
    "注见",
)

TEXT_NOISE_MARKERS = ("】", "〖", "〗", "○", "《", "》")
SEQUENCE_MARKERS = ("因", "乃", "遂", "便", "即", "俄", "忽", "既", "未几")
PERSON_MARKERS = ("公", "帝", "王", "君", "卿", "汝", "吾", "余", "我", "人", "客", "臣")
SUPERNATURAL_TEXT_MARKERS = ("野狐", "狐", "鬼", "妖", "怪", "仙", "佛", "菩萨", "精魅", "祟")


@dataclass(frozen=True)
class PassageCandidate:
    book: str
    book_id: str | None
    volume: str
    volume_id: str | None
    page: str | None
    keyword: str
    text: str
    score: int

    def to_json(self) -> dict[str, Any]:
        return {
            "book": self.book,
            "book_id": self.book_id,
            "volume": self.volume,
            "volume_id": self.volume_id,
            "page": self.page,
            "keyword": self.keyword,
            "text": self.text,
            "score": self.score,
        }


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("𫝑", "势")
    return text.strip()


def random_probe(rng: secrets.SystemRandom | None = None) -> str:
    rng = rng or secrets.SystemRandom()
    roll = rng.random()
    if roll < 0.5:
        return rng.choice(PROBE_PHRASES)
    if roll < 0.85:
        return rng.choice(PROBE_PREFIXES) + rng.choice(PROBE_CORES)
    return rng.choice(PROBE_SINGLE_CHARS)


def validate_keyword(keyword: str) -> str:
    clean = clean_text(keyword)
    if not clean:
        raise ValueError("keyword must not be empty")
    if len(clean) > MAX_KEYWORD_LENGTH:
        raise ValueError(f"keyword must be {MAX_KEYWORD_LENGTH} characters or fewer")
    if any(ord(char) < 32 for char in clean):
        raise ValueError("keyword contains control characters")
    return clean


def find_book_passages(keyword: str, page_no: int = 0) -> dict[str, Any]:
    url = f"{API_BASE_URL}/Book/Find"
    response = requests.post(
        url,
        json={"Key": keyword, "PageNo": page_no},
        timeout=TIMEOUT,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    if response.status_code == 404:
        return {
            "Count": 0,
            "PageSize": 100,
            "Key": keyword,
            "PageNo": page_no,
            "Summary": [],
            "Result": [],
            "Error": None,
        }
    response.raise_for_status()
    return response.json()


def result_page_count(payload: dict[str, Any]) -> int:
    count = int(payload.get("Count") or 0)
    page_size = int(payload.get("PageSize") or 100)
    if count <= 0 or page_size <= 0:
        return 0
    return max(1, math.ceil(count / page_size))


def build_candidate_text(page: dict[str, Any]) -> str:
    return clean_text(
        "".join(
            [
                str(page.get("PreviousText") or ""),
                str(page.get("MatchedText") or ""),
                str(page.get("LaterText") or ""),
            ]
        )
    )


def score_candidate(book: str, volume: str, text: str, book_id: str | None = None) -> int:
    score = 0
    length = len(text)
    # ponytail: 1000-char ceiling matches SKILL policy ("1000 字以内都可接受").
    # Short snippets kept surfacing single-exchange records that read flat, so they score lower.
    if 200 <= length <= 1000:
        score += 4
    elif 120 <= length < 200:
        score += 1
    elif 35 <= length < 120:
        score -= 2
    elif 1001 <= length <= 1200:
        score -= 2
    else:
        score -= 4

    marker_count = sum(1 for marker in NARRATIVE_MARKERS if marker in text)
    score += min(marker_count, 6)

    if "。" in text or "！" in text or "？" in text:
        score += 1
    if "曰" in text or "云" in text:
        score += 2
    if any(marker in book or marker in volume for marker in GOOD_ANECDOTE_SOURCE_MARKERS):
        score += 5
    if any(marker in book or marker in volume for marker in NOISY_SOURCE_MARKERS):
        score -= 3
    if any(marker in book or marker in volume for marker in COMPILATION_SOURCE_MARKERS):
        score -= 8
    if any(marker in book or marker in volume for marker in SCHOLARLY_SOURCE_MARKERS):
        score -= 4
    if any(marker in book or marker in volume for marker in REFERENCE_SOURCE_MARKERS):
        score -= 8
    if any(marker in book or marker in volume for marker in POETRY_SOURCE_MARKERS):
        score -= 8
    if any(marker in book or marker in volume for marker in RELIGIOUS_COMMENTARY_SOURCE_MARKERS):
        score -= 10
    if book_id and book_id.startswith("KR6"):
        score -= 10
    if book_id and book_id.startswith("KR9"):
        score -= 8
    if any(marker in text for marker in COMMENTARY_TEXT_MARKERS):
        score -= 6
    if any(marker in text for marker in TEXT_NOISE_MARKERS):
        score -= 3
    if any(marker in text for marker in SUPERNATURAL_TEXT_MARKERS):
        score -= 4
    has_sequence = any(marker in text for marker in SEQUENCE_MARKERS)
    has_person = any(marker in text for marker in PERSON_MARKERS)
    has_dialogue = "曰" in text or "云" in text or "问" in text or "答" in text
    if has_sequence and (has_dialogue or marker_count >= 3):
        score += 3
    if has_dialogue and has_person:
        score += 3
    if not ((has_sequence and marker_count >= 2) or (has_dialogue and has_person)):
        score -= 4
    if "……" in text or "..." in text:
        score -= 3
    if text.count("(") >= 3 and text.count("/") >= 2:
        score -= 4
    if text.count("曰") > 5 and length < 80:
        score -= 1
    if re.search(r"[A-Za-z0-9_]{4,}", text):
        score -= 2
    return score


def extract_candidates(payload: dict[str, Any], keyword: str, min_score: int = 8) -> list[PassageCandidate]:
    candidates: list[PassageCandidate] = []
    for category in payload.get("Result") or []:
        for book_entry in category.get("Books") or []:
            book = str(book_entry.get("Book") or "")
            book_id = book_entry.get("BookId")
            for volume_entry in book_entry.get("Volumes") or []:
                volume = str(volume_entry.get("Volume") or "")
                volume_id = volume_entry.get("VolumeId")
                for page in volume_entry.get("Pages") or []:
                    text = build_candidate_text(page)
                    score = score_candidate(book, volume, text, str(book_id) if book_id else None)
                    if score >= min_score:
                        candidates.append(
                            PassageCandidate(
                                book=book,
                                book_id=book_id,
                                volume=volume,
                                volume_id=volume_id,
                                page=page.get("Page"),
                                keyword=keyword,
                                text=text,
                                score=score,
                            )
                        )
    return candidates


HISTORY_PATH = "outputs/anecdote_seen.json"
HISTORY_LIMIT = 800


def candidate_keys(candidate: "PassageCandidate") -> tuple[str, str]:
    """Page key plus a text signature, so the same passage in another edition still matches."""
    page_key = f"{candidate.book}|{candidate.volume}|{candidate.page}"
    signature = candidate.text[:24]
    return page_key, signature


def load_history(path: str | None) -> set[str]:
    if not path:
        return set()
    try:
        return set(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def save_history(path: str | None, seen: set[str], added: list[str]) -> None:
    if not path:
        return
    kept = [key for key in seen if key not in added][-HISTORY_LIMIT:] + added
    target = pathlib.Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(kept[-HISTORY_LIMIT:], ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # ponytail: history is a nicety; never fail discovery over it


def discover_candidates(
    attempts: int = DEFAULT_ATTEMPTS,
    wanted: int = DEFAULT_CANDIDATES,
    rng: secrets.SystemRandom | None = None,
    history_path: str | None = HISTORY_PATH,
) -> dict[str, Any]:
    rng = rng or secrets.SystemRandom()
    attempts = max(1, attempts)
    wanted = max(1, wanted)
    all_candidates: list[PassageCandidate] = []
    trace: list[dict[str, Any]] = []
    seen_samples: set[tuple[str, int]] = set()

    for _ in range(attempts):
        keyword = random_probe(rng)
        first_payload = find_book_passages(keyword, page_no=0)
        pages = result_page_count(first_payload)
        trace_item: dict[str, Any] = {
            "keyword": keyword,
            "count": first_payload.get("Count", 0),
            "page_size": first_payload.get("PageSize", 100),
            "sampled_page": 0,
        }
        payload = first_payload
        if pages > 1:
            sampled_page = rng.randrange(pages)
            for _ in range(3):
                if (keyword, sampled_page) not in seen_samples:
                    break
                sampled_page = rng.randrange(pages)
            trace_item["sampled_page"] = sampled_page
            seen_samples.add((keyword, sampled_page))
            if sampled_page != 0:
                payload = find_book_passages(keyword, page_no=sampled_page)
        else:
            seen_samples.add((keyword, 0))
        candidates = extract_candidates(payload, keyword, min_score=MIN_CANDIDATE_SCORE)
        trace_item["candidate_count"] = len(candidates)
        trace.append(trace_item)
        all_candidates.extend(candidates)

    # Ranking by score used to hand back the same few famous pages every run, so the
    # score is only a filter now: everything above threshold is shuffled and capped per book.
    seen = load_history(history_path)
    # Weighted sampling without replacement (Efraimidis-Spirakis): better-scoring passages
    # come up more often, but every passage above the floor keeps a real chance.
    all_candidates.sort(
        key=lambda item: rng.random() ** (1.0 / max(item.score - MIN_CANDIDATE_SCORE + 1, 1)),
        reverse=True,
    )
    selected: list[PassageCandidate] = []
    fresh_keys: list[str] = []
    per_book: dict[str, int] = {}
    skipped_seen = 0
    for candidate in all_candidates:
        page_key, signature = candidate_keys(candidate)
        if page_key in seen or signature in seen:
            skipped_seen += 1
            continue
        if per_book.get(candidate.book, 0) >= 2:
            continue
        selected.append(candidate)
        fresh_keys.extend((page_key, signature))
        per_book[candidate.book] = per_book.get(candidate.book, 0) + 1
        if len(selected) >= wanted:
            break
    save_history(history_path, seen, fresh_keys)
    return {
        "skipped_already_seen": skipped_seen,
        "status": "ok" if selected else "not_found",
        "strategy": "random_corpus_probe",
        "note": "No fixed anecdote pool is used; probes are generated at runtime and Book/Find searches the full cnkgraph corpus.",
        "attempts": trace,
        "candidates": [candidate.to_json() for candidate in selected],
    }


def sample_probe_payload() -> dict[str, Any]:
    keyword = random_probe()
    return {
        "status": "ok",
        "strategy": "sample_probe_only",
        "keyword": keyword,
        "note": "Offline sample only; no fixed anecdote pool is used.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从 cnkgraph 全库随机发现可核验历史段子候选")
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS, help="随机探针尝试次数")
    parser.add_argument("--candidates", type=int, default=DEFAULT_CANDIDATES, help="最多返回候选数")
    parser.add_argument("--sample-probe", action="store_true", help="只生成一个随机检索探针，不访问网络")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--history",
        default=HISTORY_PATH,
        help=f"已抽到过的段子记录，用于避免重复（默认 {HISTORY_PATH}）",
    )
    parser.add_argument("--no-history", action="store_true", help="不读也不写重复记录")
    args = parser.parse_args()

    try:
        payload = (
            sample_probe_payload()
            if args.sample_probe
            else discover_candidates(
                attempts=args.attempts,
                wanted=args.candidates,
                history_path=None if args.no_history else args.history,
            )
        )
    except (ValueError, requests.RequestException) as exc:
        payload = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload["status"] != "ok":
            print("未发现可用候选。")
        else:
            for index, candidate in enumerate(payload.get("candidates") or [], 1):
                print(f"【{index}】{candidate['book']} {candidate['volume']}")
                print(candidate["text"])
                print("")
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
