---
description: 综合查询中国历史关键词（辞典 + cnkgraph），按本项目 SKILL.md 规范作答
allowed-tools: Bash, Read, Grep, Glob
---

# /history — 中国历史综合查询

用户查询的关键词：**$ARGUMENTS**

## 步骤 1：先跑综合查询脚本

!`cd /Users/zhi.q/HistoryAgentSkills && venv/bin/python scripts/history_query.py "$ARGUMENTS"`

## 步骤 2：补充查询（必做，不能跳过）

不管步骤 1 输出如何，**必须**用 cnkgraph 的 `find` 接口拿到带上下文的古籍原文片段：

```bash
cd /Users/zhi.q/HistoryAgentSkills && venv/bin/python cnkgraph/scripts/query_api.py find --keyword "<2-6字关键词>"
```

注意事项：
- 关键词长度 **2–6 字**，超过 8 字常 404
- 如果 `$ARGUMENTS` 本身较长（比如完整人名 + 事件描述），**拆成多个短关键词**分别查（人名一次、事件短语一次、时间词一次），交叉验证
- 如果步骤 1 的辞典输出被截断或不完整，再单独跑 `venv/bin/mdict -q "$ARGUMENTS" dict/历史辞典4合1.mdx`

**重要**：本项目所有命令统一用 `venv/bin/python` / `venv/bin/mdict` 直接调用，**不要**用 `source venv/bin/activate`——`source` 会触发 Claude Code 的权限二次确认。

## 步骤 3：按规范作答

读 @SKILL.md（重点看"标准工作流程"和"回答模板"），并遵守 @CLAUDE.md 里的红线，按规范输出回答。

**核心要求**（违反即视为低质量回答）：
1. 所有史料引用必须包含**书名 + 章节名**（如《魏书》卷三五《崔浩传》）
2. 必须补全**六类细节**：时间、地点、相关人物、起因、经过、结果
3. **查不到就说查不到**——绝不基于训练数据补全、绝不编造原文、绝不"古代应该有……"
4. 区分"辞典整理的内容"和"古籍原文片段"两种引用

如果两边都查不到，按 `COMMON_MISTAKES.md` 里的"模板2：查询失败"格式诚实回答。
