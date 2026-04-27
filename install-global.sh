#!/bin/bash
# 把本项目注册到 Claude Code 的全局位置（~/.claude/）。
# 这样在任何目录启动 claude，都能自动触发中国历史 skill、/history 命令、fact-checker subagent。
#
# 用法：
#   cd /Users/zhi.q/HistoryAgentSkills
#   ./install-global.sh
#
# 卸载（手动）：
#   rm -rf ~/.claude/skills/chinese-history-expert
#   rm ~/.claude/commands/history.md
#   rm ~/.claude/agents/history-fact-checker.md

set -e

PROJECT_ROOT="/Users/zhi.q/HistoryAgentSkills"
USER_CLAUDE_DIR="$HOME/.claude"

# 防呆：当前目录必须是项目根
if [ ! -f "$PROJECT_ROOT/SKILL.md" ]; then
  echo "❌ 找不到 $PROJECT_ROOT/SKILL.md，请确认项目位置"
  exit 1
fi

mkdir -p "$USER_CLAUDE_DIR/skills/chinese-history-expert"
mkdir -p "$USER_CLAUDE_DIR/commands"
mkdir -p "$USER_CLAUDE_DIR/agents"

# 1. 全局 skill stub —— 把 Claude 引导回项目目录读规则
cat > "$USER_CLAUDE_DIR/skills/chinese-history-expert/SKILL.md" << 'STUB'
---
name: chinese-history-expert
description: 中国历史问题专家（基于《中国历史大辞典》和 cnkgraph 古籍 API）。当用户询问中国古代（先秦至清末）的人物、事件、制度、文学作品、文化常识等历史问题时使用。提供有据可查、引用书名+章节名的史料解答；查不到就明确说查不到，绝不编造。
---

# 中国历史专家系统（全局触发入口）

本文件是项目 `/Users/zhi.q/HistoryAgentSkills` 的全局触发入口。**真正的工作规则在项目里**——本文件只负责把 Claude 引导过去。

## 启动步骤（必做，按顺序）

1. **切换到项目目录**（所有后续命令都假设此 cwd）：

   ```bash
   cd /Users/zhi.q/HistoryAgentSkills
   ```

2. **读项目守则与 skill 规范**：

   - 先读 `/Users/zhi.q/HistoryAgentSkills/CLAUDE.md`（操作约束、命令规范、红线）
   - 再读 `/Users/zhi.q/HistoryAgentSkills/SKILL.md`（详细工作流程、回答模板）

3. **按项目规范作答**。命令统一用 `venv/bin/python` / `venv/bin/mdict`，**不要**用 `source venv/bin/activate`（会触发权限拦截）。

## 关键资源（项目内）

- 综合查询：`venv/bin/python scripts/history_query.py "<关键词>"`
- 辞典直查：`venv/bin/mdict -q "<关键词>" dict/历史辞典4合1.mdx`
- 古籍原文片段（必做）：`venv/bin/python cnkgraph/scripts/query_api.py find --keyword "<2-6字>"`
- 史料引用规范：`/Users/zhi.q/HistoryAgentSkills/HISTORICAL_SOURCES_GUIDE.md`
- 常见错误警示：`/Users/zhi.q/HistoryAgentSkills/COMMON_MISTAKES.md`

## 红线提醒（详细见项目 CLAUDE.md）

- 必查辞典 + cnkgraph 两边，缺一不可
- 史料引用必须包含**书名 + 章节名**（如《魏书》卷三五《崔浩传》）
- 必须补全六类细节：时间、地点、相关人物、起因、经过、结果
- 查不到就说查不到，绝不基于训练数据编造
STUB

# 2. /history 命令 —— 符号链接到项目内
ln -sf "$PROJECT_ROOT/.claude/commands/history.md" "$USER_CLAUDE_DIR/commands/history.md"

# 3. history-fact-checker subagent —— 符号链接到项目内
ln -sf "$PROJECT_ROOT/.claude/agents/history-fact-checker.md" "$USER_CLAUDE_DIR/agents/history-fact-checker.md"

echo ""
echo "✅ 全局注册完成"
echo ""
echo "已安装到 $USER_CLAUDE_DIR："
echo "  • skills/chinese-history-expert/SKILL.md  （全局触发入口，stub）"
echo "  • commands/history.md  →  $PROJECT_ROOT/.claude/commands/history.md  （symlink）"
echo "  • agents/history-fact-checker.md  →  $PROJECT_ROOT/.claude/agents/history-fact-checker.md  （symlink）"
echo ""
echo "测试方法："
echo "  1. cd 到任意非项目目录（比如 cd ~）"
echo "  2. 启动 claude"
echo "  3. 问一个中国古代历史问题（比如「李白是谁？」）"
echo "  4. 观察 Claude 是否自动 cd 到项目并按规范作答"
echo ""
echo "卸载："
echo "  rm -rf $USER_CLAUDE_DIR/skills/chinese-history-expert"
echo "  rm $USER_CLAUDE_DIR/commands/history.md"
echo "  rm $USER_CLAUDE_DIR/agents/history-fact-checker.md"
