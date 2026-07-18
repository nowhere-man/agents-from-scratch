---
title: Context Selection
aliases:
  - 上下文筛选
  - Context Filtering
tags:
  - context-engineering
  - selection
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
---

# Context Selection

> [!important] 一句话核心
> Context Selection 决定哪些候选信息值得服务当前任务；它先执行权限和有效性硬过滤，再在相关性、权威性、新鲜度、独特性与风险之间做可评估的选择。

## Selection 与 Retrieval、Assembly 的区别

- **Retrieval** 从大型外部集合中召回候选。
- **Selection** 对所有候选做过滤、比较、去重和取舍。
- **Assembly** 把选中内容按边界、顺序和预算渲染为最终输入。

候选还可能来自 conversation、memory、tool、planning 和 workspace，因此 Selection 不等于向量搜索。

## 先做硬过滤

以下条件不应交给相似度评分抵消：

- 当前用户或 Agent 是否有权访问。
- tenant、项目、任务 ID 是否匹配。
- 来源是否被允许。
- 内容是否过期、被撤销或版本不兼容。
- 是否包含不允许进入目标模型的敏感数据。
- Tool 是否真正成功，workspace snapshot 是否仍有效。

硬过滤之后，才对剩余候选排序。

## 选择维度

可以使用概念评分帮助解释决策：

$$
S = w_rR + w_aA + w_fF + w_uU + w_dD - w_cC - w_kK
$$

- $R$：与当前任务和子问题的相关性。
- $A$：来源权威性。
- $F$：新鲜度和版本匹配。
- $U$：对当前决策的实际用途。
- $D$：相对已选材料的独特信息增益。
- $C$：token、延迟或读取成本。
- $K$：安全、冲突或误导风险。

公式不是通用真理。权重应由任务和 eval 决定，高风险领域还需保留确定性规则和人工升级。

## 三类输出

| 类别 | 含义 | 后续处理 |
|---|---|---|
| Selected | 有权、有效且服务当前任务 | 进入组装候选 |
| Rejected | 无关、重复、过期、无权或低价值 | 记录原因，不进入模型 |
| Uncertain | 来源冲突、缺少版本、置信不足 | 补充检索、标记不确定或人工复核 |

保留 rejected / uncertain reason 能帮助调试“为什么模型没看到某段信息”。

## 保留冲突和否定证据

Selection 不应只保留支持当前假设的材料。需要特别保护：

- 政策例外和禁止条件。
- 与主要来源冲突的可信证据。
- “没有找到”“尚未确认”等缺失状态。
- 时间范围、适用对象和版本限制。

多个来源冲突时，优先保留来源与冲突结构，让后续步骤按明确规则处理，而不是在 selection 阶段静默裁决。

## 去重与多样性

重复材料会浪费 token，也可能让一个观点获得不合理权重。去重可以结合：

- 稳定 ID、URL、版本或 content hash。
- 规范化后的完全匹配。
- 语义相似度聚类。
- 同一事件的多来源合并。

但语义相似不代表可互换。不同来源、时间和限定条件可能是需要保留的差异。

## 多模态 Selection

多模态任务需要根据当前问题选择信号，而不是固定抽取所有模态：

| 模态 | 候选 | 选择依据 |
|---|---|---|
| 视频 | 关键帧、镜头、时间段 | 事件变化、问题相关性、时间覆盖 |
| 音频 | ASR、说话人、音频事件 | 发言内容、身份、情绪或环境声 |
| 图像 | OCR、物体、布局、局部 crop | 文本区域、目标物体、空间关系 |
| 代码 | 文件、symbol、diff、调用链 | 修改范围、依赖、测试失败 |

例如用户询问“第 42 秒谁说了什么”，优先选择带时间戳的 ASR 和 diarization，而不是平均抽取更多视频帧。

## Selection 输出契约

```yaml
selection:
  task_id: incident-1842
  selected:
    - id: log-api-500
      reason: 与失败时间和服务匹配
      priority: p0
      evidence_span: lines 340-382
  rejected:
    - id: old-runbook-v1
      reason: superseded_by_v3
  uncertain:
    - id: deploy-event
      reason: timestamp_timezone_missing
```

这个产物应由 [[05-context-assembly|Context Assembly]] 消费，而不是把选择逻辑散落在 prompt 模板中。

## 评估

- **Precision**：选中材料中真正有用的比例。
- **Recall / Coverage**：完成任务需要的关键材料被选中的比例。
- **Redundancy**：选中内容的重复率。
- **Authority coverage**：关键结论是否有允许来源。
- **Freshness error**：选中内容过期或版本错误的比例。
- **Token utility**：单位 token 带来的任务质量增益。
- **Selection stability**：等价请求是否得到一致的关键证据集。

## 常见误区

> [!warning] Top-k 是容量参数，不是完成条件
> 固定取前 5 条不能保证事实齐全，也不能保证不存在 5 条重复材料。停止条件应与覆盖、阈值、冲突和预算相关。

- **只按相似度排序**：忽略权限、权威性、新鲜度和任务用途。
- **只保留支持证据**：产生 confirmation bias。
- **选择阶段直接写答案**：使检索、证据和生成无法独立评估。
- **语义去重删除差异**：可能丢失版本、时间或例外条件。
- **多模态全量抽取**：成本高且噪声大，应围绕问题选择信号。
- **无法解释拒绝原因**：难以定位漏召回和权限过滤问题。

## 检查表

- [ ] 权限、tenant、版本和敏感数据先做硬过滤。
- [ ] 选择标准围绕当前任务，而不是通用“重要性”。
- [ ] 保留关键否定信息、冲突和未知项。
- [ ] 重复内容被合并，但来源差异没有丢失。
- [ ] 多模态信号按问题选择，而不是固定全量注入。
- [ ] Selected、Rejected、Uncertain 都有可解释原因。
- [ ] Selection 与 Assembly 可以独立测试。
- [ ] 同时评估 precision、coverage、freshness 和 token utility。

## 相关笔记

- [[02-context-lifecycle|Context Lifecycle]]
- [[03-context-window-management|Context Window Management]]
- [[05-context-assembly|Context Assembly]]
- [[11-memory-engineering|Memory Engineering]]
- [[12-retrieval-engineering|Retrieval Engineering]]
- [[15-workspace-context|Workspace Context]]

