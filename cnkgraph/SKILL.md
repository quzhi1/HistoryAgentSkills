---
name: query-ancient-books-api
description: 查询古籍文献知识图谱API，获取古籍原文、诗词、历史人物、事件等信息。当用户需要引用古籍原文、查询诗词内容、了解历史人物关系、检索历史事件时使用此技能。
---

# 古籍文献知识图谱API查询

查询古籍文献知识图谱网（cnkgraph.com）的开放API，获取原始古籍文献、诗词作品、历史人物和事件信息。

## API基本信息

- **基础URL**：`https://open.cnkgraph.com`
- **API文档**：https://open.cnkgraph.com/swagger
- **使用限制**：仅限非商业用途
- **返回格式**：JSON

## 数据资源

API提供以下主要数据库：
- **诗文库**：约485M，包含历代诗词文章
- **古籍库**：约2GB，包含大量古籍文献
- **人物库**：历史人物信息和关系
- **事件库**：历史事件记录

## 数据格式

- 默认返回简体中文
- 设置 `Accept-Language: zh-hant` 可获取原始繁体数据
- 所有返回数据为JSON格式

## API端点（常用）

基于PostMan示例和文档，主要API端点包括：

**本技能脚本已按 [Swagger 规范](https://open.cnkgraph.com/swagger/index.html) 对齐**（规范 JSON：`/swagger/v1/swagger.json`）。

### 1. 诗文检索 POST `/api/Writing/Find`

请求体为 WritingModel（JSON 对象），如 `Key`、`Author`、`Dynasty`、`PageNo`。**非** GET `/Writing/Search`。

```bash
curl -X POST "https://open.cnkgraph.com/api/Writing/Find" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"Key":"月","Author":"李白","PageNo":0}'
```

### 2. 古籍检索 POST `/api/Book/Search`

请求体为**关键词的 JSON 字符串**（如 `"赤壁"`）。可选 query：`pageNo`、`bookId`。返回书目列表与命中数。

```bash
curl -X POST "https://open.cnkgraph.com/api/Book/Search" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '"关键词"'
```

### 2b. 古籍原文片段检索 POST `/api/Book/Find`（**历史细节必用**）

请求体为 **BookModel**（JSON 对象）：`Key`（关键词，必填）、`PageNo`（页码，0 起）、可选 `BookIds`。  
返回 **Result**：带上下文的命中片段，每项含 **PreviousText**（前文）、**MatchedText**（命中词）、**LaterText**（后文），以及 **Book**、**Volume**（出处：书名、卷）。用于补充**时间、地点、相关人物、起因、经过、结果**。

**关键词使用规范**：
- ✅ **推荐**：简短精准的关键词（2-6 字）
  - 单个人名：`"崔浩"` `"刘知远"`
  - 事件短语：`"暴扬国恶"` `"国史 刊石"` `"刘知远 称帝"`
  - 时间+人物：`"开运四年"` `"刘知远 太原"`
- ❌ **避免**：过长的多词堆砌（超过 8 字）
  - ❌ `"刘知远 河东 群臣劝进"`（太长，可能返回 404）
  - ❌ `"崔浩 国史 暴扬国恶 太平真君"`（关键词过多）
- 📌 **多维度查询**：分别使用不同关键词查询，而非堆在一起
  - 如需了解"刘知远称帝"的细节，应分别查询：
    - `"刘知远 称帝"` → 称帝事件
    - `"刘知远 太原"` → 地点相关
    - `"开运四年"` → 时间背景

```bash
# 脚本示例
python cnkgraph/scripts/query_api.py find --keyword "崔浩"
python cnkgraph/scripts/query_api.py find --keyword "暴扬国恶"
python cnkgraph/scripts/query_api.py find --keyword "刘知远 称帝"
```

```bash
curl -X POST "https://open.cnkgraph.com/api/Book/Find" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"Key":"崔浩","PageNo":0}'
```

### 3. 人物查询 GET `/api/People/{id}`

路径中的 `id` 为姓名/朝代键/人物 Id。**非** GET `/People/Search?name=`。

```bash
# 查询历史人物（姓名需 URL 编码）
curl "https://open.cnkgraph.com/api/People/苏轼"
```

### 4. 事件查询 `/api/Event/Search`

**注意**：Event 不在 Swagger 中，该端点可能返回 404。脚本中先 GET，遇 405 则 POST（body 为关键词 JSON 字符串）。

## 使用流程

### 历史细节查询（时间、地点、人物、起因、经过、结果）

回答历史人物、事件类问题时，**不要仅查辞典**；应视情况用 cnkgraph API 补充**具体时间、地点、相关人物、起因、经过、结果**：

1. **古籍原文片段**：使用 **POST /api/Book/Find**（脚本命令：`python cnkgraph/scripts/query_api.py find --keyword "关键词"`）。
   - 请求体：`{"Key": "关键词", "PageNo": 0}`，可选 `BookIds` 限定书籍。
   - 返回：`Result[].Books[].Volumes[].Pages[]` 中每项含 **PreviousText**（前文）、**MatchedText**（命中词）、**LaterText**（后文），即带上下文的原文片段；`Book`、`Volume` 为出处（书名、卷）。
   - **多次查询策略**：对人名、事件名、关键短语（如「暴扬国恶」「国史 刊石」）**分别**进行多次查询（而非堆在一个关键词中），可交叉验证并补充起因、经过、结果。每次查询使用简短关键词（2-6 字），避免超过 8 字的复杂组合。

2. **引用要求**：凡引用古籍片段，**必须**标明**书名与章节名**（如《钦定古今图书集成》某汇编某典 卷X；若片段内引《通鉴》《魏书》等，一并写出）。

3. **与辞典配合**：先查辞典得基础认知与正史线索，再用 Book/Find 检索原文片段验证并补充六类信息（时间、地点、相关人物、起因、经过、结果）。

### 标准查询流程

当用户提出历史问题需要古籍原文支撑时：

1. **分析需求**：确定需要查询的类型（诗文/古籍/人物/事件）；若为人物/事件，计划用 Book/Find 补充细节。

2. **构建查询**：根据用户问题提取关键参数；必要时多组关键词（人名+事件短语）检索。

3. **执行API调用**：使用脚本或 curl/requests；**原文片段用 Book/Find**（`find --keyword`），书目用 Book/Search（`book --keyword`）。

4. **解析结果**：Book/Find 的 Result 中提取 PreviousText+MatchedText+LaterText 组成可引用片段；记录 Book、Volume 作为出处。

5. **引用原文**：必须标注古籍出处和原文；**凡史料一律给出处，且须包含书名与章节名**（如《XX史》卷X《XX传》），格式：
   ```
   据《书名》卷X《章节/传名》记载：
   「古籍原文」
   **出处**：《书名》卷X《章节名》
   ```

### Python调用示例

```python
import requests

# 查询诗词（POST /Writing/Find，body 为 WritingModel）
def search_poetry(keyword=None, author=None, dynasty=None):
    url = "https://open.cnkgraph.com/api/Writing/Find"
    body = {"PageNo": 0}
    if keyword: body["Key"] = keyword
    if author: body["Author"] = author
    if dynasty: body["Dynasty"] = dynasty
    response = requests.post(url, json=body, headers={"Content-Type": "application/json; charset=utf-8"})
    return response.json()

# 查询古籍（POST /Book/Search，body 为关键词 JSON 字符串）
def search_books(keyword):
    url = "https://open.cnkgraph.com/api/Book/Search"
    response = requests.post(url, json=keyword, headers={"Content-Type": "application/json; charset=utf-8"})
    return response.json()

# 查询人物（GET /People/{id}，id 为姓名）
def search_people(name):
    from urllib.parse import quote
    url = f"https://open.cnkgraph.com/api/People/{quote(name, safe='')}"
    response = requests.get(url)
    return response.json()
```

## 查询策略

### 诗词查询

适用场景：
- 用户询问某首诗的内容
- 查找包含特定词语的诗句
- 查询某作者的作品
- 查找某朝代的诗词

查询技巧：
- 优先使用作者名查询
- 使用朝代缩小范围
- 关键词不要太长，2-4字为佳

### 古籍查询

适用场景：
- 查找历史事件的文献记载
- 验证历史说法的出处
- 查询历史典籍内容

查询技巧：
- 使用事件或人物核心关键词
- 结合历史辞典的信息来确定搜索方向

### 人物查询

适用场景：
- 查询历史人物基本信息
- 了解人物关系网络
- 查找人物相关著作

### 事件查询

适用场景：
- 查询历史事件详情
- 查找事件的文献记载
- 了解事件的相关人物

## 回答规范

### 必须遵守

- ✅ **引用原文**：必须完整引用古籍原文，使用「」标注
- ✅ **注明出处**：必须注明古籍名称、作者、朝代；**史料须写清书名+章节名**（卷、传/纪名）
- ✅ **保持原貌**：不要修改古文原文
- ✅ **提供翻译**：引用古文后应提供现代汉语解释

### 引用格式（史料须带书名+章节名）

```
据《史书名》卷X《传/纪名》记载：

「古文原文」

**出处**：《史书名》卷X《传名》
译文：现代汉语翻译
```

或对于诗词：

```
唐代诗人李白的《诗名》：

「诗词原文」

这首诗描述了...（解释）
```

### 禁止操作

- ❌ 不要在没有调用API的情况下编造古籍内容
- ❌ 不要修改古籍原文
- ❌ 不要省略出处信息
- ❌ 不要混淆不同古籍的内容

## 完整示例

### 示例1：查询李白的诗

**用户问题**：李白有哪些关于月亮的诗？

**操作**：
```bash
curl "https://open.cnkgraph.com/api/Writing/Search?author=李白&keyword=月"
```

**回答格式**：
```
查询古籍文献知识图谱API，找到李白关于月亮的诗作包括：

1. 《静夜思》（唐·李白）：
「床前明月光，疑是地上霜。举头望明月，低头思故乡。」

这是李白最著名的思乡诗，通过月光引发思乡之情。

2. 《月下独酌》（唐·李白）：
「花间一壶酒，独酌无相亲。举杯邀明月，对影成三人。」

诗人借月抒发孤独之感...
```

### 示例2：查询历史事件的古籍记载

**用户问题**：关于赤壁之战，古籍是怎么记载的？

**操作步骤**：
1. 先用历史辞典技能了解事件基本情况
2. 再调用古籍API查找原始记载

```bash
# 查询相关古籍
curl "https://open.cnkgraph.com/api/Book/Search?keyword=赤壁"

# 查询相关事件
curl "https://open.cnkgraph.com/api/Event/Search?keyword=赤壁之战"
```

**回答格式**：
```
根据《中国历史大辞典》：
「赤壁之战，东汉建安十三年（208年）...（辞典内容）」

据《三国志》等古籍记载：
「...（古籍原文）」

这场战役是三国时期的重要转折点...（综合分析）
```

### 示例3：查询历史人物

**用户问题**：苏轼有什么代表作？

**操作**：
```bash
# 查询人物信息
curl "https://open.cnkgraph.com/api/People/Search?name=苏轼"

# 查询其诗词作品
curl "https://open.cnkgraph.com/api/Writing/Search?author=苏轼"
```

## 与历史辞典协同

完整的历史问题回答流程：

1. **查历史辞典**（dict技能）：
   - 获取准确的历史定义和背景
   - 确定关键时间、地点、人物

2. **查古籍API**（本技能）：
   - 查找原始文献记载
   - 获取诗词原文
   - 查证历史说法

3. **综合回答**：
   - 先引用辞典提供基础认知
   - 再引用古籍原文作为史料支撑
   - 最后进行分析和解释

## 错误处理

### API返回错误

```python
response = requests.get(url, params=params)
if response.status_code != 200:
    print(f"API调用失败: {response.status_code}")
    # 尝试其他查询策略
```

### 未找到结果

- 尝试简化关键词
- 尝试使用同义词
- 扩大查询范围（如不限定朝代）
- 如果确实没有相关记载，明确告知用户

### 网络超时

- 适当增加超时时间
- 重试API调用
- 降级到只使用历史辞典

## 技术要求

### 需要的Python包

```bash
pip install requests
```

### 推荐做法

- 使用 requests.Session() 复用连接
- 设置合理的超时时间（10-30秒）
- 缓存查询结果避免重复调用
- 处理好异常情况

## 下载完整数据（可选）

如需离线使用，可以下载完整数据包：
- 诗文库：https://cnkgraph.com/Home/OpenResources
- 古籍库：https://cnkgraph.com/Home/OpenResources

但在线API查询通常更方便快捷。
