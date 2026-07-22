---
title: Embedding、向量相似度与 ANN
aliases:
  - Dense Retrieval
  - 向量检索
tags:
  - rag
  - embedding
  - vector-search
  - ann
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://www.sbert.net/
  - https://github.com/pgvector/pgvector
  - https://qdrant.tech/documentation/
  - https://github.com/milvus-io/milvus
  - https://docs.weaviate.io/weaviate
  - https://docs.lancedb.com/
  - https://docs.trychroma.com/docs/overview/introduction
---

# Embedding、向量相似度与 ANN

> [!abstract] 本章只解决一个问题
> “东京住宿上限”和“Tokyo hotel allowance”没有完全相同的词，系统为什么仍可能把它们找出来？读完后，你应该能解释 embedding 如何表示语义、相似度怎样计算、ANN 为什么需要近似，以及六类主流向量库分别解决什么工程问题。

上一篇把政策切成了 chunk。本篇先把每个 chunk 变成向量，再研究如何在数百万个向量中找到“附近”的候选。下一篇会说明：向量擅长语义，却不擅长错误码、版本号和精确数字，所以不能独立承担所有检索。

## Embedding 是“可比较的表示”，不是知识答案

**Embedding** 是一个把输入映射为固定长度数字向量的模型：

$$
f_\theta(\text{text}) = \mathbf{v}\in\mathbb{R}^{d}
$$

例如，一个句子可能被表示成 768 维向量。每一维通常没有可直接命名的“主题”；有意义的是不同文本向量之间的相对位置。

理想情况下：

- “东京每日住宿上限是多少？”和“Tokyo daily lodging cap”距离较近；
- “东京住宿报销”与“东京机票报销”有一定接近，但仍可区分；
- 无关的“办公设备采购”距离较远。

这不是把文字翻译成可读的摘要，而是训练出一个适合比较的坐标系。向量相近只说明模型认为它们在训练目标下相似，**不证明文档最新、用户有权限、数字正确或能支持答案**。

## Bi-encoder 如何为检索服务

常见的 dense retrieval 使用双编码器（bi-encoder）：

1. 用同一个或成对的 encoder 编码 query；
2. 用 encoder 编码每个 document/chunk；
3. 先离线保存 document 向量；
4. 在线只编码 query，再做近邻搜索。

~~~mermaid
flowchart LR
    D["chunk 文本"] --> ED["Document Encoder"] --> VD["文档向量"]
    Q["用户 Query"] --> EQ["Query Encoder"] --> VQ["查询向量"]
    VQ --> S["相似度 / ANN"]
    VD --> S
    S --> C["top-k 候选"]
~~~

这样做的关键优势是可扩展：文档向量可以提前计算，在线不用把每份文档重新送进模型。代价是 query 和 document 被分别编码，细粒度的词对词交互被压缩掉；reranker 会在第二阶段把两者放回同一个模型中细看。

### Embedding 模型在训练什么

一种直观训练目标是让正例 query-document 对更近，让负例更远。以余弦相似度为例，可用对比损失：

损失函数是训练时衡量“当前参数有多不符合目标”的数值；优化器会调整参数，让这个数变小。下面的式子把一个相关文档与若干不相关文档放在同一场比较中。

$$
\mathcal{L}
=
-\log
\frac{\exp(\operatorname{sim}(\mathbf{q},\mathbf{d}^{+})/\tau)}
{\exp(\operatorname{sim}(\mathbf{q},\mathbf{d}^{+})/\tau)
 + \sum_j\exp(\operatorname{sim}(\mathbf{q},\mathbf{d}^{-}_j)/\tau)}
$$

- $\mathbf{q}$ 是查询向量；
- $\mathbf{d}^{+}$ 是相关文档；
- $\mathbf{d}^{-}_j$ 是不相关或较难的负例；
- $\tau$ 是温度参数，控制分布尖锐程度。

训练数据、负例质量和领域差异会改变模型的“相似”含义。面向通用网页训练的模型，未必最擅长公司内部缩写、法律条款或中英混合代码。

## 三种常用距离

### 余弦相似度

$$
\operatorname{cos}(\mathbf{q},\mathbf{d})
=
\frac{\mathbf{q}\cdot\mathbf{d}}
{\lVert\mathbf{q}\rVert\,\lVert\mathbf{d}\rVert}
$$

它只比较方向，忽略向量长度。若已把向量归一化到长度 1，余弦相似度等于点积。

