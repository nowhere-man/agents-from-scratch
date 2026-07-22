---
title: Retrieval Engineering
aliases:
  - 检索工程
  - RAG Engineering
tags:
  - context-engineering
  - retrieval
  - rag
status: active
created: 2026-07-18
last_reviewed: 2026-07-23
sources:
  - "[[context-engineering/99-provider-guidance-and-sources]]"
  - https://arxiv.org/abs/2005.11401
---

# Retrieval Engineering：把“可能相关”变成“可引用证据”

> [!abstract] 本篇学习终点
> 当 SSO Agent 缺少运行手册或历史 incident 时，设计一条带权限、版本、缺口和引用的检索管线，并能分别判断是分块、召回、排序、选择还是生成阶段出了问题。

## 为什么“搜到了文档”仍然不够

Agent 已从当前仓库看到 token 校验代码，但不知道组织规定的 mobile audience。它需要从外部知识集合找到：

- 当前有效的 SSO 运行手册；
- 适用于 mobile client 的章节；
- 最近 incident 中的配置变更；
- 与当前部署版本相关的说明。

一个向量搜索可能返回：

1. v4 运行手册的 audience 章节；
2. v1 运行手册的完整页面；
3. 一篇提到“audience”的博客；
4. 2025 年另一项目的 incident；
5. v4 目录但没有正文 span。

候选与问题相似，不代表它有权、最新、完整或真正支持结论。Retrieval Engineering 的完成条件是：==在权限和预算内召回足以支撑当前判断的证据，保留来源、冲突和缺失，并让生成结果可以回查。==

RAG（Retrieval-Augmented Generation，检索增强生成）是“先从外部集合取得候选材料，再把选中的材料交给生成模型”的组合方式。RAG 不是一个固定产品，也不意味着检索结果天然可信。

## Retrieval 在 Context Pipeline 中处于哪一段

```mermaid
flowchart LR
    A["任务与 Evidence Requirement"] --> B["权限与 metadata 硬过滤"]
    B --> C["候选召回"]
    C --> D["融合、去重"]
    D --> E["Rerank"]
    E --> F["Context Selection"]
    F --> G["Context Assembly"]
    G --> H["带引用的生成"]
    H --> I["分别评估 Retrieval 与答案"]
```

Retrieval 的输出是候选集合和 gaps，不是最终答案。[[context-engineering/04-context-selection|Context Selection]] 还会把 memory、conversation、tool 和 workspace 候选放在一起比较。

## 先把资料准备成可回查的索引

### Chunk 是为了匹配查询，不是为了切得越小越好

Chunk（分块）是索引和召回时使用的一段检索单元，不一定等于原文的一整页或完整章节。同一份 SSO 文档可以有不同分块策略：

| 策略 | 适合什么 | 主要风险 |
|---|---|---|
| 固定长度 | 结构弱、快速 baseline | 切断规则、表格和例外 |
| 递归结构 | Markdown、HTML（网页标记语言）、章节文档 | 标题不总是完整查询单元 |
| 语义分块 | 主题变化明显的长文 | 边界不稳定、索引成本高 |
| Parent–Child | 小块召回、父章节阅读 | 索引与回查逻辑更复杂 |
| Sentence Window | 局部事实需要邻近语境 | 可能丢全局适用范围 |

如果只把“mobile audience 应为 api-v2”切成孤立句子，模型可能看不到它只适用于 v4 和 mobile client。每个 chunk 至少应保留 document ID、标题路径、版本、时间、权限和可回查 span。

### Metadata 先于相似度

Metadata（元数据）是描述文档身份、版本、权限和范围的字段，而不是文档正文。适合确定性过滤的字段包括：

- tenant、project、owner；
- document type、language、domain；
- created、updated、valid time；
- version、status、superseded by；
- sensitivity、access policy；
- modality、time range、entity。

权限和版本过滤必须发生在相似度排序之前。向量距离不能抵消越权或过期。

索引是原始文档的派生视图，不是新的 Source of Truth。文档更新、撤销权限或删除时，对应 chunk、embedding、关键词索引和 cache 都要刷新或失效；否则检索会稳定地返回已经不存在的旧知识。

### 表格、代码和多模态文档要保留结构

SSO 规则可能出现在配置表或代码块中。索引时应保留列名、标题路径、代码语言、页码、图片区域或时间段，否则召回的文本看似相关，却失去字段含义。

## Query 处理：改变表述不能改变意图

Evidence Requirement 是“比较 mobile 的 expected 与 actual audience”。系统可以采用不同查询策略：

### 原始查询

保留用户原话，最不容易改变意图，适合实体和限定条件已经明确的任务。

### Query Rewriting

补齐当前 task 已确认的实体、时间和环境：

```yaml
original: audience 为什么错误
rewritten:
  - service: auth-api
  - client: mobile
  - environment: staging-apac
  - question: expected audience 与 actual audience 的差异
```

重写必须能回到原始查询，不能把“排查”改成“确认某个假设”。

### Multi-query

用不同措辞召回“expected audience”“mobile client configuration”“invalid audience”。它可以覆盖词汇差异，但会增加重复和合并成本。

