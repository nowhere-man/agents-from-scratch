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
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
  - https://arxiv.org/abs/2005.11401
---

# Retrieval Engineering

> [!important] 一句话核心
> Retrieval Engineering 的完成条件不是“搜到若干文档”，而是在权限和预算内召回足以支持当前结论的证据，保留来源与冲突，并让生成结果可以回查。

## Retrieval 在 Context Pipeline 中的位置

```mermaid
flowchart LR
    A["任务与查询"] --> B["权限和 metadata 过滤"]
    B --> C["候选召回"]
    C --> D["融合与去重"]
    D --> E["Rerank"]
    E --> F["Context Selection"]
    F --> G["Context Assembly"]
    G --> H["生成与引用"]
    H --> I["Retrieval / Answer Eval"]
```

Retrieval 负责从外部集合产生候选；[[04-context-selection|Context Selection]] 还会综合 memory、tool、conversation 和 workspace 候选做最终取舍。

## 数据准备

### Chunking

| 策略 | 适用内容 | 风险 |
|---|---|---|
| 固定长度 | 结构弱、快速 baseline | 切断语义和表格 |
| 递归结构 | Markdown、HTML、文档章节 | 标题层级不一定等于查询单元 |
| 语义分块 | 主题变化明显的长文 | 成本高、边界不稳定 |
| Parent-Child | 需要小块召回、大块阅读 | 索引和回查更复杂 |
| Sentence Window | 局部事实与邻近语境 | 可能缺少全局限定条件 |

Chunk 应保留 document ID、标题路径、版本、时间、权限、页码或 span。不要只存 embedding 和裸文本。

### Metadata

优先支持确定性过滤的字段：

- tenant、project、owner。
- document type、language、domain。
- created / updated / valid time。
- version、status、superseded_by。
- sensitivity、access policy。
- modality、time range、entity。

权限和版本过滤应先于相似度排序。

## Query 处理

根据任务可以使用：

- 原始查询直接检索。
- Query rewriting：消除指代、补充实体和时间。
- Multi-query：覆盖不同表述或子问题。
- Decomposition：复杂问题拆成可独立检索的事实需求。
- HyDE：用假设文档改善语义召回，但不能把假设当证据。
- Metadata inference：从可信任务 state 生成过滤条件。

重写必须保留原始意图和约束，并可在日志中对照。

## Hybrid Search 与 Rerank

- **Lexical / BM25** 擅长精确名称、代码、数字和稀有词。
- **Dense retrieval** 擅长语义相近但措辞不同的内容。
- **Hybrid Search** 结合两类候选，减少单一表示的盲点。
- **Reranker** 对较小候选集进行更细粒度的 query-document 相关性判断。

Rerank 不能恢复召回阶段从未找到的文档，也不能替代权限、版本和来源校验。

## 长上下文还是 RAG

| 条件 | 倾向长上下文 | 倾向 RAG |
|---|---|---|
| 数据规模 | 单个或少量可控文档 | 大型、持续增长的集合 |
| 更新频率 | 低，调用时可提供完整版本 | 高频，需要实时索引或查询 |
| 任务 | 需要跨全文结构理解 | 只需局部事实或候选证据 |
| 权限 | 整份材料同一权限 | 文档或字段级权限复杂 |
| 延迟成本 | 可接受较长 prefill | 检索后输入更短 |
| 风险 | 位置退化和噪声 | 漏召回和排序错误 |

实际系统常用混合方案：先 retrieval 缩小范围，再把少量完整章节或时间段交给长上下文模型。

## Semantic Cache

Semantic Cache 根据查询或任务表示的相似度复用历史结果。它与 Prompt Cache 不同：

- 命中的是“语义近似”，不是相同 token 前缀。
- 必须把 tenant、权限、时间、模型、数据版本和输出契约纳入 key 或硬过滤。
- 高风险事实不应只因相似就直接复用答案。
- 可以缓存 retrieval candidate、rerank 结果或最终答案，不同层的风险不同。
- 需要监控 false hit、staleness 和真实质量收益。

一个安全 baseline 是优先缓存可重新验证的检索候选，而不是不可解释地复用最终答案。

## 多模态 Retrieval

多模态检索可以组合：

- 文本 embedding：字幕、ASR、OCR、描述。
- 图像 embedding：关键帧、页面或局部区域。
- 时间索引：视频片段、说话区间、事件边界。
- 结构 metadata：人物、场景、文档页、镜头和对象。

返回结果应保留 modality、time range、frame/page ID 和原始媒体引用，再由 [[04-context-selection|Selection]] 决定哪些信号进入最终 context。

## Evidence Packet

```yaml
retrieval_result:
  query_id: q-1842
  query: 退款政策的例外条件
  filters:
    policy_status: active
  candidates:
    - id: refund-policy-v4#exceptions
      score:
        lexical: 0.83
        dense: 0.77
        rerank: 0.91
      source_version: 4
      evidence_span: paragraphs 18-23
      content: "..."
  gaps:
    - 国际订单政策尚未找到
```

缺失项也是检索产物，不能被生成步骤用模型常识悄悄补全。

## 评估

### Retrieval 层

- Recall@k、Precision@k、MRR、nDCG。
- 权限过滤正确率。
- 版本和新鲜度错误率。
- 重复率和来源覆盖。
- 关键证据 span recall。

### 生成层

- Faithfulness / groundedness。
- 引用准确率和引用覆盖。
- Context precision / context recall。
- 材料不足时的拒答或 missing-context 准确率。
- 端到端质量、延迟、token 和成本。

最终答案正确不能证明 retrieval 正确，模型可能依靠参数知识猜中；必须分别评估候选和答案。

## 常见误区

> [!warning] “检索到了”不等于“有证据”
> 候选与问题相似，不代表它权威、最新、完整或真正支持结论。生成前仍需选择、冲突处理和来源验证。

- **固定 chunk 和 top-k 适用于所有任务**：事实、比较、摘要和程序分析需要不同单位。
- **只用向量搜索**：代码、ID、数字和专有名词常需要 lexical 信号。
- **Reranker 解决所有问题**：无法修复权限错误和零召回。
- **Query rewrite 改变用户意图**：重写应可追踪并保留原始约束。
- **Semantic Cache 跨用户复用**：可能产生权限和隐私泄漏。
- **只评最终回答**：无法定位 chunk、召回、排序还是生成失败。

## 检查表

- [ ] Chunk 保留结构、来源、版本、权限和可回查 span。
- [ ] 权限和版本过滤在相似度排序之前执行。
- [ ] Query rewrite 不丢失原始目标和约束。
- [ ] Hybrid Search 与 Rerank 由真实 eval 决定，而不是默认堆叠。
- [ ] 冲突、缺失和否定证据被保留。
- [ ] 长上下文与 RAG 根据数据、任务、权限和成本选择。
- [ ] Semantic Cache 包含权限、时效和版本失效策略。
- [ ] Retrieval 与生成分别评估，并检查引用准确性。

## 相关笔记

- [[02-context-lifecycle|Context Lifecycle]]
- [[04-context-selection|Context Selection]]
- [[05-context-assembly|Context Assembly]]
- [[11-memory-engineering|Memory Engineering]]
- [[15-workspace-context|Workspace Context]]
- [[prompt-engineering/04-reasoning-strategies|推理增强策略]]

