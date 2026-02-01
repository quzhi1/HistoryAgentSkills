# 项目总结

## 项目概述

中国历史专家系统是一个基于权威历史辞典和古籍文献API的智能问答系统，为Cursor Agent提供专业的中国历史查询能力。

## 核心价值

### 1. 权威可靠
- 基于《中国历史大辞典4合1》专业工具书
- 查询古籍文献知识图谱网的原始史料
- 所有回答都有据可查

### 2. 双重验证
- 历史辞典：提供准确定义和专业解释
- 古籍原文：提供原始文献和史料证据
- 两者结合，确保答案的准确性和可靠性

### 3. 严格引用
- 所有信息都标注来源
- 区分辞典内容和古籍原文
- 遵循学术规范

## 技术架构

### 三层技能体系

```
┌─────────────────────────────────────────┐
│  中国历史专家系统 (SKILL.md)              │
│  - 协调查询流程                          │
│  - 综合分析回答                          │
└────────────┬────────────────────────────┘
             │
       ┌─────┴──────┐
       │            │
┌──────▼─────┐ ┌───▼──────────┐
│ 辞典查询    │ │ 古籍API查询   │
│ dict/      │ │ cnkgraph/    │
│ - 权威定义  │ │ - 原始史料    │
│ - 基本信息  │ │ - 诗词原文    │
└────────────┘ └──────────────┘
```

### 数据来源

1. **本地辞典**
   - 文件: `dict/历史辞典4合1.mdx` (4GB+)
   - 格式: MDX/MDD
   - 工具: mdict-utils
   - 查询: 精确、快速

2. **在线API**
   - 地址: https://open.cnkgraph.com
   - 资源: 诗文库(485M)、古籍库(2GB)
   - 格式: JSON
   - 特点: 实时、丰富

### 查询流程

```python
def answer_history_question(question):
    # 1. 分析问题
    keywords = extract_keywords(question)
    
    # 2. 查询辞典
    dict_results = [query_dict(kw) for kw in keywords]
    
    # 3. 查询API
    api_results = query_api(keywords)
    
    # 4. 综合回答
    answer = combine_results(dict_results, api_results)
    
    # 5. 格式化输出（带引用）
    return format_with_citations(answer)
```

## 文件结构

```
HistoryAgentSkills/
├── README.md                   # 项目说明
├── SKILL.md                    # 主技能（历史专家系统）
├── QUICKSTART.md               # 快速入门
├── EXAMPLES.md                 # 使用示例
├── TROUBLESHOOTING.md          # 故障排查
├── requirements.txt            # Python依赖
├── .gitignore                  # Git忽略规则
│
├── dict/                       # 辞典查询模块
│   ├── SKILL.md               # 辞典技能
│   ├── README.md              # 辞典文档
│   ├── 历史辞典4合1.mdx        # 辞典数据
│   ├── 历史辞典4in1.mdd        # 辞典资源
│   └── scripts/
│       └── query_dict.py      # 辞典查询脚本
│
├── cnkgraph/                   # API查询模块
│   ├── SKILL.md               # API技能
│   ├── README.md              # API文档
│   └── scripts/
│       └── query_api.py       # API查询脚本
│
└── scripts/                    # 综合工具
    └── history_query.py       # 综合查询脚本
```

## 核心功能

### 1. 辞典查询
- 精确查询历史词条
- 获取权威定义和解释
- 支持人物、事件、制度、地理等

### 2. 古籍检索
- 搜索诗词原文
- 查找古籍文献
- 查询历史人物和事件

### 3. 综合查询
- 自动协调辞典和API查询
- 综合分析历史问题
- 生成有据可查的回答

### 4. 引用规范
- 标准化的引用格式
- 区分辞典和古籍来源
- 提供古文翻译

## 使用方式

### 作为Cursor Agent Skill

最主要的使用方式，Agent自动调用：

```
用户: 李白是哪个朝代的诗人？

Agent:
1. 读取 SKILL.md 了解工作流程
2. 调用 dict 技能查询辞典
3. 调用 cnkgraph 技能查询API
4. 综合回答并引用原文
```

### 命令行工具

也可直接使用命令行：

```bash
# 辞典查询
python dict/scripts/query_dict.py "关键词"

# API查询
python cnkgraph/scripts/query_api.py poetry --author 李白

# 综合查询
python scripts/history_query.py "关键词"
```