### Decomposition

把复杂问题拆成独立证据需求：

1. 当前规则是什么？
2. 失败请求实际发送了什么？
3. 哪个部署版本引入差异？

每个子查询都需要自己的 source、版本和 gap。

### HyDE

HyDE（Hypothetical Document Embeddings，假设文档向量）先让模型写一段“可能回答问题的文档”，再用这段假设文本的 embedding 去召回真实文档。它可能弥合用户问题与文档措辞的差异，但假设文本是搜索探针，不是证据；如果把其中编造的 audience 值直接带进答案，就把召回辅助误当成事实来源。

## Lexical、Dense、Hybrid 和 Rerank 各修复什么

### Lexical / BM25

Lexical retrieval（词法检索）按字词是否精确出现来匹配。BM25 是一种同时考虑词频、词项稀有度和文档长度的词法评分方法，擅长：

- audience 值；
- request ID；
- 版本号；
- 代码 symbol；
- 精确错误码。

它的常见简化形式是：

$$
\operatorname{BM25}(D, Q)
=
\sum_{q \in Q}
\operatorname{IDF}(q)
\cdot
\frac{f(q,D)(k_1+1)}
{f(q,D)+k_1\left(1-b+b\frac{|D|}{\operatorname{avgdl}}\right)}
$$

在当前场景中：

- $Q$ 是查询，例如 `mobile invalid audience api-v2`；
- $D$ 是一个待排序的运行手册 chunk；
- $f(q,D)$ 是查询词 $q$ 在 chunk 中出现的次数；
- $\operatorname{IDF}(q)$ 是 Inverse Document Frequency（逆文档频率），表示该词在整个索引中有多稀有，越少见越能区分文档；
- $|D|$ 与 $\operatorname{avgdl}$ 分别是当前 chunk 长度和平均 chunk 长度；
- $k_1$ 控制词频增加多久后趋于饱和，$b$ 控制文档长度归一化强度。

计算时，系统先为 `audience`、`api-v2` 等每个查询词算一项贡献，再相加成 $D$ 的分数。精确出现的 `api-v2` 和错误码会得到优势；同一个词重复几十次仍会加分，但因为分式趋于饱和，不会无限增长；过长 chunk 还会被长度项校正。$k_1$ 与 $b$ 是需要用真实检索集调优的参数，不是固定真理。

BM25 能抓住精确字符，却不知道“移动端身份校验失败”和“mobile SSO mismatch”语义相近，所以后面才会引入 Dense Retrieval。

### Dense Retrieval

把文本映射成 embedding（向量表示），让语义相近但用词不同的内容在向量空间中靠近。它适合“移动端认证配置不一致”与“mobile SSO audience mismatch”这类表述差异，但可能忽略精确 ID 和数字。

实现时，embedding model 分别把 query 与 document 编码成向量，再用点积或余弦相似度比较。余弦相似度的常见形式是：

$$
\cos(\mathbf{q}, \mathbf{d})
=
\frac{\mathbf{q}\cdot\mathbf{d}}
{\lVert\mathbf{q}\rVert\,\lVert\mathbf{d}\rVert}
$$

$\mathbf{q}$ 与 $\mathbf{d}$ 分别是查询和文档向量；分子衡量两者方向是否一致，分母消除向量长度的影响。分数高只表示 embedding 空间中更接近，不证明文档最新、有权或真正支持结论。

### Hybrid Search

先合并 lexical 和 dense 的候选，再用稳定规则去重。它减少单一表示的盲点，但增加融合参数和评估维度。

融合可以对两类分数归一化后加权，也可以做 rank fusion（只根据候选在各列表中的名次合并排名）。BM25 与向量相似度的原始数值不在同一尺度，不能直接相加后假设有统一含义。

### Reranker

对较小候选集进行更细粒度的 query-document 判断。它可以重新排序已召回的候选，却不能修复：

- 召回阶段根本没找到 v4 文档；
- 权限过滤错误；
- metadata 版本不匹配；
- 查询意图已经被 rewrite 改变。

第一种情况也叫 zero recall：正确证据根本没有进入候选集合。Reranker 的输入是 query 与一小组候选，输出是新的相关性顺序；它通常比第一阶段召回更慢，因此放在候选已经缩小之后。

不要把“加了 reranker”写成检索质量已经保证。

## 沿主线产出 Evidence Packet

检索结果应把命中与缺口一起返回：

```yaml
retrieval_result:
  query_id: q-sso-audience-42
  original_query: 比较 mobile SSO 的 expected 和 actual audience
  filters:
    project: auth-service
    environment: staging-apac
    policy_status: active
  candidates:
    - id: runbook-sso-v4#audience
      score:
        lexical: 0.82
        dense: 0.76
        rerank: 0.94
      version: runbook-v4
      evidence_span: section 3.2
      content: mobile client 应使用 audience api-v2
    - id: incident-20260722#config-change
      score:
        lexical: 0.51
        dense: 0.88
        rerank: 0.79
      version: incident-18
      evidence_span: paragraphs 8-11
      content: deploy-731 更新了 identity mapping
  conflicts:
    - id: runbook-sso-v3#audience
      reason: 内容要求 api-v1，已被 v4 supersede
  gaps:
    - identity_service_runtime_config_version
```

