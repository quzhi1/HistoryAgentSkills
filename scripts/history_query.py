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
from typing import Optional, Dict, Any, List

# 配置
DICT_PATH = "dict/历史辞典4合1.mdx"
API_BASE_URL = "https://open.cnkgraph.com/api"
TIMEOUT = 30

class HistoryExpert:
    """历史专家系统"""
    
    def __init__(self):
        self.dict_path = DICT_PATH
        self.api_base = API_BASE_URL
        
    def query_dictionary(self, keyword: str) -> Optional[str]:
        """查询历史辞典"""
        if not os.path.exists(self.dict_path):
            print(f"⚠️  找不到辞典文件: {self.dict_path}")
            return None
        
        try:
            result = subprocess.run(
                ["mdict", "-q", keyword, self.dict_path],
                capture_output=True,
                text=True,
                timeout=TIMEOUT
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
            
        except subprocess.TimeoutExpired:
            print(f"⚠️  辞典查询超时: {keyword}")
            return None
        except FileNotFoundError:
            print("⚠️  未安装 mdict-utils，请运行: pip install mdict-utils")
            return None
        except Exception as e:
            print(f"⚠️  辞典查询出错: {e}")
            return None
    
    def query_api_poetry(self, keyword: str = None, author: str = None) -> Optional[Dict]:
        """查询诗词API。按 Swagger 使用 POST /api/Writing/Find，请求体为 WritingModel。"""
        url = f"{self.api_base}/Writing/Find"
        body = {"PageNo": 0}
        if keyword:
            body["Key"] = keyword
        if author:
            body["Author"] = author
        if not (keyword or author):
            return None
        try:
            response = requests.post(
                url,
                json=body,
                timeout=TIMEOUT,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  诗词API查询出错: {e}")
            return None
    
    def query_api_books(self, keyword: str) -> Optional[Dict]:
        """查询古籍API。按 Swagger 使用 POST /api/Book/Search，请求体为关键词的 JSON 字符串。"""
        url = f"{self.api_base}/Book/Search"
        try:
            response = requests.post(
                url,
                json=keyword,
                timeout=TIMEOUT,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  古籍API查询出错: {e}")
            return None
    
    def query_api_people(self, name: str) -> Optional[Dict]:
        """查询人物API。按 Swagger 使用 GET /api/People/{id}，id 为姓名/朝代键/人物 Id。"""
        from urllib.parse import quote
        url = f"{self.api_base}/People/{quote(name, safe='')}"
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  人物API查询出错: {e}")
            return None
    
    def comprehensive_query(self, keyword: str):
        """综合查询：辞典 + API"""
        print("\n" + "="*70)
        print(f"中国历史专家系统 - 综合查询")
        print("="*70)
        print(f"\n🔍 查询关键词: {keyword}\n")
        
        # 步骤1：查询历史辞典
        print("📚 步骤1: 查询《中国历史大辞典》...")
        dict_result = self.query_dictionary(keyword)
        
        if dict_result:
            print("✓ 找到辞典词条\n")
            print("-"*70)
            print("根据《中国历史大辞典》：\n")
            print(f"「{dict_result}」")
            print("-"*70)
        else:
            print("✗ 辞典中未找到此词条")
            print("💡 建议: 尝试使用同义词或简化关键词\n")
        
        # 步骤2：查询古籍API（人物）
        print("\n📖 步骤2: 查询古籍文献知识图谱API...")
        print("\n2.1 尝试作为人物查询...")
        people_result = self.query_api_people(keyword)
        
        if people_result and not people_result.get('error'):
            print("✓ 找到人物信息")
            # 这里可以进一步格式化输出
            
            # 如果是人物，尝试查询其作品
            print("\n2.2 查询相关诗词作品...")
            poetry_result = self.query_api_poetry(author=keyword)
            if poetry_result:
                print("✓ 找到相关诗词")
        else:
            print("✗ 未找到人物信息")
        
        # 步骤3：查询古籍
        print("\n2.3 查询相关古籍文献...")
        book_result = self.query_api_books(keyword)
        
        if book_result and not book_result.get('error'):
            print("✓ 找到相关古籍")
        else:
            print("✗ 未找到相关古籍")
        
        # 总结
        print("\n" + "="*70)
        print("查询完成")
        print("="*70)
        
        has_result = dict_result or (people_result and not people_result.get('error')) or (book_result and not book_result.get('error'))
        
        if has_result:
            print("\n✓ 已找到相关资料，可以基于以上信息回答问题")
        else:
            print("\n✗ 未找到相关资料")
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
