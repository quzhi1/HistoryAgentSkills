# 史料检索.skill

一个跑在 Claude Code 上的中国历史问答 skill。基于《中国历史大辞典》和 [cnkgraph](https://cnkgraph.com) 古籍知识图谱 API，回答问题时**必查两边、必引出处（书名 + 章节名）、必说明被引史料、查不到就说查不到、绝不编造**。

适用范围：先秦至清末的人物、事件、制度、文学作品、文化常识。

---

## 数据资源

| 资源 | 形式 | 用途 |
|------|------|------|
| 《中国历史大辞典4合1》 | 本地 MDX 文件（约 4GB） | 权威定义、史料出处线索 |
| cnkgraph 古籍 API | HTTP 接口 [open.cnkgraph.com](https://open.cnkgraph.com/swagger) | 古籍原文片段、诗词、人物、书目、年号纪年换算 |
| 史料学 EPUB | `books/` 本地 EPUB | 按需辅助判断搜集方向，不作事实证据 |
| CHGIS/TGAZ + `cnmaps-data` | TGAZ HTTP API + 本地现代行政区边界 | 古地名坐标查询与现代省/市/区县反查 |
| 现代定位反查 | `scripts/place_admin_resolver.py` | 用辞典/cnkgraph/TGAZ 沿革给出的现代或后世地名线索反查历史地名，并验证地图区划 |
| 左图右史 | [history-map.osgeo.cn](https://history-map.osgeo.cn/) + `data/history_map_index.json` | 同代一级区划或过渡期前朝区划历史地图链接 |
| 识典古籍 | [shidianguji.com/search](https://www.shidianguji.com/search) | 原文短引的可验证检索链接 |

辞典文件需自行获取放到 `dict/历史辞典4合1.mdx`。cnkgraph API 仅限非商业用途。

---

## 安装

### 一、搭项目环境（必做）

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

脚本会根据自身所在目录识别项目根目录，创建 `venv`、安装依赖（`mdict-utils` + `requests` + `cnmaps-data` + `opencc-python-reimplemented`）、跑一次自检。完成后可直接调用 venv 内命令：macOS/Linux 用 `venv/bin/python` / `venv/bin/mdict`，Windows 用 `venv\Scripts\python.exe` / `venv\Scripts\mdict.exe`；也可以统一用 `python scripts/run_in_venv.py ...`，**不需要** `source venv/bin/activate`。

### 二、全局注册到 Claude Code（推荐）

macOS / Linux:

```bash
./install-global.sh
```

Windows PowerShell:

```powershell
.\install-global.ps1
```

跨平台通用方式：

```bash
python install_global.py
```

安装脚本会从自身所在目录推导项目根目录，不需要手动改脚本里的路径。它会在 `~/.claude/` 下生成三样东西：

- `skills/chinese-history-expert/SKILL.md` — 全局触发入口（stub，把 Claude 引导回项目）
- `commands/history.md` — `/history` 命令（写入当前项目目录）
- `agents/history-fact-checker.md` — 史料校验 subagent（写入当前项目目录）

装完之后，**在任何目录启动 `claude`** 都能用本 skill。移动项目目录或修改全局入口模板后，重新运行安装脚本即可刷新全局文件；完整规则仍以项目内 `SKILL.md` 为单一真理源。

不想全局注册也行，跳过这一步，本 skill 仍可在项目目录内使用。

### 三、在 Claude 桌面版安装（.skill 文件）

Claude 桌面版使用打包后的 `.skill` 文件安装，**不能直接指向仓库目录**。

**打包步骤**（需先完成"一、搭项目环境"）：

```bash
# 把主 SKILL.md 单独暂存到临时目录，再打包
mkdir -p /tmp/chinese-history-expert
cp SKILL.md /tmp/chinese-history-expert/SKILL.md

# 用 skill-creator 的打包脚本（路径因安装不同而异，下面是示例）
python -m scripts.package_skill /tmp/chinese-history-expert
```

打包完成后会生成 `chinese-history-expert.skill` 文件。

> **为什么要单独暂存？** 本仓库在 `cnkgraph/` 和 `dict/` 子目录下各有一个 `SKILL.md`，打包脚本要求每个技能目录里有且仅有一个 `SKILL.md`，直接打包仓库根目录会报错。

**在桌面版安装**：

1. 打开 Claude 桌面版，进入 **Settings → Skills**
2. 点击 **Install from file**，选择上面生成的 `.skill` 文件
3. 安装后即可在对话中直接使用

> **注意**：本 skill 的辞典查询和脚本（`mdict`、`cnkgraph` 等）依赖本地环境。在 Claude 桌面版中，技能指令会加载到上下文，但本地工具调用需要 Claude Code 或命令行支持。如果只在桌面版使用，Claude 会按规范作答，但无法运行本地脚本查询辞典和 API。

---

### 四、在 ChatGPT 使用

`.skill` 格式是 Claude 专用的，**ChatGPT 不支持直接安装**。但可以把 `SKILL.md` 的正文内容作为系统提示使用：

1. 打开 ChatGPT，创建一个 **Custom GPT**（或在对话开头粘贴系统提示）
2. 将 `SKILL.md` 中 YAML frontmatter 以下的正文全部复制，粘贴到 System Prompt 或 Custom GPT Instructions 里
3. 同样，本地工具（辞典、cnkgraph API、脚本）在 ChatGPT 中无法运行；ChatGPT 会按文字规范作答，但史料查询结果依赖其自身训练数据，无法调用本地辞典

---

## 使用方式（在 Claude Code 里）

### 规则来源

完整 workflow 以 `SKILL.md` 为单一真理源；`AGENTS.md` 和 `CLAUDE.md` 只是 Codex / Claude Code 的最小入口文件，负责提示代理先读 `SKILL.md`，不再复制完整长规则。

### 方式 1：直接问历史问题

```
> 崔浩国史之狱是怎么回事？
> 王安石变法的主要内容有哪些？
> 李白《将进酒》的创作背景？
```

Claude Code 识别为中国历史问题后会自动触发本 skill，按 `SKILL.md` 工作流答题：查辞典 → 查 cnkgraph 古籍片段 → 标书名+章节名 → 补全六类细节（时间、地点、相关人物、起因、经过、结果）。
若材料或草稿答案中出现年号纪年，会通过 cnkgraph Calendar API 换算为公元纪年。原文短引必须逐条生成识典检索链接，每条短引的出处行都要附 `[识典检索](...)`，供读者用原文关键片段自行核查；每部被引用史料还必须按书名查询《中国历史大辞典》，并在史料依据之后给出简要“被引史料说明”；查不到该书介绍时要明说，不得凭常识补写。

史料原文、译文、证据作用必须分开：**译文只翻译原文**，不得混入“这说明……”或“如果按……来评”等分析。历史评价/比较题中，**每个评价或比较结论**都要回扣已查询的辞典或原文证据；像“宋也可以争”这类候选，如果没有原文短引、识典检索链接和被引史料说明，就不能写成结论。

若最终回答保留古地名，会先列出地名清单，通过 CHGIS/TGAZ + 现代边界库逐一查询今地，并在正文首次出现处自然括注，如“深州乐寿（今河北省沧州市献县）”；若保留地名直查失败但材料给出现代或后世定位线索，必须运行 `scripts/place_admin_resolver.py` 反查历史地名，把现代定位、目标年代候选地名、同代一级区划或过渡期前朝图标签闭环验证；随后先用《中国历史大辞典》和 cnkgraph 检索该地名在相应时代所隶属的同代一级行政区，再逐个运行 `scripts/history_map_link.py` 做左图右史核验。能确认同代一级区划时附地图链接；已确认一级区划但左图右史没有精确或替代专题图，可用 `--allow-overview` 返回 `overview` 同代时代总图；不能确认时要记录 `needs_admin` / `not_found` / `period_mismatch`，并在正文写明“不附左图右史链接”的原因。朝代/时期整体评价题可用 `--period-overview` 交付左图右史**朝代/时期总图**，但它不能替代具体古地名的今地和同代一级区划核验。多人物/列表型回答同样不能只写今地括注后静默省略地图核验。

遇到史料搜集、方法、证据类型选择等问题时，可先检索本地史料学 EPUB 判断方向；简单事实题不必跑，没跑就不能暗示引用过。

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
# 跨平台 runner（推荐给文档和全局命令使用）
python scripts/run_in_venv.py scripts/history_query.py "李白"
python scripts/run_in_venv.py mdict -q "安史之乱" dict/历史辞典4合1.mdx

# macOS/Linux 可直接调用 venv/bin；Windows PowerShell 对应 venv\Scripts\python.exe / mdict.exe

# 综合查询
venv/bin/python scripts/history_query.py "李白"

# 年号纪年换算
venv/bin/python scripts/dynasty_converter.py "天宝十四载"
venv/bin/python scripts/dynasty_converter.py "唐 天宝三载" --json

# 古地名今地映射（TGAZ 坐标 + 现代行政边界反查）
venv/bin/python scripts/place_resolver.py "顺天府" --year 1800
venv/bin/python scripts/place_resolver.py "长安" --year 755 --json

# 地名直查失败但材料给出现代/后世定位时，反查历史地名并验证地图 admin
venv/bin/python scripts/place_admin_resolver.py --place "少林寺" --year 625 --dynasty "唐" --modern "河南登封" --lookup-name "登封" --json

# 左图右史前置核验：先用辞典/cnkgraph 确认该时代同代一级行政区
venv/bin/mdict -q "汜水县" dict/历史辞典4合1.mdx
venv/bin/mdict -q "河南道" dict/历史辞典4合1.mdx
venv/bin/python cnkgraph/scripts/query_api.py find --keyword "汜水 河南道"

# 左图右史同代一级行政区地图链接（admin 必须是已核实的一级行政区）
venv/bin/python scripts/history_map_link.py --place "济南" --year 1582 --dynasty "明" --admin "山东布政司" --json

# 合并/分置期白名单替代页：1080 年淮南路匹配官方淮南东路专题页
venv/bin/python scripts/history_map_link.py --place "黄州" --year 1080 --dynasty "宋" --admin "淮南路" --json

# 王朝交替初期可用已核实的前朝区划图，例如唐武德四年仍用隋朝河南诸郡图
venv/bin/python scripts/history_map_link.py --place "汜水" --year 621 --dynasty "唐" --admin "河南诸郡" --json

# 若无法从材料确认 admin，也必须不传 --admin 跑一次并记录 needs_admin
venv/bin/python scripts/history_map_link.py --place "济南" --year 1582 --dynasty "明" --json

# 朝代/时期整体评价题：交付左图右史朝代/时期总图
venv/bin/python scripts/history_map_link.py --place "唐朝" --year 741 --dynasty "唐" --period-overview --json

# 刷新左图右史索引；输出浏览器可打开的 hash route（/#/pageNN/html?...）
venv/bin/python scripts/update_history_map_index.py

# 识典古籍检索链接生成
venv/bin/python scripts/shidian_link.py --source "《魏书》卷三五《崔浩传》" --quote "崔浩字伯渊清河人也" --keyword "崔浩" --json

# 按需检索本地史料学 EPUB（只作搜集方向参考，不作事实证据）
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
├── AGENTS.md                       # Codex 最小入口，指向 SKILL.md
├── CLAUDE.md                       # Claude Code 最小入口，指向 SKILL.md
├── SKILL.md                        # 主 skill：详细工作流程、回答模板、引用规范
├── README.md                       # 本文件
├── install-global.sh               # 一键全局注册到 ~/.claude/
├── install-global.ps1              # Windows PowerShell 全局注册入口
├── install_global.py               # 跨平台全局注册主实现
├── setup_venv.sh                   # 一键搭虚拟环境
├── setup_venv.ps1                  # Windows PowerShell 环境设置入口
├── setup_venv.py                   # 跨平台环境设置主实现
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
│   ├── place_admin_resolver.py     # 现代/后世定位线索反查历史地名与地图 admin
│   ├── history_map_link.py         # 左图右史同代一级行政区链接
│   ├── shidian_link.py             # 识典古籍检索链接生成
│   ├── run_in_venv.py              # 跨平台调用 venv 内命令，无需 activate
│   ├── venv_utils.py               # venv/bin 与 venv/Scripts 路径工具
│   ├── update_history_map_index.py # 刷新左图右史路由索引
│   └── book_search.py              # EPUB 全文检索器
│
├── data/
│   └── history_map_index.json      # 左图右史精简 route 索引
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
4. **每部被引用史料都要有简介**：按书名运行 `python scripts/run_in_venv.py mdict -q "史料书名" dict/历史辞典4合1.mdx`（或对应平台的 venv `mdict`），用《中国历史大辞典》结果说明作者/时代、体例、内容范围或史料性质；引用《古今图书集成》《永乐大典》等大型类书时，还要按实际引用层级查询并说明《方舆汇编》这类子编/子汇编，总书介绍只能补充，不能替代；查不到就明说，不能凭常识补写
5. **必须补全六类细节**：时间、地点、相关人物、起因、经过、结果
6. **年号纪年必须保留并换算**：如天宝十四载 → 天宝十四载（公元755年）；不得只写公元年替代史料年号
7. **古地名首次出现必须标注今地**：凡最终回答保留顺天府、晋阳、长安、凤翔等古地名，先建清单，查 CHGIS/TGAZ 并用现代边界反查；正文首次出现处必须自然括注，如“深州乐寿（今河北省沧州市献县）”，不输出内部技术依据，不等同古今辖境，也不能只在文末补地点清单
8. **左图右史逐地名核验，只给同代同一级行政区、过渡期前朝区划链接，或已标明限制的同代时代总图**：最终回答保留的每个古地名都要运行 `scripts/history_map_link.py`；运行前必须先用辞典/cnkgraph 检索该地点在相应时代所隶属的同代一级行政区，不能用州、府、郡、县或现代省份反推；若地名直查失败但材料给出现代/后世定位线索，先用 `scripts/place_admin_resolver.py` 反查历史地名并验证 admin；若处于王朝交替初期、新朝一级区划尚未建立，可使用经证据确认的前朝区划图；若左图右史官方索引用合并/分置期题名承载目标 admin，脚本返回 `coverage: "admin_substitute"` 时可交付链接，但正文必须保留原图名并说明对应关系；若已确认 admin 但索引没有精确或替代专题图，可用 `--allow-overview` 返回 `overview` 同代时代总图，正文必须标明不是一级区划专题图；确认不到 admin 也要不传 `--admin` 跑一次并记录 `needs_admin`，不得静默省略；匹配不到就不猜；链接必须来自 `data/history_map_index.json` 中的 `/#/pageNN/html?...` hash route，不手写 `/pageNN/html?...` 直连路径；正文必须逐地名交付地图链接或不附原因
9. **识典检索链接逐条交付**：每条史料短引都要用 `scripts/shidian_link.py` 生成 `[识典检索](...)`；关键词优先取原文短引中的关键片段，不能只用笼统书名、人名或朝代代替。识典链接用于辅助读者核查，不等同于已解析到原书章节页，不能手写或猜测书页链接
10. **EPUB 按需只作方向**：本地史料学书籍可帮助推断应查哪些史料，但不能替代辞典与古籍原文；没实际运行或没影响检索时，不得暗示回答参考了它们
11. **查不到就说查不到**——绝不基于训练数据补全、绝不编造原文、绝不"古代应该有……"

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
- ❌ 不要在 Claude Code 触发的命令里用 `source venv/bin/activate`——会被权限系统拦截，每次按回车确认。改用 `python scripts/run_in_venv.py ...` 或对应平台的 venv 可执行文件直调
- ✅ 关键词控制 2–6 字，超过 8 字 cnkgraph 常 404；复杂问题用多次短查询交叉验证
- ✅ 最终答案要保留关键史料原文短引和年号纪年；不要用过去回答或辞典摘要替代重新整理
- ✅ 古地名今地映射使用 `scripts/place_resolver.py`；最终回答中保留的每个古地名，首次出现处都要括注今地；如果返回歧义、无坐标或无边界命中，必须用自然语言如实说明，不输出脚本状态码或内部实现细节
- ✅ 地名直查失败但材料给出现代/后世定位线索时，使用 `scripts/place_admin_resolver.py` 反查历史地名；候选必须来自辞典/cnkgraph/TGAZ 沿革，不能只凭现代地点猜
- ✅ 左图右史链接使用 `scripts/history_map_link.py`；先用辞典/cnkgraph 检索地名在相应时代所隶属的同代一级行政区，王朝交替初期可用已核实的前朝区划图；`--admin` 只能填已确认的一级区划或前朝图标签，不能填州、府、郡、县或现代省市；脚本返回 `resolved` 才能写成区划地图，`coverage: "admin_substitute"` 要说明合并/分置期对应关系，返回 `overview` 只能写成同代时代总图并说明限制；若一级区划无法确认，仍要不传 `--admin` 跑一次并记录 `needs_admin`，多人物/列表型回答也要逐地名交代地图核验结果
- ✅ 识典检索链接使用 `scripts/shidian_link.py`；优先用原文短引中的关键片段作为 `--keyword`，在每条史料出处行附 `[识典检索](...)`，供读者从识典搜索页核查原文。不要手写或猜测识典书页链接
- ✅ 修改任何核心规则前，先看 [COMMON_MISTAKES.md](COMMON_MISTAKES.md) 历史踩坑

---

## License

- 《中国历史大辞典》：仅供个人学习研究使用
- cnkgraph API：仅限非商业用途
- 本项目代码：MIT
