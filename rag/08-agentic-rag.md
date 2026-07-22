---
title: Agentic RAG：让 Agent 规划检索路径
aliases:
  - Agentic Retrieval
  - Agentic RAG 教程
tags:
  - rag
  - agentic-rag
  - agents
  - workflows
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://arxiv.org/abs/2310.11511
  - https://arxiv.org/abs/2401.15884
  - https://langchain-ai.github.io/langgraph/
  - https://docs.llamaindex.ai/en/stable/module_guides/workflow/
---

# Agentic RAG：让 Agent 规划检索路径

> [!abstract] 本章学习终点
> 你应该能区分“带一次检索的聊天机器人”和“Agentic RAG”，并能设计一个有状态、有工具权限、有停止条件的检索循环；还要知道什么时候固定 RAG 更可靠。

固定 RAG 的路径由程序预先写死：

~~~text
query → hybrid retrieve → rerank → generate
~~~

Agentic RAG 允许系统根据当前证据和未解决问题选择下一步：

~~~text
理解任务 → 选择来源 → 检索 → 观察缺口
→ 改写/分解/换工具 → 再检索 → 验证 → 停止
~~~

关键变化不是“多调用几次 LLM”，而是**检索成为 Agent 可以重复选择的动作，动作结果会更新显式状态，并受授权、预算和停止条件控制。**

## Agentic RAG 与普通 RAG 的边界

| 维度 | 固定 RAG | Agentic RAG |
|---|---|---|
| 路径 | 预先确定 | 根据中间结果选择 |
| 查询次数 | 通常 1 次或固定次数 | 动态，但有上限 |
| 数据源 | 固定一组 | 可在文档、数据库、API、Web 间路由 |
| 状态 | 请求内短暂变量 | 保存计划、证据、gaps、动作和预算 |
| 可预测性 | 高，容易测试 | 较低，需要轨迹评测 |
| 适合 | 单跳问答、稳定语料 | 多跳、验证、版本比较、开放研究 |

如果只是在固定链中加入 reranker，仍是增强的 RAG，不一定是 Agentic RAG。是否 agentic，取决于模型是否在受控状态机中决定动作路径。

## 最小 Agent 循环

~~~mermaid
stateDiagram-v2
    [*] --> Understand
    Understand --> Plan
    Plan --> Retrieve
    Retrieve --> Observe
    Observe --> Verify
    Verify --> Retrieve: 证据不足且可修复
    Verify --> Clarify: 缺少用户条件
    Verify --> Answer: 证据足够
    Verify --> Escalate: 高风险或无法验证
    Clarify --> Plan
    Answer --> [*]
    Escalate --> [*]
~~~

### Understand

把用户请求变成任务合同：

~~~yaml
objective: 回答东京普通员工每日住宿上限
as_of: 2026-07-22
required_output:
  - amount
  - currency
  - policy_version
  - citation
constraints:
  - 只访问当前用户有权查看的来源
  - 不把草案当作已发布政策
~~~

### Plan

计划不是一段隐藏思维，而是程序可检查的下一步：

~~~yaml
steps:
  - 查询已发布政策索引
  - 验证当前有效版本
  - 回取东京表格行和适用人群
  - 检查金额、币种、版本和引用是否齐全
~~~

### Retrieve / Act

Agent 只能调用预先声明的工具。每个工具要有明确输入、输出、权限和失败状态。

### Observe / Verify

把工具返回写成 evidence，不把“调用成功”当成“答案正确”。验证 evidence role、版本、冲突和 gap。

### Stop

满足完成条件、达到预算、遇到权限边界或证据不可验证时停止。没有显式停止条件的 Agent 很容易重复改写 query，形成无效循环。

## Agent 状态应该保存什么

~~~yaml
rag_state:
  task_id: travel-policy-42
  objective: 回答东京住宿上限并引用当前政策
  user_scope:
    tenant: example-corp
    groups: [all-employees]
  plan:
    current_step: verify_policy_version
  queries:
    - query_id: q1
      text: 东京 住宿 上限
      status: completed
  evidence:
    - evidence_id: ev-v4
      version: v4
      status: superseded
  gaps:
    - current_policy_version
  actions_taken:
    - search_policy_index
  budget:
    max_steps: 6
    used_steps: 1
    max_retrieval_calls: 8
  stop_reason: null
~~~

