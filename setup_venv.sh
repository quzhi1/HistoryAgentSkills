#!/bin/bash

# 中国历史专家系统 - 快速设置脚本
# 自动创建虚拟环境并安装依赖

set -e  # 遇到错误立即退出

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║          中国历史专家系统 - 环境设置                              ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
echo "📋 检查Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ 未找到Python，请先安装Python 3.6+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
echo "✓ 找到 $PYTHON_VERSION"
echo ""

# 创建虚拟环境
if [ -d "venv" ]; then
    echo "⚠️  虚拟环境已存在，跳过创建"
else
    echo "📦 创建虚拟环境..."
    $PYTHON_CMD -m venv venv
    echo "✓ 虚拟环境创建成功"
fi
echo ""

# 激活虚拟环境
echo "🔌 激活虚拟环境..."
source venv/bin/activate
echo "✓ 虚拟环境已激活"
echo ""

# 升级pip
echo "⬆️  升级pip..."
pip install --upgrade pip -q
echo "✓ pip已升级"
echo ""

# 安装依赖
echo "📥 安装项目依赖..."
pip install -r requirements.txt
echo "✓ 依赖安装完成"
echo ""

# 测试安装
echo "🧪 测试安装..."
if command -v mdict &> /dev/null; then
    echo "✓ mdict-utils 已安装"
else
    echo "⚠️  mdict命令未找到，但包可能已安装"
fi

if python -c "import requests" 2> /dev/null; then
    echo "✓ requests 已安装"
else
    echo "❌ requests 安装失败"
fi
echo ""

# 完成
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║          ✅ 环境设置完成！                                         ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "下一步："
echo "  1. 测试系统: python test_system.py"
echo "  2. 查询辞典: python dict/scripts/query_dict.py '李白'"
echo "  3. 在Cursor中直接问历史问题！"
echo ""
echo "以后使用时，记得先激活虚拟环境："
echo "  source venv/bin/activate"
echo ""
echo "退出虚拟环境："
echo "  deactivate"
echo ""
