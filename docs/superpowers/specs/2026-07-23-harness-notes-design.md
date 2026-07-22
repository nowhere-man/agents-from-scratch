# Agent Harness 工程笔记设计

## 目标

在 `harness/` 中创建一套面向 Agent 开发者、可在 Obsidian 中按顺序阅读的课程，回答三个问题：

1. Harness 在 Agent 系统中究竟拥有哪一部分控制权？
2. 常见 harness 形态各自解决什么问题，什么时候该换一种形态？
3. 怎样把模型、上下文、工具、状态、策略、恢复、观测和评测组合成可上线的运行时？

默认读者已经读过部分 `context-engineering/`、`prompt-engineering/` 和 `memory-and-state/`，但正文仍会在首次使用处解释关键术语。

## 默认假设与边界

用户没有指定贯穿案例，因此采用研究 Agent 作为默认锚点：它要跨多个来源收集供应商价格、处理不可信网页、比较证据并生成报告；期间可能发生超时、并发、目标修改、人工审批和进程崩溃。如果用户后来选择 Coding Agent，案例层可以替换，Harness Contract 和章节结构不变。

本系列负责运行时控制边界，不重复已有系列的底层主题：

- `context-engineering/` 负责信息如何被发现、选择、压缩和组装；本系列解释 harness 何时调用这些组件、预算超限如何阻断或降级。
- `memory-and-state/` 负责 State/Memory 的权威数据模型和生命周期；本系列解释 harness 如何读取版本、提交 observation、恢复和处理冲突。
- `prompt-engineering/` 负责任务契约、结构化输出和工具授权；本系列解释这些契约怎样成为运行时可执行的 policy gate。

## 核心定义

Harness 是包围模型调用的确定性运行时：它接收输入和当前执行上下文，构造模型可见的请求，验证模型产生的候选，执行获准的工具，记录真实 observation，提交状态，并决定继续、暂停、重试、升级或停止。

模型可以提出下一步，但不拥有循环控制权、授权、事实状态或外部副作用的最终确认权。Harness 不是“更长的 prompt”，也不等于某一个框架；它是一组可替换的控制面与适配器。

## 贯穿数据流

```text
外部输入
→ Run Contract / scope / budget
→ 读取 State、Memory、Workspace 和证据
→ Context Builder 生成有预算的 packet
→ Model Adapter 返回结构化候选
→ Parser + Validator + Policy Gate
→ Tool/Agent/Workflow 执行
→ Observation / error / unknown
→ Event + State commit + trace
→ stop / retry / pause / handoff / next turn
```

每一箭头都要说明 owner、输入输出、失败状态和是否可重试。`Context` 是本轮视图；`State`、`Memory`、`Artifact` 和外部系统仍由各自 owner 管理。

## 备选组织方式

### 方案 A：按框架逐个介绍

优点是容易列出产品，缺点是 API 变化快、读者难以判断边界。放弃作为主线，只保留最后的映射表。

### 方案 B：只讲一个手写 ReAct loop

优点是直观，缺点是无法解释 graph、durable workflow、multi-agent 和平台级治理何时出现。作为参考实现的一部分，而不是全系列结构。

### 方案 C：先讲 Harness Contract，再按压力演进（推荐）

先用一个最小 loop 建立控制权和不变量，再从真实压力引出 context、工具策略、编排、持久执行、隔离、可观测性和生产治理，最后把 LangGraph、OpenAI Agents SDK、Google ADK、PydanticAI、Microsoft Agent Framework、Temporal、MCP 等映射回原语。这样既能讲清机制，也能覆盖当前实践。

## 目录与职责

| 文件 | 学习职责 |
|---|---|
| `00-overview.md` | 学习终点、案例、数据流和阅读路线 |
| `01-boundaries.md` | Harness、Agent、Model、Runtime、Orchestrator、Workflow、Platform 的边界 |
| `02-run-contract.md` | Run/turn contract、输入输出 schema、预算、scope、stop reason |
| `03-minimal-loop.md` | 手写最小 loop：think/act/observe 的确定性外壳 |
| `04-context-and-policy.md` | Context Builder、提示版本、策略层、guardrail、结构化输出和拒绝路径 |
| `05-tools-and-capabilities.md` | 工具注册、schema、权限、能力 token、MCP、审批、沙箱和不可信结果 |
| `06-orchestration-patterns.md` | ReAct、plan-execute、graph、supervisor-worker、handoff、event-driven 的取舍 |
| `07-durable-runtime.md` | 超时、取消、重试、幂等、checkpoint、replay、human pause 和 durable workflow |
| `08-workspace-and-isolation.md` | Coding/数据型 Agent 的 workspace、进程、网络、文件和租户隔离 |
| `09-observability-and-evaluation.md` | trace/span、指标、轨迹评测、故障注入、成本和质量门 |
| `10-framework-map.md` | 把主流 SDK/框架/平台映射到 Contract，不把产品名当定义 |
| `11-reference-implementation.md` | Python + Protocol 的最小 harness，展示验证、工具、停止和恢复 |
| `12-production-playbook.md` | MVP→生产路线、SLO、反模式、迁移和上线检查表 |
| `99-sources.md` | 官方文档、规范、论文和版本敏感说明 |

## 最佳实践证据策略

正文只把跨实现稳定的原则写成规范性建议；框架特有行为放进映射和来源附录，并标注版本/preview 边界。重点核对：

- OpenAI Agents SDK/Responses 的 tool、guardrail、handoff、session、tracing 和 state ownership；
- LangGraph 的 persistence、interrupt、durable execution 与 store/checkpointer 边界；
- Google ADK 的 callbacks/plugins、session/state/memory 和 evaluation；
- PydanticAI、Microsoft Agent Framework 与 Temporal 的 durable/typed runtime 原语；
- MCP 的工具/资源/提示边界与授权责任；
- OpenTelemetry GenAI trace 语义、OWASP/NIST 的 Agent 安全风险与治理建议。

若官方资料之间存在差异，正文只抽取共同语义，并在 `99-sources.md` 记录差异；不把“最新”理解为某个产品 API 永久稳定。

## 参考实现与验证

参考实现不调用真实供应商，使用 Protocol/伪适配器展示：

- 每个 run 有稳定 ID、scope、预算和 stop reason；
- 模型输出必须先过 schema、权限和状态版本检查；
- 工具结果区分 success、retryable、permanent、unknown；
- 外部副作用使用幂等键和 reconcile；
- trace 记录 selected/rejected context、tool status、版本和成本；
- 故障测试覆盖超时、重复消息、取消、崩溃、CAS 冲突和越权输入。

验证包括 frontmatter、wikilink、代码围栏、Python 语法、控制字符、外链和初学者通读；Obsidian Reading View 若无法在当前环境启动，则明确记录为人工待确认项。

## 自我审查结论

- 没有把 Harness 写成“框架清单”；所有产品都必须回到 Contract、owner 和失败边界。
- 没有把 Memory/State 重新实现；只建立读取、提交和恢复接口。
- Coding Agent 只作为隔离章节和变体，不让 workspace 细节吞掉通用运行时主线。
- 参考实现保持教学规模，生产建议集中在 playbook，避免把伪代码误当 SDK 复制品。
