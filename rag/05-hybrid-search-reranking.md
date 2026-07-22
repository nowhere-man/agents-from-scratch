---
title: Hybrid Search、Reranker 与查询改写
aliases:
  - 混合检索
  - RAG 提质路径
tags:
  - rag
  - hybrid-search
  - reranker
  - query-rewriting
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://www.sbert.net/examples/applications/cross-encoder/README.html
  - https://docs.cohere.com/docs/rerank
  - https://huggingface.co/BAAI/bge-reranker-v2-m3
  - https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual
  - https://arxiv.org/abs/2212.10496
---

# Hybrid Search、Reranker 与查询改写

> [!abstract] 本章只解决一个问题
> 当 BM25 找得到版本号却理解不了同义表达、向量检索理解了语义却漏掉精确数字时，怎样组合两者，并在有限延迟内把真正有用的证据排到前面？

上一章的 BM25 和 [[rag/03-embeddings-vector-search|向量检索]]各自解决不同盲点。本章把它们接成一个两阶段系统：

> **扩大候选覆盖 → 合并不同信号 → 精细重排 → 再做上下文选择。**

## 为什么不能直接把两个分数相加

BM25 分数可能是 0 到十几，取决于 query 长度、词频和语料；余弦相似度常在 -1 到 1 或 0 到 1 之间。它们的原始数值不在同一尺度：

~~~text
文档 A: BM25=8.1, cosine=0.62
文档 B: BM25=3.4, cosine=0.86
~~~

直接相加会让某一通道因数值范围大而支配结果，权重也难以解释。混合检索至少要做以下之一：

1. 对每个通道做分数归一化后加权；
2. 只使用各通道的排名，做 rank fusion；
3. 合并候选后交给独立的 reranker。

## 一条标准的两阶段管线

~~~mermaid
flowchart LR
    Q["原始 Query"] --> QP["解析硬条件 / 改写"]
    QP --> L["BM25 top-k"]
    QP --> D["Dense top-k"]
    L --> U["去重、保留 provenance"]
    D --> U
    U --> F["分数融合或 RRF"]
    F --> C["候选集 top-N"]
    C --> R["Cross-Encoder Reranker"]
    R --> S["metadata / coverage / diversity 选择"]
    S --> P["Context Packet"]
~~~

第一阶段的目标是 **recall**：正确 chunk 至少进入候选。第二阶段的目标是 **precision**：在候选里把最能支持问题的 chunk 排到前面。Reranker 无法修复 zero recall，因此不能把 top-k 召回做得过小。

## 分数融合方法

### 1. 归一化后加权

先把每个通道的分数映射到可比区间，例如：

$$
\hat{s}_m(d)
=
\frac{s_m(d)-\min(s_m)}
{\max(s_m)-\min(s_m)+\epsilon}
$$

再计算：

$$
s_{\text{hybrid}}(d)
=
\alpha\hat{s}_{\text{bm25}}(d)
+(1-\alpha)\hat{s}_{\text{dense}}(d)
$$

$\alpha$ 越大，越偏向精确词项；越小，越偏向语义。问题是 min/max 会受当前候选集中的异常值影响，跨 query 不稳定。

### 2. Reciprocal Rank Fusion（RRF）

RRF 不比较原始分数，只看排名：

$$
\operatorname{RRF}(d)
=
\sum_{m\in M}
\frac{1}{k+\operatorname{rank}_m(d)}
$$

- $M$ 是检索通道集合；
- $\operatorname{rank}_m(d)$ 是文档在通道 m 中的名次；
- $k$ 是防止第一名权重过大的平滑常数，常见起点是 60，但仍需评测。

例如一个文档在 BM25 排名 2、dense 排名 8，另一个文档只在某一通道排名 1；RRF 会奖励“多个通道都认为相关”的文档。它对分数尺度更稳，但无法表达“某个通道在本业务更重要”的细粒度权重。

### 3. 学习排序

如果有足够标注数据，可以训练一个 learning-to-rank 模型，把 BM25、dense、字段、时间和业务特征作为输入。它的收益依赖标注质量和分布稳定性，初期通常先用 RRF 或简单加权建立可解释 baseline。

## Reranker 为什么经常带来高 ROI

在正确证据已经进入候选、只是前几名排序不准的前提下，reranker 往往是 RAG 质量/工程投入比很高的一步；如果存在 zero recall、权限错误或索引过期，它就不是优先修复项。

### Bi-encoder 与 Cross-encoder 的差异

Embedding 检索把 query 和 document 分别编码，速度快但两者之间的词级交互已经被压缩。**Cross-encoder**把 query 与一个候选拼在同一输入里，让 Transformer 的 attention 直接比较：

~~~text
[CLS] query [SEP] candidate chunk [SEP]
        ↓
相关性分数
~~~

它可以注意到：

- 问的是“普通员工”，候选却只讲实习生；
- query 要“生效日期”，候选只有历史说明；
- “不适用”改变了规则方向；
- 数字和单位是否对应同一城市。

代价是每个候选都要一次联合编码，复杂度近似与候选数和文本长度相乘。因此常见架构是先取 30–200 个候选，再对其中一小批做 rerank，而不是对整个语料做 cross-encoder。

### 常见选择

| 方案 | 形态 | 适合 | 主要权衡 |
|---|---|---|---|
| Cohere Rerank | 托管 API | 想快速上线、接受外部服务 | 延迟、费用、数据出境和供应商依赖 |
| BGE Reranker（如 bge-reranker-v2-m3） | 本地/自托管 cross-encoder | 多语言、希望控制数据和成本 | GPU/CPU 资源、模型服务运维 |
| Jina Reranker（如 jina-reranker-v2-base-multilingual） | 托管或本地模型 | 多语言和较长文本 | 版本、许可、上下文长度需核对 |

