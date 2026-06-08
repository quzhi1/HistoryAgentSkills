# 虚拟环境使用指南

## 为什么使用虚拟环境？

虚拟环境（Virtual Environment）可以：

1. ✅ **隔离依赖**：不同项目的依赖不会相互干扰
2. ✅ **版本管理**：可以为每个项目使用不同版本的包
3. ✅ **清洁环境**：避免污染系统Python环境
4. ✅ **易于复现**：通过requirements.txt轻松在其他机器上复现环境
5. ✅ **权限问题**：不需要sudo就可以安装包

## 快速开始

### 1. 自动创建虚拟环境并安装依赖

macOS / Linux:

```bash
cd /path/to/HistoryAgentSkills
./setup_venv.sh
```

Windows PowerShell:

```powershell
cd C:\path\to\HistoryAgentSkills
.\setup_venv.ps1
```

跨平台通用方式：

```bash
python setup_venv.py
```

这会创建一个名为 `venv` 的文件夹，包含独立的 Python 环境，并安装 `requirements.txt` 里的依赖。

### 2. 使用项目

```bash
# 跨平台 runner，不需要激活虚拟环境
python scripts/run_in_venv.py test_system.py

# 查询辞典
python scripts/run_in_venv.py mdict -q "李白" dict/历史辞典4合1.mdx

# API查询
python scripts/run_in_venv.py cnkgraph/scripts/query_api.py poetry --author 李白
```

macOS/Linux 也可以直接调用 `venv/bin/python` / `venv/bin/mdict`；Windows PowerShell 对应用 `venv\Scripts\python.exe` / `venv\Scripts\mdict.exe`。

### 3. 是否需要激活虚拟环境？

不需要。项目脚本和文档推荐直接调用 venv 内的可执行文件或 `scripts/run_in_venv.py`。如果你手工激活也可以：

```bash
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

## 常见问题

### Q: 需要每次都激活虚拟环境吗？

A: 不需要。推荐直接用跨平台 runner：

```bash
cd /path/to/HistoryAgentSkills
python scripts/run_in_venv.py test_system.py
```

### Q: 如何判断虚拟环境是否已激活？

A: 看命令行前面是否有 `(venv)` 标记：

```
# 已激活
(venv) zhi.q@MacBook HistoryAgentSkills %

# 未激活
zhi.q@MacBook HistoryAgentSkills %
```

### Q: 可以删除虚拟环境吗？

A: 可以。虚拟环境只是一个文件夹，删除后重新创建即可：

```bash
# 删除虚拟环境
rm -rf venv

# 重新创建
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Q: 虚拟环境占用多少空间？

A: 本项目的虚拟环境大约占用 50-100MB 空间，主要是Python解释器和依赖包。

### Q: 在Cursor中使用时需要激活虚拟环境吗？

A: 在Cursor中作为Agent Skill使用时，Cursor会自动处理Python环境。但如果你手动运行脚本，建议激活虚拟环境。

### Q: 不使用虚拟环境可以吗？

A: 可以，但不推荐。不使用虚拟环境可能导致：
- 依赖冲突
- 系统Python环境混乱
- 权限问题（可能需要sudo）
- 难以在其他机器上复现环境

## 最佳实践

### 1. 项目结构

```
HistoryAgentSkills/
├── venv/                  # 虚拟环境（已在.gitignore中）
├── requirements.txt       # 依赖清单
└── ...其他文件
```

### 2. 工作流程

```bash
# 每天开始工作
cd /path/to/HistoryAgentSkills
source venv/bin/activate

# ... 工作中 ...

# 结束工作
deactivate
```

### 3. 添加新依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装新包
pip install package-name

# 更新requirements.txt
pip freeze > requirements.txt
```

### 4. Shell别名（可选）

为了方便，可以添加别名到 `~/.zshrc` 或 `~/.bashrc`：

```bash
# 添加到 ~/.zshrc
alias history-env='cd /path/to/HistoryAgentSkills && source venv/bin/activate'
```

然后就可以用一个命令激活：
```bash
history-env
```

## 在不同系统上设置

### macOS

```bash
# 安装Python 3（如果还没有）
brew install python3

# 创建虚拟环境
python3 -m venv venv

# 激活
source venv/bin/activate
```

### Linux

```bash
# 安装Python 3和venv（Ubuntu/Debian）
sudo apt update
sudo apt install python3 python3-venv

# 创建虚拟环境
python3 -m venv venv

# 激活
source venv/bin/activate
```

### Windows

```cmd
# 创建虚拟环境
python -m venv venv

# 激活
venv\Scripts\activate
```

## VS Code 集成

如果使用VS Code，可以自动识别虚拟环境：

1. 按 `Cmd+Shift+P` (macOS) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 输入 "Python: Select Interpreter"
3. 选择 `./venv/bin/python`

VS Code会自动在打开终端时激活虚拟环境。

## 故障排查

### 问题1: python3命令找不到

**解决**：使用 `python` 代替 `python3`：
```bash
python -m venv venv
```

### 问题2: venv模块不存在

**解决**：
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# 或使用virtualenv
pip install virtualenv
virtualenv venv
```

### 问题3: 激活脚本找不到

**解决**：确认虚拟环境已正确创建：
```bash
ls venv/bin/  # macOS/Linux
dir venv\Scripts\  # Windows
```

应该能看到 `activate` 脚本。

### 问题4: pip安装失败

**解决**：升级pip：
```bash
python -m pip install --upgrade pip
```

## 总结

**推荐使用虚拟环境**，步骤很简单：

```bash
# 一次性设置
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 以后每次使用
cd /path/to/HistoryAgentSkills
source venv/bin/activate
# ... 使用项目 ...
deactivate
```

这是Python开发的最佳实践，强烈推荐！🎯
