# 中国历史专家系统 — 项目守则

本项目是基于《中国历史大辞典》和 cnkgraph 古籍 API 的中国历史问答系统。
本文件是 Codex 在本项目内工作的强制约束，每次都要遵守。

详细的 skill 工作流程见 `SKILL.md`。本文件只列**操作约束**和**红线**。

---

## 1. 环境（最容易踩的坑）

**Codex 调用命令时，统一用 venv 二进制直接调用，不要用 `source`**：

```bash
cd /Users/zhi.q/HistoryAgentSkills
venv/bin/mdict -q "关键词" dict/历史辞典4合1.mdx
venv/bin/python scripts/history_query.py "李白"
venv/bin/python cnkgraph/scripts/query_api.py find --keyword "崔浩"
```

理由：`source venv/bin/activate` 在 Codex 里每次会触发权限二次确认（`'source' evaluates arguments as shell code`），打断流程。直接走 `venv/bin/<binary>` 等价、更安全、更稳定。

出现 `未安装 mdict` 几乎一定是 venv 没建好（不是激活问题——直接调二进制不需要激活）。检查 `venv/bin/mdict` 是否存在，不存在跑 `./setup_venv.sh` 重建，**不要**到处 `pip install`。

> 注：用户在交互式 shell 里手工跑命令时仍然可以 `source venv/bin/activate`，本条只约束 Codex 调用的场景。

## 2. 文件读写禁区

- ❌ **禁止用 Read 工具直接读取 `dict/历史辞典4合1.mdx`**（约 4GB，会撑爆上下文）
- ❌ **禁止读取 `dict/历史辞典4in1.mdd`**（二进制资源文件）
- ✅ 查辞典只能通过 `mdict -q` 命令

## 3. 标准查询命令

辞典查询（基本定义 + 史料出处线索）：
```bash
venv/bin/mdict -q "关键词" dict/历史辞典4合1.mdx
```

cnkgraph 古籍原文片段（**必做**，不能只查辞典）：
```bash
venv/bin/python cnkgraph/scripts/query_api.py find --keyword "崔浩"
```
关键词控制在 **2–6 字**，超过 8 字常 404。复杂问题用多次短查询交叉验证，不要堆在一个长关键词里。

综合查询（一次跑两边）：
```bash
venv/bin/python scripts/history_query.py "李白"
```

诗词 / 人物 / 古籍书目（按需）：
```bash
venv/bin/python cnkgraph/scripts/query_api.py poetry --author 李白 --keyword 月
venv/bin/python cnkgraph/scripts/query_api.py people --name 苏轼
venv/bin/python cnkgraph/scripts/query_api.py book --keyword 崔浩
```

## 4. 回答历史问题的红线

**a. 必查两边**：辞典 + cnkgraph，缺一不可。只查辞典作答 = 违规。

**b. 史料引用必须包含书名 + 章节名**：
- ✅ 《魏书》卷三五《崔浩传》
- ✅ 《旧唐书》卷一八三《罗士信传》
- ❌ 据史书记载（无书名）
- ❌ 《魏书》记载（无卷、传名）

**c. 必须补全六类细节**：时间、地点、相关人物、起因、经过、结果。

**d. 查不到就说查不到。绝不**：
- 基于"历史常识"推测
- 编造辞典内容或古籍原文
- 假装查询过
- 用"古代应该有……"这类措辞补内容
- 用训练数据里的先验知识冒充查询结果

详细错误案例见 `COMMON_MISTAKES.md`，修改任何核心规则前先读它。

## 5. 修改本项目时

- 改 `SKILL.md` / `dict/SKILL.md` / `cnkgraph/SKILL.md` 前，想清楚是否与现有规则冲突
- 改完跑 `python test_system.py` 验证无回归
- 重要规则变动同步到 `README.md`

## 6. 关键文件速查

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 主 skill 入口（详细工作流程在此） |
| `dict/SKILL.md` | 辞典子 skill |
| `cnkgraph/SKILL.md` | API 子 skill |
| `scripts/history_query.py` | 综合查询脚本 |
| `COMMON_MISTAKES.md` | 历史踩坑记录（修改规则前必读） |
| `HISTORICAL_SOURCES_GUIDE.md` | 二十四史引用指南 |
| `setup_venv.sh` | 一键搭环境 |
| `requirements.txt` | Python 依赖 |

## Imported Claude Cowork project instructions
