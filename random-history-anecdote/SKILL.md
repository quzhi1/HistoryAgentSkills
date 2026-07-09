---
name: random-history-anecdote
description: 随机提供一个有趣、短小、经史料核验的中国古代历史段子。适合用户说“来个历史段子”“随机历史小故事”“random-history-anecdote”等请求；输出原文、译文和出处，保持简短。不附识典古籍链接和左图右史地图链接，但仍按项目规则换算年号、标注古地名今地，查不到就重抽或明说。
---

# 随机历史小段子

本 skill 是项目根目录 `SKILL.md` 的轻量入口：目标是让用户快速得到一个有趣的历史小段子，而不是完整历史问答报告。证据底座仍然使用《中国历史大辞典》和 cnkgraph 古籍原文；不得编造段子、不得凭记忆补出处。

## 适用范围

- 中国古代（先秦至清末）人物、事件、言语、轶事、制度运行中的片段，通常不超过 1000 字。
- 每次调用时动态随机发现候选；不使用固定段子池，不限定书目范围，不限定主题词。
- 段子应有现代读者也能感到的趣味：机智、反转、语言梗、人物性格、处世判断、制度荒诞、名实错位等。

不适合：
- 长篇人物传记、完整事件复盘、严肃比较评价题；这些转用根目录 `SKILL.md` 的完整流程。
- 查不到原文或出处的传闻；不要为了有趣而补写。

## 与主 skill 的关系

继承主 skill 的底线：
- 必须真实查询，不得编造原文、出处、译文或背景。
- 原文必须来自本轮查到的辞典或 cnkgraph 片段。
- 出处必须写书名 + 卷/篇/章节名；cnkgraph 只返回卷名时，不要凭空补篇名。
- 译文只翻译原文；不要另写“好玩处”或趣味解释。
- 史料中出现年号纪年，必须运行 `scripts/dynasty_converter.py`，并写成 `年号（公元年）`。
- 最终回答保留古地名时，必须运行 `scripts/place_resolver.py`，并在首次出现处括注今地；查不到就写“今地未能确认”。

本 skill 的明确例外：
- **不运行、不输出识典古籍链接**。出处行只写书名 + 卷/篇/章节名。
- **不运行、不输出左图右史地图链接**。地点只做现代今地括注。
- 默认不输出“被引史料说明”，除非来源性质会影响理解或用户追问。
- 输出要短；不要展开成长篇史论。

## 标准流程

> 命令路径默认 macOS/Linux。Windows PowerShell 可用 `python scripts/run_in_venv.py <script.py|mdict> ...` 或对应 `venv\Scripts\python.exe` / `venv\Scripts\mdict.exe`。

1. 切到项目根目录，即本 skill 目录**真实位置**的上一级。全局安装时本 skill 目录是 `~/.claude/skills/` 下的符号链接，必须先用 `realpath` 解析，不能直接用符号链接的上一级：

```bash
cd "$(dirname "$(realpath ~/.claude/skills/random-history-anecdote)")"
# 已在项目目录时直接：cd /path/to/HistoryAgentSkills
```

```powershell
Set-Location (Split-Path (Get-Item "$env:USERPROFILE\.claude\skills\random-history-anecdote").Target)
```

2. 随机发现候选。

```bash
venv/bin/python scripts/random_anecdote_seed.py --json
```

脚本会在运行时随机生成古汉语检索探针，调用 cnkgraph `Book/Find` 检索全库，随机跳到命中结果页，再返回若干带书名、卷名和上下文的候选片段。它不读取固定段子 JSON。

```bash
venv/bin/python scripts/random_anecdote_seed.py --attempts 15 --candidates 8 --json
```

3. 从返回的 `candidates` 里挑一个完整、有动作或对话、读起来像一则小故事的片段；必要时用候选 `keyword` 或原文中的短句再次查询 cnkgraph，确认上下文。

```bash
venv/bin/python cnkgraph/scripts/query_api.py find --keyword "<候选 keyword 或原文短句>"
```

4. 用《中国历史大辞典》核定人物、书名或关键背景。

```bash
venv/bin/mdict -q "<人物或书名>" dict/历史辞典4合1.mdx
```

5. 若查到的段子含年号，运行年号换算。

```bash
venv/bin/python scripts/dynasty_converter.py "永乐十五年"
```

6. 若最终原文、译文或一句必要背景里保留古地名，逐一查今地。

```bash
venv/bin/python scripts/place_resolver.py "长安" --year 755 --json
```

7. 若候选查不到可靠原文、出处不清、译文无法确定，最多重抽两次。仍失败时简短说明“这次没有抽到可核验段子”。

## 输出格式

默认只输出原文、出处和译文，不加长标题、查询日志、地图、识典链接，也不另写“好玩处”。

```markdown
**今天的小段子：[短题名]**

原文：「[一段短引]」
出处：《[书名]》卷/篇《[章节名]》

译文：[只翻译原文；涉及古地名时首次出现括注今地；涉及年号时保留年号并括注公元年。]
```

## 选材标准

优先：
- 一条原文即可讲完整的小故事；几十字到数百字都可以。
- 1000 字以内都可接受，优先完整性和趣味性；超过 1000 字时才截取完整情节的关键片段，并标明“节引”。
- 有明确人物动作、对话或反转。
- 读者不需要额外解释也能看出趣味。

避免：
- 只有惨烈处刑、灾异、战争死亡数字的材料。
- 需要大段背景才看懂的材料。
- 只在后世笔记中孤证且出处不清的材料；如果使用，必须如实说“仅据某书所载”。
- 把现代段子感强行套到史料上。

## 质量自查

- [ ] 是否真实运行了随机发现脚本，且不是从固定段子池抽取？
- [ ] 是否查到了原文，而不是凭记忆复述？
- [ ] 出处是否包含书名 + 卷/篇/章节名？
- [ ] 译文是否只翻译原文，没有把分析塞进译文？
- [ ] 年号是否已换算；无年号则跳过？
- [ ] 古地名是否已查今地；无古地名则跳过？
- [ ] 是否没有输出识典链接、没有输出左图右史地图链接？
- [ ] 原文是否在 1000 字以内，或已对更长材料作完整情节节引？
- [ ] 是否确实有趣？
