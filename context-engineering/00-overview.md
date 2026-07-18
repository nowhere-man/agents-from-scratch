---
title: overview
aliases:
  - Context Engineering
  - 上下文工程
tags:
  - context-engineering
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
---

# 上下文工程

> [!important] 一句话核心
> 上下文工程不是把更多内容塞进模型，而是把完成当前任务所需的==规则、状态、证据和环境信息==，在正确的时间以正确的边界交给模型，并在失效后及时更新或移除。

## 它解决什么问题

模型只能根据当前调用可见的信息生成结果。即使模型能力足够，以下问题仍会让系统失败：

- 关键事实没有进入 context。
- 无关材料占满窗口并稀释目标。
- 过期状态、错误 tool 结果或旧计划继续被使用。
- 文档中的恶意指令与可信规则混在一起。
- 多轮对话只追加历史，无法恢复真实任务状态。
- Memory、retrieval、workspace 和 tool 各自返回材料，却没有统一筛选和组装。

因此，Context Engineering 处理的是从“信息存在于系统某处”到“模型在这一刻看到了正确的信息”的完整链路。

## 核心闭环

```mermaid
flowchart LR
    A["定义当前任务"] --> B["发现候选上下文"]
    B --> C["验证来源与权限"]
    C --> D["筛选与去重"]
    D --> E["压缩与标准化"]
    E --> F["按边界组装"]
    F --> G["模型与工具执行"]
    G --> H["评估结果和轨迹"]
    H --> I["更新、持久化或淘汰"]
    I --> A
```

这个闭环中，任何阶段都可能成为主要失败点。回答错误不一定意味着 prompt 不够强，也可能是选错了证据、状态已经过期、组装顺序不合理，或窗口预算没有为输出和 tool result 留出空间。

## 七个质量维度

| 维度 | 核心问题 | 典型失败 |
|---|---|---|
| 相关性 | 这段信息是否服务当前决策？ | 把整份知识库都放进请求 |
| 充分性 | 完成任务所需的关键材料是否齐全？ | 只有结论，没有限定条件 |
| 权威性 | 来源、版本和信任等级是否清楚？ | 用论坛转述覆盖正式政策 |
| 时效性 | 信息在当前时间是否仍有效？ | 使用过期价格、状态或代码 |
| 隔离性 | 指令、数据、状态和不可信内容是否分开？ | 网页文字改变 tool 权限 |
| 可恢复性 | 压缩或切换窗口后能否继续？ | 只保留聊天摘要，丢失待办和授权 |
| 效率 | 质量、token、延迟和缓存命中是否平衡？ | 为追求完整而重复注入相同材料 |

## Context Stack

一个实用的 Context Stack 可以分为：

1. **规则层**：稳定职责、安全边界、来源策略和输出契约。
2. **任务层**：当前目标、计划、进度、决定和完成条件。
3. **证据层**：retrieval 文档、memory、用户输入和结构化业务数据。
4. **交互层**：conversation history、tool result、workspace 与运行环境观察。
5. **呈现层**：最终进入模型请求的顺序、标签、格式和 token 分配。

各层不是消息角色的固定映射。不同 API 的角色与状态机制会变化，但职责、信任边界和生命周期仍应明确。详见 [[01-context-architecture|Context Architecture]]。

## Context 不等于什么

- **Context 不等于 Memory**：Memory 是跨调用持久化并可检索的信息；只有重新选中并注入后才成为当前 context。
- **Context 不等于 State**：State 是应用保存的可信任务事实；模型看到的只是 state 的一个投影。
- **Context 不等于 Prompt**：Prompt 主要定义目标和行为，context 还包含证据、历史、工具、计划和 workspace。
- **Context Window 不等于有效容量**：API 接受输入不代表模型能稳定利用所有位置和全部细节。

基础概念可结合 [[llm-basic/03-inference-context-and-efficiency|推理、Context 与效率]] 和 [[prompt-engineering/10-context-and-instruction-architecture|上下文与指令架构]] 阅读。

## 快速决策表

| 问题 | 优先阅读 |
|---|---|
| 系统里有哪些上下文层，它们怎样流动？ | [[01-context-architecture|Context Architecture]] |
| 信息何时产生、刷新和失效？ | [[02-context-lifecycle|Context Lifecycle]] |
| Token 不够或长输入退化怎么办？ | [[03-context-window-management|Context Window Management]] |
| 哪些材料值得进入当前任务？ | [[04-context-selection|Context Selection]] |
| 选中的材料怎样排列和标记？ | [[05-context-assembly|Context Assembly]] |
| 多轮对话怎样保留连续性？ | [[10-conversation-context|Conversation Context]] |
| 哪些信息应该跨任务保存？ | [[11-memory-engineering|Memory Engineering]] |
| 外部知识怎样检索、排序和引用？ | [[12-retrieval-engineering|Retrieval Engineering]] |
| Tool 定义和结果怎样进入上下文？ | [[13-tool-context|Tool Context]] |
| 计划与中间状态怎样跨窗口恢复？ | [[14-planning-context|Planning Context]] |
| 代码、文件、终端和 IDE 状态怎样管理？ | [[15-workspace-context|Workspace Context]] |

## 两层阅读路径

### 第一层：建立通用管线

1. [[01-context-architecture|Context Architecture]]
2. [[02-context-lifecycle|Context Lifecycle]]
3. [[03-context-window-management|Context Window Management]]
4. [[04-context-selection|Context Selection]]
5. [[05-context-assembly|Context Assembly]]

### 第二层：进入运行时上下文

1. [[10-conversation-context|Conversation Context]]
2. [[11-memory-engineering|Memory Engineering]]
3. [[12-retrieval-engineering|Retrieval Engineering]]
4. [[13-tool-context|Tool Context]]
5. [[14-planning-context|Planning Context]]
6. [[15-workspace-context|Workspace Context]]

## 常见误区

- **Context Engineering 就是 prompt engineering**：prompt 只负责部分行为表达，context 还包括状态、证据、工具、记忆和 workspace。
- **更大的窗口会自动解决问题**：容量不会修复错误来源、过期状态、权限冲突和位置退化。
- **把所有可用信息都提供给模型**：候选信息仍需筛选、去重、压缩和分区。
- **Memory 自动改善每个任务**：错误或无关记忆会污染当前输入，必须按任务检索和验证。
- **只优化 token 数量**：还要验证质量、引用、恢复、安全、延迟和成本。

## 检查表

- [ ] 能说明当前任务真正需要哪些信息，而不是从“有哪些数据”倒推。
- [ ] 每份上下文都有来源、版本、时间、权限和任务范围。
- [ ] 规则、状态、证据和不可信材料有明确边界。
- [ ] 选择与组装是两个独立步骤，可以分别评估。
- [ ] Context window 为输出、tool result 和后续步骤留有余量。
- [ ] 压缩、刷新和淘汰不会丢失目标、否定约束或未完成事项。
- [ ] Memory、retrieval、tool 和 workspace 都经过统一验证后再注入。
- [ ] 同时评估质量、token、延迟、成本、缓存命中和恢复成功率。

## 相关笔记

- [[roadmap|AI Agents Roadmap]]
- [[prompt-engineering/10-context-and-instruction-architecture|上下文与指令架构]]
- [[llm-basic/03-inference-context-and-efficiency|推理、Context 与效率]]
- [[llm-basic/08-using-assistant-models-in-agents|在 Agent 中正确使用 Assistant Model]]