缺失项是检索产物的一部分。它告诉 [[context-engineering/05-context-assembly|Context Assembly]] 当前材料不足，也告诉 Planning 下一步要查什么。生成步骤不能用模型常识把 gap 填成事实。

## 从一次检索到自适应检索循环

固定流程会对每个问题执行一次相同的检索。可是当前 Context 可能已经足够，也可能第一次查询只找到旧文档。自适应检索会先判断证据需求，再根据 gaps、冲突和结果质量决定是否改写 query、切换来源、分解问题或停止。

一些方案把这种控制称为：

- **Self-RAG**：生成模型在生成过程中判断何时检索，并对取得的证据或答案做自我评估；
- **CRAG（Corrective RAG）**：先评估召回结果是否可靠，不足时改写查询、切换来源或触发纠正路径；
- **Agentic RAG**：由 Agent 工作流把检索当成可重复调用的动作，根据计划、工具结果和 gaps 决定下一步。

这些方案修改的是 Retrieval 的控制循环，而不是推翻基础管线。无论由模型、独立评估器还是程序规则作判断，都不能绕过权限、版本、Evidence Packet 和引用验证。

自适应循环会增加调用、延迟和反复搜索同一假设的风险，因此需要 attempt budget、查询历史和停止条件，并与 [[context-engineering/14-planning-context|Planning Context]] 配合。

## 长上下文还是 RAG

选择不是“RAG 永远更好”或“窗口越大越好”：

| 条件 | 倾向一次提供较完整材料 | 倾向 Retrieval |
|---|---|---|
| 数据规模 | 单个或少量可控文档 | 大型、持续增长集合 |
| 更新频率 | 低，调用时可提供完整版本 | 高频，需要按时间和版本查询 |
| 任务 | 需要跨全文结构理解 | 只需局部事实或候选证据 |
| 权限 | 整份材料同一权限 | 文档或字段级权限复杂 |
| 延迟与成本 | 可接受长 prefill | 需要缩短输入 |
| 主要风险 | 位置退化、噪声 | 漏召回、排序错误 |

实际系统常用混合方式：先用 retrieval 缩小范围，再向模型提供少量完整章节或连续时间段。选择依据应来自真实任务 eval。

## Semantic Cache 与 Prompt Cache 不同

Semantic Cache 根据查询或任务表示的相似度复用历史候选、排序结果或答案；Prompt Cache 复用相同 token 前缀的计算。

对 SSO 任务，安全 key 至少要考虑：

- tenant、用户和项目权限；
- environment 与数据版本；
- 查询时间范围；
- 目标模型与输出 schema；
- 当前运行手册版本；
- 原始 Evidence Requirement。

风险随缓存层次变化：

- 缓存可重新验证的候选，风险相对低；
- 缓存 rerank 结果，需要检查文档版本；
- 直接复用最终答案，最难发现权限、时效和上下文差异。

高风险事实不应只因语义相似就跳过重新验证。监控 false hit、staleness、权限泄漏和质量收益。

## 多模态 Retrieval 怎样保留关系

对视频或扫描文档，索引可以组合：

- 文本 embedding：字幕、ASR、OCR；
- 图像 embedding：关键帧、页面或局部区域；
- 时间索引：片段、说话区间、事件边界；
- 结构 metadata：人物、场景、页面和对象。

返回结果必须保留 modality、time range、frame/page ID 和原始媒体引用。[[context-engineering/04-context-selection|Selection]] 再决定哪些信号进入最终 packet，并用同一 segment 或 entity 对齐。

## Retrieval 与生成必须分别评估

### Retrieval 层

- Recall@k、Precision@k、MRR、nDCG；其中 MRR 关注第一个正确结果排得多早，nDCG 同时考虑多个结果的相关性和排序位置；
- 权限过滤正确率；
- 版本和新鲜度错误率；
- 关键 evidence span recall；
- 来源覆盖和重复率；
- gap 识别准确率。

### 生成层

- Faithfulness / groundedness；
- 引用准确率和覆盖；
- Context precision / context recall；
- 材料不足时的 missing-context 或拒答准确率；
- 端到端质量、延迟、token 和成本。

最终答案正确不等于 retrieval 正确。模型可能凭参数知识猜中，也可能引用了并未支持结论的文档。必须分别检查候选、Selected 结果和最终 claim。

## 用三个问题检查本篇

1. 为什么 reranker 无法修复 zero recall？
2. Query rewrite 怎样保留原始意图，又避免把“排查”改成“证明某个假设”？
3. 检索没有找到身份服务运行时版本时，为什么 gap 比一个猜测值更有用？

下一篇处理检索无法替代的实时观察和外部动作：模型需要查询当前状态、运行测试或请求批准时，Tool Context 怎样工作。见 [[context-engineering/13-tool-context|Tool Context]]。