### Python库

可以在代码中导入使用：

```python
from scripts.history_query import HistoryExpert

expert = HistoryExpert()
result = expert.comprehensive_query("李白")
```

## 适用场景

### ✅ 适合

- 中国古代历史问题（先秦至清末）
- 历史人物查询和介绍
- 历史事件背景和影响
- 历史制度文化解释
- 古代诗词鉴赏
- 古籍文献查询

### ❌ 不适合

- 现当代历史（资源限制）
- 纯学术争议问题
- 需要考古证据的问题
- 历史假设类问题
- 外国历史
- 实时新闻

## 技术特点

### 优点

1. **准确性高**: 基于权威资料
2. **可验证性**: 所有信息都有出处
3. **易用性**: Agent自动调用
4. **扩展性**: 可添加更多数据源
5. **离线能力**: 辞典支持离线查询

### 限制

1. **辞典文件大**: 约4GB，首次查询较慢
2. **API依赖网络**: 需要互联网连接
3. **非商业使用**: API限制商业用途
4. **中文限制**: 主要支持中文查询

## 依赖项

### Python包
- `mdict-utils`: 辞典查询 (>=1.3.0)
- `requests`: HTTP请求 (>=2.28.0)

### 外部资源
- 历史辞典MDX文件（已包含）
- 古籍文献知识图谱API（在线）

## 安装与使用

### 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 测试辞典
python dict/scripts/query_dict.py "李白"

# 3. 测试API
python cnkgraph/scripts/query_api.py poetry --author 李白

# 4. 在Cursor中使用
直接问历史问题，Agent会自动调用
```

详见: `QUICKSTART.md`

## 文档体系

- `README.md`: 项目整体介绍
- `QUICKSTART.md`: 快速入门指南
- `EXAMPLES.md`: 详细使用示例
- `TROUBLESHOOTING.md`: 故障排查
- `SUMMARY.md`: 项目总结（本文件）
- `dict/README.md`: 辞典模块文档
- `cnkgraph/README.md`: API模块文档

## 核心原则

### 1. 有据可查
所有回答必须基于查询结果，不能凭空推测。

### 2. 双重验证
辞典提供定义，古籍提供证据，两者结合。

### 3. 严格引用
必须标注来源，使用规范的引用格式。

### 4. 诚实原则
查不到就承认，不编造不猜测。

## 最佳实践

### 查询策略
1. 先查辞典获取准确定义
2. 再查API获取原始文献
3. 综合分析给出完整回答

### 引用规范
```markdown
根据《中国历史大辞典》：
「辞典原文」

据《古籍名》（朝代·作者）记载：
「古籍原文」
译文：翻译
```

### 质量保证
- 所有信息都要验证
- 所有引用都要标注
- 所有古文都要翻译
- 区分事实和分析

## 未来改进

### 可能的扩展

1. **更多数据源**
   - 添加更多历史辞典
   - 集成更多古籍API
   - 支持历史地图

2. **性能优化**
   - 添加查询缓存
   - 并发查询
   - 增量索引

3. **功能增强**
   - 支持模糊查询
   - 支持图片引用
   - 生成引用列表

4. **用户体验**
   - 可视化查询过程
   - 交互式问答
   - 查询历史记录

## 贡献指南

### 添加新技能

1. 在相应目录创建 `SKILL.md`
2. 编写技能说明和使用方法
3. 创建辅助脚本（如需要）
4. 更新主 `README.md`

### 改进现有功能

1. 修改对应的脚本
2. 更新文档
3. 测试功能
4. 提交变更

## 许可与使用限制

- **辞典**: 仅供个人学习研究
- **API**: 仅限非商业用途
- **代码**: MIT License

## 总结

中国历史专家系统通过整合权威历史辞典和古籍文献API，为Cursor Agent提供了专业、可靠的中国历史查询能力。系统遵循"有据可查"的核心原则，所有回答都基于真实的历史资料，并严格标注引用来源。

这个系统适合处理各类中国古代历史问题，从人物事件到诗词文化，都能给出准确、详实、有据可查的回答。

**核心优势**: 权威 + 原始 + 规范 = 可信赖

---

**项目创建**: 2026-02-01
**版本**: 1.0
**状态**: 已完成并可用 ✓
