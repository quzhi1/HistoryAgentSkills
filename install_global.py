#!/usr/bin/env python3
"""Install the project as a global Claude Code skill."""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def _insert_after_frontmatter(text: str, block: str) -> str:
    if not text.startswith("---\n"):
        return block + "\n" + text
    end = text.find("\n---", 4)
    if end == -1:
        return block + "\n" + text
    insert_at = end + len("\n---")
    return text[:insert_at] + "\n\n" + block + text[insert_at:]


def render_skill_stub(project_root: Path) -> str:
    root = str(project_root)
    runner = str(project_root / "scripts" / "run_in_venv.py")
    return f"""---
name: chinese-history-expert
description: 中国历史问题专家（基于《中国历史大辞典》和 cnkgraph 古籍 API）。当用户询问中国古代（先秦至清末）的人物、事件、制度、文学作品、文化常识等历史问题时使用。提供有据可查、引用书名+章节名的史料解答；查不到就明确说查不到，绝不编造。
---

# 中国历史专家系统（全局触发入口）

本文件是项目 `{root}` 的全局触发入口。**真正的工作规则在项目里**——本文件只负责把 Claude 引导过去。

## 启动步骤（必做，按顺序）

1. **切换到项目目录**（所有后续命令都假设此 cwd）：

   macOS/Linux:
   ```bash
   cd "{root}"
   ```

   Windows PowerShell:
   ```powershell
   Set-Location "{root}"
   ```

2. **读项目守则与 skill 规范**：

   - 先读 `{root}/CLAUDE.md`（操作约束、命令规范、红线）
   - 再读 `{root}/SKILL.md`（详细工作流程、回答模板）

3. **按项目规范作答**。命令优先通过跨平台 runner 调用，不需要激活虚拟环境：

   ```bash
   python "{runner}" scripts/history_query.py "<关键词>"
   python "{runner}" mdict -q "<关键词>" dict/历史辞典4合1.mdx
   ```

## 关键资源（项目内）

- 综合查询：`python "{runner}" scripts/history_query.py "<关键词>"`
- 辞典直查：`python "{runner}" mdict -q "<关键词>" dict/历史辞典4合1.mdx`
- 古籍原文片段（必做）：`python "{runner}" cnkgraph/scripts/query_api.py find --keyword "<2-6字>"`
- 史料引用规范：`{root}/HISTORICAL_SOURCES_GUIDE.md`
- 常见错误警示：`{root}/COMMON_MISTAKES.md`

## 红线提醒（详细见项目 CLAUDE.md）

- 必查辞典 + cnkgraph 两边，缺一不可
- 史料引用必须包含**书名 + 章节名**（如《魏书》卷三五《崔浩传》）
- 必须补全六类细节：时间、地点、相关人物、起因、经过、结果
- 查不到就说查不到，绝不基于训练数据编造
"""


