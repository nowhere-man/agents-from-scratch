---
title: 文档摄取、Chunking 与 Metadata
aliases:
  - RAG 分块
  - Chunking 策略
tags:
  - rag
  - chunking
  - metadata
  - ingestion
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://docs.llamaindex.ai/
  - https://python.langchain.com/docs/concepts/text_splitters/
---

# 文档摄取、Chunking 与 Metadata

> [!abstract] 本章只解决一个问题
> 为什么同一份政策文档，换一种切法就会让 RAG 的答案完全不同？读完后，你应该能为不同文档选择固定、递归、语义或结构化分块，并解释每种选择保留了什么、丢失了什么。

上一章已经定义了 Chunk Record。本章把它从一段抽象文本变成可执行的设计：先解析原文的结构，再决定检索单元的边界，最后把版本、权限和回查位置写进 metadata。

## Chunking 其实是在选择“证据边界”

假设原文如下：

~~~text
7. 海外住宿
7.1 普通员工
东京、首尔等城市每日住宿上限为 180 美元。该标准自 2026 年 6 月 1 日起生效。
若出差超过 14 天，需提前获得部门负责人批准。
7.2 实习生
实习生适用每日 120 美元上限。
~~~

如果只切出一句“每日住宿上限为 180 美元”，召回很容易，但模型看不到它只适用于普通员工、哪些城市和何时生效。如果把整份 80 页手册当作一个 chunk，范围信息完整，却难以精确召回，而且会浪费上下文窗口。

因此，chunk 的目标不是“越小越精确”或“越大越完整”，而是在以下目标之间取平衡：

1. **可召回：**查询中的词或语义能在单元内出现；
2. **可理解：**单元带有足够的上下文和适用范围；
3. **可引用：**能回到原文的页码、段落或表格行；
4. **可去重：**相邻单元不会反复占满上下文；
5. **可更新：**局部修改不必重建整套索引。

## 先把原文解析成结构，而不是直接按字符切

摄取流程通常是：

~~~mermaid
flowchart LR
    A["文件 / 程序接口 / 网页"] --> B["解析器"]
    B --> C["结构树<br/>标题、段落、表格、代码、图片"]
    C --> D["规范化与去重"]
    D --> E["按结构切 chunk"]
    E --> F["补 metadata 与 provenance"]
    F --> G["校验、embedding、写索引"]
~~~

**Provenance（来源链）**至少包括 source URI、文档版本和原文位置。对于 PDF，位置可以是页码和文本框坐标；对于网页，可以是 URL、标题路径和抓取时间；对于代码，可以是文件路径、符号名和行号。

解析阶段要特别留意：

- PDF 的双栏阅读顺序；
- 表格跨页、合并单元格和单位；
- 列表编号与标题层级；
- HTML 导航栏、页脚和重复模板；
- Markdown 代码块、引用块和 frontmatter；
- OCR 把“180”识别成“18O”、把“≤”丢掉；
- 同一文档的多语言版本和附件关系。

如果结构已经在解析阶段丢失，后面的 embedding 无法把它“学回来”。

## 策略一：固定长度分块

固定分块按字符数、词数或 tokenizer 的 token 数切割，通常加一个 overlap（重叠区）。

~~~python
def fixed_chunks(tokens, size=400, overlap=80):
    step = size - overlap
    return [
        tokens[start:start + size]
        for start in range(0, len(tokens), step)
    ]
~~~

### 为什么需要 overlap

如果一句规则正好跨过边界：

~~~text
chunk A: 东京、首尔等城市每日住宿上限为
chunk B: 180 美元，自 2026 年 6 月 1 日起生效。
~~~

没有 overlap，两个 chunk 都只包含半条规则。重叠一小段可以提高跨边界命中的概率。

### 固定分块的取舍

| 参数 | 增大后的好处 | 增大后的代价 |
|---|---|---|
| chunk size | 更多局部上下文，较少断句 | 召回不够精细，重排和生成成本上升 |
| overlap | 边界信息更不容易丢 | 索引重复、候选去重更难 |
| token 而非字符 | 与模型窗口和成本更一致 | 需要使用目标 tokenizer，中文/代码长度差异更大 |

固定分块适合快速 baseline、结构弱的日志或大规模纯文本，但它不知道标题、表格和主题是否在边界处变化。

## 策略二：递归分块

递归分块从“较大的结构分隔符”逐步退到“较小的分隔符”。对 Markdown 可以按：

~~~text
标题 → 段落 → 句子 → 空格/字符
~~~

