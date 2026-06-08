# 史料检索.skill

一个跑在 Claude Code 上的中国历史问答 skill。基于《中国历史大辞典》和 [cnkgraph](https://cnkgraph.com) 古籍知识图谱 API，回答问题时**必查两边、必引出处（书名 + 章节名）、查不到就说查不到、绝不编造**。

适用范围：先秦至清末的人物、事件、制度、文学作品、文化常识。

---

## 数据资源

| 资源 | 形式 | 用途 |
|------|------|------|
| 《中国历史大辞典4合1》 | 本地 MDX 文件（约 4GB） | 权威定义、史料出处线索 |
| cnkgraph 古籍 API | HTTP 接口 [open.cnkgraph.com](https://open.cnkgraph.com/swagger) | 古籍原文片段、诗词、人物、书目、年号纪年换算 |
| 史料学 EPUB | `books/` 本地 EPUB + SQLite FTS 缓存 | 搜集史料前判断检索方向 |
| CHGIS/TGAZ + `cnmaps-data` | TGAZ HTTP API + 本地现代行政区边界 | 古地名坐标查询与现代省/市/区县反查 |
| 左图右史 | [history-map.osgeo.cn](https://history-map.osgeo.cn/) + `data/history_map_index.json` | 同一时代、同一一级行政区历史地图链接 |
| 识典古籍 | [shidianguji.com/zh/search](https://www.shidianguji.com/zh/search) | 原文短引的可验证章节链接 |
| 书目链接索引 | `data/source_book_index.sqlite` | SQLite 点查索引；保存识典/cnkgraph 书目和两边同名书的一对多 crosswalk |

辞典文件需自行获取放到 `dict/历史辞典4合1.mdx`。cnkgraph API 仅限非商业用途。

---

## 安装

### 一、搭项目环境（必做）

```bash
cd /Users/zhi.q/HistoryAgentSkills
./setup_venv.sh
```

脚本会建 venv、装依赖（`mdict-utils` + `requests` + `cnmaps-data` + `opencc-python-reimplemented`）、跑一次自检。完成后 `venv/bin/mdict` 和 `venv/bin/python` 即可直接调用，**不需要** `source venv/bin/activate`。

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
若材料或草稿答案中出现年号纪年，会通过 cnkgraph Calendar API 换算为公元纪年；若最终回答保留古地名，会先列出地名清单，通过 CHGIS/TGAZ + 现代边界库逐一查询今地，并在正文首次出现处自然括注，如“深州乐寿（今河北省沧州市献县）”；若辞典/原文能确认同代一级行政区，会附左图右史地图链接；原文短引必须逐条用识典验证，首次 `not_found` 不得直接省略链接，需换关键词、别名、篇名/卷名或短引二次验证，优先改用可解析到识典原文章节的短引。史料原文与现代汉语译文必须分别另起一段，不混在正文叙述里。搜集史料前可先检索本地史料学 EPUB 判断方向。

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

# 古地名今地映射（TGAZ 坐标 + 现代行政边界反查）
venv/bin/python scripts/place_resolver.py "顺天府" --year 1800
venv/bin/python scripts/place_resolver.py "长安" --year 755 --json

# 左图右史同代一级行政区地图链接（admin 必须由辞典/原文确认）
venv/bin/python scripts/history_map_link.py --place "济南" --year 1582 --dynasty "明" --admin "山东布政司" --json

# 刷新左图右史索引；输出浏览器可打开的 hash route（/#/pageNN/html?...）
venv/bin/python scripts/update_history_map_index.py

# 识典古籍原文章节链接验证
venv/bin/python scripts/shidian_link.py --source "《魏书》卷三五《崔浩传》" --quote "崔浩字伯渊清河人也" --keyword "崔浩" --json

# 刷新识典/cnkgraph 书目链接索引
venv/bin/python scripts/update_source_book_index.py --verbose

# 不联网，只基于现有 SQLite 重建 normalized_title 与 crosswalk
venv/bin/python scripts/update_source_book_index.py --from-existing

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
│
├── scripts/
│   ├── history_query.py            # 综合查询脚本（史料方向 + 年号 + 辞典 + API）
│   ├── dynasty_converter.py        # 通过 cnkgraph Calendar API 换算年号纪年
│   ├── place_resolver.py           # CHGIS/TGAZ 古地名今地映射
│   ├── history_map_link.py         # 左图右史同代一级行政区链接
│   ├── shidian_link.py             # 识典古籍原文章节链接验证
│   ├── source_book_index.py        # 识典/cnkgraph 书目索引读取与匹配
│   ├── update_history_map_index.py # 刷新左图右史路由索引
│   ├── update_source_book_index.py # 刷新识典/cnkgraph 书目链接索引
│   └── book_search.py              # EPUB 全文检索器
│
├── data/
│   ├── history_map_index.json      # 左图右史精简 route 索引
│   └── source_book_index.sqlite    # 识典/cnkgraph 书目 + crosswalk 点查索引
│
├── HISTORICAL_SOURCES_GUIDE.md     # 二十四史引用指南
├── COMMON_MISTAKES.md              # 历史踩坑记录（修改规则前必读）
└── ENVIRONMENT_SETUP.md            # 环境配置详解
```

---

## 核心原则

1. **必查两边**：辞典 + cnkgraph，缺一不可。只查辞典作答 = 违规。
2. **史料引用必须包含书名 + 章节名**：✅《魏书》卷三五《崔浩传》｜❌《魏书》记载｜❌ 据史书记载
3. **最终回答必须有史料原文短引和译文**：人物、事件、制度类回答不能只给出处或白话概括；原文和现代汉语译文必须分别另起一段
4. **必须补全六类细节**：时间、地点、相关人物、起因、经过、结果
5. **年号纪年必须保留并换算**：如天宝十四载 → 天宝十四载（公元755年）；不得只写公元年替代史料年号
6. **古地名首次出现必须标注今地**：凡最终回答保留顺天府、晋阳、长安、凤翔等古地名，先建清单，查 CHGIS/TGAZ 并用现代边界反查；正文首次出现处必须自然括注，如“深州乐寿（今河北省沧州市献县）”，不输出内部技术依据，不等同古今辖境，也不能只在文末补地点清单
7. **左图右史只给同代同一级行政区链接**：必须先由辞典/原文确认历史一级区划，不能用现代省份反推；匹配不到就不猜；链接必须来自 `data/history_map_index.json` 中的 `/#/pageNN/html?...` hash route，不手写 `/pageNN/html?...` 直连路径
8. **识典原文链接必须验证并追踪失败**：只有短引与出处能匹配到章节页，且 `matched_source` 所属书名与所引原书或公认同书别名一致时，才写“识典原文”；首次 `not_found`、查询失败或命中后代类书/总集/别集/注释书/转引页时，必须换关键词、原书别名、篇名/卷名、短引或出处二次验证，优先改用可 `resolved` 的原始短引；不能把检索页或转引页冒充原书链接，也不能静默省略失败
9. **EPUB 只作方向**：本地史料学书籍可帮助推断应查哪些史料，但不能替代辞典与古籍原文
10. **查不到就说查不到**——绝不基于训练数据补全、绝不编造原文、绝不"古代应该有……"

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
- ✅ 最终答案要保留关键史料原文短引和年号纪年；不要用过去回答或辞典摘要替代重新整理
- ✅ 古地名今地映射使用 `scripts/place_resolver.py`；最终回答中保留的每个古地名，首次出现处都要括注今地；如果返回歧义、无坐标或无边界命中，必须用自然语言如实说明，不输出脚本状态码或内部实现细节
- ✅ 左图右史链接使用 `scripts/history_map_link.py`；`--admin` 必须是辞典/原文确认的同时代一级行政区，脚本返回 `resolved` 才能写进答案
- ✅ 识典原文链接使用 `scripts/shidian_link.py`；脚本会读取 `data/source_book_index.sqlite` 的 crosswalk 表优先核对识典书页与 cnkgraph 书名。返回 `resolved` 且 `matched_source` 原书名核对通过，才能写 `[识典原文](...)`；若候选是后代转引或异书，或返回 `not_found` / `invalid` / 查询失败，必须重新收窄 `--quote` / `--keyword`、改用原书别名或篇名/卷名，优先换成可 `resolved` 的同义证据短引；仍不能确认时要在答案中明示“识典原文链接二次验证未通过”
- ✅ 书目链接索引用 `scripts/update_source_book_index.py` 刷新；识典来自 sitemap 书页，cnkgraph 来自 `GET /api/Book` 及 `GET /api/Book/{部}/{类}`，`crosswalk` 只做归一化书名能对应上的一对多候选，不手写或猜测书页链接
- ✅ 修改任何核心规则前，先看 [COMMON_MISTAKES.md](COMMON_MISTAKES.md) 历史踩坑

---

## License

- 《中国历史大辞典》：仅供个人学习研究使用
- cnkgraph API：仅限非商业用途
- 本项目代码：MIT
