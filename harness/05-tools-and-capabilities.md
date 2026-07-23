---
title: Tools 与 Capabilities
aliases:
  - Agent Tools
  - Tool Execution Lifecycle
  - Agent Capabilities
tags:
  - agents
  - harness
  - tools
  - mcp
  - security
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# Tools 与 Capabilities：从“模型会调用”到“系统允许执行”

> [!abstract] 本篇学习终点
> 你将能把 tool discovery、selection、validation、approval、invocation、observation 和 commit 分开；能设计 capability 与最小权限，正确处理幂等、unknown、并发和大结果，并理解 Model Context Protocol（MCP，模型上下文协议）解决了集成协议但没有替你完成授权。

## Tool schema 只是菜单，不是通行证

向模型暴露：

```json
{
  "name": "fetch_vendor_price",
  "parameters": {
    "vendor": {"type": "string"}
  }
}
```

只说明模型可以提出这种请求。真正执行前仍要知道：当前 actor 能否访问该 vendor、是否允许登录、调用是否收费、参数是否命中 allowlist、工具版本是否匹配，以及本次业务操作是否已执行过。

## 七阶段工具生命周期

```text
1. discovery      本轮哪些工具对模型可见
2. selection      模型提出 tool call candidate
3. validation     schema、版本、scope、预算、业务规则
4. approval       必要时持久化等待 approve/edit/reject
5. invocation     绑定身份、幂等键、timeout、cancel 后真实调用
6. observation    success/retryable/permanent/unknown + artifact
7. commit         event、effect ledger、state、trace
```

恢复时不能重新从第 1 步“猜一次”。稳定的 `tool_call_id`、approval ID 和 operation ID 要保留，已完成调用直接复用结果，未知调用先 reconcile。

## Tool Registry 应保存什么

一个生产 ToolSpec 至少包括：

| 字段 | 作用 |
|---|---|
| name + version | 稳定身份与兼容边界 |
| input/output schema | 参数重建和结果验证 |
| description | 帮助模型正确选择，不承担权限 |
| required capabilities/scopes | 运行前确定性授权 |
| side-effect class | read / idempotent write / non-idempotent write |
| timeout/retry policy | 避免每层自行重试 |
| concurrency/rate limits | 保护依赖与预算 |
| approval policy | 哪些参数组合需要人审 |
| idempotency/reconcile hooks | crash 后确认外部效果 |
| data classification | Context、trace 与留存策略 |

Tool description 应具体说明输入、限制、失败和何时使用；但不要把 secret、内部 policy 细节或“模型可自行放宽”的权限写进描述。

## Capability 比工具名更接近真实授权

工具名通常太粗。例如 `database` 可能同时代表读公开表、读客户数据和删除记录。Capability 应包含资源与动作：

```text
db:pricing:read
artifact:task/vendor-report-43:write
web:domains[a.example,b.example]:read
publish:external:request-approval
```

Harness 先根据 actor 和 Run Contract 计算 capability set，再过滤可见工具；Tool adapter 仍要对具体对象做最终授权。Capability token 若存在，应短期、最小 scope、绑定 audience/actor/run，不能把上游 bearer token 原样透传给下游。

## MCP 的位置：标准化连接，不替代控制面

MCP 将 Host、Client 与 Server 的工具/资源/提示交换标准化。对 Harness 来说：

- MCP Server 提供候选 tools/resources；
- MCP Client 负责协议、连接和结果转换；
- Host/Harness 仍负责展示、选择、用户同意、授权、timeout、校验、审计和结果进入 Context 的方式。

> [!warning] “连接成功”不等于“授权完成”
> MCP 安全实践明确关注 confused deputy、token passthrough、SSRF（Server-Side Request Forgery，服务端请求伪造）、session hijacking 和 scope。Proxy server 需要 per-client consent；redirect URI、OAuth state 和 scope 必须严格验证。不要因 server 已登录就允许任意 Agent 继承全部权限。

