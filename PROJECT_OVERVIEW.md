# 中国历史专家系统 - 项目总览

## 🎯 一句话介绍

通过查询权威历史辞典和古籍文献API，为Cursor Agent提供专业、可靠、有据可查的中国历史查询能力。

## 📦 项目组成

### Agent Skills (Cursor技能)
```
SKILL.md                    # 主技能：历史专家系统
├── dict/SKILL.md          # 子技能：历史辞典查询
└── cnkgraph/SKILL.md      # 子技能：古籍API查询
```

### 工具脚本
```
scripts/history_query.py        # 综合查询工具
dict/scripts/query_dict.py      # 辞典查询工具
cnkgraph/scripts/query_api.py   # API查询工具
test_system.py                  # 系统测试工具
```

### 文档体系
```
README.md              # 项目主文档
QUICKSTART.md          # 快速入门（10分钟上手）
EXAMPLES.md            # 使用示例（4个完整案例）
TROUBLESHOOTING.md     # 故障排查指南
SUMMARY.md             # 项目技术总结
COMPLETION.md          # 项目完成报告
dict/README.md         # 辞典模块文档
cnkgraph/README.md     # API模块文档
```

## 🚀 如何使用

### 最简单：在Cursor中使用

直接问历史问题，Agent自动调用：

```
你: 李白是哪个朝代的诗人？

Agent:
1. 自动读取技能文件
2. 查询历史辞典
3. 查询古籍API
4. 综合回答并引用原文
```

### 命令行使用

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 测试系统
python test_system.py

# 3. 查询
python scripts/history_query.py "李白"
```

## 📊 核心数据

### 数据源
- **本地辞典**: 4GB《中国历史大辞典4合1》
- **在线API**: 485M诗文库 + 2GB古籍库

### 查询能力
- ✅ 历史人物查询
- ✅ 历史事件查询
- ✅ 历史制度查询
- ✅ 诗词作品查询
- ✅ 古籍文献查询

### 质量保证
- ✅ 所有信息有据可查
- ✅ 严格的引用规范
- ✅ 双重验证机制

## 🎓 适用范围

**适合**: 中国古代历史（先秦至清末）、历史人物、事件、制度、诗词、文化

**不适合**: 现当代历史、外国历史、纯学术争议

## 📈 项目统计

- **Agent Skills**: 3个
- **Python脚本**: 4个
- **文档文件**: 9个
- **代码量**: ~800行
- **文档量**: ~3500行

## 🌟 技术亮点

1. **三层架构**: 主技能协调两个专业子技能
2. **双源验证**: 本地辞典提供定义，在线API提供原文
3. **标准引用**: 学术级别的引用格式
4. **完整文档**: 从入门到排错一应俱全
5. **开箱即用**: 安装依赖即可使用

## 💡 核心原则

1. **有据可查**: 所有回答基于真实查询
2. **双重验证**: 辞典 + 古籍
3. **严格引用**: 标注来源
4. **诚实原则**: 查不到就承认

## 📚 文档导航

| 文档 | 用途 | 阅读时间 |
|------|------|----------|
| README.md | 项目介绍和基本使用 | 5分钟 |
| QUICKSTART.md | 快速上手指南 | 10分钟 |
| EXAMPLES.md | 详细使用示例 | 15分钟 |
| TROUBLESHOOTING.md | 遇到问题时查看 | 按需 |
| SUMMARY.md | 技术架构和总结 | 10分钟 |
| dict/README.md | 辞典模块详解 | 10分钟 |
| cnkgraph/README.md | API模块详解 | 10分钟 |

## 🔧 技术栈

- **Python 3.6+**
- **mdict-utils**: MDX辞典查询
- **requests**: HTTP API调用
- **古籍文献知识图谱API**: 在线古籍数据

## 📝 示例问题

试试问这些问题：

1. 李白有哪些著名的诗？
2. 安史之乱对唐朝有什么影响？
3. 科举制度是什么时候开始的？
4. 如何理解苏轼的《念奴娇·赤壁怀古》？
5. 王安石变法的主要内容是什么？

## ✅ 项目状态

- [x] 核心功能完成
- [x] 文档完善
- [x] 测试通过
- [x] 可以使用

**版本**: 1.0  
**状态**: ✅ 生产就绪  
**创建**: 2026-02-01

---

## 快速链接

- 🚀 [快速开始](QUICKSTART.md)
- 🐍 [虚拟环境指南](VENV_GUIDE.md)
- 📖 [使用示例](EXAMPLES.md)
- 🔧 [故障排查](TROUBLESHOOTING.md)
- 📊 [技术总结](SUMMARY.md)

**立即开始**: 运行 `./setup_venv.sh` 自动设置，或在Cursor中问一个历史问题！📚
