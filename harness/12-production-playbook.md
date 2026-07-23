---
title: Agent Harness 生产落地手册
aliases:
  - Harness Production Playbook
  - Agent Runtime Checklist
tags:
  - agents
  - harness
  - production
  - reliability
  - security
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# Harness 生产落地手册：按真实失败逐层增加控制

> [!abstract] 本篇学习终点
> 你将能从普通函数、单次模型调用、bounded loop 逐步演进到可恢复和平台级 Harness；能使用上线检查表、SLO、canary、kill switch 和 incident response 控制风险，并识别常见的过度设计与假安全。

## 第一原则：能不用 Agent，就先不用 Agent

如果输入输出固定、规则可枚举、外部动作确定，普通代码通常更便宜、更快、更容易证明正确。使用 Agent 的合理理由是任务包含开放语义判断，例如：从多种未知网页结构中寻找证据、决定下一条检索路径或综合互相冲突的资料。

即使需要 Agent，也应把确定部分留在代码中：schema、权限、计算、排序、事务、完成检查和发布流程。

## 五级成熟度

### Level 0：确定性函数

```text
input → validate → function/tool → output
```

适合固定转换和业务规则。先建立测试、指标与错误分类。

### Level 1：单次模型调用

增加明确 task contract、最小 prompt、structured output 和 eval。模型不直接执行副作用。

完成标准：输出 schema 可验证，失败能定位到 prompt/context/model，而不是靠人工猜。

### Level 2：Bounded Agent Loop

增加 Run Contract、tool registry、policy gate、turn/tool/token/deadline budget、四态 Observation 和 stop reason。

完成标准：模型无法绕过工具权限；无限 loop 与成本失控被硬上限阻止。

### Level 3：Recoverable Runtime

增加 Event、versioned State、checkpoint、effect ledger、idempotency/reconcile、HITL pause/resume、cancellation cleanup 和 fault injection。

完成标准：任一边界 crash 后不重复副作用，不把 unknown 误写成 success。

### Level 4：Workflow / Multi-Agent

仅在固定分支、并行、专家隔离或消息型协作确有收益时，增加 graph、worker、handoff 或 actor runtime。

完成标准：每个子任务有自包含 contract、独立 budget、failure isolation 与 trace lineage；多 Agent 的质量收益超过成本与复杂度。

### Level 5：Platform Harness

当多个团队/租户共享能力时，再统一 sandbox、credential broker、network policy、policy service、registry、observability、eval、deployment、quota 和 incident response。

完成标准：平台默认安全，业务团队不需要每次重新实现路径 containment、secret handling 或 trace redaction。

## MVP 的最小安全闭环

一个会访问外部资料的研究 Agent，至少要有：

- stable task/run/tool-call identity；
- actor、tenant、scope 与 allowed capabilities；
- strict action/output schema；
- model candidate 与真实 tool execution 分离；
- `success/retryable/permanent/unknown`；
- turn/tool/token/time budget；
- 原始结果 Artifact + provenance；
- stop reason；
- run/turn/tool/policy trace；
- 代表性 eval set。

缺少其中一项时，先补闭环，不急着增加 planning、memory 或多 Agent。

## 上线前检查表

### Contract 与状态

- [ ] task/run/turn/tool-call/approval ID 的粒度明确。
- [ ] objective、success criteria、scope、budget、deadline 和 stop reasons 结构化。
- [ ] State、tool、policy、agent 和 output schema 有版本。
- [ ] secret 只保存引用，不进入 serialized State。
- [ ] 并发提交使用 transaction/CAS，不做 last-write-wins 覆盖。

### Context 与模型

- [ ] control、task、state、memory、evidence 和 tool result 有分区与 provenance。
- [ ] 控制规则超预算时 fail closed，不静默裁掉。
- [ ] Prompt/agent/model version 可追踪和回滚。
- [ ] Streaming 策略与敏感输出风险匹配。
- [ ] 模型输出始终作为候选处理。

### Tools 与 MCP

- [ ] discovery、approval、invocation 和 result commit 分离。
- [ ] 每个工具声明 schema、required scope、side-effect class 和 timeout owner。
- [ ] 写操作有幂等键或 reconcile 路径。
- [ ] MCP OAuth/consent/scope/token/SSRF/session 边界已实现。
- [ ] 大结果 spill 到 Artifact，返回值标明截断与回查引用。

### Durability

