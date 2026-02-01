# 环境配置指南

## 常见问题：未安装 mdict

### 错误信息

```
当前环境未安装 mdict，无法直接查《中国历史大辞典》MDX。
```

或

```
mdict: command not found
```

### 原因

这个错误通常是因为：
1. ❌ **未激活虚拟环境**（最常见）
2. ❌ 虚拟环境损坏
3. ❌ 依赖包未安装

## 解决方案

### 方案1：激活虚拟环境（推荐）⭐

```bash
# 1. 进入项目目录
cd /Users/zhi.q/HistoryAgentSkills

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 验证 mdict 是否可用
which mdict
mdict --version

# 4. 现在可以查询了
python dict/scripts/query_dict.py "李白"
```

**成功标志**：
- 命令行前面出现 `(venv)` 标记
- `which mdict` 返回 `.../venv/bin/mdict`

### 方案2：使用完整路径

如果不想激活虚拟环境，可以直接使用完整路径：

```bash
cd /Users/zhi.q/HistoryAgentSkills

# 直接使用虚拟环境中的 mdict
venv/bin/mdict -q "李白" dict/历史辞典4合1.mdx
```

### 方案3：重新安装（如果虚拟环境损坏）

```bash
cd /Users/zhi.q/HistoryAgentSkills

# 删除旧的虚拟环境
rm -rf venv

# 重新创建并安装
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 验证
mdict --version
```

### 方案4：使用自动设置脚本

```bash
cd /Users/zhi.q/HistoryAgentSkills
./setup_venv.sh
```

## 验证环境

### 快速检查

```bash
cd /Users/zhi.q/HistoryAgentSkills

# 检查虚拟环境是否存在
ls -d venv

# 检查 mdict 是否在虚拟环境中
ls venv/bin/mdict

# 激活并测试
source venv/bin/activate
mdict --version
```

### 完整测试

```bash
cd /Users/zhi.q/HistoryAgentSkills
source venv/bin/activate

# 运行系统测试
python test_system.py

# 测试辞典查询
python dict/scripts/query_dict.py "李白"
```

## 在 Cursor Agent 中使用

### 正确的做法

当 Agent 需要查询辞典时，应该：

```bash
# 方式1：激活虚拟环境后查询
cd /Users/zhi.q/HistoryAgentSkills && source venv/bin/activate && mdict -q "李白" dict/历史辞典4合1.mdx

# 方式2：使用完整路径
cd /Users/zhi.q/HistoryAgentSkills && venv/bin/mdict -q "李白" dict/历史辞典4合1.mdx
```

### 错误的做法

❌ 直接运行 `mdict`（如果虚拟环境未激活）
```bash
mdict -q "李白" dict/历史辞典4合1.mdx  # 错误！
```

## 环境检查清单

使用前检查：

- [ ] 是否在项目根目录？
  ```bash
  pwd  # 应该是 /Users/zhi.q/HistoryAgentSkills
  ```

- [ ] 虚拟环境是否存在？
  ```bash
  ls venv/bin/mdict  # 应该存在
  ```

- [ ] 虚拟环境是否激活？
  ```bash
  echo $VIRTUAL_ENV  # 应该不为空
  # 或查看命令行前缀是否有 (venv)
  ```

- [ ] mdict 是否可用？
  ```bash
  which mdict  # 应该指向 venv/bin/mdict
  ```

- [ ] 辞典文件是否存在？
  ```bash
  ls dict/历史辞典4合1.mdx  # 应该存在
  ```

## 常见错误和解决

### 错误1：bash: mdict: command not found

**原因**：未激活虚拟环境

**解决**：
```bash
source venv/bin/activate
```

### 错误2：No such file or directory: 'mdict'

**原因**：Python脚本无法找到 mdict 命令

**解决**：
```bash
# 先激活虚拟环境再运行脚本
source venv/bin/activate
python dict/scripts/query_dict.py "李白"
```

### 错误3：找不到辞典文件

**原因**：不在项目根目录

**解决**：
```bash
cd /Users/zhi.q/HistoryAgentSkills
pwd  # 确认目录
ls dict/*.mdx  # 确认文件存在
```

### 错误4：Permission denied

**原因**：脚本没有执行权限

**解决**：
```bash
chmod +x dict/scripts/query_dict.py
chmod +x setup_venv.sh
```

## 技术说明

### 为什么需要虚拟环境？

1. **隔离依赖**：不污染系统 Python 环境
2. **版本管理**：每个项目独立的包版本
3. **权限问题**：不需要 sudo 安装包
4. **可复现性**：便于在其他机器上重建环境

### mdict-utils 的安装位置

```
HistoryAgentSkills/
└── venv/
    ├── bin/
    │   └── mdict          # mdict 命令在这里
    └── lib/
        └── python3.x/
            └── site-packages/
                └── mdict/  # mdict-utils 包在这里
```

### 虚拟环境激活的作用

激活虚拟环境时，系统会：
1. 修改 `$PATH`，将 `venv/bin` 放在最前面
2. 设置 `$VIRTUAL_ENV` 变量
3. 修改命令行提示符（显示 `(venv)`）

这样运行 `mdict` 时，系统会自动找到 `venv/bin/mdict`。

## 最佳实践

### 开发时

```bash
# 每次开始工作
cd /Users/zhi.q/HistoryAgentSkills
source venv/bin/activate

# ... 工作 ...

# 结束时
deactivate
```

### 在脚本中

```python
#!/usr/bin/env python3
import shutil

# 检查 mdict 是否可用
if not shutil.which('mdict'):
    print("错误：请先激活虚拟环境")
    print("运行: source venv/bin/activate")
    sys.exit(1)
```

### 在 Agent 中

```bash
# 总是包含虚拟环境激活
cd /Users/zhi.q/HistoryAgentSkills && source venv/bin/activate && mdict -q "关键词" dict/历史辞典4合1.mdx
```

## 故障排查流程

```
1. 是否在项目目录？
   ├─ 否 → cd /Users/zhi.q/HistoryAgentSkills
   └─ 是 → 继续

2. 虚拟环境是否存在？
   ├─ 否 → ./setup_venv.sh
   └─ 是 → 继续

3. 虚拟环境是否激活？
   ├─ 否 → source venv/bin/activate
   └─ 是 → 继续

4. mdict 是否可用？
   ├─ 否 → pip install mdict-utils
   └─ 是 → 可以查询了！

5. 辞典文件是否存在？
   ├─ 否 → 检查文件路径
   └─ 是 → 开始查询
```

## 快速参考

```bash
# 激活环境
cd /Users/zhi.q/HistoryAgentSkills && source venv/bin/activate

# 查询辞典
mdict -q "关键词" dict/历史辞典4合1.mdx

# 或使用脚本
python dict/scripts/query_dict.py "关键词"

# 退出环境
deactivate
```

## 获取帮助

如果以上方法都无法解决：

1. 查看完整安装指南：`QUICKSTART.md`
2. 查看虚拟环境指南：`VENV_GUIDE.md`
3. 查看故障排查：`TROUBLESHOOTING.md`
4. 运行系统测试：`python test_system.py`

---

**记住**：90%的环境问题都是因为**忘记激活虚拟环境**！

使用前先运行：
```bash
source venv/bin/activate
```
