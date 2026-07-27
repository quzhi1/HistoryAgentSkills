#!/usr/bin/env python3
"""
中国历史专家系统 - 综合查询工具

这个脚本结合历史辞典和古籍API，提供完整的历史问题查询流程。

使用示例：
    python scripts/history_query.py "李白"
    python scripts/history_query.py "安史之乱"
    python scripts/history_query.py "科举制度"
"""

import sys
import subprocess
import requests
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from book_search import BookSearchError, search_books
from dynasty_converter import EraConversionError, convert_era_expression
from venv_utils import venv_executable

# 配置
ROOT = Path(__file__).resolve().parents[1]
DICT_PATH = ROOT / "dict" / "历史辞典4合1.mdx"
MDICT_BIN = venv_executable(ROOT, "mdict", must_exist=False)
API_BASE_URL = "https://open.cnkgraph.com/api"
TIMEOUT = 30
QUERY_STATUS_FOUND = "found"
QUERY_STATUS_NOT_FOUND = "not_found"
QUERY_STATUS_ERROR = "error"


def query_found(data: Any) -> Dict[str, Any]:
    return {"status": QUERY_STATUS_FOUND, "data": data}


def query_not_found(reason: str) -> Dict[str, Any]:
    return {"status": QUERY_STATUS_NOT_FOUND, "reason": reason}


def query_error(reason: str) -> Dict[str, Any]:
    return {"status": QUERY_STATUS_ERROR, "reason": reason}


def payload_has_results(payload: Any) -> bool:
    """Return whether a successful API response contains a usable result."""
    if payload is None:
        return False
    if isinstance(payload, list):
        return bool(payload)
    if not isinstance(payload, dict):
        return bool(payload)

    for key in ("Result", "result", "Results", "results", "Data", "data", "Items", "items"):
        if key in payload:
            return bool(payload[key])
    for key in ("Count", "count", "Total", "total"):
        if key in payload:
            try:
                return int(payload[key]) > 0
            except (TypeError, ValueError):
                return False
    return bool(payload)

