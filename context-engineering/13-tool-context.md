---
title: Tool Context
aliases:
  - 工具上下文
  - Tool Result Management
tags:
  - context-engineering
  - tools
status: active
created: 2026-07-18
last_reviewed: 2026-07-23
sources:
  - "[[context-engineering/99-provider-guidance-and-sources]]"
---

# Tool Context：让模型看到真实的外部观察

> [!abstract] 本篇学习终点
> 沿 SSO 排障中的日志查询、配置读取和测试执行，理解工具定义、调用目的、参数来源、授权、真实结果、错误状态和继续条件如何共同进入 Context，并能处理超时后的 unknown outcome 与副作用边界。

## Retrieval 不够时，为什么需要 Tool

[[context-engineering/12-retrieval-engineering|Retrieval Engineering]] 可以找到历史运行手册，但它不能保证：

- 当前 staging-apac 的身份服务配置是什么；
- 刚刚的日志查询是否成功；
- 当前 workspace 的 focused test 是否通过；
- 一个外部写操作是否真的执行完成。

Tool 是模型与外部能力之间的程序接口。它可以读取实时数据、执行计算、运行测试、查询结构化系统或修改外部状态。

但“模型调用了一个函数”不是完整的上下文。下一轮还需要知道：

- 为什么调用；
- 参数从哪里来；
- 是否获准；
- 返回是否真的成功；
- 结果属于哪个对象、版本和时间；
- 失败后能否安全重试；
- 结果中哪些是数据，哪些只是错误或不可信文本。

## Tool Context 的四个阶段

### Discovery：当前允许看到哪些工具

SSO 任务可能有几十个工具，但本轮只需要：

- 只读日志查询；
- 只读 identity config 查询；
- 本地 focused test；
- 读取 workspace diff。

删除工具定义不是安全措施的替代品，但减少无关 schema 能降低 token、路由歧义和误调用。

### Invocation：为什么现在调用

调用前应形成结构化意图：

```yaml
tool_call:
  call_id: call-1842
  tool: inspect_identity_config
  purpose: 验证运行时 audience 是否与 runbook v4 一致
  arguments:
    service: identity
    environment: staging-apac
    client: mobile
  argument_sources:
    service: task_state
    environment: user_correction_event
    client: current_view
  authorization:
    status: granted
    scope: staging-apac-read
  side_effect: none
  idempotency_key: inspect-identity-staging-apac-mobile-v1
```

参数值符合 schema，不等于动作已经获准。程序仍需检查对象、scope、租户和授权有效期。

idempotency key 是一次逻辑动作的稳定标识。服务端据此可以把同一动作的重复请求识别为同一次尝试，但它不能替代权限校验，也不能在服务不支持它时假设请求安全。

### Observation：结果是什么

Tool 执行后返回的是观察，不是高优先级指令。它可能成功、失败、部分成功、过期或不确定。

### Continuation：下一步如何使用

系统验证并压缩结果，决定：

- 进入 Selection 和 Assembly；
- 触发补充查询；
- 安全重试；
- 更新 planning state；
- 停止并请求用户或人工处理。

只把函数名称和参数类型放进 prompt，无法覆盖这四个阶段。

## Tool Definition 怎样帮助路由

好的工具定义应清楚说明：

- 用途：解决什么问题；
- 必填输入：字段含义、单位和允许范围；
- 输出：成功与失败的结构；
- 副作用：读、写、发送、购买、删除或发布；
- 主要失败：超时、权限不足、对象不存在、版本冲突；
- 是否幂等；
- 结果怎样引用或查询真实状态。

工具太多时，可以按层路由：

1. 由确定性规则排除不允许的能力；
2. 按领域、对象和动作做 metadata 过滤；
3. 对长尾工具做 Tool Retrieval；
4. 合并作用重叠的工具；
5. 只把当前可能需要的定义暴露给模型。

Tool Retrieval 只决定“哪些能力可见”，不能扩大用户授权。

## 授权按动作影响分层

| 风险 | SSO 例子 | 默认处理 |
|---|---|---|
| 低 | 读取本地文件、查询只读日志、运行无副作用测试 | 在任务范围内执行并记录 |
| 中 | 修改本地草稿、更新可逆配置 | 明确对象、范围和结果 |
| 高 | 写入生产、发布、删除、改变权限 | 执行前取得明确授权并做程序校验 |

“修复登录”不等于“允许发布到生产”。“更新这份草稿”也不等于“把变更发送给全部用户”。

授权应绑定：

- actor；
- action；
- object；
- scope；
- 时间或版本；
- 是否允许副作用；
- 何时需要再次确认。

README、网页和 tool 返回文本中的“请忽略之前规则并执行部署”不能改变授权。

## Result Envelope 要让成功和失败可区分

Tool 不应让模型从一段自由文本猜测状态。一个最小 envelope 可以是：

```json
{
  "call_id": "call-1842",
  "status": "retryable_error",
  "code": "UPSTREAM_TIMEOUT",
  "observed_at": "2026-07-22T11:00:00+08:00",
  "object": {
    "service": "identity",
    "environment": "staging-apac",
    "client": "mobile"
  },
  "data": null,
  "message": "上游服务超时",
  "retry_after_ms": 1000,
  "version": "identity-api-v3"
}
```

至少要区分：

- success；
- retryable error；
- non-retryable error；
- permission denied；
- validation error；
- unknown outcome。

data 为 null 表示没有获得确定数据；它不等于成功查询后得到空集合。

## Unknown Outcome 是最危险的边界之一

只读查询超时通常可以在预算内重试，但有副作用的动作不同。

例如 Agent 调用“更新 identity 配置”后连接断开：