def render_history_command(project_root: Path) -> str:
    runner = str(project_root / "scripts" / "run_in_venv.py")
    root = str(project_root)
    return f"""---
description: 综合查询中国历史关键词（辞典 + cnkgraph），按本项目 SKILL.md 规范作答
allowed-tools: Bash, Read, Grep, Glob
---

# /history — 中国历史综合查询

用户查询的关键词：**$ARGUMENTS**

项目目录：`{root}`

## 步骤 1：先跑综合查询脚本

!`python "{runner}" scripts/history_query.py "$ARGUMENTS"`

## 步骤 2：年号换算与史料方向（必做）

如果 `$ARGUMENTS` 或后续查询材料中出现年号纪年（如天宝十四载、太平真君十一年、康熙六十一年），必须运行：

```bash
python "{runner}" scripts/dynasty_converter.py "<年号纪年>"
```

回答中写作：`年号纪年（公元XXXX年）`。换算脚本调用 cnkgraph Calendar API；若 API 返回同名年号或多政权候选，按上下文判断，判断不了就列出歧义。

搜集史料前可用本地史料学 EPUB 判断方向：

```bash
python "{runner}" scripts/book_search.py "<关键词>" --limit 5
```

EPUB 检索结果只作为搜集方向，不能替代辞典和 cnkgraph 原文证据。

## 步骤 3：补充查询（必做，不能跳过）

不管步骤 1 输出如何，**必须**用 cnkgraph 的 `find` 接口拿到带上下文的古籍原文片段：

```bash
python "{runner}" cnkgraph/scripts/query_api.py find --keyword "<2-6字关键词>"
```

注意事项：
- 关键词长度 **2–6 字**，超过 8 字常 404
- 如果 `$ARGUMENTS` 本身较长（比如完整人名 + 事件描述），**拆成多个短关键词**分别查（人名一次、事件短语一次、时间词一次），交叉验证
- 如果步骤 1 的辞典输出被截断或不完整，再单独跑 `python "{runner}" mdict -q "$ARGUMENTS" dict/历史辞典4合1.mdx`

**重要**：本项目命令优先通过 `scripts/run_in_venv.py` 或 venv 内可执行文件直接调用，**不要**用 `source venv/bin/activate`。

## 步骤 4：查询被引用史料说明（必做）

最终答案准备引用哪几部史料，就按唯一书名逐一查询《中国历史大辞典》：

```bash
python "{runner}" mdict -q "<史料书名>" dict/历史辞典4合1.mdx
```

- 查询对象是书名本身，如 `魏书`、`旧唐书`、`资治通鉴`、`明史`
- 同一部书多次引用只需查一次
- 答案中必须有“被引史料说明”，简要说明作者/时代、体例、内容范围或史料性质
- 查不到书名词条时，明说未在《中国历史大辞典》中查到可用介绍，不能凭常识补写

## 步骤 5：按规范作答

读 `{root}/SKILL.md`（重点看"标准工作流程"和"回答模板"），并遵守 `{root}/CLAUDE.md` 里的红线，按规范输出回答。

**核心要求**（违反即视为低质量回答）：
1. 所有史料引用必须包含**书名 + 章节名**（如《魏书》卷三五《崔浩传》）
2. 每部被引用史料都必须按书名查《中国历史大辞典》，并在答案中给“被引史料说明”
3. 必须补全**六类细节**：时间、地点、相关人物、起因、经过、结果
4. 凡出现年号纪年，必须用 `scripts/dynasty_converter.py` 换算成公元纪年
5. **查不到就说查不到**——绝不基于训练数据补全、绝不编造原文、绝不"古代应该有……"
6. 区分"辞典整理的内容"和"古籍原文片段"两种引用

如果两边都查不到，按 `{root}/COMMON_MISTAKES.md` 里的"模板2：查询失败"格式诚实回答。
"""


def render_fact_checker(project_root: Path) -> str:
    source = (project_root / ".claude" / "agents" / "history-fact-checker.md").read_text(encoding="utf-8")
    runner = str(project_root / "scripts" / "run_in_venv.py")
    block = f"""全局安装信息：项目根目录为 `{project_root}`。所有复查命令先以该目录为准；跨平台调用优先使用：

```bash
python "{runner}" <script.py|mdict> [args...]
```"""
    return _insert_after_frontmatter(source, block)


def install_global(project_root: Path = PROJECT_ROOT, claude_dir: Path | None = None) -> dict[str, Path]:
    project_root = project_root.resolve()
    claude_dir = (claude_dir or (Path.home() / ".claude")).expanduser().resolve()

    required = [
        project_root / "SKILL.md",
        project_root / "CLAUDE.md",
        project_root / ".claude" / "agents" / "history-fact-checker.md",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"找不到必要文件: {path}")

    skill_dir = claude_dir / "skills" / "chinese-history-expert"
    commands_dir = claude_dir / "commands"
    agents_dir = claude_dir / "agents"
    for directory in (skill_dir, commands_dir, agents_dir):
        directory.mkdir(parents=True, exist_ok=True)

    outputs = {
        "skill": skill_dir / "SKILL.md",
        "command": commands_dir / "history.md",
        "agent": agents_dir / "history-fact-checker.md",
    }
    outputs["skill"].write_text(render_skill_stub(project_root), encoding="utf-8")
    outputs["command"].write_text(render_history_command(project_root), encoding="utf-8")
    outputs["agent"].write_text(render_fact_checker(project_root), encoding="utf-8")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="把本项目注册到 Claude Code 的全局位置")
    parser.add_argument("--claude-dir", type=Path, default=None, help="自定义 Claude 配置目录，默认 ~/.claude")
    args = parser.parse_args()

    try:
        outputs = install_global(claude_dir=args.claude_dir)
    except OSError as exc:
        print(f"❌ 全局注册失败: {exc}")
        return 1

    print("")
    print("✅ 全局注册完成")
    print("")
    print("已安装：")
    print(f"  • skill stub: {outputs['skill']}")
    print(f"  • /history 命令: {outputs['command']}")
    print(f"  • fact-checker subagent: {outputs['agent']}")
    print("")
    print("这些文件根据当前项目目录生成；移动项目后请重新运行安装脚本。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
