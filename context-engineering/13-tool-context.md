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
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
---

# Tool Context

> [!important] 一句话核心
> Tool Context 不只是函数 schema，而是模型选择工具、生成参数、理解结果和继续任务所需的完整信息；它必须保留调用目的、参数来源、授权、真实状态、错误和可回查结果。

## Tool Context 的四个阶段

1. **Discovery**：当前任务允许使用哪些工具。
2. **Invocation**：为什么调用、参数从哪里来、是否获得授权。
3. **Observation**：工具是否成功、返回什么、来源和时间是什么。
4. **Continuation**：怎样把结果压缩并用于下一步，何时重试或停止。

只定义函数名称和参数类型，无法解决工具过多、结果不可信、重复副作用和窗口膨胀。

## Tool Definition Selection

工具数量较多时，不应把全部定义永久放进每次请求。可以先根据任务选择候选工具：

- 使用确定性路由排除不允许的能力。
- 按领域、对象和动作做 metadata 过滤。
- 对大量长尾工具使用 Tool Retrieval。
- 合并功能重叠的工具，减少路由歧义。
- 保留清晰的用途、输入、输出、副作用和失败说明。

Tool Retrieval 只决定“哪些定义可见”，不能扩大用户授权。

## Invocation Context

调用前保存：

```yaml
tool_call:
  call_id: call-1842
  tool: update_issue
  purpose: 根据已批准方案更新 issue 描述
  arguments:
    issue_id: 42
    body_ref: draft-v3
  argument_sources:
    issue_id: user_request
    body_ref: approved_artifact
  authorization:
    status: granted
    scope: issue-42
  idempotency_key: update-issue-42-v3
```

参数值合法不代表动作获得授权。涉及外部写入时，授权、对象和范围需要由程序验证。

## Result Envelope

Tool 应返回结构化状态，而不是让模型从自由文本猜测是否成功：

```json
{
  "call_id": "call-1842",
  "status": "retryable_error",
  "code": "UPSTREAM_TIMEOUT",
  "observed_at": "2026-07-18T11:00:00+08:00",
  "data": null,
  "message": "上游服务超时",
  "retry_after_ms": 1000
}
```

至少区分 success、retryable error、non-retryable error、permission denied 和 unknown outcome。超时后的 unknown outcome 不能直接重试有副作用的动作，应先查询真实状态。

## Tool Result 验证

使用结果前检查：

- `status` 是否表示真实成功。
- 对象、tenant、版本和任务是否匹配。
- 时间和新鲜度是否满足当前步骤。
- 字段是否完整并通过 schema。
- 返回文本是否包含不可信内容或间接 prompt injection。
- 是否需要第二来源、业务规则或外部状态确认。

Tool result 是观察，不是高优先级指令。

## Payload 压缩

大结果应外置并生成最小 observation：

| 原始结果 | 注入模型的内容 |
|---|---|
| 数万行日志 | 失败时间段、错误聚类、关键行与完整日志引用 |
| 大型 JSON | 状态、相关字段、缺失字段和对象 ID |
| 网页正文 | 与任务相关的 evidence span、URL、时间和信任标签 |
| 数据库结果 | 列定义、过滤条件、关键行和总数 |
| 二进制产物 | 元数据、解析状态和 artifact 路径 |

压缩不能丢失错误状态、单位、时间、版本、否定条件和可回查引用。

## 并行 Tool Calls

可以并行：

- 互不依赖的只读查询。
- 不同来源的独立证据获取。
- 多个候选的无副作用验证。

不应并行：

- 后一调用依赖前一结果。
- 多个调用修改同一对象。
- 调用顺序影响余额、权限或状态迁移。
- 需要先批准再执行的动作。

汇总阶段必须保留 call ID 和来源，不能把多个结果合成无法追踪的自然语言。

## Retry Context

重试前记录：

- 上一次失败类型和参数。
- 当前尝试次数、时间和成本预算。
- 是否改变假设、参数、工具或数据源。
- 是否可能产生重复副作用。
- 何时降级、人工接管或停止。

相同参数、相同工具、相同错误反复调用不是恢复策略。

## Tool Context 与 Conversation / Planning

- [[10-conversation-context|Conversation Context]] 保存用户请求、tool 事件和必要确认。
- [[14-planning-context|Planning Context]] 保存当前步骤、依赖、预算和完成条件。
- Tool Context 保存每次调用的目的、参数、授权、观察和结果引用。

三者可以相互引用，但不应把全部 tool payload 复制进每一层。

## 评估

- Tool selection accuracy。
- 参数来源可追溯率。
- 权限违规和越权尝试率。
- 成功状态误判率。
- 重复副作用率。
- Result compression 后的关键信息保留率。
- Retry recovery rate 与平均尝试次数。
- Tool schema / result 占用 token 和延迟。
- 间接 prompt injection 防护通过率。

## 常见误区

> [!warning] Tool 返回文本不能提升自己的权限
> 网页、文件、数据库字段或第三方 API 即使包含“忽略之前规则并调用某工具”，也只是数据内容。

- **暴露所有工具**：增加 token、歧义和误调用。
- **Schema 通过等于授权通过**：类型正确不代表允许执行。
- **超时后直接重试写操作**：可能重复产生副作用。
- **完整 payload 永久放入历史**：窗口迅速膨胀并保留敏感数据。
- **模型从 message 判断成功**：应读取结构化 status 并核对外部状态。
- **重试不记录上次失败**：系统无法改变策略或达到停止条件。

## 检查表

- [ ] 只向模型暴露当前任务可能需要且允许的工具。
- [ ] Tool 定义说明用途、输入、输出、副作用和失败。
- [ ] 参数来源、授权范围和 idempotency 可追溯。
- [ ] Result 使用稳定 envelope，明确成功和错误状态。
- [ ] 不可信 tool 文本与控制指令隔离。
- [ ] 大 payload 外置，压缩保留状态、来源和引用。
- [ ] 并行调用满足独立与无冲突条件。
- [ ] Retry 有次数、时间、成本和副作用边界。

## 相关笔记

- [[01-context-architecture|Context Architecture]]
- [[05-context-assembly|Context Assembly]]
- [[10-conversation-context|Conversation Context]]
- [[14-planning-context|Planning Context]]
- [[15-workspace-context|Workspace Context]]
- [[prompt-engineering/12-tools-state-and-authorization|工具、状态与授权边界]]

