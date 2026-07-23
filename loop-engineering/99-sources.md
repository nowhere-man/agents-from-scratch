---
title: Loop Engineering 资料与来源
aliases:
  - Loop Engineering Sources
  - Agent Loop Sources
tags:
  - agents
  - sources
  - research
  - loop-engineering
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
---

# Loop Engineering 资料与来源

## 证据使用规则

本系列把来源分成四层：

1. **原始论文**：用于解释方法的原始问题、结构和实验设置；
2. **官方规范/文档/仓库**：用于描述当前公开产品能力和 API 概念；
3. **近期预印本**：用于展示正在发展的研究问题，明确标注尚新；
4. **本教程工程推导**：统一 contract、owner、状态和故障边界，不冒充论文结论或厂商保证。

所有网页访问日期为 **2026-07-23**。动态产品文档可能继续变化；正文依赖稳定语义，并尽量避免绑定 preview 方法名。

## 经典推理与 Agent 方法

| 主题 | 原始来源 | 本系列采用的主张 | 不采用的推断 |
|---|---|---|---|
| ReAct | Yao et al., [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629), ICLR 2023 | reasoning 与 task-specific action 交错，环境 observation 更新后续决策 | 不把公开 reasoning trace 等同于生产必须保存私有思维链 |
| Plan-and-Solve | Wang et al., [Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091), ACL 2023 | 先拆子任务再求解，针对 Zero-shot-CoT 的漏步等问题 | 不把任何有计划的 Agent 都称为论文实现 |
| Reflexion | Shinn et al., [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) | 根据反馈生成语言反思，并放入 episodic memory，不更新模型权重 | 不把普通“再想一次”或长期用户记忆称为 Reflexion |
| ToT | Yao et al., [Tree of Thoughts](https://arxiv.org/abs/2305.10601), NeurIPS 2023 | 在 thought 粒度生成、评估、搜索和回溯多个路径 | 不把普通条件分支图称为 ToT |
| GoT | Besta et al., [Graph of Thoughts](https://arxiv.org/abs/2308.09687), AAAI 2024 | thought 可形成任意图，支持依赖、合并和反馈 | 不声称任意 Agent graph 都复现论文实验 |
| LATS | Zhou et al., [Language Agent Tree Search](https://arxiv.org/abs/2310.04406) | 将 MCTS、LM value/reflection 和环境反馈组合 | 不把一个带树的 Planner 自动称为 LATS |
| Self-Refine | Madaan et al., [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651) | 生成—反馈—修订是一类可复用循环 | 自反馈不自动等于真实正确性 |
| Tool-interactive critique | Gou et al., [CRITIC](https://arxiv.org/abs/2305.11738) | 外部工具反馈可增强 critique/correction | 不跳过工具权限和 observation 验证 |

`Plan-and-Execute` 在本系列中是通用工程模式，不指向唯一论文：Planner 维护可验证 plan items，Executor 每次执行一个步骤，并在 observation 后重规划。其工程选择还参考下面的 Anthropic workflow、LangGraph 和 SDK 文档。

## Harness 与 Agent 系统工程

### 官方工程资料

- Anthropic Engineering, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), 2024-12-19：workflow 与 agent 的区分；prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer；保持简单、透明和认真设计 ACI。
- Anthropic, [Claude Code documentation](https://code.claude.com/docs/en/overview)：coding agent 产品形态参考。
- OpenAI, [Codex CLI repository](https://github.com/openai/codex)：公开说明 Codex CLI 是本地运行的 coding agent；只用于产品形态和公开入口，不推断内部数据库/协议。
- Cursor, [Agent documentation](https://docs.cursor.com/agent)：workspace coding agent 产品形态参考；正文不复刻厂商未公开实现。

### 2026 年近期预印本快照

| 论文 | 研究问题 | 本系列如何使用 |
|---|---|---|
| [Don't Blame the Large Language Model: How Agent Harness Evolution Shapes Coding Agent Quality](https://arxiv.org/abs/2607.03691) | harness 演进怎样影响 coding-agent 效果和效率 | 支持把 Harness 视为独立实验变量；结果仍需按论文设置阅读 |
| [What makes a harness a harness](https://arxiv.org/abs/2606.10106) | 产品、运行中间层、评测 harness 等术语混用 | 强化正文对 Harness/Runtime/Workflow/评测脚手架的边界 |
| [Code as Agent Harness](https://arxiv.org/abs/2605.18747) | 代码作为推理、行动、环境建模和执行验证基底 | 作为 coding-agent harness 的新研究视角 |
| [Natural-Language Agent Harnesses](https://arxiv.org/abs/2603.25723) | 将 harness 逻辑表达为可执行自然语言对象 | 说明 harness 表示和可移植性是活跃研究问题 |
| [GATS: Graph-Augmented Tree Search](https://arxiv.org/abs/2607.08894) | 用显式 world model/树搜索减少 LLM 规划调用 | 作为搜索降本方向，不写成成熟标准 |

这些论文在资料核验时仍较新。正文不使用其单一 benchmark 数字制定生产阈值。

## Skills、工具与协议

- Anthropic, [`anthropics/skills`](https://github.com/anthropics/skills)：Skills 是包含 instructions、scripts、resources 的自包含目录，按需动态加载；仓库明确提示示例主要用于演示/教育，需要自行测试。
- [Agent Skills specification](https://agentskills.io/specification)：`SKILL.md`、必填 `name`/`description`、可选兼容性/metadata 等字段；实验字段以规范当前标记为准。
- Anthropic Engineering, [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)：能力打包与真实工作流的官方工程说明。
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification/latest)：Tools、Resources、Prompts 与 client/host/server 协议边界。MCP 连接能力，不替代宿主授权和业务 State。

## Runtime、协同和 Workflow 框架

- OpenAI, [OpenAI Agents SDK Python](https://github.com/openai/openai-agents-python) 与 [documentation](https://openai.github.io/openai-agents-python/)：Agents、tools/MCP、guardrails、human-in-the-loop、sessions、tracing、agents-as-tools、handoffs、sandbox agents。
  - [Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
  - [Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
  - [Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)
  - [Sessions](https://openai.github.io/openai-agents-python/sessions/)
  - [Tracing](https://openai.github.io/openai-agents-python/tracing/)
- LangGraph, [official repository](https://github.com/langchain-ai/langgraph) 与 [overview](https://docs.langchain.com/oss/python/langgraph/overview)：低层 stateful orchestration、durable execution、HITL、memory 和 tracing。
  - [Persistence / durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
  - [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- CrewAI, [official repository](https://github.com/crewAIInc/crewAI) 与 [documentation](https://docs.crewai.com/)：Crews 偏角色化自主协作，Flows 偏事件驱动、精确控制；Tasks、Roles/Agents 和 structured outputs/human review 的当前概念以官方文档为准。
  - [Agents](https://docs.crewai.com/en/concepts/agents)
  - [Tasks](https://docs.crewai.com/en/concepts/tasks)
  - [Flows](https://docs.crewai.com/en/concepts/flows)
- LlamaIndex, [Workflows](https://developers.llamaindex.ai/python/llamaagents/workflows/)：事件驱动、数据/RAG 取向的工作流参考。

框架映射只说明“某个公开概念可承载哪类 contract”。应用仍需定义 State owner、权限、幂等、停止和删除/保留策略。

## 可靠性、安全与观测

- OpenTelemetry, [Semantic conventions for generative AI systems](https://opentelemetry.io/docs/specs/semconv/gen-ai/)：GenAI trace/span 的标准化方向；具体字段状态可能演进。
- OWASP, [Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)：prompt injection、敏感信息、供应链、过度代理等风险分类。
- NIST, [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)：治理、测量、管理和剩余风险框架。
- Temporal, [Workflow execution](https://docs.temporal.io/workflow-execution) 与 [Event History](https://docs.temporal.io/workflow-execution/event)：durable workflow、replay 和外部 Activity 的工程参考。Temporal 不是 Memory 产品，也不是所有短任务的默认依赖。

## Agent 评测与近期研究

### 公开基准

- [SWE-bench](https://www.swebench.com/)：真实软件仓库 issue 修复。
- Mialon et al., [GAIA](https://arxiv.org/abs/2311.12983)：需要推理、工具和现实知识的通用助手任务。
- Liu et al., [AgentBench](https://arxiv.org/abs/2308.03688)：多种交互环境中的 Agent 评测。
- Zhou et al., [WebArena](https://arxiv.org/abs/2307.13854)：可执行网页环境。
- Yao et al., [τ-bench](https://arxiv.org/abs/2406.12045)：工具—Agent—用户交互与策略遵守。

### 2025–2026 研究提示

- [AgentGym2](https://arxiv.org/abs/2607.05174)：去理想化、带噪声和不完整输入的真实环境评测。
- [What Drives Interactive Improvement from Feedback?](https://arxiv.org/abs/2606.30774)：区分有效自然语言反馈、重复尝试和额外 test-time compute。
- [RobustFlow](https://arxiv.org/abs/2509.21834)：语义等价指令下自动生成 workflow 的一致性/鲁棒性。
- [Demystifying the Lifecycle of Failures in Platform-Orchestrated Agentic Workflows](https://arxiv.org/abs/2509.23735)：错误跨节点、工具和自然语言控制流传播的问题。
- [Sherlock: Reliable and Efficient Agentic Workflow Execution](https://arxiv.org/abs/2511.00330)：workflow 中细粒度验证与错误传播的研究方向。

这些来源用于设计更真实的故障集和因果对照，不替代组织自己的任务、权限和风险数据。

## 仓库内前置资料

- [[llm-basics/31-llm-capabilities-boundaries-and-agents|LLM 能力边界与 Agent]]：模型输出候选、运行时拥有循环控制权。
- [[context-engineering/00-overview|Context Engineering]]：Context pipeline 总览。
- [[context-engineering/13-tool-context|Tool Context]]：工具定义、结果和不可信数据怎样进入 Context。
- [[context-engineering/14-planning-context|Planning Context]]：计划、checkpoint 和完成审计。
- [[memory-and-state/00-overview|Memory 与 State]]：State/Memory/Event/Artifact 的总边界。
- [[memory-and-state/06-consistency-recovery|一致性、并发与恢复]]：CAS、幂等、checkpoint、replay 和 unknown 副作用。
- [[memory-and-state/09-evaluation-observability|Memory/State 评测与可观测性]]：状态与记忆层指标。
- [[prompt-engineering/04-reasoning-strategies|推理增强策略]]：Prompt、sampling、workflow 与 tool/runtime 的分层。
- [[prompt-engineering/13-decomposition-and-agent-workflows|任务拆解与 Agent 工作流]]：decomposition、workflow 和阶段契约。
- [[rag/08-agentic-rag|Agentic RAG]]：Router、查询规划和证据反馈在 RAG 中的具体形态。

## 本教程的工程推导

以下不是某篇论文或厂商的固定 API，而是把来源映射到统一 Loop 后给出的建议：

- Agent = 目标约束下的 State + Tools + Plan + Feedback 执行系统；
- 模型只提出候选，Harness 持有权限、真实 State、工具执行和停止权；
- ToolResult 使用 success/retryable/permanent/unknown 四类；
- 每种推理/协同模式都必须说明 State、feedback、budget 和 stop condition；
- 高风险控制流优先固定为 Workflow，局部长尾判断交给 Agent；
- Skill 是可发现、按需加载的能力包，不是权限；
- 结果与轨迹同时评测，并用同一数据集比较复杂模式的收益与成本。

这些建议应按业务风险、工具特性和组织基础设施调整，并通过 [[loop-engineering/10-evaluation-observability|评测与可观测性]] 中的发布门验证。
