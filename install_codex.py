#!/usr/bin/env python3
"""Install the project as global Codex skills."""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def render_history_skill_stub(project_root: Path) -> str:
    root = str(project_root)
    return f"""---
name: chinese-history-expert
description: 中国历史问题专家（基于《中国历史大辞典》和 cnkgraph 古籍 API）。当用户询问中国古代（先秦至清末）的人物、事件、制度、文学作品、文化常识等历史问题时使用。提供有据可查、引用书名+章节名的史料解答；查不到就明确说查不到，绝不编造。
---

# 中国历史专家系统（Codex 全局触发入口）

本文件是项目 `{root}` 的 Codex 全局触发入口。**真正的工作规则在项目里**——本文件只负责把 Codex 引导过去。

## 启动步骤（必做，按顺序）

1. **切换到项目目录**（所有后续命令都假设此 cwd）：

   ```bash
   cd "{root}"
   ```

2. **读项目守则与 skill 规范**：

   - 先读 `{root}/AGENTS.md`（操作约束、命令规范、红线）
   - 再读 `{root}/SKILL.md`（详细工作流程、回答模板）

3. **按项目规范作答**。命令统一用 `venv/bin/python` / `venv/bin/mdict`，不要用 `source venv/bin/activate`。

## 关键资源（项目内）

- 综合查询：`venv/bin/python scripts/history_query.py "<关键词>"`
- 辞典直查：`venv/bin/mdict -q "<关键词>" dict/历史辞典4合1.mdx`
- 古籍原文片段（必做）：`venv/bin/python cnkgraph/scripts/query_api.py find --keyword "<2-6字>"`
- 史料引用规范：`{root}/HISTORICAL_SOURCES_GUIDE.md`
- 常见错误警示：`{root}/COMMON_MISTAKES.md`
"""


def render_anecdote_skill_stub(project_root: Path) -> str:
    root = str(project_root)
    skill_path = str(project_root / "random-history-anecdote" / "SKILL.md")
    return f"""---
name: random-history-anecdote
description: 随机提供一个有趣、短小、经史料核验的中国古代历史段子。适合用户说“来个历史段子”“随机历史小故事”“random-history-anecdote”等请求；输出原文、译文和出处，保持简短。不附识典古籍链接和左图右史地图链接，但仍按项目规则换算年号、标注古地名今地，查不到就重抽或明说。
---

# 随机历史小段子（Codex 全局触发入口）

本文件是项目 `{root}` 的随机历史段子 skill 入口。**真正的工作规则在项目里**——本文件只负责把 Codex 引导过去。

## 启动步骤（必做，按顺序）

1. **切换到项目目录**：

   ```bash
   cd "{root}"
   ```

2. **读项目守则与本 skill 规范**：

   - 先读 `{root}/AGENTS.md`（操作约束、命令规范、红线）
   - 再读 `{skill_path}`（随机段子的详细流程和输出格式）

3. **先动态发现候选，再查证据**：

   ```bash
   venv/bin/python scripts/random_anecdote_seed.py --json
   venv/bin/python cnkgraph/scripts/query_api.py find --keyword "<候选 keyword 或原文短句>"
   venv/bin/mdict -q "<人物或书名>" dict/历史辞典4合1.mdx
   ```

## 关键例外

- 不附识典古籍链接。
- 不附左图右史地图链接。
- 仍要真实查询原文和出处。
- 不使用固定段子池；`random_anecdote_seed.py` 每次随机生成探针并检索 cnkgraph 全库。
- 出现年号要换算；保留古地名要查今地。
- 输出保持简短：原文、出处、译文；不另写“好玩处”。
"""


def install_codex(project_root: Path = PROJECT_ROOT, agents_dir: Path | None = None) -> dict[str, Path]:
    project_root = project_root.resolve()
    agents_dir = (agents_dir or (Path.home() / ".agents")).expanduser().resolve()

    required = [
        project_root / "AGENTS.md",
        project_root / "SKILL.md",
        project_root / "random-history-anecdote" / "SKILL.md",
        project_root / "scripts" / "random_anecdote_seed.py",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"找不到必要文件: {path}")

    history_skill_dir = agents_dir / "skills" / "chinese-history-expert"
    anecdote_skill_dir = agents_dir / "skills" / "random-history-anecdote"
    for directory in (history_skill_dir, anecdote_skill_dir):
        directory.mkdir(parents=True, exist_ok=True)

    outputs = {
        "skill": history_skill_dir / "SKILL.md",
        "anecdote_skill": anecdote_skill_dir / "SKILL.md",
    }
    outputs["skill"].write_text(render_history_skill_stub(project_root), encoding="utf-8")
    outputs["anecdote_skill"].write_text(render_anecdote_skill_stub(project_root), encoding="utf-8")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="把本项目注册到 Codex 的全局 skill 目录")
    parser.add_argument("--agents-dir", type=Path, default=None, help="自定义 Codex agents 目录，默认 ~/.agents")
    args = parser.parse_args()

    try:
        outputs = install_codex(agents_dir=args.agents_dir)
    except OSError as exc:
        print(f"❌ Codex 全局注册失败: {exc}")
        return 1

    print("")
    print("✅ Codex 全局注册完成")
    print("")
    print("已安装：")
    print(f"  • history skill stub: {outputs['skill']}")
    print(f"  • anecdote skill stub: {outputs['anecdote_skill']}")
    print("")
    print("这些文件根据当前项目目录生成；移动项目后请重新运行安装脚本。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