Tools、Resources、Prompts 也不等于同一信任级别。Resource 与 tool result 都可能包含间接提示注入；Prompt 模板是可复用内容，不应自动获得平台 system policy 的权力。

## 外部结果的四态模型

| 状态 | 含义 | 默认处理 |
|---|---|---|
| `success` | 已确认动作完成且结果通过校验 | 提交 State，缓存可复用结果 |
| `retryable_error` | 明确未成功，且同语义调用可安全重试 | 有界退避，消耗 retry budget |
| `permanent_error` | 参数、权限或业务条件不允许 | 不重试，重新规划或停止 |
| `unknown` | 请求可能已产生效果，但无法确认 | 冻结同一副作用，先 reconcile |

HTTP timeout 不是天然 retryable。GET 一般较安全；创建订单、发消息或扣款在响应丢失后可能已经成功。

## Idempotency 与 reconcile

**幂等（idempotency）**指同一个业务操作即使因重试被请求多次，也只产生一次预期效果；**reconcile** 指崩溃后向外部系统对账，确认效果究竟是否发生。

外部写操作应使用业务语义稳定的幂等键：

```text
{task_id}:{tool}:{target}:{desired_effect_version}
vendor-report-43:save-artifact:vendor-a-price:v2
```

重试同一业务效果沿用同一 key；用户明确要求新的动作才生成新 key。Tool-effect ledger 记录：

```yaml
operation_id: vendor-report-43:publish:draft:v1
tool_call_id: call-017
status: started
external_id: null
idempotency_key: vendor-report-43:publish:draft:v1
started_at: 2026-07-23T11:02:00+08:00
```

崩溃后若只有 `started`，Reconciler 使用幂等键、外部 ID 或查询 API 确认：已完成则补写 completed；明确未发生才允许重试；仍无法确认就暂停人工处理。

## Approval 是持久化状态，不是弹窗

高风险 tool call 应生成稳定 approval request：

```yaml
approval_id: approval-91
run_id: run-7f2a
tool: authenticated_login@v2
arguments_hash: sha256:...
requested_scope: vendor-b/account/read
expires_at: 2026-07-23T12:00:00+08:00
choices: [approve, edit, reject]
```

恢复时必须验证 approval 仍绑定同一 tool version、参数 hash、actor 和 scope。参数变化后旧批准失效。“Don't ask again” 规则也应有资源、动作、时限和撤销能力，不能变成全局永久放行。

## 并行工具调用

并行适合彼此独立的只读检索，但需要：

- 有界并发和共享 budget；
- 保持模型原始 call 顺序与结果 identity；
- sibling failure 隔离，已成功结果不被抹掉；
- 取消时等待每个 sibling 清理；
- 写操作若共享对象，使用锁、compare-and-set（CAS）或 workflow 依赖显式串行化。

不要仅因模型一次返回多个 tool calls 就全部无界 `gather`。

## 大工具结果怎样返回

数万行网页或日志不应永久进入 message history。推荐：

```text
raw result
→ 完整保存 Artifact（hash、source、timestamp）
→ 结构化解析与安全检查
→ 返回 status + 关键字段 + 缺失项 + artifact_ref
→ 下一轮按需检索 evidence span
```

截断时保留错误尾部、总量、是否截断和回查方式。压缩结果不能丢单位、时间、版本、否定条件和 error status。

## 工具设计自检

- [ ] discovery、approval 与 invocation 已分离。
- [ ] 输入/输出 schema 与真实类型使用同一版本。
- [ ] actor、resource、action 在工具内再次授权。
- [ ] side-effect class、timeout、retry owner 明确。
- [ ] 有 operation ID、幂等键和 reconcile 路径。
- [ ] secret 不进入参数回显、State 或 trace。
- [ ] 并发有上限，取消会等待清理。
- [ ] 原始大结果存 Artifact，Context 只放必要 Observation。

当一个 Agent 和几个工具已经不足以表达固定分支或并行关系时，才进入下一层：[[harness/06-orchestration-patterns|Agent 编排模式与选择]]。
