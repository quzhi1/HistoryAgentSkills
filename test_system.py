#!/usr/bin/env python3
"""
简单测试脚本 - 验证系统是否正常工作

运行: python test_system.py
"""

import sys
import os

def test_imports():
    """测试依赖包是否安装"""
    print("测试1: 检查依赖包...")
    
    try:
        import requests
        print("✓ requests 已安装")
    except ImportError:
        print("✗ requests 未安装，请运行: pip install requests")
        return False
    
    # 注意: mdict-utils 是命令行工具，不是Python包
    # 我们通过检查命令是否可用来验证
    import subprocess
    try:
        result = subprocess.run(
            ["mdict", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ mdict-utils 已安装")
        else:
            print("✗ mdict-utils 可能未正确安装")
            return False
    except FileNotFoundError:
        print("✗ mdict 命令未找到，请运行: pip install mdict-utils")
        return False
    except Exception as e:
        print(f"✗ 检查 mdict 时出错: {e}")
        return False
    
    return True

def test_files():
    """测试必要文件是否存在"""
    print("\n测试2: 检查文件...")
    
    required_files = [
        "dict/历史辞典4合1.mdx",
        "dict/历史辞典4in1.mdd",
        "dict/scripts/query_dict.py",
        "cnkgraph/scripts/query_api.py",
        "scripts/history_query.py",
        "SKILL.md",
        "dict/SKILL.md",
        "cnkgraph/SKILL.md"
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 不存在")
            all_exist = False
    
    return all_exist

def test_scripts():
    """测试脚本是否可执行"""
    print("\n测试3: 检查脚本...")
    
    scripts = [
        "dict/scripts/query_dict.py",
        "cnkgraph/scripts/query_api.py",
        "scripts/history_query.py"
    ]
    
    for script in scripts:
        if os.access(script, os.X_OK):
            print(f"✓ {script} 可执行")
        else:
            print(f"⚠ {script} 不可执行（可能需要: chmod +x {script}）")
    
    return True

def test_api_connection():
    """测试API连接"""
    print("\n测试4: 检查API连接...")
    
    try:
        import requests
        response = requests.get(
            "https://open.cnkgraph.com",
            timeout=10
        )
        if response.status_code == 200:
            print("✓ API服务器可访问")
            return True
        else:
            print(f"⚠ API服务器返回状态码: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("✗ API连接超时")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到API服务器")
        return False
    except Exception as e:
        print(f"✗ API连接测试失败: {e}")
        return False

def main():
    print("="*60)
    print("中国历史专家系统 - 系统测试")
    print("="*60)
    print()
    
    results = []
    
    # 运行所有测试
    results.append(("依赖包", test_imports()))
    results.append(("文件完整性", test_files()))
    results.append(("脚本可执行性", test_scripts()))
    results.append(("API连接", test_api_connection()))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统已就绪。")
        print("\n快速开始:")
        print("  1. 在Cursor中直接问历史问题")
        print("  2. 或运行: python dict/scripts/query_dict.py '李白'")
        print("  3. 查看文档: README.md 或 QUICKSTART.md")
        return 0
    else:
        print("\n⚠️  部分测试失败，请查看上面的详细信息。")
        print("\n故障排查:")
        print("  1. 运行: pip install -r requirements.txt")
        print("  2. 查看: TROUBLESHOOTING.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())
