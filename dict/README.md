# 中国历史大辞典查询技能

查询《中国历史大辞典4合1》，获取权威的历史人物、事件、制度、地理等专业解释。

## 辞典简介

《中国历史大辞典》是一部权威的历史工具书，包含：
- 历史人物传记
- 历史事件记载
- 典章制度解释
- 历史地理说明
- 文化典故阐释

## 使用方法

### 通过Agent自动查询

当你询问历史问题时，Agent会自动使用此技能查询辞典。

### 命令行查询

```bash
# 查询单个词条
python dict/scripts/query_dict.py "李白"

# 同时查询多个词条
python dict/scripts/query_dict.py "李白" "杜甫" "白居易"
```

### Python代码查询

```python
import subprocess

def query_dict(keyword):
    result = subprocess.run(
        ["mdict", "-q", keyword, "dict/历史辞典4合1.mdx"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

# 使用
content = query_dict("李白")
print(content)
```

## 查询技巧

### 1. 精确关键词

优先使用最精确的名称：
- ✅ "李白" 而不是 "唐代诗人李白"
- ✅ "安史之乱" 而不是 "安禄山叛乱"

### 2. 尝试多种表述

如果查不到，尝试：
- 简化表述："唐太宗李世民" → "李世民" 或 "唐太宗"
- 使用别名："诗仙" → "李白"
- 使用正式名称："玄武门之变" 而不是 "玄武门事变"

### 3. 相关词条

如果直接查询不到，查询相关概念：
- 查询人物所在的朝代
- 查询事件涉及的主要人物
- 查询制度所属的类别

## 输出格式

辞典返回的是HTML格式的内容，包含：
- 词条标题
- 详细解释
- 时间信息
- 相关链接

在回答用户时，应该：
1. 提取关键信息
2. 使用「」标注原文
3. 注明出处为《中国历史大辞典》

## 常见问题

**Q: 辞典文件太大，可以压缩吗？**
A: 不需要压缩，使用mdict命令查询时不会加载整个文件。

**Q: 查询速度慢怎么办？**
A: 首次查询可能需要建立索引，后续会快很多。

**Q: 可以模糊查询吗？**
A: mdict支持精确查询。如需模糊查询，可以多尝试几个相关词条。

**Q: 查询不到怎么办？**
A: 尝试简化关键词、使用同义词，或查询相关的更大类别。

## 技术细节

### MDX格式

- MDX: 辞典索引和文本内容
- 格式说明: https://github.com/zhansliu/writemdict

### mdict-utils工具

安装：
```bash
pip install mdict-utils
```

主要功能：
- 查询：`mdict -q <word> <file.mdx>`
- 解包：`mdict -x <file.mdx> -d <output_dir>`
- 打包：`mdict -a <input.txt> <output.mdx>`

## 与其他技能协同

此技能通常与以下技能配合使用：

1. **cnkgraph技能**: 查询古籍原文
2. **历史专家系统**: 综合查询和回答

工作流程：
1. 先用本技能查辞典获取定义
2. 再用cnkgraph查古籍获取原文
3. 综合两者给出完整回答

## 参考资料

- [mdict-utils PyPI](https://pypi.org/project/mdict-utils/)
- [MDX文件格式说明](https://github.com/zhansliu/writemdict/blob/master/fileformat.md)
