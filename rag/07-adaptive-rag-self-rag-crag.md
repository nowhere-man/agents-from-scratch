---
title: 自适应 RAG：Self-RAG、CRAG 与主动检索
aliases:
  - Adaptive RAG
  - Self-RAG 与 CRAG
tags:
  - rag
  - self-rag
  - crag
  - adaptive-retrieval
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://arxiv.org/abs/2310.11511
  - https://arxiv.org/abs/2401.15884
---

# 自适应 RAG：Self-RAG、CRAG 与主动检索

> [!abstract] 本章只解决一个问题
> 固定 RAG 对每个问题都检索一次，但有些问题不需要检索，有些一次检索又远远不够。系统怎样判断“要不要查”“查到的够不够”“应该怎样纠正”？

前面六篇建立的是固定流水线。用户提问后，系统总会执行同一组步骤。自适应 RAG 把两个判断显式加入管线：

1. 当前回答是否需要外部证据？
2. 当前证据是否足以支持回答？

这两个判断看起来相近，实际发生在不同位置。

## 三种问题不能走同一条路径

| 用户请求 | 是否需要外部检索 | 原因 |
|---|---|---|
| 把这段政策改写得更简洁 | 通常不需要 | 材料已在输入中，任务是变换 |
| 最新东京住宿上限是多少 | 需要 | 事实会更新且要求引用 |
| 比较 v4 与 v5 并解释变化原因 | 需要多步 | 要取两个版本、差异和变更说明 |

如果所有请求都检索，系统会增加延迟、成本和无关材料；如果所有请求只检索一次，复杂问题又可能在第一轮漏证据。

## Adaptive RAG 的最小循环

~~~mermaid
flowchart TD
    Q["问题 + 当前状态"] --> N{"需要检索吗？"}
    N -->|否| G["直接生成或处理已给材料"]
    N -->|是| R["检索候选"]
    R --> E{"证据足够且可信？"}
    E -->|是| A["带引用生成"]
    E -->|否，可修复| C["改写、分解、扩展或换来源"]
    C --> R
    E -->|否，不可修复| H["澄清、拒答或人工升级"]
~~~

“需要检索”和“证据够不够”都不能只靠一句 prompt 的主观感觉。可靠实现会组合：

- 明确规则：出现 latest、current、引用要求、用户私有数据时强制检索；
- 分类器或 LLM router：判断任务类型和证据需求；
- 检索信号：top-k 分数、reranker margin、版本覆盖；
- 内容信号：是否覆盖每个 evidence role、是否冲突；
- 生成后检查：每个 claim 是否有引用支持。

## Self-RAG：在生成过程中学习检索和自我批评

Self-RAG 的原始工作不是“在 prompt 里让模型反思一句”这么简单。它通过训练，让模型在生成过程中产生特殊的 reflection tokens（反思标记），用来表达检索与批评决策。

概念上包括：

1. **Retrieve：**当前步骤是否需要取外部 passage；
2. **IsRel：**取回的 passage 与问题是否相关；
3. **IsSup：**生成内容是否被 passage 支持；
4. **IsUse：**回答对任务是否有用。

可把它想成：

~~~text
生成一部分
→ 判断是否需要检索
→ 取得 passage
→ 判断 passage 是否相关
→ 继续生成
→ 判断当前 claim 是否被支持
→ 选择继续、重写或停止
~~~

### Self-RAG 修改了哪一层

固定 RAG 的检索发生在生成前；Self-RAG 把“何时检索”和“如何批评证据/答案”嵌入生成策略。它希望模型按需要检索，而不是每次都检索，也不是只在开头检索一次。

### 适合什么问题

- 长回答中不同段落需要不同证据；
- 模型生成到某个具体 claim 时才发现缺资料；
- 需要在相关性、支持性和实用性之间做动态取舍。

### 代价和边界

- 原始 Self-RAG 涉及专门训练或适配，不等同于普通 API 模型加一段 prompt；
- 自我评分仍可能偏置或失准，需要外部评测；
- 多次检索增加延迟和 token；
- 检索文本仍需要 ACL、版本和注入防护。

工程上可以用 workflow 模拟类似控制流，但应称为“Self-RAG 风格的自适应流程”，不要把它和论文中的训练方法混为一谈。

## CRAG：先判断检索结果，再进入纠正路径

CRAG（Corrective Retrieval-Augmented Generation）的中心问题是：**第一次召回的文档可能不可靠，不能无条件交给生成模型。**

其概念流程是：

1. 用 retrieval evaluator 评估候选与 query 的相关性；
2. 将结果分成较可信、含糊或不相关的状态；
3. 对可信结果做知识精炼，提取真正相关的片段；
4. 对不可靠结果触发查询重写、外部搜索或替代来源；
5. 将精炼后的知识交给生成模型。

~~~mermaid
flowchart LR
    Q["Query"] --> R["初次检索"]
    R --> EV["Retrieval Evaluator"]
    EV -->|Correct| K["提取相关 knowledge strips"]
    EV -->|Ambiguous| M["保留部分 + 补充搜索"]
    EV -->|Incorrect| W["改写 / 换来源 / Web Search"]
    M --> K
    W --> K
    K --> G["生成并引用"]
