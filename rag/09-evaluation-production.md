---
title: RAG 评测、可观测性、安全与生产取舍
aliases:
  - RAG Evaluation
  - RAG 生产化
tags:
  - rag
  - evaluation
  - observability
  - security
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://docs.ragas.io/en/stable/
  - https://www.trulens.org/
  - https://arxiv.org/abs/2005.11401
---

# RAG 评测、可观测性、安全与生产取舍

> [!abstract] 本章学习终点
> 你应该能把“RAG 回答错了”拆成索引、召回、排序、上下文和生成五类问题；为每一层选择指标；并用固定评测集证明一次优化是否真的提高了质量，而不是只让答案看起来更流畅。

RAG 最危险的评测方式是随便问几个问题，然后凭感觉判断“比之前好”。生成文本会变化、模型很会说服人，而真正的错误可能藏在引用、版本或漏召回里。

## 先建立分层故障模型

~~~mermaid
flowchart LR
    A["原始文档"] --> B["解析 / Chunk"]
    B --> C["索引"]
    C --> D["召回"]
    D --> E["融合 / Rerank"]
    E --> F["Context"]
    F --> G["Answer"]

    B -.-> B1["结构或 span 丢失"]
    C -.-> C1["版本过期 / 删除未传播"]
    D -.-> D1["zero recall"]
    E -.-> E1["正确候选排太后"]
    F -.-> F1["重复 / 冲突 / 预算错误"]
    G -.-> G1["误读 / 无引用 / 幻觉"]
~~~

端到端答案正确率只能告诉你“最后错了”，不能告诉你该改 embedding、chunk、reranker 还是 prompt。评测必须同时看中间层。

## 先做一套最小评测集

每条样本不只保存参考答案，还保存 gold evidence：

~~~yaml
id: travel-001
question: 最新政策中东京普通员工每日住宿上限是多少？
as_of: 2026-07-22
user_scope:
  groups: [all-employees]
reference_answer:
  amount: 180
  currency: USD
  version: v5
gold_evidence:
  - document_id: policy-travel-2026
    version: v5
    span: page 7, row 东京
required_claims:
  - amount
  - currency
  - audience
  - version
must_not_use:
  - version: v4
~~~

样本应覆盖：

- 常见问法和口语改写；
- 精确 ID、数字和版本；
- 相似但不适用的 hard negative；
- 没有答案、需要拒答的 query；
- 权限不同的用户；
- 多跳、冲突和过期索引；
- 中文、英文和中英混合；
- prompt injection 或数据污染测试。

评测集越贴近真实流量，优化越可信。公开 benchmark 能测试通用能力，但不能替代你的文档结构、ACL 和业务定义。

## 召回层指标

### Hit Rate@k

只关心 top-k 中是否至少出现一个正确证据：

$$
\operatorname{HitRate@k}
=
\frac{1}{|Q|}
\sum_{q\in Q}
\mathbb{1}[\text{top-k 包含 gold}]
$$

适合每个问题只需要一个关键 chunk 的简单问答。

### Recall@k

若一个问题有多个必要证据：

$$
\operatorname{Recall@k}
=
\frac{|\text{top-k 中的相关证据}|}
{|\text{全部相关证据}|}
$$

例如问题需要“金额表格”和“生效日期”两条证据，只召回表格，Recall 不是 1。

### Precision@k

$$
\operatorname{Precision@k}
=
\frac{|\text{top-k 中的相关证据}|}{k}
$$

高 recall 常通过增大 k 获得，但会引入更多无关上下文；precision 衡量候选中的噪声。

### MRR

MRR（Mean Reciprocal Rank）关注第一个相关结果出现多早：

$$
\operatorname{MRR}
=
\frac{1}{|Q|}
\sum_{q\in Q}
\frac{1}{\operatorname{rank}_q}
$$

若正确 chunk 分别排 1、2、10 名，对应贡献为 1、0.5、0.1。它适合“最先看到一个正确证据就够”的任务。

### nDCG

当相关性有等级，例如“直接支持”“部分相关”“仅背景”，nDCG 更合适。

$$
\operatorname{DCG@k}
=
\sum_{i=1}^{k}
\frac{2^{rel_i}-1}{\log_2(i+1)}
$$

$$
\operatorname{nDCG@k}
=
\frac{\operatorname{DCG@k}}{\operatorname{IDCG@k}}
$$

