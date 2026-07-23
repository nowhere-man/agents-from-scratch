---
title: Agent Run Contract
aliases:
  - Run Contract
  - Agent 运行契约
tags:
  - agents
  - harness
  - contract
  - state
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# Run Contract：先定义一次运行，再启动模型

> [!abstract] 本篇学习终点
> 你将能为一次 Agent run 定义稳定身份、actor/tenant、目标、成功标准、scope、能力、预算、版本和停止原因；能区分 run、turn、model request 与 tool call，并知道哪些字段必须由程序生成和校验。

## 为什么“帮我调研三家供应商”还不是可执行任务

这句话描述了意图，却没有说明：

- 当前用户是谁，能读哪些内部资料？
- “三家”具体是哪三家，价格要以哪个时间点为准？
- 能否登录网站、下载文件或调用付费 API？
- 最多运行多久、调用多少次模型和工具？
- 缺少一家数据时应该失败、部分交付还是询问用户？
- 什么证据才算完成，谁有权发布？

如果这些问题只留在自然语言 prompt 中，恢复、审计和测试都会依赖模型解释。**Run Contract** 把它们变成 Harness 可执行的入口数据。

## 四种不同粒度的身份

| 粒度 | 含义 | 示例 |
|---|---|---|
| `task_id` | 跨暂停和多次 run 的业务任务 | `vendor-report-43` |
| `run_id` | 一次具体执行尝试 | `run-20260723-7f2a` |
| `turn_id` | 一次 model→tool/answer 决策周期 | `turn-004` |
| `tool_call_id` / `operation_id` | 一次工具请求及外部副作用身份 | `run-...:vendor-a:v1` |

这些 ID 不能互相替代。多轮对话可以共享 `task_id`，每次恢复或重跑应有新的 `run_id`；外部幂等键则应表达同一个业务操作，即使它跨 run 重试也保持稳定。

## 一个最小 Contract

```yaml
schema_version: harness.run.v1
task_id: vendor-report-43
run_id: run-20260723-7f2a
actor:
  tenant_id: acme
  user_id: user-123
  roles: [researcher]
objective: 比较 Vendor A、B、C 的当前价格与可靠性证据
success_criteria:
  - 每家供应商至少有一个可回查的当前价格来源
  - 每个价格记录币种、版本或抓取时间
  - 无法验证的字段明确标为 unknown
scope:
  vendors: [vendor-a, vendor-b, vendor-c]
  data_classification: internal
  allowed_domains: [a.example, b.example, c.example]
capabilities:
  allowed: [web_read, artifact_write]
  approval_required: [authenticated_login, external_publish]
budgets:
  max_turns: 12
  max_model_requests: 16
  max_tool_calls: 20
  max_total_tokens: 80000
  deadline: 2026-07-23T18:00:00+08:00
state:
  expected_version: 12
  resume_from: checkpoint-12
output:
  schema: vendor_comparison.v2
  delivery: draft_only
```

Contract 应在模型调用之前由 ingress/Harness 校验。缺失身份、scope 冲突、schema 不支持或 deadline 已过时，应直接拒绝或要求澄清，不要先让模型“试试看”。

## 目标与成功标准不是一回事

`objective` 告诉系统要达成什么；`success_criteria` 告诉 Harness 如何验收。

“生成高质量报告”无法机械检查。更好的标准是：

- 三家供应商都有记录，缺失必须显式；
- 价格字段包含数值、币种、时间和 source artifact；
- 引用能定位到具体 evidence span；
- 报告未调用 `external_publish`；
- schema validator 与引用检查器通过。

模型可以评价语言质量，但完整性、字段、权限和工具轨迹应尽量由程序验证。

## Scope 要同时约束数据与动作

Scope 不只是允许哪些工具，还包括：

- **主体范围**：tenant、user、project、task；
- **对象范围**：允许访问的供应商、文件、数据库表、仓库；
- **动作范围**：read、write、delete、publish、execute；
- **网络范围**：域名、协议、端口和 egress；
- **数据范围**：敏感级别、地区、保留期限；
- **时间范围**：授权有效期和审批过期时间。

工具参数必须是 scope 的子集。模型请求 `web_read(url=evil.example)` 时，即使 `web_read` 工具本身可用，也应因目标域名越界而拒绝。

## Budget 是多维向量，不只是 token 上限

| Budget | 防止什么 | 超限后的典型动作 |
|---|---|---|
| turns/model requests | 反复思考或无效 retry | 停止、降级或人工升级 |
| tool calls | 工具循环和 fan-out 爆炸 | 阻止新调用，保留已完成结果 |
| tokens/cost | 成本失控 | 压缩、换模型、partial result |
| wall-clock deadline | 长时间占用与过期结果 | 取消下游调用并停止 |
| per-tool timeout | 单个依赖卡死 | 分类为 retryable/unknown |
| concurrency | 资源打满和供应商限流 | 排队或有界并发 |
| artifact/workspace size | 磁盘与 context 膨胀 | spill、清理或拒绝 |

多 Agent 特别容易漏算子树成本。父 Agent 的 token limit 不一定自动约束每个 worker；Contract 应定义预算是否共享、如何聚合，以及谁有权创建子任务。

## 停止原因必须是一等数据

不要只返回一段文本“已完成”。Harness 应保存机器可读的 `stop_reason`：

| Stop reason | 含义 | 是否可继续 |
|---|---|---|
| `completed` | success criteria 已通过 | 通常不需要 |
| `partial` | 交付了允许的部分结果 | 取决于用户决定 |
| `needs_input` | 缺少用户选择或材料 | 是，等待输入 |
| `approval_required` | 高风险动作等待审批 | 是，使用稳定 approval ID |
| `denied` | policy 明确拒绝 | 只有 scope/policy 改变后 |
| `budget_exhausted` | 预算耗尽 | 新 run 或追加预算 |
| `timeout` | 运行 deadline 到达 | 检查外部状态后决定 |
| `cancelled` | 用户或平台取消 | 先完成清理，再决定恢复 |
| `failed` | 永久错误或不变量破坏 | 修复后新 run |
| `unknown_external_state` | 副作用可能已发生 | 必须先 reconcile |

> [!important] “未知”不是“失败”
> 工具在请求发出后连接断开，系统无法确认外部动作是否发生。此时自动重试可能造成重复写入；正确状态是 `unknown_external_state`，先查询外部系统或使用幂等键 reconcile。

## Contract、State 与 Prompt 的版本

一次可恢复 run 至少要记录：

- Run Contract schema version；
- Agent definition / instruction version；
- model/provider 与关键参数；
- tool registry 和每个 tool schema version；
- State snapshot version；
- policy bundle version；
- output schema version。

恢复时如果新代码无法读取旧 schema，应明确迁移或拒绝，不要静默猜字段。Secret 只保存引用或 credential binding，不能直接进入 serialized run state、prompt 或 trace。

## Contract 的校验顺序

```text
解析 schema
→ 验证 actor 与 tenant
→ 验证 task/state 版本
→ 计算实际 scope 和 capability set
→ 校验 budgets/deadline
→ 绑定 policy、agent、tool 和 output 版本
→ 创建 run/trace
→ 才允许第一次 model request
```

这一顺序让非法请求在最便宜、最确定的位置失败。下一篇把已验证 Contract 放进真正的运行循环：[[harness/03-minimal-loop|最小 Agent Loop]]。
