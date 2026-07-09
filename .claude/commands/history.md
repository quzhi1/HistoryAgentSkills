---
description: 综合查询中国历史关键词（辞典 + cnkgraph），按本项目 SKILL.md 规范作答
allowed-tools: Bash, Read, Grep, Glob
---

# /history — 中国历史综合查询

用户查询的关键词：**$ARGUMENTS**

## 步骤 0：定位项目根目录

本命令可能通过 `~/.claude/commands/` 的符号链接全局触发，当前目录不一定是项目根目录。后续每个 Bash 会话都先执行（在项目内触发时 `realpath` 失败，留在当前目录即可）：

```bash
cd "$(realpath ~/.claude/skills/chinese-history-expert 2>/dev/null || echo .)"
```

## 步骤 1：先跑综合查询脚本

!`cd "$(realpath ~/.claude/skills/chinese-history-expert 2>/dev/null || echo .)" && python scripts/run_in_venv.py scripts/history_query.py "$ARGUMENTS"`

## 步骤 2：年号换算与史料方向（必做）

如果 `$ARGUMENTS` 或后续查询材料中出现年号纪年（如天宝十四载、太平真君十一年、康熙六十一年），必须运行：

```bash
python scripts/run_in_venv.py scripts/dynasty_converter.py "<年号纪年>"
```

回答中写作：`年号纪年（公元XXXX年）`。换算脚本调用 cnkgraph Calendar API；若 API 返回同名年号或多政权候选，按上下文判断，判断不了就列出歧义。

搜集史料前可用本地史料学 EPUB 判断方向：

```bash
python scripts/run_in_venv.py scripts/book_search.py "<关键词>" --limit 5
```

EPUB 检索结果只作为搜集方向，不能替代辞典和 cnkgraph 原文证据。

## 步骤 3：补充查询（必做，不能跳过）

不管步骤 1 输出如何，**必须**用 cnkgraph 的 `find` 接口拿到带上下文的古籍原文片段：

```bash
python scripts/run_in_venv.py cnkgraph/scripts/query_api.py find --keyword "<2-6字关键词>"
```

注意事项：
- 关键词长度 **2–6 字**，超过 8 字常 404
- 如果 `$ARGUMENTS` 本身较长（比如完整人名 + 事件描述），**拆成多个短关键词**分别查（人名一次、事件短语一次、时间词一次），交叉验证
- 如果步骤 1 的辞典输出被截断或不完整，再单独跑 `python scripts/run_in_venv.py mdict -q "$ARGUMENTS" dict/历史辞典4合1.mdx`

**重要**：本项目命令优先通过 `scripts/run_in_venv.py` 或 venv 内可执行文件直接调用，**不要**用 `source venv/bin/activate`。

## 步骤 4：查询被引用史料说明（必做）

最终答案准备引用哪几部史料，就按唯一书名逐一查询《中国历史大辞典》：

```bash
python scripts/run_in_venv.py mdict -q "<史料书名>" dict/历史辞典4合1.mdx
```

- 查询对象是书名本身，如 `魏书`、`旧唐书`、`资治通鉴`、`明史`
- 同一部书多次引用只需查一次
- 答案中必须有“被引史料说明”，简要说明作者/时代、体例、内容范围或史料性质
- 查不到书名词条时，明说未在《中国历史大辞典》中查到可用介绍，不能凭常识补写

## 步骤 5：按规范作答

读 @SKILL.md（重点看"标准工作流程"和"回答模板"），并遵守 @CLAUDE.md 里的红线，按规范输出回答。

**核心要求**（违反即视为低质量回答）：
1. 所有史料引用必须包含**书名 + 章节名**（如《魏书》卷三五《崔浩传》）
2. 每部被引用史料都必须按书名查《中国历史大辞典》，并在答案中给“被引史料说明”
3. 必须补全**六类细节**：时间、地点、相关人物、起因、经过、结果
4. 凡出现年号纪年，必须用 `scripts/dynasty_converter.py` 换算成公元纪年
5. **查不到就说查不到**——绝不基于训练数据补全、绝不编造原文、绝不"古代应该有……"
6. 区分"辞典整理的内容"和"古籍原文片段"两种引用

如果两边都查不到，按 `COMMON_MISTAKES.md` 里的"模板2：查询失败"格式诚实回答。