先尝试让一个标题下的内容成为单元；若超过大小，再按段落拆；段落仍太长，再按句子拆。这样比“从头每 400 token 切一刀”更容易保留局部结构。

### 一个最小过程

~~~python
def recursive_split(text, separators, limit):
    if token_len(text) <= limit:
        return [text]
    separator = first_separator_that_occurs(separators, text)
    parts = text.split(separator)
    groups = pack_adjacent_parts(parts, limit)
    result = []
    for group in groups:
        if token_len(group) <= limit:
            result.append(group)
        else:
            result.extend(
                recursive_split(group, separators[1:], limit)
            )
    return result
~~~

递归不是“自动理解语义”。它只是利用文档已有的结构；如果原文标题本身混乱，分块仍可能不理想。

## 策略三：语义分块

语义分块先按句子或短段落切出候选，再计算相邻片段的 embedding 相似度。当相邻片段的主题突然变化时，在那里设置断点。

设相邻句子的向量为 $\mathbf{s}_i$ 和 $\mathbf{s}_{i+1}$，可以计算：

$$
\operatorname{sim}(i,i+1)
=
\frac{\mathbf{s}_i \cdot \mathbf{s}_{i+1}}
{\lVert\mathbf{s}_i\rVert\,\lVert\mathbf{s}_{i+1}\rVert}
$$

若相似度低于阈值，或低于整篇相似度分布的某个分位点，就认为主题可能发生了切换。

### 语义分块的隐含成本

- 需要先调用 embedding，摄取速度和费用上升；
- 阈值受领域、语言和文档风格影响；
- 同一文档修改一点点，边界可能整体漂移，增量更新更复杂；
- 语义相似并不等于规则适用范围相同。

它适合主题段落明显变化、没有可靠标题的长文；不应把阈值当成跨所有语料的常数。

## 策略四：结构感知分块

政策、技术文档、代码和表格通常有比“句子相似度”更可靠的结构：

| 文档类型 | 优先保留的结构 | 常见做法 |
|---|---|---|
| 政策/手册 | 标题路径、适用对象、例外条款、生效时间 | 标题树 + 段落组装 |
| 表格 | 表头、行标题、单位、脚注 | 每行附表头，必要时整表保留 |
| FAQ | 问题与回答成对 | 不拆开 Q/A |
| 代码 | 文件、类、函数、注释、import | 按 symbol 切，并保留文件路径 |
| 日志 | 时间、request id、stack trace | 按事件或 trace 聚合 |
| PDF | 页码、区域、图表标题 | 文本块与页面位置双存 |

### 表格为什么不能只转成一串文本

原表：

| 城市 | 普通员工 | 实习生 | 币种 |
|---|---:|---:|---|
| 东京 | 180 | 120 | USD |

如果只写成“东京 180 120 USD”，模型可能不知道哪个数字对应哪个人群。更安全的 chunk 文本可以是：

~~~text
表：海外住宿上限
列：城市=东京；普通员工=180；实习生=120；币种=USD
脚注：自 2026-06-01 生效
~~~

同时保留原表页码和行列坐标，回答时可以引用整行。

## Chunk 大小没有通用答案

“每块 512 token”只是起点，不是定律。可以用三个问题决定大小：

1. 一个候选是否能独立回答一个最小问题？
2. 如果不能，缺的是邻近句、父章节还是全局表格？
3. 候选数量和上下文预算是否允许先取大一点再缩小？

经验上：

- **事实型问答：**较小 chunk 提高定位和引用精度；
- **规则/流程：**需要把前置条件、步骤和例外放在同一父级；
- **长篇解释：**可小块召回、大块回取；
- **代码：**按函数/类比固定 token 更自然；
- **表格：**宁可保留完整表头和脚注，也不要追求最小字符数。

真正应优化的是验证集上的 retrieval recall、context precision 和答案正确率，而不是某个流行数字。

## Parent-Child、Small-to-Big 与 Sentence-Window

这些模式解决同一个矛盾：**小单元更容易命中，大单元更容易理解。**

### Parent-Child

- **Child：**小 chunk，用于 embedding/BM25 召回；
- **Parent：**包含标题、适用范围和邻近规则的较大段落；
- 命中 child 后，回取 parent 给模型。

例如只用“东京 180 美元”作为 child，命中后回取“海外住宿 → 普通员工 → 生效日期”的 parent。

### Small-to-Big

先取小范围证据，再根据需要逐步扩展到邻居、父章节或整张表。它比每次都返回大段文本节省上下文，但需要一个明确的扩展规则，不能让模型无限扩大。