模型名会更新；选型时看真实 query-document 对上的 nDCG（衡量分级相关结果是否排在前面的指标）、P95 延迟（95% 请求不超过的延迟）、最大输入长度和许可，不要只看排行榜。nDCG 的完整公式见 [[rag/09-evaluation-production#nDCG|评测章节]]。

### Reranker 的边界

它只能重新排序已经召回的候选。以下问题不属于 reranker 能解决的范围：

- 正确 v5 文档因为过滤或分块错误根本没进候选；
- 用户无权访问的草案仍混在候选里；
- query rewrite 把“最新”改成了“历史”；
- Source of Truth 已删除，索引未失效。

## Query Rewriting：改变表述，不改变问题

用户问题常常短、含糊或口语化：

~~~text
原始：东京住一晚能报多少？
~~~

可以改写为一个带已知约束的检索 query：

~~~yaml
original: 东京住一晚能报多少？
rewritten:
  - 东京 每日 住宿 上限 币种
  - overseas travel lodging cap Tokyo employee
constraints:
  audience: employee
  as_of: 2026-07-22
  region: APAC
~~~

程序应保存 original query、rewrite 结果和触发原因，方便排错。改写器不能凭空填入“普通员工”或“2026”这样的未确认事实；如果信息缺失，应把它作为待澄清条件，而不是假设。

## Multi-Query：从多个措辞覆盖词汇差异

Multi-Query 让模型为同一意图生成若干搜索表达：

~~~text
1. 东京 每日 住宿 上限 普通员工
2. Tokyo hotel allowance employee
3. 海外差旅 东京 住宿额度 180 USD
~~~

每个 query 独立召回，再去重和融合。它能覆盖术语差异，但会：

- 增加 embedding/BM25 查询次数；
- 召回更多重复或相互矛盾的文档；
- 让错误改写被放大。

应保留每个候选来自哪个 query，不能把“被多次召回”误当成独立证据。

## RAG-Fusion：用排名融合多个查询

RAG-Fusion 通常把 Multi-Query 与 RRF 结合：

1. 生成多个查询；
2. 对每个查询独立检索；
3. 用 RRF 汇总排名；
4. 再做 rerank 和上下文选择。

它的增益来自“不同问法都指向同一证据”，不是因为模型生成的假设自动变成事实。查询数量应受延迟和成本预算限制，常见做法是先用 2–5 个高差异 query 做实验。

## HyDE：用假设答案作搜索探针

HyDE（Hypothetical Document Embeddings）先让模型写一段可能相关的“假设文档”，再对这段假设文本做 embedding，用它去召回真实文档：

~~~mermaid
flowchart LR
    Q["用户问题"] --> H["生成假设文档"]
    H --> E["假设文档 embedding"]
    E --> V["向量召回真实文档"]
    V --> C["真实证据"]
~~~

它可能弥合“用户问题很口语、资料写得很正式”的表达差距。但假设文档里可能有幻觉：

- 它只是查询探针，不是证据；
- 其中出现的金额、版本和人群不能直接进入答案；
- 若问题本来含有精确 ID，HyDE 反而可能把它改写得过于模糊。

适合在 dense retrieval 词汇鸿沟明显、又有足够生成预算的场景；应与原始 query 并行保留，而不是完全替换。

## Query Decomposition：把复合问题拆成证据角色

“最新东京住宿上限是多少，并说明是否需要审批？”其实包含两个证据需求：

1. 东京、普通员工的金额和币种；
2. 超过某个天数时的审批条件。

分解后分别检索，再在组装阶段按问题结构合并。每个子问题都应有自己的 query_id、候选和 gap，防止一个子问题命中后掩盖另一个子问题缺证。

## 一个可解释的混合检索伪代码

~~~python
def hybrid_retrieve(intent, filters):
    lexical = bm25_search(
        query=intent.original_text,
        filters=filters,
        top_k=50,
    )
    dense = vector_search(
        vector=embed(intent.original_text),
        filters=filters,
        top_k=50,
    )

    merged = union_by_chunk_id(lexical, dense)
    for item in merged:
        item.fused_score = rrf_score(item.ranks, k=60)

    candidates = sorted(
        merged,
        key=lambda item: item.fused_score,
        reverse=True,
    )[:40]
    return rerank(intent.original_text, candidates)[:10]
~~~

生产实现还要保留 BM25/dense 原始分数、排名、过滤条件、模型版本和时间戳。否则当结果改变时，只能看到最终列表，无法知道是哪一通道出了问题。

## 先做哪一个升级

面对一个质量不高的 baseline，建议按以下顺序排查：

1. **先修索引和 chunk：**正确证据不在候选，所有后续优化都无效；
2. **加 metadata/ACL 过滤：**避免旧版本和越权内容；
3. **加 BM25 + dense：**覆盖精确和语义两类表达；
4. **加 reranker：**候选已有覆盖但前几名不准；
5. **再试 query rewrite/Multi-Query/HyDE：**确认查询表述是瓶颈；
6. **最后考虑 Agentic 多轮：**只有问题确实需要分解、交叉验证或动态换来源时才值得。

> [!warning] 不要把“更复杂”当成“更准确”
> Multi-Query、HyDE 和 rerank 每增加一层，就增加延迟、费用、日志和新的失败面。用固定评测集做逐层 ablation（一次只开一个变量），才能知道收益来自哪里。

下一篇处理一个常见矛盾：最容易召回的小 chunk 往往不是最适合交给模型的上下文。见 [[rag/06-context-assembly-and-advanced-retrievers|上下文组装与高级检索器]]。
