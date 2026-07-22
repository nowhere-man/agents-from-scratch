---
title: RAG 的完整架构与数据契约
aliases:
  - RAG Pipeline
  - RAG 架构
tags:
  - rag
  - retrieval
  - architecture
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://arxiv.org/abs/2005.11401
  - https://docs.ragas.io/
---

# RAG 的完整架构与数据契约

> [!abstract] 本章只解决一个问题
> 一份会更新、带权限的政策文档，怎样从“原始文件”变成可以被检索、排序、引用和审计的证据？

上一章用“东京住宿上限”的问题画出了总图。本章先不急着讨论 BM25 的公式或某个向量数据库，而是把每个阶段的输入、输出和责任边界固定下来。后文的优化都应该能回答：**它修改了哪一层，改善了哪个指标，又增加了什么代价。**

## RAG 是两条相反方向的流水线

离线索引把大量原始资料压缩成可搜索的派生结构；在线问答再从这些结构中取回少量材料。

~~~mermaid
flowchart TB
    subgraph OFF["离线：把资料变成索引"]
      A["Source of Truth<br/>政策原文"] --> B["解析与规范化"]
      B --> C["Document Record"]
      C --> D["Chunk Record + metadata"]
      D --> E["Lexical Index"]
      D --> F["Vector Index"]
    end
    subgraph ON["在线：把问题变成答案"]
      Q["用户 Query"] --> Q0["意图、权限、时间过滤"]
      Q0 --> R["Retriever"]
      R --> X["候选 Evidence"]
      X --> RR["Reranker / Selector"]
      RR --> P["Context Packet"]
      P --> L["LLM Generator"]
      L --> O["Answer + Citation + Gaps"]
    end
    F --> R
    E --> R
    O -. "反馈、失效、评测" .-> OFF
~~~

离线阶段出错，在线阶段再聪明也无法凭空恢复原文。在线阶段出错，索引即使完美也可能因为过滤、排序或组装不当而答错。

## 先定义 Source of Truth

**Source of Truth（事实源）**是拥有文档权威性的地方，例如 HR 文档系统中的已发布政策。索引、摘要、embedding 和缓存都是它们的派生视图，不应反过来成为新的事实源。

以一份政策为例：

- 原文在文档系统里被更新为 v5；
- 索引里仍有 v4 的 chunk；
- 一个语义缓存保存了上次关于“东京住宿”的回答；
- 模型长期记忆里写着“上限是 150 美元”。

只有原文系统能决定 v5 是否已发布、v4 是否失效。RAG 的刷新任务必须把版本变化传播到所有派生视图；回答时也要把版本和有效期作为可检查字段返回。

> [!warning] 不能把“向量库返回了它”当成“它是真的”
> 向量库只证明某个索引记录满足查询条件。它不证明记录没有过期、用户有权查看、正文没有解析损坏，或它足以支持最终结论。

## 最小数据契约：Document、Chunk、Evidence

如果每个阶段只传一段没有身份的字符串，后面无法做版本过滤、引用或删除传播。最小可用结构至少要保留三层对象。

### Document Record：一份原始文档

~~~yaml
document_id: policy-travel-2026
source_uri: hr://policies/travel/2026
title: 海外差旅费用政策
version: v5
status: published
effective_from: 2026-06-01
effective_until: null
tenant: example-corp
acl:
  groups: [all-employees]
checksum: sha256:...
source_updated_at: 2026-06-02T09:30:00Z
~~~

这里的 **version** 是同一事实源的版本标识；**effective_from** 是规则何时开始生效，不等同于文档上传时间。后续需要同时保留 event time（规则生效时间）和 observed time（索引系统观察到更新时间），否则“最新”会被误解为“最后上传”。

这里的 tenant 是“租户”，即系统中彼此隔离的客户或组织空间；ACL（Access Control List，访问控制列表）说明哪些用户或用户组可以读取文档；checksum 是内容校验值，用来判断原文是否变化。

### Chunk Record：用于搜索的派生单元