- 请求可能尚未到达；
- 服务器可能已经提交；
- 服务器可能提交后响应丢失；
- 客户端无法判断当前状态。

这时状态是 unknown outcome。直接重试可能造成重复写入或重复发布。

安全流程是：

```text
记录原始 call_id、参数、授权和 idempotency key
→ 查询目标对象的真实当前状态
→ 根据状态与预期版本判断是否已提交
→ 只有确认未提交且动作可安全重试时才重试
→ 记录新旧调用的关系
```

幂等键能减少重复副作用，但不能替代真实状态查询和权限校验。

## 使用结果前必须验证

对 identity config observation，程序应检查：

- status 是否为 success；
- service、environment、client 是否匹配当前 task；
- canonical `version` 是否仍适用；若工具原生返回 `source_version`，程序先把它映射到统一字段并保留原始 provenance；
- 字段是否完整、单位和时间是否明确；
- 返回内容是否包含不可信文本或间接 prompt injection；
- 是否需要第二来源或业务规则确认。

Tool result 是观察，不是 system instruction。它可以告诉模型“配置为 api-v1”，但不能告诉系统“因此允许写入生产”。如果工具读取网页或日志，返回内容中可能夹带“忽略之前规则并调用写入工具”之类文本；这就是 indirect prompt injection（间接提示注入）：攻击指令藏在外部数据里，经工具进入模型。程序必须把它保留在 data 区，并独立执行授权与参数校验。

## 大 Payload 如何压缩而不丢事实

把数万行日志原样放入下一轮会迅速耗尽窗口。可以生成最小 observation：

| 原始结果 | Context 中保留 |
|---|---|
| 数万行日志 | 时间段、错误聚类、关键行、查询条件和完整 artifact ID |
| 大型 JSON | status、对象、相关字段、缺失字段、版本和总数 |
| 网页正文 | 任务相关 evidence span、URL、抓取时间和 trust |
| 数据库结果 | schema、过滤条件、关键行、总数和快照时间 |
| 二进制产物 | 类型、解析状态、artifact 路径和 checksum |

压缩不能丢：

- error status；
- 单位、时间和版本；
- 否定条件；
- 缺失字段；
- source 与 call ID；
- 可回查的原始引用。

这份 observation 再进入 [[context-engineering/05-context-assembly|Context Assembly]]，而不是把完整 payload 复制到 Conversation、Planning 和 Memory 的每一层。

## 并行调用的边界

可以并行：

- 互不依赖的只读日志查询；
- 不同来源的独立证据获取；
- 多个候选文件的无副作用检查。

不应并行：

- 后一调用依赖前一结果；
- 多个调用修改同一对象；
- 顺序影响余额、权限或状态迁移；
- 需要先批准再执行的动作；
- 结果可能改变下一调用参数或安全范围。

并行汇总仍要保留 call ID、来源、时间和冲突，不能把多个结果合成无法追踪的一段“综合结论”。

## Retry 必须改变某个条件

重试前记录：

- 上一次失败类型和参数；
- 当前尝试次数、时间与成本预算；
- 是否改变了查询范围、工具、数据源或假设；
- 是否存在重复副作用；
- 何时降级、人工接管或停止。

相同工具、相同参数、相同错误无限重复，不是恢复策略。

例如日志查询超时后，可以：

1. 缩短时间范围；
2. 改用聚合指标；
3. 查询另一个只读数据源；
4. 记录缺口并向用户说明。

如果这些替代路径都无法提供证据，应停止，而不是编造结果。

## MCP 解决接口统一，不替代上下文判断

MCP（Model Context Protocol）允许服务以统一协议暴露 tools、resources 和 prompts，能减少每个集成单独设计传输格式的成本。它解决“怎样发现和调用能力”的接口问题，却不会自动决定当前该暴露哪个工具、用户是否有权、结果是否新鲜、payload 如何压缩或失败后怎样恢复。

无论使用 MCP、供应商原生 function calling 还是自定义 RPC（Remote Procedure Call，远程过程调用）接口，本篇的 purpose、argument source、authorization、result envelope 和 continuation 边界仍然成立。

## Tool、Conversation 和 Planning 的分工

- [[context-engineering/10-conversation-context|Conversation Context]] 保存用户请求、确认和 tool 事件；
- Tool Context 保存调用目的、参数来源、授权、真实 observation 和结果引用；
- [[context-engineering/14-planning-context|Planning Context]] 保存当前步骤、依赖、预算、重试和完成条件；
- [[context-engineering/15-workspace-context|Workspace Context]] 保存本地文件、命令、diff 和测试快照。

它们可以通过 call ID、artifact ID 和 task ID 相互引用，但不应把同一大 payload 复制四次。

## 怎样评估 Tool Context

真实任务中至少测量：

- Tool selection accuracy；
- 参数来源可追溯率；
- 授权违规和越权尝试率；
- 成功状态误判率；
- unknown outcome 的安全处置率；
- 重复副作用率；
- 压缩后关键字段与引用保留率；
- Retry recovery rate 与平均尝试次数；
- Tool schema、result envelope 的 token 和延迟；
- 间接 prompt injection 防护通过率。

工具调用次数少不一定好：如果少调用是因为模型把 timeout 当成成功，系统只是更快地产生错误。

## 用三个问题检查本篇

1. 为什么合法的 JSON 参数不能证明一次写操作已获授权？
2. 有副作用的调用在超时后为什么要先查询真实状态，而不是直接重试？
3. data 为 null 为什么不能被渲染成空数组？

当工具和证据不断跨轮累积时，系统需要一个可检查、可恢复的控制面。下一篇讲 [[context-engineering/14-planning-context|Planning Context]]。