### 点积

$$
\operatorname{dot}(\mathbf{q},\mathbf{d})
=
\sum_{i=1}^{d}q_i d_i
$$

点积同时受方向和长度影响。有些模型训练时就以点积为目标，不能随意改成余弦而不重新评测。

### 欧氏距离

$$
\operatorname{L2}(\mathbf{q},\mathbf{d})
=
\sqrt{\sum_{i=1}^{d}(q_i-d_i)^2}
$$

距离越小越相似。对已归一化向量，L2 和余弦在排序上有单调关系；对未归一化向量则不一定。

> [!warning] 指标必须和模型契约一致
> 选择 cosine、dot 或 L2 不是数据库界面的偏好，而是 embedding 模型训练和归一化方式的一部分。更换指标、是否 normalize、是否截断维度，都应重新跑检索评测。

## 从“精确近邻”到 ANN

假设有 N 个文档，每个向量 d 维。最简单的搜索是把 query 与全部向量逐个比较，复杂度近似为 $O(Nd)$。N 小时这很好理解，N 到百万级后延迟和成本会变高。

**ANN（Approximate Nearest Neighbor，近似最近邻）**不保证每次都找到数学上绝对最近的向量，而是用索引结构快速找到足够好的近邻。它用少量 recall 换取速度、内存或存储成本。

### HNSW：用多层图缩小搜索范围

HNSW（Hierarchical Navigable Small World）把向量作为图节点，每个节点连接若干“邻居”；上层图更稀疏，用来快速跳到大致区域，下层图更密，用来精细搜索。

查询大致是：

1. 从最高层入口点开始；
2. 如果某个邻居更接近 query，就移动过去；
3. 到当前层无法明显改善时，下降一层；
4. 在底层维护一组候选，返回最好的 top-k。

关键参数的直觉：

| 参数 | 作用 | 增大后的取舍 |
|---|---|---|
| M | 每个节点允许的邻居数量 | recall/内存/构建时间上升 |
| efConstruction | 构建时考察的候选数量 | 索引质量和构建成本上升 |
| efSearch | 查询时考察的候选数量 | recall 和查询延迟上升 |

HNSW 适合低延迟、内存充足、在线查询频繁的场景；删除和大规模更新需要考虑 tombstone（逻辑删除标记）、重建和图碎片。

### IVF：先分桶，再在少数桶中搜索

IVF（Inverted File）先用聚类得到若干中心，把向量分到最近的桶。查询时只搜索最接近的 nprobe 个桶，而不是全部桶。

- 桶数太少：每个桶很大，速度优势小；
- 桶数太多：边界误差变大，构建和维护复杂；
- nprobe 增大：recall 变好，查询成本上升。

IVF 适合可接受近似、数据量大且需要控制扫描范围的场景。

### PQ：压缩向量

PQ（Product Quantization）把向量分成若干子空间，再用短码表示每个子空间的聚类中心。它能显著减少内存和磁盘，但会引入量化误差。

常见组合是 IVF+PQ：先少量分桶，再用压缩码快速比较。是否值得压缩，取决于内存预算、向量维度和 recall 目标。

## Metadata 过滤与 ANN 的交互

“先过滤再向量搜索”听起来简单，实际取决于索引实现：

- **预过滤：**搜索过程只在符合 tenant、region、version 的候选中走，安全和效率更好；
- **后过滤：**先取 ANN top-k，再删除不符合条件的记录；如果过滤很严格，返回可能不足；
- **分区/租户索引：**把数据按业务范围分开，降低过滤成本，但分区过多会增加运维；
- **混合索引：**向量图和 payload 索引共同参与搜索，需要调参。

ACL（访问控制列表）不是相似度分数。无论底层实现如何，最终返回给模型的集合都必须经过程序化授权检查。

## 六类常见向量库怎样选择

它们都能保存向量，但“最适合”取决于既有系统、规模、过滤、部署和运维能力。表中的 payload 指与向量一起保存、可用于过滤的 metadata 字段。