### Sentence-Window

以单句为索引单元，命中后取回前后若干句。它适合“答案在一句，适用条件在相邻句”的文档；窗口过大则会把多个规则混在一起。

这些模式不是三种互斥产品，而是**索引单元与展示单元分离**的设计。详细的上下文打包和去重见 [[rag/06-context-assembly-and-advanced-retrievers|上下文组装与高级检索器]]。

## Metadata 不是附属标签，而是检索逻辑的一部分

推荐把 metadata 分成四类：

| 类别 | 示例 | 作用 |
|---|---|---|
| 身份 | document_id、chunk_id、source_uri | 回查和去重 |
| 时间 | version、effective_from、effective_until、observed_at | 版本和新鲜度过滤 |
| 范围 | region、audience、product、language、modality | 缩小搜索空间 |
| 安全 | tenant、acl、sensitivity、retention | 授权和合规 |

一个可复用的 schema：

~~~yaml
document_id: policy-travel-2026
chunk_id: policy-travel-2026:v5:tokyo-hotel:03
version: v5
source_uri: hr://policies/travel/2026
heading_path: [海外差旅, 住宿, 亚洲地区]
language: zh
region: APAC
audience: employee
effective_from: 2026-06-01
effective_until: null
observed_at: 2026-06-02T09:30:00Z
supersedes: v4
acl:
  groups: [all-employees]
provenance:
  page: 7
  char_start: 18240
  char_end: 18412
~~~

### 版本字段要区分什么

- **version：**事实源明确给出的版本；
- **effective_from/until：**规则对业务世界何时有效；
- **observed_at：**摄取系统何时看到这份内容；
- **supersedes：**新版本取代哪份旧版本；
- **validity：**索引记录本身是否仍可被返回。

不要只用 updated_at 一个字段解决所有时间问题。文档刚上传但还未生效，或规则已生效但索引晚一天刷新，都会造成不同判断。

## 过滤顺序与安全边界

理想顺序是：

1. 解析用户身份和允许的 tenant/ACL；
2. 过滤掉未发布、过期、无权或不匹配范围的 chunk；
3. 在剩余集合中做 BM25/dense 相似度；
4. 召回、重排、组装和引用。

如果底层向量库无法做预过滤，至少要在返回模型前做强制后过滤；但要意识到后过滤会让 top-k 候选可能全部被删掉，导致隐性低召回。更好的做法是让索引支持与业务过滤条件一致的 payload/metadata 索引。

## 如何验证分块是否合理

不要只肉眼看几个 chunk。建立小型“问题 → 证据 span”数据集：

~~~yaml
question: 东京每日住宿上限是多少？
gold_document: policy-travel-2026
gold_span: page 7, row 东京
required_conditions:
  - audience=employee
  - effective_date<=2026-07-22
must_not_use:
  - superseded=v4
~~~

对每种分块策略比较：

- gold span 是否在 top-k 候选中；
- 候选是否包含必要的适用条件；
- 同一文档重复 chunk 的比例；
- 平均 chunk token 数和 P95（第 95 百分位，即 95% 的 chunk 不超过该长度）；
- 生成答案是否引用了正确页码和版本。

如果 chunk 能命中数字，却经常漏掉“实习生/普通员工”的条件，说明边界需要调整，而不是盲目增大 top-k。

## 最小摄取伪代码

~~~python
def ingest(document):
    tree = parse_preserving_structure(document.bytes)
    normalized = normalize_without_changing_meaning(tree)
    sections = split_by_heading_and_semantics(normalized)

    records = []
    for section in sections:
        metadata = build_metadata(document, section)
        for chunk in make_chunks(section, metadata):
            assert chunk.text
            assert chunk.provenance
            assert chunk.version == document.version
            records.append(chunk)

    write_lexical_index(records)
    write_vector_index(embed_many([r.text for r in records]), records)
    return records
~~~

这里的 assert 代表上线前应有的契约检查：没有来源、版本或 ACL 的 chunk 不应进入生产索引。

> [!success] 读者自测
> 对“东京 180 美元、普通员工、2026-06-01 生效”这条规则，为什么一个只包含数字的 child 可能比整章更容易召回，但又不能直接作为最终上下文？请用 parent-child 的数据流解释。

下一篇会把 chunk 送进两种完全不同的空间：一个是词项到文档的倒排结构，一个是向量近邻结构。先看 [[rag/03-embeddings-vector-search|Embedding、向量相似度与 ANN]]。