IDCG 是理想排序的 DCG。nDCG 同时奖励高相关文档和靠前位置，常用于比较 reranker。

> [!important] 先验证 zero recall
> 如果 gold evidence 没进候选，reranker、prompt 和生成模型都不可能修复。排错时先看 Recall@k，再看 nDCG/MRR。

## 上下文层指标

### Context Precision

放进模型的 context 中，有多少信息真正服务答案。重复、无关和错误版本会降低 precision。

### Context Recall

回答所需证据是否都进入 context。检索召回了 gold，但 assembly 因预算删除了它，retrieval recall 可以高，context recall 仍然低。

### Context Utilization

模型是否真正使用了提供的证据。某个 span 被放进 prompt，不代表生成模型引用或正确理解了它。可以检查输出 claim 与 evidence 的对应关系。

### Redundancy / Diversity

统计相同 parent、近重复 chunk 和来源覆盖。上下文全是同一段 overlap，会消耗窗口却不增加证据。

## 答案与引用指标

### Faithfulness / Groundedness

把答案拆成可验证 claim，检查每个 claim 是否能由 context 支持：

$$
\operatorname{Faithfulness}
=
\frac{|\text{被 evidence 支持的 claims}|}
{|\text{答案中的全部可验证 claims}|}
$$

模型答对 180，但同时编造“无需发票”，仍不是完全 faithful。

### Answer Correctness

与参考答案比较事实、数字、单位、条件和版本。它可以由规则、字符串、结构化字段、人评或校准后的 LLM judge 共同计算。

### Answer Relevance

回答是否回应用户问题。一个引用很多正确政策却没有给出金额的答案，faithfulness 可能不低，relevance 仍然差。

### Citation Precision

模型给出的引用中，有多少真正支持对应 claim。

### Citation Recall

需要引用的 claims 中，有多少都有可验证 citation。只有文末列一份文档列表，不能证明每条 claim 的来源。

### Abstention Quality

对没有答案或证据不足的样本，系统是否能正确拒答、说明 gap 或请求澄清。强行回答会提高表面覆盖，却降低可靠性。

## RAGAS 与 TruLens 各自做什么

### RAGAS

RAGAS 提供面向 RAG 的评测组件，例如 context precision/recall、faithfulness、answer relevance 等，也支持构造和管理评测流程。它能加速实验，但指标定义、judge 模型和数据版本仍需自己固定。

### TruLens

TruLens 更强调对 LLM/RAG 应用的 trace、反馈函数和可观测性，可在 query、retrieval、context 和 answer 之间检查 groundedness、relevance 等。

它们不是“装上就自动知道质量”的裁判。要记录：

- 使用的 judge 模型和版本；
- 提示模板和温度；
- evidence 与 reference 是否完整；
- 同一批样本的重复运行方差；
- 与人类标注的一致性。

## LLM-as-Judge 的边界

LLM judge 擅长自然语言语义比较，但可能：

- 偏爱更长、更有说服力的答案；
- 受被评答案中的指令影响；
- 对数字、否定、引用范围判断不稳；
- 和被测模型共享同样的知识偏差；
- 模型升级后标准漂移。

降低风险的方法：

1. 数字、日期、ID 用确定性规则检查；
2. 对 judge 输入做结构化分区；
3. 用人工标注样本校准阈值；
4. 对关键指标使用多个 judge 或 pairwise 比较；
5. 固定 judge 版本并做回归；
6. 高风险任务保留人工复核。

## Agentic RAG 还要评测轨迹

除了答案和 evidence，还要看：

| 指标 | 问题 |
|---|---|
| Step Success | 每一步是否让 gap 减少 |
| Tool Selection Accuracy | 是否选择了正确来源/工具 |
| Query Efficiency | 是否用较少查询取得足够证据 |
| Loop Rate | 是否出现重复 query 和候选 |
| Stop Accuracy | 证据够时是否停止，不够时是否拒答 |
| Recovery Rate | 首次检索失败后能否纠正 |
| Policy Compliance | 是否始终遵守 ACL、预算和审批 |

最终答对但通过越权文档得到答案，仍然是失败。

## 端到端 trace 应记录什么

