# 中国历史专家系统 — 项目守则

本项目是基于《中国历史大辞典》和 cnkgraph 古籍 API 的中国历史问答系统。
本文件是 Claude 在本项目内工作的强制约束，每次都要遵守。

详细的 skill 工作流程见 `SKILL.md`。本文件只列**操作约束**和**红线**。

---

## 1. 环境（最容易踩的坑）

**Claude Code 调用命令时，统一用 venv 二进制直接调用，不要用 `source`**：

```bash
cd /Users/zhi.q/HistoryAgentSkills
venv/bin/mdict -q "关键词" dict/历史辞典4合1.mdx
venv/bin/python scripts/history_query.py "李白"
venv/bin/python cnkgraph/scripts/query_api.py find --keyword "崔浩"
```

理由：`source venv/bin/activate` 在 Claude Code 里每次会触发权限二次确认（`'source' evaluates arguments as shell code`），打断流程。直接走 `venv/bin/<binary>` 等价、更安全、更稳定。

出现 `未安装 mdict` 几乎一定是 venv 没建好（不是激活问题——直接调二进制不需要激活）。检查 `venv/bin/mdict` 是否存在，不存在跑 `./setup_venv.sh` 重建，**不要**到处 `pip install`。

> 注：用户在交互式 shell 里手工跑命令时仍然可以 `source venv/bin/activate`，本条只约束 Claude Code 调用的场景。

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

刷新识典/cnkgraph 书目链接索引（维护时）：
```bash
venv/bin/python scripts/update_source_book_index.py --pretty --verbose
```

## 4. 回答历史问题的红线

**a. 必查两边**：辞典 + cnkgraph，缺一不可。只查辞典作答 = 违规。

**b. 史料引用必须包含书名 + 章节名**：
- ✅ 《魏书》卷三五《崔浩传》
- ✅ 《旧唐书》卷一八三《罗士信传》
- ❌ 据史书记载（无书名）
- ❌ 《魏书》记载（无卷、传名）

**c. 必须补全六类细节**：时间、地点、相关人物、起因、经过、结果。

**e. 识典验证和左图右史验证脚本，每次必须真实运行**：
- 凡最终回答保留原文短引，必须逐条运行 `scripts/shidian_link.py`，不得以"找不到"为由直接省略脚本执行
- 凡最终回答保留古地名，必须逐个运行 `scripts/history_map_link.py`，不得以"不确定"为由直接省略脚本执行
- **"没有运行脚本后省略"与"运行后 not_found"是两回事**；前者一定违规，后者也不是终点
- `scripts/shidian_link.py` 会读取 `data/source_book_index.json` 先核对识典书页/cnkgraph 书名；若用户指出识典链接问题或索引缺失，先刷新 `scripts/update_source_book_index.py`
- `scripts/shidian_link.py` 返回 `not_found`、`invalid`、查询失败，或 `matched_source` 显示为后代类书/总集/别集/注释书/转引页时，必须继续换关键词、原书别名、篇名/卷名、短引或出处二次验证；优先改用能 `resolved` 的原始短引
- 用户明确要求识典原文链接、答案用于对外发布、或核心结论只靠一两条史料支撑时，核心结论至少要有一条 `resolved` 的识典原文链接；否则不能把无链接答案当完整答案交付，必须继续换源检索或明确说明无法提供合格链接
- 两个脚本的验证必须在步骤5.7核查清单中有据可查，步骤6进入前不得跳过

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
| `scripts/source_book_index.py` | 识典/cnkgraph 书目索引读取与匹配 |
| `scripts/update_source_book_index.py` | 刷新识典/cnkgraph 书目链接索引 |
| `data/source_book_index.json` | 识典书页与 cnkgraph 书目/API 链接索引 |
| `COMMON_MISTAKES.md` | 历史踩坑记录（修改规则前必读） |
| `HISTORICAL_SOURCES_GUIDE.md` | 二十四史引用指南 |
| `setup_venv.sh` | 一键搭环境 |
| `requirements.txt` | Python 依赖 |
