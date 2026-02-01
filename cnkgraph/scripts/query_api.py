#!/usr/bin/env python3
"""
古籍文献知识图谱API查询工具

使用示例：
    # 查询诗词
    python cnkgraph/scripts/query_api.py poetry --author 李白 --keyword 月
    
    # 查询古籍（书目与命中数）
    python cnkgraph/scripts/query_api.py book --keyword 赤壁
    
    # 检索古籍原文片段（带上下文，用于补充时间/地点/人物/起因/经过/结果）
    python cnkgraph/scripts/query_api.py find --keyword 崔浩
    python cnkgraph/scripts/query_api.py find --keyword "暴扬国恶"
    
    # 查询人物
    python cnkgraph/scripts/query_api.py people --name 苏轼
    
    # 查询事件
    python cnkgraph/scripts/query_api.py event --keyword 安史之乱
"""

import sys
import argparse
import requests
import json
from typing import Optional, Dict, Any, List
from urllib.parse import quote

# API基础URL
BASE_URL = "https://open.cnkgraph.com/api"

# 超时设置（秒）
TIMEOUT = 30

def search_poetry(keyword: Optional[str] = None,
                  author: Optional[str] = None,
                  dynasty: Optional[str] = None,
                  title: Optional[str] = None,
                  limit: int = 10) -> Dict[str, Any]:
    """查询诗词。按 Swagger 使用 POST /api/Writing/Find，请求体为 WritingModel。"""
    url = f"{BASE_URL}/Writing/Find"
    body: Dict[str, Any] = {"PageNo": 0}
    if keyword:
        body["Key"] = keyword
    if author:
        body["Author"] = author
    if dynasty:
        body["Dynasty"] = dynasty
    if title and not keyword:
        body["Key"] = title
    try:
        response = requests.post(
            url,
            json=body,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def search_books(keyword: str, limit: int = 10, page_no: int = 0, book_id: Optional[str] = None) -> Dict[str, Any]:
    """查询古籍。按 Swagger 使用 POST /api/Book/Search，请求体为关键词 JSON 字符串，可选 query: pageNo, bookId。"""
    url = f"{BASE_URL}/Book/Search"
    params: Dict[str, Any] = {"pageNo": page_no}
    if book_id:
        params["bookId"] = book_id
    try:
        response = requests.post(
            url,
            json=keyword,
            params=params,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def find_book_passages(keyword: str, page_no: int = 0, book_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """检索古籍原文片段。按 Swagger 使用 POST /api/Book/Find，返回带上下文的命中片段（PreviousText/MatchedText/LaterText），
    用于补充时间、地点、相关人物、起因、经过、结果等细节。"""
    url = f"{BASE_URL}/Book/Find"
    body: Dict[str, Any] = {"Key": keyword, "PageNo": page_no}
    if book_ids:
        body["BookIds"] = book_ids
    try:
        response = requests.post(
            url,
            json=body,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def search_people(name: str) -> Dict[str, Any]:
    """查询人物。按 Swagger 使用 GET /api/People/{id}，id 为姓名/朝代键/人物 Id。"""
    url = f"{BASE_URL}/People/{quote(name, safe='')}"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def search_event(keyword: str) -> Dict[str, Any]:
    """查询事件。Event 不在 Swagger 中，先 GET，遇 405 则 POST 请求体为关键词 JSON 字符串。"""
    url = f"{BASE_URL}/Event/Search"
    try:
        response = requests.get(url, params={"keyword": keyword}, timeout=TIMEOUT)
        if response.status_code == 405:
            response = requests.post(
                url,
                json=keyword,
                timeout=TIMEOUT,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def format_poetry_result(data: Dict[str, Any]):
    """格式化诗词结果"""
    if "error" in data:
        print(f"\n❌ 查询失败: {data['error']}")
        return
    
    # 注意：实际API返回的结构可能不同，这里是示例
    print("\n" + "="*60)
    print("诗词查询结果")
    print("="*60)
    
    if isinstance(data, list):
        for i, item in enumerate(data[:5], 1):  # 只显示前5条
            print(f"\n【{i}】")
            print(f"标题：{item.get('title', '未知')}")
            print(f"作者：{item.get('author', '未知')} ({item.get('dynasty', '未知')})")
            print(f"\n{item.get('content', '内容缺失')}")
            print("-"*60)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))

def format_book_result(data: Dict[str, Any]):
    """格式化古籍结果"""
    if "error" in data:
        print(f"\n❌ 查询失败: {data['error']}")
        return
    
    print("\n" + "="*60)
    print("古籍查询结果")
    print("="*60)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def format_people_result(data: Dict[str, Any]):
    """格式化人物结果"""
    if "error" in data:
        print(f"\n❌ 查询失败: {data['error']}")
        return
    
    print("\n" + "="*60)
    print("人物查询结果")
    print("="*60)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def format_event_result(data: Dict[str, Any]):
    """格式化事件结果"""
    if "error" in data:
        print(f"\n❌ 查询失败: {data['error']}")
        return
    
    print("\n" + "="*60)
    print("事件查询结果")
    print("="*60)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(
        description="古籍文献知识图谱API查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 查询李白关于月的诗
  %(prog)s poetry --author 李白 --keyword 月
  
  # 查询赤壁相关古籍
  %(prog)s book --keyword 赤壁
  
  # 检索古籍原文片段（补充时间/地点/人物/起因/经过/结果）
  %(prog)s find --keyword 崔浩
  
  # 查询苏轼的信息
  %(prog)s people --name 苏轼
  
  # 查询安史之乱
  %(prog)s event --keyword 安史之乱
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='查询类型')
    
    # 诗词查询
    poetry_parser = subparsers.add_parser('poetry', help='查询诗词')
    poetry_parser.add_argument('--keyword', help='关键词')
    poetry_parser.add_argument('--author', help='作者')
    poetry_parser.add_argument('--dynasty', help='朝代')
    poetry_parser.add_argument('--title', help='题目')
    poetry_parser.add_argument('--limit', type=int, default=10, help='返回结果数量限制')
    
    # 古籍查询
    book_parser = subparsers.add_parser('book', help='查询古籍（书目与命中数）')
    book_parser.add_argument('--keyword', required=True, help='关键词')
    book_parser.add_argument('--limit', type=int, default=10, help='返回结果数量限制')
    
    # 古籍原文片段检索（带上下文的命中片段，用于补充时间地点人物起因经过结果）
    find_parser = subparsers.add_parser('find', help='检索古籍原文片段（Book/Find，返回 PreviousText/MatchedText/LaterText）')
    find_parser.add_argument('--keyword', required=True, help='关键词或组合，如 崔浩、暴扬国恶、国史 刊石')
    find_parser.add_argument('--page', type=int, default=0, help='页码，默认 0')
    
    # 人物查询
    people_parser = subparsers.add_parser('people', help='查询人物')
    people_parser.add_argument('--name', required=True, help='人名')
    
    # 事件查询
    event_parser = subparsers.add_parser('event', help='查询事件')
    event_parser.add_argument('--keyword', required=True, help='关键词')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    print(f"\n正在查询古籍文献知识图谱API...")
    
    try:
        if args.command == 'poetry':
            result = search_poetry(
                keyword=args.keyword,
                author=args.author,
                dynasty=args.dynasty,
                title=args.title,
                limit=args.limit
            )
            format_poetry_result(result)
            
        elif args.command == 'book':
            result = search_books(args.keyword, args.limit)
            format_book_result(result)
            
        elif args.command == 'find':
            result = find_book_passages(args.keyword, args.page)
            format_book_result(result)
            
        elif args.command == 'people':
            result = search_people(args.name)
            format_people_result(result)
            
        elif args.command == 'event':
            result = search_event(args.keyword)
            format_event_result(result)
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
