# 快速入门指南

这个指南帮助你快速开始使用中国历史专家系统。

## 1. 安装依赖（5分钟）

### 推荐方式：使用虚拟环境

**强烈推荐使用虚拟环境**，这样可以隔离项目依赖，避免与系统Python或其他项目冲突。

```bash
# 进入项目目录
cd /Users/zhi.q/HistoryAgentSkills

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

你会看到命令行前面出现 `(venv)` 标记，表示虚拟环境已激活。

### 快捷方式：直接安装（不推荐）

如果不使用虚拟环境，也可以直接安装：

```bash
cd /Users/zhi.q/HistoryAgentSkills
pip install -r requirements.txt
```

这会安装两个必需的包：
- `mdict-utils`: 用于查询历史辞典
- `requests`: 用于调用古籍API

### 验证安装

```bash
# 验证mdict-utils
mdict --version

# 验证requests
python -c "import requests; print(requests.__version__)"
```

如果都能正常输出版本号，说明安装成功。

### 以后使用时

每次使用前，记得激活虚拟环境：

```bash
cd /Users/zhi.q/HistoryAgentSkills
source venv/bin/activate  # macOS/Linux
```

退出虚拟环境：

```bash
deactivate
```

## 2. 第一次查询（2分钟）

### 测试辞典查询

```bash
python dict/scripts/query_dict.py "李白"
```

如果成功，你会看到《中国历史大辞典》中关于李白的详细解释。

### 测试API查询

```bash
python cnkgraph/scripts/query_api.py poetry --author 李白 --keyword 月
```

如果成功，你会看到李白关于月的诗词列表。

### 综合查询

```bash
python scripts/history_query.py "李白"
```

这会执行完整的查询流程，同时查询辞典和API。

## 3. 在Cursor中使用（最简单）

在Cursor中，你只需要问历史问题，Agent会自动使用这些技能：

### 示例对话

**你**: 李白是哪个朝代的诗人？

**Agent**: 
- 自动读取 `SKILL.md`
- 调用 `mdict -q "李白" dict/历史辞典4合1.mdx`
- 调用古籍API查询李白的作品
- 综合整理后给你回答

**你**: 安史之乱是怎么回事？

**Agent**:
- 查询辞典获取事件基本信息
- 查询API获取相关古籍记载
- 查询相关人物（安禄山、史思明等）
- 给出完整的、有据可查的回答

## 4. 理解工作原理（3分钟）

### 三层技能结构

```
中国历史专家系统 (SKILL.md)
├── 历史辞典查询 (dict/SKILL.md)
│   └── 提供权威定义和准确信息
└── 古籍API查询 (cnkgraph/SKILL.md)
    └── 提供原始史料和文献证据
```

### 标准查询流程

```
用户问题
    ↓
步骤1: 分析问题，提取关键词
    ↓
步骤2: 查询历史辞典（准确定义）
    ↓
步骤3: 查询古籍API（原始文献）
    ↓
步骤4: 综合回答（引用原文）
```

### 引用格式

所有回答都要标注出处：

```markdown
根据《中国历史大辞典》：
「辞典原文」

据《古籍名》（朝代·作者）记载：
「古文原文」
译文：翻译
```

## 5. 常见使用场景

### 场景1: 查询历史人物

**问题类型**:
- "xxx是谁？"
- "xxx是哪个朝代的？"
- "xxx有什么作品？"

**系统操作**:
1. 查辞典获取人物基本信息
2. 查API获取人物相关诗文
3. 综合回答

### 场景2: 查询历史事件

**问题类型**:
- "xxx是怎么回事？"
- "xxx为什么会发生？"
- "xxx有什么影响？"

**系统操作**:
1. 查辞典获取事件概述
2. 查API获取相关史料记载
3. 查相关人物补充背景
4. 综合分析

### 场景3: 文学赏析

**问题类型**:
- "如何理解某首诗？"
- "某篇文章表达了什么？"

**系统操作**:
1. 查API获取作品原文
2. 查辞典了解作者和时代背景
3. 结合背景分析作品

### 场景4: 历史制度文化

**问题类型**:
- "科举制度是什么？"
- "某个制度是如何运作的？"

**系统操作**:
1. 查辞典获取制度定义和历史
2. 查API查找相关文献记载
3. 系统性解释

## 6. 最佳实践

### ✅ 推荐做法

1. **问题清晰具体**
   - 好：李白是哪个朝代的诗人？
   - 不好：李白的情况

2. **相信查询结果**
   - 所有回答基于查询结果
   - 引用原文准确无误

3. **多角度查询**
   - 查人物、查事件、查背景
   - 从多个词条获取完整信息

### ❌ 避免的错误

1. **不要凭记忆回答**
   - 必须先查询再回答

2. **不要编造引用**
   - 所有引用必须来自真实查询

3. **不要省略出处**
   - 每个引用都要标注来源

## 7. 故障排查

### 问题1: 找不到mdict命令

**解决**:
```bash
pip install mdict-utils
```

### 问题2: 辞典查询失败

**检查**:
- 辞典文件是否存在？
  ```bash
  ls -lh dict/*.mdx
  ```
- 关键词是否准确？尝试简化

### 问题3: API调用失败

**检查**:
- 网络是否正常？
  ```bash
  ping cnkgraph.com
  ```
- 关键词是否合适？尝试简化

### 问题4: 查询速度慢

**原因**:
- 首次查询需要建立索引
- 网络速度影响API调用

**解决**:
- 耐心等待首次查询
- 后续查询会快很多

## 8. 进阶使用

### 自定义查询脚本

可以基于提供的脚本创建自己的查询工具：

```python
from scripts.history_query import HistoryExpert

expert = HistoryExpert()

# 查询辞典
result = expert.query_dictionary("李白")
print(result)

# 查询API
poetry = expert.query_api_poetry(author="李白")
print(poetry)
```

### 批量查询

```bash
# 查询多个词条
python dict/scripts/query_dict.py "李白" "杜甫" "白居易"
```

### 结果保存

```bash
# 保存查询结果
python dict/scripts/query_dict.py "李白" > output.txt
```

## 9. 获取帮助

### 查看文档

- 主README: `/Users/zhi.q/HistoryAgentSkills/README.md`
- 使用示例: `/Users/zhi.q/HistoryAgentSkills/EXAMPLES.md`
- 辞典文档: `dict/README.md`
- API文档: `cnkgraph/README.md`

### 查看技能说明

- 主技能: `SKILL.md`
- 辞典技能: `dict/SKILL.md`
- API技能: `cnkgraph/SKILL.md`

### 脚本帮助

```bash
# 辞典查询帮助
python dict/scripts/query_dict.py --help

# API查询帮助
python cnkgraph/scripts/query_api.py --help
```

## 10. 开始使用！

现在你已经准备好了。在Cursor中直接问历史问题，Agent会自动使用这些技能为你查询和回答！

**试试这些问题**:
- 李白有哪些著名的诗？
- 安史之乱对唐朝有什么影响？
- 科举制度是什么时候开始的？
- 如何理解苏轼的《念奴娇·赤壁怀古》？

祝你使用愉快！📚
