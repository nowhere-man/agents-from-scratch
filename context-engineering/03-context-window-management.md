---
title: Context Window Management
aliases:
  - 上下文窗口管理
  - Token Budget Management
tags:
  - context-engineering
  - context-window
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
  - https://arxiv.org/abs/2307.03172
---

# Context Window Management

> [!important] 一句话核心
> 窗口管理的目标不是刚好塞进模型上限，而是在输入、输出、工具和后续步骤之间分配预算，让关键内容保持可见、可利用并为恢复留出余量。

## 预算模型

一次调用可以用下面的概念式拆分：

$$
W \ge P + U + H + E + T + O + R
$$

- $W$：目标模型可用 context window。
- $P$：稳定规则、工具定义和输出契约。
- $U$：当前用户输入。
- $H$：对话历史和任务状态投影。
- $E$：retrieval、memory、workspace 等证据。
- $T$：本轮或后续 tool result 的预留。
- $O$：最终输出预算。
- $R$：防止截断、格式膨胀和估算误差的安全余量。

预算是在模型调用前完成的系统决策。不要把超限后静默截断当成管理策略。

## 最大窗口与有效窗口

API 接受某个长度，只证明请求在格式上可处理。有效窗口还受以下因素影响：

- 关键事实在输入中的位置。
- 无关或重复材料的干扰。
- 多个远距离事实的组合难度。
- 模型、版本、任务和输出长度。
- Tool schema、图片、音频等非正文内容的 token 消耗。

Lost in the Middle 研究表明，长输入中的中间位置可能更难被稳定利用。不能把它简化为“所有模型都只看头尾”，而应在目标模型和真实长度上测试位置敏感性。

## 三档优先级

| 优先级 | 内容 | 处理方式 |
|---|---|---|
| P0 不可丢失 | 目标、权限、关键否定条件、当前步骤、输出契约 | 原样保留并校验 |
| P1 可压缩 | 已完成步骤、长历史、重复证据、tool 详情 | 结构化摘要或按需回查 |
| P2 可淘汰 | 无关页面、过期状态、低价值日志、重复示例 | 删除或保留外部引用 |

当预算不足时，通常按过滤、去重、检索、结构化压缩、拆分任务的顺序处理，而不是直接裁掉最旧消息。

## 压缩不变量

压缩后至少保留：

- 当前目标和成功标准。
- 用户明确约束和禁止事项。
- 已做决定及其理由。
- 已完成、进行中、待完成事项。
- 关键来源、冲突和未知项。
- 授权范围和副作用状态。
- 下一步继续执行所需的对象 ID 与版本。

自由文本摘要适合阅读，但可恢复状态应使用固定字段。详见 [[10-conversation-context|Conversation Context]] 和 [[14-planning-context|Planning Context]]。

## 长上下文的排列

一个可测试的 baseline：

1. 稳定规则、权限和来源策略。
2. 当前任务状态与目标。
3. 带来源标识的主要证据。
4. 必要的 tool / workspace observation。
5. 当前动作、局部约束和输出契约。

对于很长的资料，明确任务通常应靠近最终动作，并通过标题、标签和引用把任务与材料连接起来。具体顺序必须用 [[04-context-selection|选出的真实材料]] 进行 eval。

## Prompt Cache

Prompt Cache 或 Prefix Cache 复用稳定前缀的处理结果，主要降低重复 prefill 的成本或延迟。常见设计原则：

- 把稳定规则、工具定义和共享文档放在前缀。
- 把用户请求、时间和动态状态放在后缀。
- 保持序列化、顺序、模型和相关配置稳定。
- 对来源变化、权限变化和敏感数据定义失效策略。
- 分开观察 cache hit、TTFT、总成本和输出质量。

> [!warning] Prompt Cache 不是 Semantic Cache
> Prompt Cache 复用相同或兼容前缀的计算；Semantic Cache 根据语义相似度复用已有结果或检索结果，风险和验证方式不同。后者见 [[12-retrieval-engineering|Retrieval Engineering]]。

## 窗口管理策略

| 策略 | 适用场景 | 主要风险 |
|---|---|---|
| Sliding Window | 连续对话、流式事件 | 丢失早期约束 |
| Summary Buffer | 长对话与阶段任务 | 摘要累积错误 |
| Retrieval on Demand | 大型知识库和历史记录 | 召回不足 |
| Hierarchical Summary | 长文档、长视频、长轨迹 | 层层压缩损失 |
| Task Decomposition | 不同阶段需要不同材料 | 接口和状态复杂度增加 |
| External State | 需要可靠恢复的 Agent | 状态 schema 和一致性成本 |

通常需要组合策略，而不是寻找一个万能窗口算法。

## 评估指标

- Input / output token 分布。
- 截断率和预算超限率。
- 关键事实召回与引用覆盖。
- 不同位置的任务准确率。
- 压缩前后约束保留率。
- TTFT、端到端延迟和成本。
- Prompt Cache 命中率与失效率。
- 中断后的恢复成功率。

## 常见误区

- **窗口越大越准确**：噪声、冲突和位置退化不会因容量增加自动消失。
- **只统计正文 token**：工具定义、图片、历史、输出和 tool result 都占预算。
- **总是删除最旧消息**：最旧消息可能包含仍有效的目标或授权边界。
- **摘要就是可靠 state**：摘要是模型生成的压缩视图，需要结构化状态支撑。
- **缓存命中就是优化成功**：还需确认质量、新鲜度、安全和真实成本。
- **没有输出余量**：输入填满窗口后，结果可能被截断或无法继续 tool loop。

## 检查表

- [ ] 预算包含规则、历史、证据、tool、输出和安全余量。
- [ ] P0、P1、P2 内容有明确处理方式。
- [ ] 压缩保留目标、否定约束、来源和未完成事项。
- [ ] 长输入在不同位置和长度上经过 eval。
- [ ] Tool loop 为后续结果预留窗口。
- [ ] Prompt Cache 的稳定前缀和失效条件明确。
- [ ] 超限时不会静默丢弃关键内容。
- [ ] 同时监控质量、token、延迟、成本和恢复能力。

## 相关笔记

- [[02-context-lifecycle|Context Lifecycle]]
- [[04-context-selection|Context Selection]]
- [[05-context-assembly|Context Assembly]]
- [[10-conversation-context|Conversation Context]]
- [[03-inference-context-and-efficiency|推理、Context 与效率]]