| 方案 | 核心定位 | 适合的起点 | 需要留意 |
|---|---|---|---|
| **pgvector** | PostgreSQL 扩展，把向量放进关系数据库 | 已经使用 Postgres，需要事务、SQL join 和业务表过滤 | 大规模 ANN、分片和高并发要按实际数据量压测 |
| **Qdrant** | 专注向量和 payload 过滤的服务 | 需要清晰的向量 API、过滤和独立部署 | 事务型业务数据仍可能在别的数据库，需设计一致性 |
| **Milvus** | 面向大规模向量检索的分布式系统 | 数据量大、索引类型和水平扩展要求高 | 运维组件较多，小项目可能显得过重 |
| **Weaviate** | 对象/向量数据库，强调模块和混合检索 | 希望快速组合向量、BM25、过滤和云服务 | 需要理解模块、版本和托管形态的差异 |
| **LanceDB** | 基于 Lance 列式格式的嵌入式/云原生分析取向 | 本地原型、多模态数据、与数据科学工作流结合 | 高并发服务和生态集成要按目标部署形态验证 |
| **Chroma** | 开发者友好的本地/轻量向量存储 | 学习、原型、小规模应用 | 生产级高可用、权限和大规模运维需额外设计 |

一个更稳的决策顺序是：

1. 已有 Postgres 且数据量中等：先评估 pgvector；
2. 需要独立向量服务和丰富 payload 过滤：评估 Qdrant/Weaviate；
3. 规模、吞吐和分布式索引是首要约束：评估 Milvus；
4. 本地实验或 notebook：Chroma/LanceDB 往往更快；
5. 需要混合检索时，确认 BM25、过滤、分数返回和更新语义是否满足要求；
6. 在同一数据集上压测 recall、P95 延迟（95% 请求的延迟不超过该值）、更新延迟和成本，而不是只看功能列表。

产品页面会变化，当前文档入口见 [[rag/99-sources|论文、官方文档与延伸阅读]]。

## 选择 Embedding 模型的检查表

### 代表性模型路线

下面是便于建立方向感的代表性路线，不是固定推荐名单。模型的版本、维度、许可和价格会变化，最终要在自己的 query-document 对上比较：

| 路线 | 代表性选择 | 适合 | 主要取舍 |
|---|---|---|---|
| 托管通用 embedding | OpenAI text-embedding 系列、Cohere Embed、Voyage AI Embeddings | 希望少运维、快速验证 | API 延迟、费用、数据出境和供应商锁定 |
| 开源多语言 | BGE-M3、multilingual-e5、Jina Embeddings | 中英混合、可本地部署 | GPU/CPU、模型服务和版本管理 |
| 代码/领域专用 | 面向 code、法律、金融或企业语料微调的模型 | 专有术语和结构稳定的领域 | 需要领域评测、负例和维护数据 |

选择时不要只看通用排行榜：query 的写法、chunk 长度、语言比例、负例难度和相似度指标都会改变排序。若模型要求 query/passages 前缀或指令模板，索引和在线查询必须严格保持一致。

### 语言与领域

- 中文、英文和中英混合是否都覆盖；
- 专有名词、缩写、代码、数字是否保留区分度；
- query 和 document 是否需要不同指令模板；
- 长 chunk 是否会被截断；
- 许可是否允许商业部署，是否可在本地运行。

### 维度和归一化

维度越高不必然越好。高维向量占更多内存，ANN 构建和传输也更贵；低维或截断可能损失细粒度区分。用同一评测集比较“原始维度、截断维度、量化后”的 recall 和延迟。

### 负例与领域微调

如果“东京住宿”和“东京机票”经常互相召回，可以收集真实误召回作为 hard negative（很像正确答案、但应判为不相关的困难负例）。微调或换模型前，先确认问题确实来自表示空间，而不是 metadata、分块或 query 解析。

## Dense Retrieval 的边界

向量检索容易找到：

- “出差住宿额度”与“travel lodging allowance”；
- “取消订单后的退款规则”与“refund after cancellation”；
- 同一概念的不同语言表达。

它可能不擅长：

- 版本号 v5、错误码 40123、订单号；
- 两个只差一个数字的规则；
- 需要精确字段匹配的表格；
- 文档里出现同义词但适用范围完全不同的段落。

这就是下一篇要讲 BM25 的原因：先理解词项如何通过倒排索引精确命中，再把两种信号合起来。

> [!success] 读者自测
> 如果 query 和文档向量的余弦相似度很高，能否直接证明答案是最新、用户有权限且数字正确？请分别指出“向量表示”“metadata 过滤”“Source of Truth”各自负责什么。

下一篇进入词法检索的底层：[[rag/04-lexical-retrieval-and-bm25|倒排索引与 BM25]]。
