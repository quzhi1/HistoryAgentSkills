# 中国历史专家系统 — Codex 入口

本文件是 Codex 进入本项目时的最小启动入口，不承载完整工作流。完整、唯一的规则源是 [`SKILL.md`](SKILL.md)。

## 单一真理源

- 回答中国历史问题、修改 workflow、更新模板或调整红线时，先读并遵守 `SKILL.md`。
- `AGENTS.md` 与 `CLAUDE.md` 只保留入口规则，不复制长流程。
- 如果本文件与 `SKILL.md` 冲突，以 `SKILL.md` 为准，并修正本文件。

## 启动红线

- 禁止直接读取 `dict/历史辞典4合1.mdx` 和 `dict/历史辞典4in1.mdd`；查辞典只能用项目 venv 的 `mdict`（macOS/Linux: `venv/bin/mdict`；Windows: `venv\Scripts\mdict.exe`）或 `python scripts/run_in_venv.py mdict ...`。
- 统一用项目 venv 命令（macOS/Linux: `venv/bin/python` / `venv/bin/mdict`；Windows: `venv\Scripts\python.exe` / `venv\Scripts\mdict.exe`）或 `scripts/run_in_venv.py`，不要 `source venv/bin/activate`。
- 历史回答必须按 `SKILL.md` 执行：辞典 + cnkgraph、被引史料说明、识典链接验证、古地名今地与左图右史门禁、查不到就说查不到。
- 修改核心规则前先读 `COMMON_MISTAKES.md`；修改后同步 `README.md`（若影响用户可见流程），并运行 `python scripts/run_in_venv.py test_system.py` 或对应平台的 venv Python。
