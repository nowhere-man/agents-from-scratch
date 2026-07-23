---
title: Agent Harness 可观测性与评测
aliases:
  - Agent Observability
  - Agent Evaluation
  - Harness Tracing
tags:
  - agents
  - harness
  - observability
  - evaluation
  - opentelemetry
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# 可观测性与评测：不仅看最后一句答得像不像

> [!abstract] 本篇学习终点
> 你将能设计 run→turn→model/tool/policy/commit 的 trace，选择默认安全的记录字段；能分别评最终结果、trajectory、工具、State、恢复、安全和成本，并通过 fault injection 证明 Harness 在失败条件下仍保持不变量。

## 最终报告正确，不代表运行过程安全

研究 Agent 可能生成一份看起来正确的报告，但过程中：

- 访问了未授权域名，只是没有把内容写进最终答案；
- 同一个付费 API 重试了八次；
- 引用来自旧版本网页；
- worker crash 后重复创建了外部 job；
- output guard 拦截了敏感内容，但 partial stream 已经发出。

只评最终文本看不见这些问题。Agent 系统至少有“结果质量”和“运行轨迹正确性”两条轴。

## Trace 的推荐层级

```text
run / invoke_agent
├─ load_state
├─ build_context
│  ├─ retrieve_memory
│  └─ resolve_artifacts
├─ turn-1
│  ├─ model_request
│  ├─ validate_candidate
│  ├─ policy_check
│  ├─ execute_tool
│  └─ commit_state
├─ turn-2
│  ├─ plan
│  └─ ...
└─ finalize / stop_reason
```

多 Agent 时，worker run 应通过 parent/linked span 关联，同时保留自己的 run identity 和 budget。

## OpenTelemetry GenAI 语义的使用方式

截至 2026-07-23，OpenTelemetry GenAI semantic conventions 已迁移到独立仓库，Agent spans 仍标记为 **Development**。当前 operation 包括：

- `create_agent`
- `invoke_agent`
- `invoke_workflow`
- `plan`
- `execute_tool`

这提供了跨框架的命名起点，但不能假设字段永久稳定。内部 trace schema 应有版本和适配层。

## 默认记录什么

推荐默认记录低敏感、可聚合字段：

| 类别 | 字段示例 |
|---|---|
| Identity | task/run/turn/tool-call/trace ID，agent/tool/workflow version |
| Operation | operation name、provider、model、tool、node |
| State | input/expected/result version、checkpoint ID、stop reason |
| Policy | policy version、verdict、reason code、approval ID |
| Reliability | status、error type、attempt、timeout、unknown/reconcile |
| Usage | token、tool calls、cost、latency、queue time |
| Context | 各分区 token、selected/rejected count、artifact refs |
| Security | actor、scope hash、sandbox/network policy version |

System instructions、input/output messages、tool definitions、arguments/results 和原始异常内容都可能含敏感数据。OpenTelemetry 将多类内容字段设为 opt-in；即使关闭内容采集，也要审计 exception、log、traceback 和 exporter 是否泄露原文。

> [!important] Trace 不是第二份无限期聊天数据库
> 先定义数据分类、访问控制、采样、脱敏和留存。必要的调查证据可保存在受控 Artifact Store，trace 只保存引用和安全摘要。

## Exporter 故障不能改变业务真值

Trace processor/exporter 超时或后端不可用时：

- 不应把已成功的工具动作报告为失败；
- 不应阻塞主 loop 到超过业务 deadline；
- 应有有界队列、丢弃/降级指标和本地缓冲策略；
- 必要的审计若属于合规强制项，应在 Run Contract 中明确 fail-open 或 fail-closed，而不是偶然行为。

## 六层 Eval

### 1. Final outcome

报告字段是否完整、事实是否正确、引用是否支持结论、格式和语言是否合格。

### 2. Trajectory 与 tool use

是否选择了正确工具、顺序是否合理、是否出现多余调用、是否绕过必需步骤。Google ADK 等当前评测文档也明确区分 trajectory/tool use 与 final response。

### 3. State 与 completion

只有真实成功 Observation 才完成 step；unknown 没有被写成 success；并行结果没有覆盖；stop reason 与 pending work 一致。

### 4. Recovery

Crash/resume 后不重复副作用，预算和 turn 不重复计数，safe checkpoint 可继续，旧 schema 能迁移或明确拒绝。

### 5. Policy 与 security

越权工具、间接提示注入、路径逃逸、SSRF、secret exfiltration、approval replay 和跨租户访问被阻止。

### 6. Efficiency 与 operations

成功率、p50/p95 latency、token/cost、tool error rate、approval wait、reconcile rate、loop length 与资源使用是否达标。

## 不要把理想轨迹写得过死

开放研究任务可能有多条合理路径。Trajectory eval 可分层：

- **必须发生**：三家来源都经过当前性检查；发布前必须人审。
- **禁止发生**：访问未授权域名、调用发布工具、引用无来源数据。
- **允许集合**：搜索→抓取与直接 API 查询都可以。
- **效率偏好**：避免重复抓同一版本；独立来源可并行。

这样既保留 Agent 灵活性，又能验证关键不变量。

## LLM-as-Judge 的正确位置

Judge 适合评价语义覆盖、写作质量和证据是否支持结论，但要：

- 用人工标注样本校准；
- 固定 rubric、judge model/version 和输入边界；
- 与确定性 schema、权限和状态检查分开；
- 对关键决策使用 pairwise、人审或多个独立信号；
- 记录 judge 自身成本、偏差和失败。

不要让 judge 决定真实权限或外部副作用是否成功。

## Fault injection 矩阵

| 注入点 | 预期不变量 |
|---|---|
| model 429/timeout | 有界 retry，budget 正确，trace 完整 |
| 非法 tool JSON | 不执行工具，结构化反馈或失败 |
| tool 响应在副作用后丢失 | 状态为 unknown，不盲重试 |
| State CAS 冲突 | 不覆盖新版本，重读或重新规划 |
| stream 中途取消 | partial 暴露可知，资源完成 cleanup |
| exporter 崩溃 | 业务结果不被篡改 |
| worker 部分失败 | sibling 成功结果保留，父级正确汇总 |
| sandbox 路径/网络逃逸 | 在硬边界拒绝并留下 reason code |
| approval 过期或参数改变 | 旧 approval 不可重放 |

每个故障都应在自动测试里验证 State、effect ledger、trace 与外部 mock，而不只是检查函数有没有抛异常。

## 生产指标与 SLO 示例

SLO（Service-Level Objective，服务等级目标）把“系统应该多可靠”变成可测量目标，而不只是监控图上的曲线。

- 任务成功率与 partial/needs-input 分布；
- 未经批准的高风险工具执行数必须为 0；
- unknown external effects 的发现、reconcile 时长和人工积压；
- crash-resume 后重复副作用率必须为 0；
- p95 run latency、model/tool latency 和 approval wait；
- 每成功任务成本、turn/tool 数和 context cache 命中；
- 引用覆盖率、过期证据率和 policy false-positive；
- cancellation 后残留进程/workspace 数必须为 0。

下一篇把这些稳定原语映射到当前框架：[[harness/10-framework-map|主流 Harness 与 Runtime 框架地图]]。