~~~yaml
chunk_id: policy-travel-2026:v5:tokyo-hotel:03
document_id: policy-travel-2026
version: v5
text: 东京：每日住宿上限为 180 美元；须提供发票。
heading_path: [海外差旅, 住宿, 亚洲地区]
page: 7
char_start: 18240
char_end: 18412
language: zh
region: APAC
audience: employee
modality: text
parent_id: policy-travel-2026:v5:lodging
valid_from: 2026-06-01
valid_until: null
acl:
  groups: [all-employees]
~~~

**Chunk**的 text 用于 BM25、embedding 和 reranker；其余字段用于过滤、解释和回查。一个 chunk 可以同时写入关键词索引和向量索引，但两份索引应共享相同的 chunk_id。

### Evidence：一次查询返回的证据

~~~yaml
evidence_id: ev-8f2
chunk_id: policy-travel-2026:v5:tokyo-hotel:03
query_id: q-2026-07-22-01
retrieval_method: bm25+dense+rerank
rank: 1
score:
  bm25: 4.82
  dense: 0.79
  rerank: 0.94
source_version: v5
evidence_span: page 7, paragraph 2
supports:
  - lodging_limit_tokyo
~~~

Evidence 不是答案。它是“某次查询中，某个 chunk 以什么方式被选中”的带 provenance（来源链）的记录。span 指原文中可精确定位的一段连续范围，例如第 7 页第 2 段。回答引用应指向 evidence 的 source_uri、版本和 span，而不是只显示一个无法回查的相似度分数。

## 离线摄取：每一步都可能改变可检索事实

### 1. 解析

解析器把 PDF、HTML、Markdown、表格、幻灯片或扫描图片转换为带结构的文档。结果不应只是纯文本，还应尽量保留：

- 标题层级、列表和段落顺序；
- 表格的列名、行名和单元格关系；
- 代码块的语言和缩进；
- 页码、坐标、图片区域；
- 文档链接和附件关系。

扫描 PDF 需要 OCR（光学字符识别）；会议录音或视频需要 ASR（自动语音识别）。OCR/ASR 会引入数字、单位和专名错误，因此高风险字段要保留原图/音频位置供复核。

### 2. 规范化与去重

规范化可以统一空白、日期、单位和 Unicode 表示，但不能删除会改变语义的符号。例如把“≤ 180 USD”清洗成“180”会丢掉上限关系；把“2026-06”变成“2026”会丢掉时间粒度。

去重既可以按文档 checksum，也可以按段落 fingerprint。近重复版本不能简单全部删除：若新版本只改了一行，旧版本仍需要保留为历史证据，但必须标记 superseded（被哪个版本取代）。

### 3. 分块和 metadata

分块会在后续 [[rag/02-ingestion-chunking-metadata|文档摄取、分块与 metadata]] 详细展开。这里先固定一个原则：

> 分块不是纯粹的长度操作，而是“为未来查询设计证据边界”。

例如“东京 180 美元”必须和“适用于普通员工、2026-06-01 生效”尽量保持可回查的关系。若因为切块而失去标题和适用范围，召回分数再高也不够安全。

### 4. 写入两种索引

同一个 chunk 通常同时写入：

- **倒排索引：**保存词项到文档列表的映射，支持精确字符、错误码和版本号；
- **向量索引：**保存 embedding 与近邻结构，支持同义表达和跨语言语义。

两种索引的更新必须有相同的 ingestion job id 和版本记录。只更新向量、不更新 BM25，或反过来，都会产生难以解释的结果差异。

## 在线问答：从 Query 到 Context Packet

### 1. 识别问题中的硬条件

“最新”“海外”“东京”“员工”“每日住宿上限”并不是同一种信息：

- “东京”是实体过滤或词法信号；
- “最新”要求按 effective time 和版本排序；
- “员工”是 audience/ACL 条件；
- “上限是多少”决定需要数值和单位；
- “请给出处”决定必须保留 citation。

