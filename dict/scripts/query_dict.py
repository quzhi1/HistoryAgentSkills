#!/usr/bin/env python3
"""
中国历史大辞典查询工具

使用示例：
    python dict/scripts/query_dict.py 李白
    python dict/scripts/query_dict.py 安史之乱 科举制度
"""

import sys
import subprocess
import os
import shutil

def query_dictionary(keyword):
    """查询历史辞典"""
    dict_path = "dict/历史辞典4合1.mdx"
    
    if not os.path.exists(dict_path):
        print(f"错误：找不到辞典文件 {dict_path}")
        return None
    
    try:
        # 使用 mdict 命令查询
        result = subprocess.run(
            ["mdict", "-q", keyword, dict_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                return output
            else:
                return None
        else:
            print(f"查询出错：{result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"查询超时（关键词：{keyword}）")
        return None
    except FileNotFoundError:
        print("错误：未安装 mdict-utils，请运行：pip install mdict-utils")
        return None
    except Exception as e:
        print(f"查询出错：{e}")
        return None

def format_result(keyword, result):
    """格式化输出结果"""
    print(f"\n{'='*60}")
    print(f"关键词：{keyword}")
    print(f"{'='*60}")
    
    if result:
        print(f"\n根据《中国历史大辞典》：")
        print(f"\n「{result}」")
    else:
        print(f"\n未找到词条"{keyword}"")
        print("\n建议：")
        print("  1. 尝试简化关键词")
        print("  2. 使用同义词或别称")
        print("  3. 查询相关的更大类别")
    
    print(f"\n{'='*60}\n")

def check_environment():
    """检查环境是否正确配置"""
    # 检查mdict命令是否可用
    if not shutil.which('mdict'):
        print("❌ 错误：未找到 mdict 命令")
        print("\n可能的解决方案：")
        print("1. 激活虚拟环境：")
        print("   cd /Users/zhi.q/HistoryAgentSkills")
        print("   source venv/bin/activate")
        print("\n2. 或安装 mdict-utils：")
        print("   pip install mdict-utils")
        print("\n3. 或运行设置脚本：")
        print("   ./setup_venv.sh")
        return False
    
    # 检查辞典文件是否存在
    dict_path = "dict/历史辞典4合1.mdx"
    if not os.path.exists(dict_path):
        print(f"❌ 错误：找不到辞典文件 {dict_path}")
        print("\n请确保在项目根目录运行此脚本")
        return False
    
    return True

def main():
    if len(sys.argv) < 2:
        print("用法: python dict/scripts/query_dict.py <关键词1> [关键词2] ...")
        print("\n示例:")
        print("  python dict/scripts/query_dict.py 李白")
        print("  python dict/scripts/query_dict.py 安史之乱 李白 杜甫")
        sys.exit(1)
    
    # 环境检查
    if not check_environment():
        sys.exit(1)
    
    keywords = sys.argv[1:]
    
    print(f"\n正在查询 {len(keywords)} 个关键词...")
    
    results = {}
    for keyword in keywords:
        print(f"查询中：{keyword}...", end=" ", flush=True)
        result = query_dictionary(keyword)
        results[keyword] = result
        print("✓" if result else "✗")
    
    # 输出所有结果
    print("\n" + "="*60)
    print("查询结果")
    print("="*60)
    
    for keyword, result in results.items():
        format_result(keyword, result)

if __name__ == "__main__":
    main()
