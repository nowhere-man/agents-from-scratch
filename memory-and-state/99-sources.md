---
title: Agent Memory 与 State：资料与来源
aliases:
  - Memory State Sources
  - Agent 状态记忆参考资料
tags:
  - agents
  - memory
  - state
  - sources
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
---

# Agent Memory 与 State：资料与来源

> [!note] 使用说明
> 正文优先讲稳定的工程原语；框架 API、模型能力、产品名称和价格会变化。部署前请打开官方链接核对当前版本、SDK 参数、存储后端和合规条款。来源用于支撑选型方向，不替代你自己的压测、故障演练和安全评审。

## 仓库内前置与接口

- [[context-engineering/00-overview|Context Engineering 总览]]
- [[context-engineering/01-context-architecture|Context Architecture]]
- [[context-engineering/10-conversation-context|Conversation Context]]
- [[context-engineering/11-memory-engineering|Memory Engineering]]
- [[context-engineering/12-retrieval-engineering|Retrieval Engineering]]
- [[context-engineering/14-planning-context|Planning Context]]
- [[context-engineering/15-workspace-context|Workspace Context]]
- [[prompt-engineering/12-tools-state-and-authorization|工具、状态与授权边界]]
- [[prompt-engineering/13-decomposition-and-agent-workflows|任务拆解与 Agent 工作流]]
- [[rag/00-overview|RAG 与 Agentic RAG 总览]]

## Agent 框架与运行时

- LangGraph Persistence（checkpointer 与 store）：https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Stores（namespace、semantic search、持久后端）：https://docs.langchain.com/oss/python/langgraph/stores
- LangGraph Checkpointers：https://docs.langchain.com/oss/python/langgraph/checkpointers
- OpenAI Agents SDK Sessions：https://openai.github.io/openai-agents-python/sessions/
- OpenAI Agents SDK conversation state ownership（官方仓库参考）：https://github.com/openai/openai-agents-python/blob/main/.agents/references/conversation-state-ownership.md
- OpenAI Conversation State guide：https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI Agents running guide：https://developers.openai.com/api/docs/guides/agents/running-agents
- Google ADK Session / State / Memory：https://adk.dev/sessions/
- Google ADK State：https://adk.dev/sessions/state/
- Google ADK MemoryService：https://adk.dev/sessions/memory/
- Microsoft Agent Framework：https://learn.microsoft.com/en-us/agent-framework/
- Microsoft Agent Framework Memory & Persistence：https://learn.microsoft.com/en-us/agent-framework/get-started/memory
- AutoGen：https://microsoft.github.io/autogen/
- CrewAI：https://docs.crewai.com/
- LlamaIndex Workflows：https://developers.llamaindex.ai/python/llamaagents/workflows/
- PydanticAI：https://pydantic.dev/docs/ai/overview/
- Semantic Kernel：https://learn.microsoft.com/en-us/semantic-kernel/overview/

## 专用 Memory 方案

- Mem0 How It Works：https://docs.mem0.ai/core-concepts/how-it-works
- Mem0 Add Memory：https://docs.mem0.ai/core-concepts/memory-operations/add
- Mem0 Memory Types：https://docs.mem0.ai/core-concepts/memory-types
- Mem0 Memory Evaluation：https://docs.mem0.ai/core-concepts/memory-evaluation
- Zep Key Concepts（Context Graph / Context Block / temporal facts）：https://help.getzep.com/concepts
- Zep Graphiti（开源 temporal knowledge graph）：https://help.getzep.com/graphiti
- Letta Stateful Agents：https://docs.letta.com/concepts/stateful-agents/
- Letta Memory & Dreaming：https://docs.letta.com/configuration/memory/
- Letta MemFS：https://docs.letta.com/concepts/memfs/

## Durable execution 与基础设施

- Temporal Event History：https://docs.temporal.io/workflow-execution/event
- Temporal Workflow Execution：https://docs.temporal.io/workflow-execution
- Temporal deterministic constraints：https://docs.temporal.io/workflow-definition#deterministic-constraints
- PostgreSQL transaction isolation：https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL JSON types：https://www.postgresql.org/docs/current/datatype-json.html
- PostgreSQL row-level locking：https://www.postgresql.org/docs/current/explicit-locking.html
- pgvector：https://github.com/pgvector/pgvector
- Redis data types and persistence：https://redis.io/docs/latest/develop/data-types/
- Redis Streams：https://redis.io/docs/latest/develop/data-types/streams/
- Amazon DynamoDB conditional writes（可选文档型 State 参照）：https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html

## 研究与背景

- Generative Agents（episodic memory、reflection、planning）：https://arxiv.org/abs/2304.03442
- MemGPT / Letta 的分层 memory 思路：https://arxiv.org/abs/2310.08560
- Reflexion（语言反馈与 episodic memory）：https://arxiv.org/abs/2303.11366
- ReAct（reasoning + acting）：https://arxiv.org/abs/2210.03629
- RAG 原始论文：https://arxiv.org/abs/2005.11401

## 版本与证据边界

- 本系列在 2026-07-23 进行资料核对；官方文档中标注为 preview、managed-only、OSS-only 或实验功能的内容，不应当作跨供应商稳定契约。
- 框架文档里的 `Session`、`State`、`Memory` 名称相似，但数据 owner、序列化格式和恢复保证不同；阅读时以语义和失败边界为准。
- 向量/图检索产品的召回、延迟和价格取决于 embedding、索引参数、数据规模、过滤条件和部署区域，必须用自己的 eval set 验证。
- Temporal、LangGraph checkpoint、SDK session 和专用 Memory service 可以组合，也可以不用；本系列推荐先定义 Contract、owner 和不变量，再选实现。