系统可以让模型做 query rewrite，但硬条件最好先由程序解析和校验。一个自然语言改写若把“最新”删掉，后面的检索再精确也会偏离问题。

### 2. 先过滤，再相似度排序

在允许的租户、权限、语言、状态和时间范围内搜索：

~~~yaml
filters:
  tenant: example-corp
  status: published
  audience: employee
  effective_from_lte: 2026-07-22
  effective_until_gt: 2026-07-22
  region: APAC
~~~

**权限不是一个可被相似度抵消的软分数。** 如果用户无权查看 HR 草案，草案即使和问题最相似，也必须在候选阶段被排除。

### 3. 召回、融合、重排

第一阶段追求 **recall（召回覆盖）**：宁可取回几十个候选，再在后面缩小。BM25 和 dense retrieval 互补；混合方法见 [[rag/05-hybrid-search-reranking|Hybrid Search、Reranker 与查询改写]]。

第二阶段追求 **precision（前几名精度）**：reranker 逐个看 query 与候选的关系，通常比单独的向量距离更细，但更慢。

### 4. 组装上下文

模型不应该收到“搜索结果数组原样拼接”，而应收到有明确分区和引用的 packet：

~~~yaml
context_packet:
  question: 最新海外差旅政策中东京每日住宿上限是多少？
  hard_constraints:
    as_of: 2026-07-22
    audience: employee
    region: APAC
  evidence:
    - evidence_id: ev-8f2
      quote: 东京：每日住宿上限为 180 美元；须提供发票。
      citation: hr://policies/travel/2026#page=7
      version: v5
  gaps: []
  instructions:
    - 只使用 evidence 支持的事实
    - 给出金额、币种、版本和出处
    - 若 evidence 不足，明确说不知道
~~~

上下文组装、窗口预算、冲突和注入边界见 [[rag/06-context-assembly-and-advanced-retrievers|上下文组装与高级检索器]]。

## 失败契约比“尽量回答”更重要

每一层都应能返回可诊断的失败状态：

| 状态 | 含义 | 下一步 |
|---|---|---|
| no_candidates | 过滤后没有候选 | 检查权限、版本、解析和 query |
| zero_recall | 候选存在但没有正确证据 | 扩大召回、改写或切换来源 |
| low_confidence | 候选相似但不能支撑结论 | 触发 CRAG/人工复核 |
| conflict | 两个有效版本或来源冲突 | 按权威性/时间规则解决或显式报告 |
| stale_index | Source of Truth 更新但索引未刷新 | 重建或增量更新索引 |
| insufficient_context | 证据存在但缺少适用范围 | 回取 parent、邻近句或完整表格 |

“没有找到”不是“没有这条政策”。前者是检索观测，后者是关于世界的结论，不能直接互换。

## 最小 baseline 的伪代码

下面的代码故意不绑定某个框架；它展示的是责任边界，而不是可直接上线的安全实现。

~~~python
def answer(question, user):
    intent = parse_question(question)
    filters = build_acl_and_time_filters(intent, user)

    lexical = bm25_search(
        query=intent.original_text,
        filters=filters,
        top_k=30,
    )
    dense = vector_search(
        vector=embed(intent.original_text),
        filters=filters,
        top_k=30,
    )
    candidates = deduplicate_and_fuse(lexical, dense)
    ranked = rerank(intent.original_text, candidates[:50])[:8]
    packet = assemble_context(intent, ranked)

    if packet.gaps or not packet.evidence:
        return abstain_or_request_clarification(packet)
    return generate_with_citations(packet)
~~~

这段 baseline 有意省略了 query rewrite、缓存、重试和 Agent 循环。先让每个中间结果可记录、可复现、可评测，再引入更复杂的自适应策略。

> [!question] 读者自测
> 如果 v5 文档已发布但检索仍返回 v4，问题属于生成模型还是索引生命周期？如果用户无权看 v5 草案，应该在 reranker 之后再过滤，还是在相似度搜索之前做 ACL 过滤？说出理由后再读下一篇。