State 不应只是一段自然语言 scratchpad。关键字段要结构化，才能做恢复、权限检查、去重和评测。checkpoint（检查点）就是保存下来的状态快照，允许 Agent 从中断处继续。

## 工具契约决定 Agent 能否可靠工作

一个检索工具可以定义为：

~~~yaml
name: search_policy_chunks
input:
  query: string
  filters:
    tenant: string
    status: published
    effective_as_of: date
    audience: string
  top_k: integer
output:
  candidates:
    - chunk_id
    - text
    - version
    - source_uri
    - scores
  gaps: list
errors:
  - unauthorized
  - stale_index
  - timeout_unknown
~~~

### 为什么要有 timeout_unknown

工具超时不代表“没有搜索结果”。调用可能：

- 根本没执行；
- 已执行但响应丢失；
- 部分完成；
- 返回太慢被客户端中断。

Agent 在重试前要知道工具是否有副作用。纯搜索通常可安全重试；会更新索引或写数据库的工具则需要 idempotency key（幂等键），避免重复执行。

## 沿主线看一次 Agentic 检索

### 第 1 步：搜索政策索引

结果只有 v4，金额 150 美元。Agent 不应立即回答，因为任务要求“最新”。

~~~yaml
observation:
  evidence_found: true
  required_role_current_version: missing
  index_freshness: uncertain
  next_action: query_policy_catalog
~~~

### 第 2 步：查询版本目录

目录显示 v5 已在 2026-06-01 生效，但向量索引更新时间早于该日期。现在可以诊断为 stale index，而不是 query 不相关。

### 第 3 步：从 Source of Truth 回取 v5

Agent 使用文档 API 读取 v5 对应表格行。工具仍然强制 ACL，不因 Agent “认为需要”就越权。

### 第 4 步：验证适用范围

候选包含普通员工 180、美金、东京和生效日期；实习生 120 被标记为不同 audience，不进入主 claim。

### 第 5 步：停止并回答

所有 evidence role 已覆盖，引用可回查，未发现冲突。Agent 写入 stop_reason=all_requirements_satisfied，而不是继续搜索更多文档。

这个轨迹的价值在于：系统不仅答出 180，还发现索引过期，并能把修复任务交给 ingestion pipeline。

## 常见 Agentic RAG 模式

### 1. Router

先判断应该去哪类来源：

- 政策文档 → BM25/向量；
- 当前余额 → 数据库或业务 API；
- 最新公共信息 → 受控 Web Search；
- 代码行为 → 当前 workspace 和测试工具。

Router 适合来源职责清晰的系统。错误路由会造成 zero recall，因此要保留 fallback 和可观测日志。

### 2. Query Planning / Decomposition

把复合问题拆成子问题，并建立依赖：

~~~text
当前有效版本是什么？
        ↓
东京普通员工上限是多少？
        ↓
超过 14 天是否需要额外审批？
~~~

有依赖的子问题不能盲目并行；没有依赖的来源查询可以并行以降低延迟。

### 3. Iterative Retrieval

第一轮结果暴露新实体后，再生成第二轮 query。例如先发现政策编号 TRV-2026-05，再按编号获取附件。每轮都要检查是否真的增加新证据，防止同义改写原地循环。

### 4. Multi-source Verification

一个来源给规则，另一个来源给当前生效状态或实时数据。Agent 需要分别记录 source authority：

- 文档系统回答“政策写了什么”；
- 发布目录回答“哪个版本当前有效”；
- 费用系统回答“某次报销实际使用了哪个规则”。

不能用低权威网页覆盖内部 Source of Truth。

### 5. Human-in-the-Loop

以下情况应暂停：

- 不同权威来源冲突；
- 需要访问更高权限材料；
- 回答会触发付款、合规或法律后果；
- Agent 想扩大数据范围或调用有副作用工具。

人工节点可以是 approve、edit、reject 三态，并把决定写入状态供恢复。

## GraphRAG 与 Agentic RAG 不是同一概念

**GraphRAG**通常先从语料抽取实体、关系和社区结构，再用图遍历或社区摘要回答全局关系问题。例如：

~~~text
政策 v5
  ├─ 适用于 → 普通员工
  ├─ 覆盖地区 → APAC
  └─ 替代 → 政策 v4
~~~

它适合：

- “哪些政策共同影响 APAC 员工？”；
- “这次规则更新关联哪些部门和流程？”；
- 需要跨文档关系和全局摘要。

