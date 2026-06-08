# 故障排查指南

遇到问题？这里提供详细的排查步骤和解决方案。

## 常见问题分类

- [安装问题](#安装问题)
- [辞典查询问题](#辞典查询问题)
- [API调用问题](#api调用问题)
- [性能问题](#性能问题)
- [结果问题](#结果问题)

---

## 安装问题

### 问题1: pip安装失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement mdict-utils
```

**解决方案**:

1. 检查Python版本（需要3.6+）
   ```bash
   python --version
   ```

2. 升级pip
   ```bash
   pip install --upgrade pip
   ```

3. 使用国内镜像
   ```bash
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple mdict-utils requests
   ```

### 问题2: mdict命令找不到

**症状**:
```
mdict: command not found
```

**解决方案**:

1. 确认是否安装成功
   ```bash
   pip show mdict-utils
   ```

2. 查找mdict可执行文件
   ```bash
   which mdict
   ```

3. 如果找不到，尝试使用完整路径
   ```bash
   python -m mdict -q "李白" dict/历史辞典4合1.mdx
   ```

4. 或重新安装
   ```bash
   pip uninstall mdict-utils
   pip install mdict-utils
   ```

### 问题3: 权限问题

**症状**:
```
Permission denied
```

**解决方案**:

1. 给脚本添加执行权限
   ```bash
   chmod +x scripts/*.py dict/scripts/*.py cnkgraph/scripts/*.py
   ```

2. 或使用python直接运行
   ```bash
   python dict/scripts/query_dict.py "李白"
   ```

---

## 辞典查询问题

### 问题1: 找不到辞典文件

**症状**:
```
错误：找不到辞典文件 dict/历史辞典4合1.mdx
```

**解决方案**:

1. 检查文件是否存在
   ```bash
   ls -lh dict/*.mdx
   ```

2. 检查文件路径
   ```bash
   pwd  # 确认当前目录
   ```

3. 确保在项目根目录运行
   ```bash
   cd /path/to/HistoryAgentSkills
   python dict/scripts/query_dict.py "李白"
   ```

### 问题2: 查询超时

**症状**:
```
查询超时（关键词：xxx）
```

**原因**:
- 首次查询需要建立索引
- 辞典文件较大

**解决方案**:

1. 增加超时时间（修改脚本中的TIMEOUT）
   ```python
   TIMEOUT = 60  # 增加到60秒
   ```

2. 耐心等待首次查询完成

3. 后续查询会快很多

### 问题3: 查询结果为空

**症状**:
```
未找到词条"xxx"
```

**解决方案**:

1. **简化关键词**
   - "唐太宗李世民" → "李世民" 或 "唐太宗"
   - "玄武门事变" → "玄武门之变"

2. **尝试同义词**
   - "诗仙" → "李白"
   - "杜工部" → "杜甫"

3. **使用正式名称**
   - 使用历史上的正式称谓
   - 避免现代简称

4. **查询相关概念**
   - 如果查不到人物，查其所在朝代
   - 如果查不到事件，查主要人物

### 问题4: 返回结果乱码

**症状**:
显示的文字不可读

**解决方案**:

1. 检查终端编码
   ```bash
   echo $LANG
   ```

2. 设置UTF-8编码
   ```bash
   export LANG=zh_CN.UTF-8
   ```

3. 在Python脚本中指定编码
   ```python
   result = subprocess.run(..., encoding='utf-8')
   ```

---

## API调用问题

### 问题1: 网络连接失败

**症状**:
```
requests.exceptions.ConnectionError
```

**解决方案**:

1. 检查网络连接
   ```bash
   ping cnkgraph.com
   ```

2. 检查是否能访问API
   ```bash
   curl https://open.cnkgraph.com/api/Writing/Search?author=李白
   ```

3. 检查防火墙设置

4. 尝试使用代理（如需要）
   ```python
   proxies = {
       'http': 'http://proxy:port',
       'https': 'http://proxy:port'
   }
   requests.get(url, proxies=proxies)
   ```

### 问题2: API返回错误

**症状**:
```
{"error": "..."}
```

**解决方案**:

1. 检查请求参数是否正确
   ```python
   print(params)  # 打印参数查看
   ```

2. 查看完整错误信息
   ```python
   print(response.text)
   ```

3. 参考API文档调整参数
   - https://open.cnkgraph.com/swagger

4. 确认API没有变更
   - 访问官网查看最新文档

### 问题3: 请求超时

**症状**:
```
requests.exceptions.Timeout
```

**解决方案**:

1. 增加超时时间
   ```python
   response = requests.get(url, params=params, timeout=60)
   ```

2. 检查网络速度

3. 尝试减少请求数据量
   ```python
   params['limit'] = 5  # 减少返回数量
   ```

4. 重试机制
   ```python
   import time
   for i in range(3):
       try:
           response = requests.get(url, params=params, timeout=30)
           break
       except requests.exceptions.Timeout:
           if i < 2:
               time.sleep(2)
               continue
           raise
   ```

### 问题4: API返回空结果

**症状**:
API调用成功但返回空列表或None

**解决方案**:

1. **简化搜索条件**
   ```python
   # 不好：条件太多
   params = {"author": "李白", "dynasty": "唐", "keyword": "明月", "genre": "诗"}
   
   # 好：条件适中
   params = {"author": "李白", "keyword": "月"}
   ```

2. **放宽搜索范围**
   ```python
   # 只用关键词，不限制其他条件
   params = {"keyword": "赤壁"}
   ```

3. **检查关键词拼写**

4. **尝试相关词汇**

---

## 性能问题

### 问题1: 查询速度慢

**现象**:
查询需要很长时间

**原因分析**:
1. 辞典文件大（首次查询）
2. 网络速度慢（API调用）
3. 查询关键词太宽泛

**解决方案**:

1. **辞典查询优化**
   ```python
   # 首次查询后，mdict会建立缓存
   # 耐心等待首次查询完成即可
   ```

2. **API查询优化**
   ```python
   # 限制返回数量
   params['limit'] = 5
   
   # 使用更精确的查询条件
   params = {"author": "李白", "title": "静夜思"}  # 精确
   # 而不是
   params = {"keyword": "月"}  # 太宽泛
   ```

3. **并发查询**
   ```python
   import concurrent.futures
   
   with concurrent.futures.ThreadPoolExecutor() as executor:
       futures = [
           executor.submit(query_dictionary, "李白"),
           executor.submit(query_api_poetry, author="李白")
       ]
       results = [f.result() for f in futures]
   ```

4. **缓存结果**
   ```python
   import json
   from pathlib import Path
   
   cache_file = Path(f".cache/{keyword}.json")
   if cache_file.exists():
       return json.loads(cache_file.read_text())
   # 否则查询并缓存
   ```

### 问题2: 内存占用高

**现象**:
系统内存占用过高

**解决方案**:

1. 不要一次加载全部辞典
   ```python
   # 好：使用mdict命令查询
   subprocess.run(["mdict", "-q", keyword, dict_file])
   
   # 不好：读取整个文件
   with open(dict_file, 'rb') as f:
       content = f.read()  # 文件太大！
   ```

2. 限制API返回数量
   ```python
   params['limit'] = 10  # 不要请求太多数据
   ```

3. 及时清理不需要的数据
   ```python
   result = query_something()
   process(result)
   del result  # 释放内存
   ```

---

## 结果问题

### 问题1: 引用格式不正确

**错误示例**:
```
李白（701-762），字太白...
```

**正确示例**:
```
根据《中国历史大辞典》：
「李白（701-762），字太白...」
```

**规范**:
- 必须使用「」标注原文
- 必须注明出处
- 必须区分辞典和古籍

### 问题2: 未找到信息就编造

**错误做法**:
查询不到信息时凭记忆或猜测回答

**正确做法**:
```python
result = query_dictionary(keyword)
if not result:
    print(f"未找到词条"{keyword}"")
    print("建议：")
    print("  1. 尝试简化关键词")
    print("  2. 使用同义词或别称")
    print("  3. 查询相关的更大类别")
    return None
```

### 问题3: 混淆不同来源

**错误做法**:
将辞典内容和古籍内容混在一起

**正确做法**:
```markdown
## 基本信息
根据《中国历史大辞典》：
「辞典内容」

## 文献记载
据《史记》（汉·司马迁）记载：
「古籍内容」
```

---

## 调试技巧

### 1. 启用详细日志

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug(f"查询参数: {params}")
logger.debug(f"查询结果: {result}")
```

### 2. 逐步测试

```bash
# 步骤1: 测试mdict命令
mdict -q "李白" dict/历史辞典4合1.mdx

# 步骤2: 测试Python脚本
python dict/scripts/query_dict.py "李白"

# 步骤3: 测试API
curl "https://open.cnkgraph.com/api/Writing/Search?author=李白"

# 步骤4: 测试综合查询
python scripts/history_query.py "李白"
```

### 3. 查看详细错误

```python
import traceback

try:
    result = query_something()
except Exception as e:
    print(f"错误: {e}")
    traceback.print_exc()  # 打印完整堆栈
```

### 4. 测试网络连接

```bash
# 测试DNS解析
nslookup cnkgraph.com

# 测试连接
curl -I https://open.cnkgraph.com

# 测试API端点
curl -v "https://open.cnkgraph.com/api/Writing/Search?author=李白"
```

---

## 获取更多帮助

### 查看日志

```bash
# 如果脚本有日志输出
tail -f logs/history_query.log
```

### 查看文档

- 主README: `README.md`
- 快速入门: `QUICKSTART.md`
- 使用示例: `EXAMPLES.md`
- 各模块README: `dict/README.md`, `cnkgraph/README.md`

### 查看源码

所有脚本都有注释，可以直接查看：
- `dict/scripts/query_dict.py`
- `cnkgraph/scripts/query_api.py`
- `scripts/history_query.py`

### 在线资源

- [古籍文献知识图谱网](https://cnkgraph.com)
- [开放API文档](https://open.cnkgraph.com/swagger)
- [mdict-utils文档](https://pypi.org/project/mdict-utils/)

---

## 问题仍未解决？

如果以上方法都无法解决问题：

1. **检查基础环境**
   - Python版本
   - 网络连接
   - 文件权限

2. **简化问题**
   - 使用最简单的示例测试
   - 排除其他因素干扰

3. **收集信息**
   - 完整的错误信息
   - 使用的命令
   - 环境信息

4. **查看最新文档**
   - API可能已更新
   - 检查官方网站

祝你顺利解决问题！🔧
