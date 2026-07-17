---
title: overview
aliases:
  - Prompt Engineering
tags:
  - prompt-engineering
status: active
created: 2026-07-16
last_reviewed: 2026-07-16
sources:
  - "[[99-provider-guidance-and-sources]]"
---

# 提示词工程

> [!important] 一句话核心
> 提示词工程不是把 prompt 写得更长，而是把模型行为设计成一个==目标明确、边界清楚、结果可验证、失败可处理==的系统契约。

## 它解决什么问题

提示词工程解决的是“怎样让模型在给定输入、上下文和运行条件下，持续产生符合要求的行为”。它不只关心一段文字，还关心这段文字与模型、数据、schema、工具、状态和评估之间的分工。

一个生产级 LLM 功能通常包含以下部分：

- **任务契约**：要为谁完成什么，输入输出和成功标准是什么。
- **Prompt**：模型必须理解的目标、语义规则和判断边界。
- **Context / Retrieval**：完成当前任务所需的事实和材料。
- **Schema / Code**：类型、字段、解析和确定性业务规则。
- **Tools**：获取实时信息、计算或执行外部动作。
- **State**：保存跨步骤、跨轮次继续任务所需的信息。
- **Eval**：判断改动是否真的改善结果。

因此，prompt 是系统接口的一部分，但不是整个系统。

## 核心闭环

```mermaid
flowchart LR
    A["定义任务契约"] --> B["选择正确机制"]
    B --> C["建立最小 Baseline"]
    C --> D["用代表性样例运行"]
    D --> E["分析失败层"]
    E --> F["只修改一个主要变量"]
    F --> G["同条件 Eval"]
    G -->|"改善"| H["版本化并发布"]
    G -->|"未改善"| E
    H --> I["监控与回滚"]
```

这个闭环比任何单一 prompting technique 更重要。没有任务契约，无法判断输出是否正确；没有 baseline 和 eval，无法判断改写是否有效；没有失败路径，prompt 在生产环境中只是一次性文案。

## 五个核心判断

### 1. 先定义成功，再写 prompt

“专业、准确、高质量”无法直接验收。应改成可以观察的标准，例如：字段完整、引用覆盖、约束通过、工具调用正确、延迟和成本处于允许范围。

详见 [[01-task-contract|任务契约]]。

### 2. 先定位失败层，再选择手段

信息缺失不应靠更强措辞补救；严格格式不应只靠自然语言保证；计算和外部动作不应由模型猜测完成。

详见 [[03-choose-the-right-lever|选择正确的工程杠杆]]。

### 3. 从最小 prompt 开始

先写能够表达目标、输入边界和输出要求的直接指令。只有真实失败证明有必要时，才增加示例、额外上下文、任务拆解或恢复步骤。

详见 [[02-minimum-effective-prompt|最小有效 Prompt]]。

### 4. 模型负责语义，程序负责确定性

模型适合理解、判断、归纳和生成；schema 与代码更适合类型、枚举、精确计数、排序、去重、解析和业务规则校验。

详见 [[11-structured-output-and-determinism|结构化输出与确定性保证]]。

### 5. 优化必须基于证据

Prompt 改得更长或读起来更清楚，不代表模型表现更好。使用同一测试集和运行条件比较 baseline 与新版本，每轮只改变一个主要变量。

详见 [[14-evaluation-and-iteration|Prompt 评估与迭代]]。

## 快速分工表

| 主要问题 | 优先机制 | 不应先做什么 |
|---|---|---|
| 指令含糊、规则冲突 | Prompt | 堆更多示例掩盖冲突 |
| 缺少事实或材料过多 | Retrieval / Context selection | 要求模型“不要幻觉” |
| 字段、类型、枚举不稳定 | Structured Outputs / Schema | 只写“返回 JSON” |
| 排序、去重、计算、业务校验 | Code | 让模型重复自检 |
| 需要实时信息或执行动作 | Tools | 让模型依赖记忆或假装执行 |
| 多轮任务丢失进度 | State management | 无限追加完整对话 |
| 复杂任务单步不可靠 | Decomposition / Workflow | 无条件把所有任务都拆链 |
| 成本、延迟、能力不匹配 | Model / Architecture | 继续扩写 prompt |
| 不知道改动是否有效 | Eval | 凭单个样例判断 |

## 两层阅读路径

### 第一层：建立主线

1. [[01-task-contract|任务契约]]：先定义任务及通过条件。
2. [[02-minimum-effective-prompt|最小有效 Prompt]]：建立最简单可验证的 baseline。
3. [[03-choose-the-right-lever|选择正确的工程杠杆]]：把问题交给正确机制。

### 第二层：进入生产系统

1. [[10-context-and-instruction-architecture|上下文与指令架构]]
2. [[11-structured-output-and-determinism|结构化输出与确定性保证]]
3. [[12-tools-state-and-authorization|工具、状态与授权边界]]
4. [[13-decomposition-and-agent-workflows|任务拆解与 Agent 工作流]]
5. [[14-evaluation-and-iteration|Prompt 评估与迭代]]
6. [[15-production-lifecycle|Prompt 的生产生命周期]]
## 最小检查表

- [ ] 能用一句话说明“谁会使用模型的输出、模型需要交付什么具体结果，以及这个结果将用于哪项后续决策或操作”。
- [ ] 输入、上下文和不可信数据有明确边界。
- [ ] 每项事实有允许来源，缺失时有确定行为。
- [ ] 输出要求可以人工或机械验收。
- [ ] Schema、代码、工具和模型的职责没有混淆。
- [ ] 至少有一个 baseline 和一组代表性样例。
- [ ] 每个主要失败都有恢复或停止方式。
- [ ] 改动经过同条件 eval，而不是凭感觉接受。

## 参考

+ [OpenAI](https://developers.openai.com/api/docs/guides/prompt-engineering)
+ [Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
+ [Google Gemini](https://ai.google.dev/gemini-api/docs/prompting-strategies) 