代价包括实体抽取错误、图更新成本、关系 schema 设计和更复杂评测。Agentic RAG 可以把图检索当作一个工具；GraphRAG 本身不一定有 Agent 循环。

## 结构化数据和多模态来源

不是所有知识都应先转成文本 chunk：

- 价格、余额、库存：优先通过 SQL（关系数据库查询语言）或 API（程序接口）查询；
- 表格：保留 schema（字段结构）和行列关系，必要时生成文本视图；
- 图片：保存图像 embedding、OCR、区域坐标和原图；
- 视频：保存 ASR、关键帧、时间戳和视觉描述；
- 知识图谱：按实体和关系检索。

Agentic RAG 的优势之一是能按问题选择工具，而不是把所有来源强行塞进同一种向量库。

## 安全与控制

### 权限

- 工具层强制 tenant、ACL 和数据范围；
- 模型不能通过自然语言扩大权限；
- 每个 evidence 记录访问主体和授权结果；
- Web/邮件等外部内容按不可信数据处理。

### 预算

~~~yaml
limits:
  max_steps: 6
  max_retrieval_calls: 8
  max_web_calls: 1
  max_context_tokens: 12000
  deadline_ms: 8000
~~~

达到限制时应输出已知证据和 gaps，而不是静默给出猜测。

### 死循环检测

如果连续 query 高度相似、候选集合不变、gaps 没减少，就停止或切换策略。可记录：

- 新增 evidence 数；
- evidence role 覆盖变化；
- query 相似度；
- 候选 Jaccard 重合率（两个候选集合交集占并集的比例）；
- 剩余预算。

## 框架怎样选

框架只负责承载状态和工具，不替代检索设计：

| 方案 | 适合 | 提醒 |
|---|---|---|
| 手写状态机 | 学习、路径简单、需要完全可控 | 先从这里理解数据流 |
| LangGraph | 有状态图、checkpoint、人工中断与恢复 | 图结构仍需自己设计 |
| LlamaIndex Workflows | 数据/RAG 为中心的事件工作流 | 不要把索引策略藏在默认配置里 |
| Haystack Pipelines/Agents | 搜索管线与组件组合 | 仍需独立评测每层 |
| LangChain | 集成模型、retriever 和工具 | 业务状态和授权不宜只依赖链式封装 |
| 官方 Agents SDK | 绑定供应商模型和工具调用（tool calling） | 数据层、索引和 eval 仍是自己的责任 |

先手写一个 30–50 行的固定循环，确认 state、tool contract 和 stop condition，再选框架，通常比一开始堆抽象更容易排错。

## 一个最小 Agentic RAG 伪代码

~~~python
def run_agentic_rag(state, tools):
    while not state.done:
        if exceeded_budget(state):
            state.stop_reason = "budget_exceeded"
            break

        action = choose_next_action(state)
        validate_action_against_policy(action, state.user_scope)
        observation = tools.execute(action)
        state = update_state(state, action, observation)

        assessment = assess_evidence(
            state.evidence,
            state.required_roles,
        )
        if assessment.complete:
            state.answer = generate_with_citations(state)
            state.stop_reason = "all_requirements_satisfied"
            state.done = True
        elif not assessment.recoverable:
            state.stop_reason = "insufficient_verifiable_evidence"
            state.done = True

    return state
~~~

choose_next_action 可以由规则、模型或二者共同决定；validate_action_against_policy 和 budget 必须由程序控制。

## 什么时候固定 RAG 更好

- 问题是单跳、数据源固定；
- 证据 schema 清楚，hybrid + reranker 已达标；
- P95 延迟严格；
- 每次额外调用的成本高；
- 合规要求需要可预测路径；
- 没有足够的轨迹评测数据。

Agentic RAG 不是 RAG 的“高级版按钮”。它用自主路径换取多步能力，同时带来状态、授权、循环和评测复杂度。只有当问题的不确定性真的需要动态决策时，它才值得。

> [!success] 读者自测
> 在“索引只返回 v4，但版本目录显示 v5 已生效”的场景里，Agent 应怎样更新 state、选择下一工具并停止？答案应包含 stale index、Source of Truth、ACL、evidence role 和 stop reason。

下一篇回答上线前最重要的问题：怎么证明这套系统真的比 baseline 好。见 [[rag/09-evaluation-production|评测、观测、安全与生产取舍]]。
