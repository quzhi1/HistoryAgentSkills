# 古籍文献知识图谱API查询技能

查询古籍文献知识图谱网的开放API，获取古籍原文、诗词、历史人物、事件等信息。

## API简介

[古籍文献知识图谱网](https://cnkgraph.com)提供开放的Web API接口，包含：

- **诗文库**: 约485M，历代诗词文章
- **古籍库**: 约2GB，古籍文献原文
- **人物库**: 历史人物信息和关系网络
- **事件库**: 历史事件记录

## 快速开始

### 安装依赖

```bash
pip install requests
```

### 基本使用

#### 1. 查询诗词

```bash
# 命令行
python cnkgraph/scripts/query_api.py poetry --author 李白 --keyword 月

# Python代码
import requests

response = requests.get(
    "https://open.cnkgraph.com/api/Writing/Search",
    params={"author": "李白", "keyword": "月"}
)
print(response.json())
```

#### 2. 查询古籍

```bash
# 命令行
python cnkgraph/scripts/query_api.py book --keyword 赤壁

# Python代码（Book/Search 仅支持 POST，body 为关键词的 JSON 字符串）
response = requests.post(
    "https://open.cnkgraph.com/api/Book/Search",
    json="赤壁",
    headers={"Content-Type": "application/json; charset=utf-8"}
)
print(response.json())
```

#### 3. 查询人物

```bash
# 命令行
python cnkgraph/scripts/query_api.py people --name 苏轼

# Python代码
response = requests.get(
    "https://open.cnkgraph.com/api/People/Search",
    params={"name": "苏轼"}
)
print(response.json())
```

#### 4. 查询事件

```bash
# 命令行
python cnkgraph/scripts/query_api.py event --keyword 安史之乱

# Python代码
response = requests.get(
    "https://open.cnkgraph.com/api/Event/Search",
    params={"keyword": "安史之乱"}
)
print(response.json())
```

## API详细说明

### 基础信息

- **基础URL**: `https://open.cnkgraph.com/api`
- **文档地址**: https://open.cnkgraph.com/swagger/index.html
- **Swagger JSON**: https://open.cnkgraph.com/swagger/v1/swagger.json
- **返回格式**: JSON
- **使用限制**: 仅限非商业用途

**本仓库脚本已按 Swagger 规范对齐**：诗词用 POST `/Writing/Find`，人物用 GET `/People/{id}`，古籍用 POST `/Book/Search`。Event 不在 Swagger 中，可能返回 404。

### 常用端点（与 Swagger 一致）

#### 诗词检索 POST `/Writing/Find`

请求体为 WritingModel（JSON 对象）：
- `Key`: 主搜索关键词（可选）
- `Author`: 作者（可选）
- `Dynasty`: 朝代（可选）
- `PageNo`: 页码，从 0 开始（可选）

示例：
```python
# 查询李白关于月的诗
body = {"Key": "月", "Author": "李白", "PageNo": 0}
response = requests.post(
    "https://open.cnkgraph.com/api/Writing/Find",
    json=body,
    headers={"Content-Type": "application/json; charset=utf-8"}
)
```

#### 古籍检索 POST `/Book/Search`

请求体为**关键词的 JSON 字符串**（如 `"赤壁"`）。可选 query：`pageNo`（页码）、`bookId`（限定书籍）。

#### 人物查询 GET `/People/{id}`

路径中的 `id` 为姓名/朝代键/人物 Id（支持别名）。无 query 参数。

示例：
```python
# 查询苏轼
from urllib.parse import quote
name = "苏轼"
response = requests.get(f"https://open.cnkgraph.com/api/People/{quote(name, safe='')}")
```

#### 事件查询 `/Event/Search`

**注意**：Event 不在官方 Swagger 中，该端点可能返回 404。脚本中保留 GET，遇 405 时尝试 POST（body 为关键词 JSON 字符串）。

### 数据格式设置

HTTP Header设置：
- 默认返回简体中文
- `Accept-Language: zh-hant` 获取繁体原文

```python
headers = {
    "Accept-Language": "zh-hant"  # 获取繁体原文
}
response = requests.get(url, params=params, headers=headers)
```

## 使用技巧

### 1. 诗词查询策略

**优先级顺序**：
1. 作者 + 题目（最精确）
2. 作者 + 关键词
3. 朝代 + 关键词
4. 仅关键词（范围最广）

**示例**：
```python
# 最佳：精确查询
{"author": "李白", "title": "静夜思"}

# 较好：作者+关键词
{"author": "李白", "keyword": "月"}

# 一般：朝代+关键词
{"dynasty": "唐", "keyword": "月"}

# 备用：仅关键词
{"keyword": "明月"}
```

### 2. 关键词选择

**好的关键词**：
- ✅ 2-4个字
- ✅ 核心概念词
- ✅ 避免虚词

**不好的关键词**：
- ❌ 过长的短语
- ❌ 包含标点符号
- ❌ 包含"的"、"是"等虚词

### 3. 错误处理

```python
try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    if "error" in data:
        # 处理业务错误
        print(f"查询失败: {data['error']}")
    else:
        # 处理正常返回
        process_data(data)
        
except requests.exceptions.Timeout:
    print("请求超时，请稍后重试")
except requests.exceptions.RequestException as e:
    print(f"网络错误: {e}")
```

### 4. 结果为空的处理

如果API返回空结果：
1. 简化关键词
2. 尝试同义词
3. 扩大范围（如不限定朝代）
4. 尝试相关词汇

## 引用规范

### 诗词引用格式

```markdown
朝代·作者《诗名》：

「诗词原文」

[解释说明]
```

示例：
```markdown
唐·李白《静夜思》：

「床前明月光，疑是地上霜。
举头望明月，低头思故乡。」

这是李白的代表作之一，通过月光引发思乡之情。
```

### 古籍引用格式

```markdown
据《书名》（朝代·作者）记载：

「古文原文」

译文：现代汉语翻译
```

### 人物信息引用

```markdown
据古籍文献知识图谱记载，[人名]（[生卒年]）：
- 朝代：[朝代]
- 字号：[字号]
- 主要成就：[成就]
```

## 与辞典技能协同

完整的查询流程：

```python
# 1. 先查辞典（dict技能）
dict_result = query_dictionary("李白")
# 获取：基本信息、生卒年、历史地位

# 2. 再查API（本技能）
api_result = query_api_poetry(author="李白")
# 获取：实际诗词作品

# 3. 综合回答
answer = format_answer(dict_result, api_result)
```

## 高级用法

### 1. 批量查询

```python
authors = ["李白", "杜甫", "白居易"]
results = {}

for author in authors:
    response = requests.get(
        "https://open.cnkgraph.com/api/Writing/Search",
        params={"author": author, "limit": 5}
    )
    results[author] = response.json()
```

### 2. 分页查询

```python
def query_all_poetry(author, page_size=20):
    all_results = []
    offset = 0
    
    while True:
        params = {
            "author": author,
            "limit": page_size,
            "offset": offset
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data or len(data) == 0:
            break
            
        all_results.extend(data)
        offset += page_size
        
    return all_results
```

### 3. 缓存优化

```python
import json
from pathlib import Path

cache_dir = Path(".cache/cnkgraph")
cache_dir.mkdir(parents=True, exist_ok=True)

def cached_query(endpoint, params):
    # 生成缓存键
    cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
    cache_file = cache_dir / f"{cache_key}.json"
    
    # 检查缓存
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    
    # 查询API
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    data = response.json()
    
    # 保存缓存
    cache_file.write_text(json.dumps(data, ensure_ascii=False))
    
    return data
```

## 注意事项

### 使用限制

- ⚠️ 仅限非商业用途
- ⚠️ 请合理控制请求频率
- ⚠️ 大量查询建议下载离线数据包

### 网络问题

- 设置合理的超时时间（建议30秒）
- 处理好网络异常
- 考虑添加重试机制

### 数据准确性

- API返回的是已整理的数据
- 可能存在少量错误或遗漏
- 重要内容建议交叉验证

## 下载离线数据

如需离线使用完整数据：

1. 访问 https://cnkgraph.com/Home/OpenResources
2. 下载诗文库（约485M）或古籍库（约2GB）
3. 解压后可本地查询

## 参考资源

- [古籍文献知识图谱网](https://cnkgraph.com)
- [开放API文档](https://open.cnkgraph.com/swagger)
- [PostMan示例](https://open.cnkgraph.com/Api/postman.zip)
- [开放资源下载](https://cnkgraph.com/Home/OpenResources)

## 常见问题

**Q: API调用失败怎么办？**
A: 检查网络连接，确认URL正确，查看返回的错误信息。

**Q: 如何获取繁体原文？**
A: 设置HTTP Header: `Accept-Language: zh-hant`

**Q: API有访问频率限制吗？**
A: 文档未明确说明，建议合理控制请求频率，避免短时间大量请求。

**Q: 可以商业使用吗？**
A: 不可以，开放API仅限非商业用途。商业使用请联系网站。
