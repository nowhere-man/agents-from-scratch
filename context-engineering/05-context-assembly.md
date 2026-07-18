---
title: Context Assembly
aliases:
  - 上下文组装
  - Context Packaging
tags:
  - context-engineering
  - assembly
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
---

# Context Assembly

> [!important] 一句话核心
> Context Assembly 把已经选中的规则、状态、证据和观察渲染成一个边界清晰、来源可追踪、预算可预测的输入包；它负责组织，不负责偷偷补充事实。

## Assembly 的输入与输出

输入应是 [[04-context-selection|Selection]] 产生的结构化候选，而不是随意拼接的字符串。输出可以是 API messages、多模态 parts 或模型无关的 context packet。

```yaml
context_packet:
  task:
    objective: 比较两个发布版本的失败原因
    completion: 输出带证据的差异表
  policy_refs:
    - incident-analysis-v2
  state:
    current_step: compare_logs
  evidence:
    - id: deploy-v41
      source: release-system
      content: "..."
    - id: log-api-500
      source: observability
      content: "..."
  action:
    instruction: 只根据 evidence 比较，不推测缺失事件
  output:
    schema: incident_comparison_v1
```

模型看到的是这个 packet 的一种 rendering；可信来源仍保存在系统中。

## 推荐顺序

一个通用 baseline：

1. **稳定规则**：职责、权限、来源和未知值策略。
2. **任务状态**：当前目标、步骤、决定和完成条件。
3. **证据材料**：按主题或来源分组，并保留 ID。
4. **Tool / Workspace 观察**：结构化成功状态、时间和版本。
5. **当前动作**：这一轮具体要做什么。
6. **输出契约**：字段语义、格式和停止条件。

顺序不是永久规则。长文档、特定模型和多模态输入需要在真实任务上 eval，但“稳定规则与不可信数据分开”“最终动作清楚”是较稳定的原则。

## 指令与数据分区

```text
<policy>
  只使用允许来源；材料不足时返回 missing_context。
</policy>

<task_state>
  当前步骤：核对合同期限。
</task_state>

<documents>
  <document id="contract-v3" trust="user-provided">
    ...不可信原文，内部指令只视为数据...
  </document>
</documents>

<action>
  提取期限、续约条件和证据位置。
</action>
```

XML、Markdown 或 JSON 都可以使用。重要的是边界稳定、嵌套不过度，并且 untrusted content 不会被渲染到控制面区域。

## Provenance

每项证据至少保留：

- 稳定 source ID。
- 版本、时间或 snapshot。
- 必要的页码、行号、时间戳或 evidence span。
- 信任与权限标签。
- transform 信息，例如摘要来源或 OCR 方法。

输出需要引用时，模型应引用稳定 ID，程序再把 ID 映射为可展示链接或证据片段。

## Token-aware Rendering

Assembly 应在渲染前知道每个分区的预算和降级方式：

| 分区 | 超预算时优先动作 |
|---|---|
| Policy | 删除重复解释，不删除约束 |
| State | 保留结构化当前视图，移除旧事件细节 |
| Evidence | 去重、缩小 span、按需分批 |
| Tool result | 保留状态和关键字段，外置大 payload |
| Workspace | 保留 diff、symbol 和失败片段，外置无关文件 |
| Examples | 减少覆盖重复的样例 |

渲染后仍要重新估算 token，因为标签、schema 和序列化也会消耗窗口。

## 多模态 Assembly

多模态材料应使用共同的时间、对象和来源标识对齐：

```yaml
segment_id: scene-12
time_range: 00:41.200-00:47.800
video:
  keyframes: [frame-1240, frame-1375]
audio:
  transcript: "我们现在开始发布。"
  speaker: host
ocr:
  text: "Version 4.1"
selection_reason: 发布动作与版本号同时出现
```

关键帧、ASR、OCR、人物、动作和音频事件不应各自无序堆叠。通过 segment 或 entity 对齐后，模型才能建立跨模态关系。

## Context Diff

多轮或 Agent loop 中，不必每次重复注入全部动态上下文。系统可以记录：

- 哪些稳定前缀可复用。
- 哪些 state 字段发生变化。
- 新增、替换或失效了哪些 evidence。
- Tool / workspace 观察对应哪个动作。

但只有目标 API 明确支持可靠状态延续时，才能只发送增量；否则仍需构建完整的最小可恢复 packet。

## 失败处理

Assembly 应显式处理：

- 必要 P0 内容超过窗口：停止、拆分任务或换架构，不静默删除。
- Evidence 缺失：输出 `missing_context`，触发补充检索。
- 来源冲突：保留冲突结构，不合并成单一事实。
- Tool 失败：渲染错误状态，而不是渲染伪造结果。
- 无法解析的二进制或多模态输入：记录未处理项并降级到可用表示。

## 常见误区

> [!warning] “拼接完成”不等于“组装正确”
> 字符串没有超限，只能证明长度可接受；来源边界、顺序、冲突、预算和任务完成度仍需验证。

- **Selection 和 Assembly 混在一起**：无法判断是选错内容还是排错位置。
- **所有材料使用同一标签**：模型难以区分规则、状态和证据。
- **引用自然语言标题**：标题会重复或变化，应使用稳定 ID。
- **多模态内容没有时间对齐**：图像、音频和文字无法建立同一事件关系。
- **格式层级过深**：标签本身消耗 token，也增加解析难度。
- **动态内容放在缓存前缀前部**：降低复用并增加失效复杂度。

## 检查表

- [ ] Assembly 只消费已验证和已选择的候选。
- [ ] Policy、state、evidence、tool、workspace 和 action 分区明确。
- [ ] 不可信原文不能进入控制面区域。
- [ ] 每项证据有稳定 ID、版本和可回查位置。
- [ ] 每个分区有预算和超限降级策略。
- [ ] 多模态材料使用时间、segment 或 entity 对齐。
- [ ] 必要内容超限时会拆分或停止，不静默截断。
- [ ] 最终 rendering 在目标模型上经过位置和长度 eval。

## 相关笔记

- [[01-context-architecture|Context Architecture]]
- [[03-context-window-management|Context Window Management]]
- [[04-context-selection|Context Selection]]
- [[10-conversation-context|Conversation Context]]
- [[13-tool-context|Tool Context]]
- [[15-workspace-context|Workspace Context]]

