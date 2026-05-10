# 史料检索.skill

一个跑在 Claude Code 上的中国历史问答 skill。基于《中国历史大辞典》和 [cnkgraph](https://cnkgraph.com) 古籍知识图谱 API，回答问题时**必查两边、必引出处（书名 + 章节名）、查不到就说查不到、绝不编造**。

适用范围：先秦至清末的人物、事件、制度、文学作品、文化常识。

---

## 数据资源

| 资源 | 形式 | 用途 |
|------|------|------|
| 《中国历史大辞典4合1》 | 本地 MDX 文件（约 4GB） | 权威定义、史料出处线索 |
| cnkgraph 古籍 API | HTTP 接口 [open.cnkgraph.com](https://open.cnkgraph.com/swagger) | 古籍原文片段、诗词、人物、书目 |
| 上海图书馆中国历史纪年表 | 本地 JSON 索引，来源 [data.library.sh.cn](https://data.library.sh.cn/dynasty/main) | 年号纪年换算为公元纪年 |
| 史料学 EPUB | `books/` 本地 EPUB + SQLite FTS 缓存 | 搜集史料前判断检索方向 |

辞典文件需自行获取放到 `dict/历史辞典4合1.mdx`。cnkgraph API 仅限非商业用途。
上海图书馆年表数据须 credit 上海图书馆开放数据平台；非特别注明，遵循 CC2.0（署名-非商业性使用-相同方式共享）。

---

## 安装

### 一、搭项目环境（必做）

```bash
cd /Users/zhi.q/HistoryAgentSkills
./setup_venv.sh
```

脚本会建 venv、装依赖（`mdict-utils` + `requests`）、跑一次自检。完成后 `venv/bin/mdict` 和 `venv/bin/python` 即可直接调用，**不需要** `source venv/bin/activate`。

### 二、全局注册到 Claude Code（推荐）

```bash
./install-global.sh
```

脚本会在 `~/.claude/` 下放三样东西：

- `skills/chinese-history-expert/SKILL.md` — 全局触发入口（stub，把 Claude 引导回项目）
- `commands/history.md` → 项目内文件的 symlink
- `agents/history-fact-checker.md` → 项目内文件的 symlink

装完之后，**在任何目录启动 `claude`** 都能用本 skill。改规则只改项目内的文件，全局自动生效（symlink 单一真理源）。

不想全局注册也行，跳过这一步，本 skill 仍可在项目目录内使用。

---

## 使用方式（在 Claude Code 里）

### 方式 1：直接问历史问题

```
> 崔浩国史之狱是怎么回事？
> 王安石变法的主要内容有哪些？
> 李白《将进酒》的创作背景？
```

Claude Code 识别为中国历史问题后会自动触发本 skill，按 `SKILL.md` 工作流答题：查辞典 → 查 cnkgraph 古籍片段 → 标书名+章节名 → 补全六类细节（时间、地点、相关人物、起因、经过、结果）。
若材料中出现年号纪年，会先用本地年表程序换算为公元纪年；搜集史料前可先检索本地史料学 EPUB 判断方向。

### 方式 2：`/history` 斜杠命令

```
> /history 安史之乱
> /history 苏轼
```

一键跑 `scripts/history_query.py` 综合查询脚本，再让 Claude 按规范整理输出。适合"我已经有明确关键词，想直接拿结果"的场景。

### 方式 3：用 fact-checker 校验回答

任何历史回答给出后，可以让独立的 subagent 复查每一条引用：

```
> 用 history-fact-checker 校验上面这段回答
```

它会重跑 mdict / cnkgraph 验证每条史料，输出**通过 / 有瑕疵 / 不通过**报告，列出哪条引用篡改了原文、哪条卷章对不上、哪句没引用就陈述了内容。**它不重写答案**——只挑错。

### 方式 4：命令行直接调用

不进 Claude Code，直接跑：

```bash
# 综合查询
venv/bin/python scripts/history_query.py "李白"

# 年号纪年换算
venv/bin/python scripts/dynasty_converter.py "天宝十四载"
venv/bin/python scripts/dynasty_converter.py "唐 天宝三载" --json

# 下载/重建上海图书馆年表 JSON 数据
venv/bin/python scripts/fetch_dynasty_data.py --rebuild

# 检索本地史料学 EPUB（只作搜集方向参考）
venv/bin/python scripts/book_search.py "甲骨文" --limit 5

# 仅查辞典
venv/bin/mdict -q "安史之乱" dict/历史辞典4合1.mdx

# 古籍原文片段（关键词 2–6 字，超 8 字常 404）
venv/bin/python cnkgraph/scripts/query_api.py find --keyword "崔浩"

# 诗词 / 人物 / 古籍书目
venv/bin/python cnkgraph/scripts/query_api.py poetry --author 李白 --keyword 月
venv/bin/python cnkgraph/scripts/query_api.py people --name 苏轼
venv/bin/python cnkgraph/scripts/query_api.py book --keyword 崔浩
```

---

## 项目结构

```
HistoryAgentSkills/
├── CLAUDE.md                       # Claude Code 进项目时必读的操作守则与红线
├── SKILL.md                        # 主 skill：详细工作流程、回答模板、引用规范
├── README.md                       # 本文件
├── install-global.sh               # 一键全局注册到 ~/.claude/
├── setup_venv.sh                   # 一键搭虚拟环境
├── requirements.txt                # Python 依赖
├── test_system.py                  # 系统自检
│
├── .claude/
│   ├── commands/history.md         # /history 斜杠命令
│   └── agents/history-fact-checker.md   # 史料校验 subagent
│
├── dict/                           # 辞典子 skill
│   ├── SKILL.md
│   ├── 历史辞典4合1.mdx            # （需自备，约 4GB）
│   └── scripts/query_dict.py
│
├── cnkgraph/                       # cnkgraph API 子 skill
│   ├── SKILL.md
│   └── scripts/query_api.py
│
├── books/                          # 史料学 EPUB（本地检索来源）
├── data/dynasty/                   # 上海图书馆年表 JSON 与本地索引
│   ├── dynasty_index.json
│   ├── metadata.json
│   └── raw/
│
├── scripts/
│   ├── history_query.py            # 综合查询脚本（史料方向 + 年号 + 辞典 + API）
│   ├── fetch_dynasty_data.py       # 下载上海图书馆年表 JSON
│   ├── dynasty_converter.py        # 年号纪年换算为公元纪年
│   └── book_search.py              # EPUB 全文检索器
│
├── HISTORICAL_SOURCES_GUIDE.md     # 二十四史引用指南
├── COMMON_MISTAKES.md              # 历史踩坑记录（修改规则前必读）
└── ENVIRONMENT_SETUP.md            # 环境配置详解
```

---

## 核心原则

1. **必查两边**：辞典 + cnkgraph，缺一不可。只查辞典作答 = 违规。
2. **史料引用必须包含书名 + 章节名**：✅《魏书》卷三五《崔浩传》｜❌《魏书》记载｜❌ 据史书记载
3. **必须补全六类细节**：时间、地点、相关人物、起因、经过、结果
4. **年号纪年必须换算**：如天宝十四载 → 天宝十四载（公元755年），来源 credit 上海图书馆开放数据平台
5. **EPUB 只作方向**：本地史料学书籍可帮助推断应查哪些史料，但不能替代辞典与古籍原文
6. **查不到就说查不到**——绝不基于训练数据补全、绝不编造原文、绝不"古代应该有……"

详细的反例与正例见 [COMMON_MISTAKES.md](COMMON_MISTAKES.md)。

---

## 适用 / 不适用

**适合回答**

- 中国古代（先秦至清末）的人物、事件、制度
- 古代文学作品的内容、背景
- 历史文化常识

**不适合回答**

- 现当代历史（资源不收录）
- 纯学术争议问题
- 需要考古证据的问题
- 历史假设类问题

---

## 注意事项

- ❌ 不要用 Read 工具直接读 `dict/历史辞典4合1.mdx`（约 4GB，会撑爆上下文），只能通过 `mdict -q` 查询
- ❌ 不要在 Claude Code 触发的命令里用 `source venv/bin/activate`——会被权限系统拦截，每次按回车确认。改用 `venv/bin/python` / `venv/bin/mdict` 直调
- ✅ 关键词控制 2–6 字，超过 8 字 cnkgraph 常 404；复杂问题用多次短查询交叉验证
- ✅ 修改任何核心规则前，先看 [COMMON_MISTAKES.md](COMMON_MISTAKES.md) 历史踩坑

---

## License

- 《中国历史大辞典》：仅供个人学习研究使用
- cnkgraph API：仅限非商业用途
- 本项目代码：MIT