~~~

### “纠正”不是修改原文

CRAG 的纠正对象是检索路径和上下文选择，不是把不喜欢的文档改成想要的答案。知识精炼通常把长 passage 分解成更小片段，再选择与 query 相关的部分，减少噪声。

### 例子

用户问 2026 年东京上限，初次候选全是 v4：

- evaluator 发现候选时间不匹配；
- 系统把状态记为 incorrect 或 ambiguous；
- query 加入生效日期、published、v5 等约束；
- 切换到 HR Source of Truth 或版本 API；
- 若仍找不到，输出索引可能过期，而不是回答 150 美元。

### CRAG 的边界

- evaluator 本身也会误判，需要校准；
- 相关性高不代表事实正确，仍要看权威性和版本；
- 外部 Web Search 可能带来隐私、注入和不可信来源；
- 纠正循环必须有次数、成本和停止条件。

## Self-RAG 与 CRAG 的区别

| 维度 | Self-RAG | CRAG |
|---|---|---|
| 主要问题 | 生成过程中何时检索、内容是否被支持 | 初次检索结果是否可靠、如何纠正 |
| 控制位置 | 生成策略内部或与生成交错 | 检索与生成之间的 evaluator |
| 典型动作 | retrieve、critique、continue/rewrite | accept、refine、rewrite、switch source |
| 原始方法特征 | reflection tokens 与训练 | retrieval evaluator + corrective actions |
| 工程模拟 | 可用状态机近似 | 可用路由节点较直接地实现 |

它们可以组合，但不是同义词：先用 CRAG 风格检查候选，再用 Self-RAG 风格在长回答中按 claim 继续检索，是一种可能架构。

## 主动检索与 FLARE 思路

另一类方法在生成时观察模型对未来内容的不确定性。当即将生成低置信度 token 或需要具体事实时，先把尚未完成的句子转成查询，再检索补证。这类思路常被称为 active retrieval；FLARE 是代表性工作之一。

它的难点是：

- token 概率低不一定意味着需要外部事实；
- 模型可能对错误内容也很自信；
- 每个句子都检索会产生巨大延迟；
- 查询来自未完成文本，容易偏离原始问题。

因此，实际系统通常把“模型不确定性”与规则、证据覆盖和领域风险一起使用。

## 怎样判断“证据足够”

不要只用最高相似度超过 0.8 这样的单阈值。更可靠的是多信号检查：

~~~yaml
retrieval_assessment:
  required_roles:
    current_policy: covered
    amount_currency: covered
    audience: covered
    citation: covered
  top_rerank_score: 0.91
  score_margin: 0.18
  independent_sources: 1
  conflict_count: 0
  index_freshness: current
  verdict: sufficient
~~~

### 关键术语

- **score margin：**第一名与后续候选的分数差，只能作为排序稳定性信号；
- **coverage：**问题要求的证据角色是否都被覆盖；
- **freshness：**索引版本是否跟上 Source of Truth；
- **conflict：**有效候选是否给出不同结论；
- **citation entailment：**引用 span 是否真的支持 claim。

这些值不是天然概率。阈值应通过标注数据和风险级别校准。

## 一个自适应 RAG 状态机

~~~python
def adaptive_answer(state):
    if not needs_external_evidence(state.request):
        return answer_from_provided_material(state)

    while state.steps < state.max_steps:
        result = retrieve(state.query, state.filters)
        assessment = evaluate_retrieval(
            request=state.request,
            evidence=result.evidence,
            required_roles=state.required_roles,
        )

        if assessment.sufficient:
            return generate_with_citations(
                assemble_context(state.request, result.evidence)
            )

        if not assessment.recoverable:
            return abstain_with_gaps(assessment.gaps)

        state = corrective_transition(
            state,
            assessment,
            actions=[
                "rewrite_query",
                "decompose_question",
                "expand_parent",
                "switch_source",
            ],
        )

    return stop_due_to_budget(state)
~~~

需要把 state.steps、每次 query、候选、assessment、动作和停止原因都写入 trace。否则自适应系统出错时只会表现为“它多搜了几次”，无法定位哪次判断偏了。

## 什么时候先不要用自适应 RAG

- 固定 query 类型，证据源单一且稳定；
- BM25+dense+reranker 已能达到目标；
- 延迟预算严格；
- 没有可用的 retrieval eval 集；
- 系统无法可靠记录状态和停止原因。

此时固定工作流更容易测试和审计。自适应性应该用来处理真实不确定性，而不是隐藏基础索引质量问题。

> [!success] 读者自测
> 如果初次检索返回的是 v4，Self-RAG、CRAG 和普通 reranker 各能做什么、不能做什么？答案应包含：是否能发现 zero recall、是否能切换来源、是否能把不存在的 v5 排出来。

下一篇把这些自适应动作放进一个更完整的 Agent 循环：[[rag/08-agentic-rag|Agentic RAG：让 Agent 规划检索路径]]。