class HistoryExpert:
    """历史专家系统"""
    
    def __init__(self):
        self.dict_path = DICT_PATH
        self.api_base = API_BASE_URL

    def query_source_guidance(self, keyword: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search local historiography EPUBs for source-collection direction."""
        try:
            return search_books(keyword, limit=limit)
        except (BookSearchError, OSError) as e:
            print(f"⚠️  EPUB史料方向检索出错: {e}")
            return []

    def query_era_conversion(self, expression: str) -> Optional[Dict[str, Any]]:
        """Convert a reign-year expression if the keyword looks like one."""
        if "年" not in expression and "载" not in expression:
            return None
        try:
            result = convert_era_expression(expression)
        except (EraConversionError, Exception) as e:
            print(f"⚠️  年号换算出错: {e}")
            return None
        return result if result.get("matches") or result.get("errors") else None
        
    def query_dictionary(self, keyword: str) -> Dict[str, Any]:
        """查询历史辞典，并区分命中、无结果和查询失败。"""
        if not os.path.exists(self.dict_path):
            return query_error("辞典文件不可用")
        if not MDICT_BIN.exists():
            return query_error("mdict 工具不可用，请运行 ./setup_venv.sh")
        
        try:
            result = subprocess.run(
                [str(MDICT_BIN), "-q", keyword, str(self.dict_path)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return query_found(result.stdout.strip())
            if result.returncode == 0:
                return query_not_found(f"辞典未命中关键词：{keyword}")
            return query_error("辞典查询命令执行失败")
            
        except subprocess.TimeoutExpired:
            return query_error(f"辞典查询超时：{keyword}")
        except FileNotFoundError:
            return query_error("mdict 工具不可用，请运行 ./setup_venv.sh")
        except Exception:
            return query_error("辞典查询发生错误")
    
    def query_api_poetry(
        self, keyword: Optional[str] = None, author: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询诗词API，并区分命中、无结果和查询失败。"""
        url = f"{self.api_base}/Writing/Find"
        body = {"PageNo": 0}
        if keyword:
            body["Key"] = keyword
        if author:
            body["Author"] = author
        if not (keyword or author):
            return query_error("诗词查询缺少关键词或作者")
        try:
            response = requests.post(
                url,
                json=body,
                timeout=TIMEOUT,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            if response.status_code == 404:
                return query_not_found("诗词 API 未命中")
            response.raise_for_status()
            payload = response.json()
            return query_found(payload) if payload_has_results(payload) else query_not_found("诗词 API 未命中")
        except requests.exceptions.Timeout:
            return query_error("诗词 API 查询超时")
        except (requests.exceptions.RequestException, ValueError):
            return query_error("诗词 API 查询失败")
    
    def query_api_books(self, keyword: str) -> Dict[str, Any]:
        """查询古籍API，并区分命中、无结果和查询失败。"""
        url = f"{self.api_base}/Book/Search"
        try:
            response = requests.post(
                url,
                json=keyword,
                timeout=TIMEOUT,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            if response.status_code == 404:
                return query_not_found(f"古籍 API 未命中关键词：{keyword}")
            response.raise_for_status()
            payload = response.json()
            return query_found(payload) if payload_has_results(payload) else query_not_found(
                f"古籍 API 未命中关键词：{keyword}"
            )
        except requests.exceptions.Timeout:
            return query_error("古籍 API 查询超时")
        except (requests.exceptions.RequestException, ValueError):
            return query_error("古籍 API 查询失败")
    
    def query_api_people(self, name: str) -> Dict[str, Any]:
        """查询人物API，并区分命中、无结果和查询失败。"""
        from urllib.parse import quote
        url = f"{self.api_base}/People/{quote(name, safe='')}"
        try:
            response = requests.get(url, timeout=TIMEOUT)
            if response.status_code == 404:
                return query_not_found(f"人物 API 未命中：{name}")
            response.raise_for_status()
            payload = response.json()
            return query_found(payload) if payload_has_results(payload) else query_not_found(
                f"人物 API 未命中：{name}"
            )
        except requests.exceptions.Timeout:
            return query_error("人物 API 查询超时")
        except (requests.exceptions.RequestException, ValueError):
            return query_error("人物 API 查询失败")
    
    def comprehensive_query(self, keyword: str):
        """综合查询：辞典 + API"""
        print("\n" + "="*70)
        print(f"中国历史专家系统 - 综合查询")
        print("="*70)
        print(f"\n🔍 查询关键词: {keyword}\n")

        # 步骤0：年号换算（如果输入本身是年号纪年）
        era_result = self.query_era_conversion(keyword)
        if era_result:
            print("🗓️  步骤0: 年号纪年换算...")
            for item in era_result.get("matches", []):
                reign = item.get("reignTitle") or item.get("dynasty")
                print(f"✓ {item.get('dynasty')}{reign}{era_result['year_number']}年 = {item['gregorian_label']}")
            for error in era_result.get("errors", []):
                print(f"⚠️  {error}")
            print()

        # 步骤0.5：从本地史料学 EPUB 判断搜集方向
        print("🧭 步骤0.5: 检索本地史料学 EPUB，判断搜集方向...")
        guidance_results = self.query_source_guidance(keyword, limit=3)
        if guidance_results:
            for i, item in enumerate(guidance_results, 1):
                print(f"\n【方向{i}】{item['book_title']} / {item.get('section', '')}")
                print(f"位置: {item['book_path']}#{item['href']}")
                print(f"片段: {item['snippet']}")
            print("\n注: EPUB 检索结果只用于判断史料搜集方向，最终史实仍需辞典与 cnkgraph 核验。\n")
        else:
            print("未在本地史料学 EPUB 中找到直接匹配片段。\n")
        
        # 步骤1：查询历史辞典
        print("📚 步骤1: 查询《中国历史大辞典》...")
        dict_result = self.query_dictionary(keyword)
        
        if dict_result["status"] == QUERY_STATUS_FOUND:
            print("✓ 找到辞典词条\n")
            print("-"*70)
            print("根据《中国历史大辞典》：\n")
            print(f"「{dict_result['data']}」")
            print("-"*70)
        elif dict_result["status"] == QUERY_STATUS_NOT_FOUND:
            print("○ 辞典查询完成，但未命中此词条")
            print("  无结果只表示该来源未命中，不构成相反证据或矛盾。")
            print("💡 建议: 尝试使用同义词或简化关键词\n")
        else:
            print(f"⚠️  辞典查询失败：{dict_result['reason']}")
        
        # 步骤2：查询古籍API（人物）
        print("\n📖 步骤2: 查询古籍文献知识图谱API...")
        print("\n2.1 尝试作为人物查询...")
        people_result = self.query_api_people(keyword)
        
        poetry_result: Optional[Dict[str, Any]] = None
        if people_result["status"] == QUERY_STATUS_FOUND:
            print("✓ 找到人物信息")
            # 这里可以进一步格式化输出
            
            # 如果是人物，尝试查询其作品
            print("\n2.2 查询相关诗词作品...")
            poetry_result = self.query_api_poetry(author=keyword)
            if poetry_result["status"] == QUERY_STATUS_FOUND:
                print("✓ 找到相关诗词")
            elif poetry_result["status"] == QUERY_STATUS_NOT_FOUND:
                print("○ 诗词 API 查询完成，但未命中相关作品")
            else:
                print(f"⚠️  诗词 API 查询失败：{poetry_result['reason']}")
        elif people_result["status"] == QUERY_STATUS_NOT_FOUND:
            print("○ 人物 API 查询完成，但未命中人物信息")
        else:
            print(f"⚠️  人物 API 查询失败：{people_result['reason']}")
        
        # 步骤3：查询古籍
        print("\n2.3 查询相关古籍文献...")
        book_result = self.query_api_books(keyword)
        
        if book_result["status"] == QUERY_STATUS_FOUND:
            print("✓ 找到相关古籍")
        elif book_result["status"] == QUERY_STATUS_NOT_FOUND:
            print("○ 古籍 API 查询完成，但未命中相关古籍")
        else:
            print(f"⚠️  古籍 API 查询失败：{book_result['reason']}")
        
        # 总结
        print("\n" + "="*70)
        print("查询完成")
        print("="*70)
        
        primary_results = [dict_result, people_result, book_result]
        has_result = any(result["status"] == QUERY_STATUS_FOUND for result in primary_results)
        has_error = any(result["status"] == QUERY_STATUS_ERROR for result in primary_results)
        
        if has_result:
            print("\n✓ 已找到相关资料，可以基于以上信息回答问题")
            if has_error:
                print("⚠️  部分来源查询失败；只能使用已成功命中的材料，不能把失败来源当作反证。")
        elif has_error:
            print("\n⚠️  当前没有得到可用结果，且至少一个来源查询失败。")
            print("查询失败不等于无结果；无结果也不构成资料不存在或与问题相矛盾的证据。")
        else:
            print("\n○ 已完成的来源均未命中相关资料")
            print("这只表示当前来源和关键词没有命中，不证明相关资料不存在，也不构成矛盾。")
            print("\n💡 建议:")
            print("  • 检查关键词拼写")
            print("  • 尝试使用同义词或别称")
            print("  • 简化查询词（如'唐太宗李世民' → '李世民'）")
            print("  • 查询相关的更大类别")
        
        print()

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/history_query.py <关键词>")
        print("\n示例:")
        print("  python scripts/history_query.py 李白")
        print("  python scripts/history_query.py 安史之乱")
        print("  python scripts/history_query.py 科举制度")
        sys.exit(1)
    
    keyword = sys.argv[1]
    
    expert = HistoryExpert()
    expert.comprehensive_query(keyword)

if __name__ == "__main__":
    main()