- [ ] safe checkpoint 不包含孤立 tool call/message。
- [ ] started 无 terminal effect 被识别为 unknown。
- [ ] resume 保留 tool/approval identity，已完成动作不重复。
- [ ] timeout、retry、cancel 和 cleanup 在每层有上限。
- [ ] 旧 checkpoint 的迁移/拒绝策略已定义。

### Sandbox 与多租户

- [ ] workspace 按 tenant/task/run 隔离并有 TTL。
- [ ] canonical path、symlink、archive、mount traversal 有测试。
- [ ] Shell denylist 未被当作硬 sandbox。
- [ ] 子进程最小 env、短期 credential、network default-deny。
- [ ] background process、临时文件和 browser session 会清理。

### Observability 与 Eval

- [ ] trace 覆盖 context、model、policy、tool、commit、stop 和 recovery。
- [ ] 原始内容默认不采集或经过分级脱敏。
- [ ] exporter 故障不会篡改业务结果。
- [ ] 同时评 final outcome、trajectory、State/recovery、security 和 cost。
- [ ] crash、timeout、CAS、unknown、approval replay、路径/网络逃逸有 fault tests。

## SLO 应围绕用户结果和运行不变量

不要只监控 API uptime。一个 Harness 的 SLO 可以包括：

| 目标 | 示例指标 |
|---|---|
| 正确完成 | 可验证任务成功率、引用覆盖率 |
| 可控成本 | 每成功任务 p50/p95 成本、budget exhaustion rate |
| 安全 | 未授权高风险工具执行数 = 0、跨租户泄露数 = 0 |
| 可恢复 | crash-resume 重复副作用率 = 0 |
| 可运维 | unknown effect reconcile p95 时长、人工积压 |
| 可停止 | cancel 后残留进程/workspace 数 = 0 |
| 可解释 | 关键动作具有 actor、policy、tool、source 与 state version |

阈值应基于业务风险和 baseline，不要复制别人的数字。

## 发布流程

```text
离线 eval
→ replay 历史 traces
→ shadow（不执行副作用）
→ 内部用户 + 只读工具
→ 小流量 canary
→ 逐步开放写能力/自动审批
→ 全量，但保留 kill switch 与回滚
```

模型、prompt、tool schema、policy 和 workflow 都应独立版本化。每次发布尽量只改变一个主要变量，才能判断性能变化来自哪里。

## Kill switch 与降级

平台至少能：

- 禁用某个 tool/version、MCP server、agent 或 model；
- 把写能力降级为 draft/approval-only；
- 降低并发、turn 和 cost budget；
- 切换到只读或 deterministic workflow；
- 停止新 run，同时允许已有 run 进入安全 checkpoint；
- 撤销 credential 与“don't ask again”规则。

Kill switch 本身也要有授权、审计和演练。

## Incident response

发生误调用、泄露或重复副作用时：

1. 立即冻结相关 tool/capability/credential；
2. 用 task/run/tool-call/operation ID 确定影响范围；
3. 保存必要 Artifact 与 trace，限制访问；
4. reconcile 外部状态，执行补偿或人工修复；
5. 通知受影响方和责任人；
6. 把事故转成回归样例与 fault test；
7. 更新 policy、runbook、SLO 和发布门，而不只改 prompt。

NIST AI RMF 的 Govern/Map/Measure/Manage 可作为组织层结构：先明确 owner 与风险容忍度，再描述部署场景，测量实际行为，最后持续监控、override、停用和恢复。

## 十个常见反模式

1. 把 Harness 当成一个超长 system prompt；
2. 模型自由文本直接修改 State；
3. 只校验 JSON，不校验真实对象与权限；
4. 所有异常统一自动重试；
5. Timeout 被当成明确失败；
6. 用聊天记录代替 checkpoint/effect ledger；
7. 把 command denylist 当 sandbox；
8. 为固定流程引入 supervisor 模型；
9. 只评最终答案，不评工具轨迹和副作用；
10. 一开始就上多 Agent、分布式 runtime 和平台抽象。

## 最后回到一个判断

一个 Harness 是否成熟，不看它集成了多少模型、工具或 Agent，而看它能否对每个动作回答：

```text
谁请求的？
为什么允许？
用了哪个版本和预算？
外部世界实际发生了什么？
结果怎样进入 State？
失败或崩溃后从哪里继续？
什么时候以及为什么停止？
```

如果这些答案能从 Contract、State、ledger、Artifact 和 trace 中被验证，模型才真正拥有了一副可上线的运行身体。

所有版本敏感依据与官方链接见 [[harness/99-sources|资料与来源]]。