~~~yaml
trace:
  request_id: rag-20260722-001
  query:
    original: 东京住一晚能报多少？
    rewritten: 东京 每日 住宿 上限 普通员工
  filters:
    status: published
    as_of: 2026-07-22
  index_versions:
    lexical: 2026-07-22T08:00Z
    vector: 2026-07-22T08:00Z
  retrieval:
    bm25_top_k: 50
    dense_top_k: 50
    candidates_after_union: 73
  reranker:
    model: pinned-model-version
    input_count: 40
  context:
    evidence_ids: [ev-8f2]
    token_count: 920
    gaps: []
  answer:
    claims: 3
    cited_claims: 3
  latency_ms:
    embed: 25
    retrieve: 40
    rerank: 130
    generate: 600
  cost:
    total: 0.00x
~~~

没有 index version、模型版本和中间候选，就无法复现“昨天正确、今天错误”的变化。

## 延迟和成本预算

典型在线延迟由以下部分组成：

$$
L_{\text{total}}
=
L_{\text{rewrite}}
+L_{\text{embed}}
+L_{\text{retrieve}}
+L_{\text{rerank}}
+L_{\text{generate}}
+L_{\text{agent loops}}
$$

优化顺序：

- 并行执行独立的 BM25 和 dense search；
- 批量 embedding 和 rerank；
- 缓存稳定 query 的 embedding，但 key 要含模型版本；
- 只 rerank 候选子集；
- 对低风险、简单请求走固定短路径；
- 设置 Agent 最大步骤和 deadline；
- 把长 parent 只在需要时回取。

缓存必须含权限、tenant、as_of、索引版本和模型版本；否则会把另一个用户或旧政策的结果错误复用。

## 新鲜度与删除传播

生产 RAG 需要监控：

- Source of Truth 到索引的 lag；
- 文档更新后 lexical/vector 索引是否都完成；
- 删除和权限撤销是否传播到 chunk、embedding、缓存和摘要；
- failed ingestion job 是否可重放；
- embedding 模型升级是否使用双索引迁移。

索引是派生数据。允许重建，但重建过程中要有版本切换和回滚策略，不能让半套新索引与半套旧索引混用。

## 安全清单

### ACL 与租户隔离

- 过滤条件来自受信身份系统，不来自模型猜测；
- 检索前和返回前双重检查；
- trace 不记录超出当前用户权限的正文；
- 缓存 key 包含用户权限范围。

### Prompt Injection

- 外部文档按不可信数据处理；
- evidence 与 system/tool 指令分区；
- 工具调用需程序授权；
- 高风险输出经过 policy gate；
- 对 Web、邮件和用户上传文档做专门测试。

### 数据投毒

攻击者可能写入大量关键词或近似文本，让恶意文档排到前面。防护包括：

- 写入权限和发布审批；
- Source authority 权重；
- 近重复和异常关键词监控；
- 文档签名/checksum；
- 版本与来源审计；
- 评测集中的 poisoning 用例。

### PII 与合规

PII（Personally Identifiable Information，个人可识别信息）指能直接或间接识别个人的数据，例如姓名、证件号、邮箱和精确位置。

- 摄取前识别敏感字段；
- 最小化索引正文和日志；
- 对 embedding 也按敏感数据处理；
- 定义保留期、删除和访问审计；
- 外部 embedding/rerank API 前确认数据出境要求。

## 一次可靠的实验流程

1. 固定评测集、索引快照和模型版本；
2. 运行 baseline，保存每层指标和 trace；
3. 一次只改一个变量，例如加 reranker；
4. 比较 Recall@k、nDCG、context precision、faithfulness、延迟和成本；
5. 检查分组结果：语言、query 类型、权限、长文档；
6. 人工阅读赢/输样本，找机制原因；
7. 达到门槛后先做 shadow（影子流量，只观察不影响用户）或 canary（小流量灰度），而不是直接全量；
8. 把评测加入每次模型、prompt、chunk 和索引升级的回归。

### 一个推荐的升级序列

~~~text
BM25 baseline
→ Dense baseline
→ Hybrid + RRF
→ Reranker
→ Parent-Child / Context Assembly
→ Query Rewrite / Multi-Query
→ Adaptive / Agentic RAG
~~~

每一步都要证明增益覆盖新增复杂度。若 Hybrid + Reranker 已满足业务，就没有必要为了“先进”而加入 Agent。

> [!success] 读者自测
> 如果最终答案错误，应按什么顺序检查 gold span 是否进 top-k、是否被 reranker 排前、是否进入 context、是否被 citation 支持？为什么只看 faithfulness 不能发现 zero recall？

下一篇把这些接口串成一个最小实现：[[rag/10-minimal-implementation|最小可运行实现与升级路线]]。
