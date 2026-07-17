---
title: 推理增强策略
aliases:
  - Reasoning Strategies
  - Reasoning Prompting Techniques
tags:
  - prompt-engineering
  - reasoning
status: active
created: 2026-07-17
last_reviewed: 2026-07-17
sources:
  - https://arxiv.org/abs/2201.11903
  - https://arxiv.org/abs/2203.11171
  - https://arxiv.org/abs/2205.10625
  - https://arxiv.org/abs/2305.10601
  - https://arxiv.org/abs/2310.06117
  - https://arxiv.org/abs/2210.03629
  - https://developers.openai.com/api/docs/guides/reasoning-best-practices
---

# 推理增强策略

> [!important] 一句话核心
> 推理技巧不是附加在每个 prompt 上的咒语，而是针对特定失败选择的推理时机制；先建立直接 baseline，再根据任务结构、可验证信号和成本决定是否使用。

## 怎样理解“有效”

本篇收录有论文实验或主流官方实践支持的方法，但“论文报告提升”不等于“对所有模型和任务都有效”。效果会受到以下因素影响：

- 目标模型是否已经具有内部推理能力。
- 任务是否真的需要多步推理、搜索、计算或外部证据。
- 示例、采样预算、评分器和工具是否可靠。
- 指标测量的是答案正确、事实有据、约束通过，还是只偏好更长的输出。
- 新增调用、token、延迟和失败点是否值得。

本篇使用两档证据：

| 档位 | 收录标准 | 应如何使用 |
|---|---|---|
| **核心方法** | 有明确机制，并有多个任务实验、后续复现或主流官方实践支持 | 仍需在目标模型和真实样例上与直接 baseline 比较 |
| **条件性方法** | 有初步实验或实际用途，但效果强依赖自评质量、任务或实现 | 作为待验证假设，不默认进入生产 prompt |

> [!warning] 证据支持的是条件性选择，不是技巧排行榜
> 原论文通常只验证特定模型、数据集和预算。模型升级后必须重新 eval；没有当前对照实验时，不声称某种技巧必然提升质量。

## 先分清它改变了什么

许多被统称为“prompt 技巧”的方法其实位于不同系统层。

| 层 | 作用 | 代表方法 | 新增成本 |
|---|---|---|---|
| Prompt | 改变任务表达、示例或中间产物 | Few-shot、CoT、Step-Back | 上下文和输出 token |
| Decomposition | 把复合任务变成有依赖关系的子任务 | Least-to-Most、Plan-and-Solve | 阶段、状态和传播错误 |
| Sampling / Search | 生成并选择多条候选路径 | Self-Consistency、Best-of-N、ToT | 多次推理和评分 |
| Workflow | 在生成、反馈、验证和恢复之间建立循环 | ReAct、Self-Refine、Reflexion | 调用、停止条件和状态 |
| Tool / Runtime | 把事实、计算或校验交给外部能力 | Retrieval、PAL、Program of Thoughts、Verifier | 工具、权限和运行失败 |

如果一种方法需要多次模型调用、状态、程序执行或候选聚合，就不要把它伪装成一段更长的 prompt。它应按 [[13-decomposition-and-agent-workflows|工作流]]设计和评估。

## 核心方法

### Few-shot / In-Context Learning

**机制**：提供少量输入输出示例，让模型从上下文中识别任务映射、判断边界、格式或风格。

**适合**：规则难以用短定义表达，分类边界容易混淆，或输出模式需要示范。

**不适合**：模型缺少事实、计算能力或工具；这些问题不能靠示例凭空补足。现代 reasoning model 应先尝试 zero-shot，再根据失败加入最少示例。

**失效模式**：示例错误、分布偏窄、标签不一致、示例与文字规则冲突，或示例占用过多 context。

```text
任务：把工单分类为 billing、technical 或 needs_review。

示例：
输入：扣款两次，但服务可以正常使用。
输出：billing

输入：页面空白，尚未发生扣款。
输出：technical

现在只返回当前工单的标签。
```

示例选择原则详见 [[02-minimum-effective-prompt#Few-shot 的正确位置|Few-shot 的正确位置]]。

### Chain-of-Thought（CoT）

**机制**：让模型在得出答案前产生中间推理步骤。原始研究在算术、常识和符号推理任务上观察到显著提升。

**适合**：需要组合多个条件、进行多步推导，且中间步骤确实有助于得到答案的任务。

**现代模型注意**：不要把“请逐步思考”设为通用前缀。许多当前 reasoning model 在内部完成推理；例如 OpenAI 当前官方指南建议对其 reasoning model 保持 prompt 简单直接。需要可检查性时，要求简短依据、关键假设、计算结果或阶段产物，而不是完整私有思维过程。

**失效模式**：生成流畅但错误的 rationale；更长输出被误判为更好；错误早期步骤持续传播；增加延迟和 token。

```text
根据给定规则判断结论。返回：
1. 结论；
2. 最多三条决定结论的依据；
3. 无法确定时缺少的信息。
```

来源：[Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903)、[OpenAI reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)。

### Decomposition、Least-to-Most 与 Plan-and-Solve

**机制**：先识别子问题或制定计划，再按依赖关系逐步解决。Least-to-Most 特别针对“待解决问题比示例更难”的组合泛化；Plan-and-Solve 将计划与执行分开，减少漏步骤。

**适合**：子任务有明确依赖，不同阶段具有不同输入输出，或单次调用经 eval 证明容易漏步骤。

**不适合**：简单任务，或无法判断分解是否正确的任务。错误分解会让后续步骤稳定地走错方向。

```text
先只返回完成任务所需的子问题，按依赖顺序排列。
每个子问题必须说明所需输入和完成条件。

确认分解后，逐项求解；后一步只能依赖已声明的阶段输出。
```

生产系统应把阶段输出保存为外部状态，而不是依赖上一轮未声明的隐含推理。详见 [[13-decomposition-and-agent-workflows#阶段契约|阶段契约]]。

来源：[Least-to-Most Prompting](https://arxiv.org/abs/2205.10625)、[Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091)。

### Step-Back Prompting

**机制**：先从具体问题抽象出高层概念、第一原则或不变量，再用这些原则约束具体解答。

**适合**：模型容易被局部细节带偏，但任务存在稳定原则，例如数学性质、物理规律、架构约束或程序不变量。

**不适合**：事实检索、格式转换，或不存在可靠抽象原则的开放问题。

**失效模式**：生成空泛原则；选择错误抽象层；把模型自己生成的“原则”误当外部事实。

```text
先列出解决此类并发问题必须保持的两个不变量。
再根据这两个不变量分析当前实现，只报告会破坏不变量的路径。
```

来源：[Take a Step Back](https://arxiv.org/abs/2310.06117)。

### Self-Consistency

**机制**：以非确定性采样生成多条推理路径，再聚合它们的最终答案。它是 decoding / sampling 策略，不是“让模型自我检查”的一句指令。

**适合**：存在单一或可规范化答案，而且不同有效推理路径可能到达同一答案的数学、符号或封闭式推理任务。

**不适合**：事实问答、开放式写作和多个答案都合理的任务。多数模型输出不是事实证据。

**失效模式**：样本共享同一偏差；答案无法可靠规范化；投票掩盖少数正确答案；调用成本按样本数增加。

```text
同一输入 → 独立采样 N 个候选 → 提取规范化答案
         → 聚合答案 → 用可执行规则或基准答案验证
```

不要规定通用的 `N`。根据目标正确率、结果分布、延迟和成本，通过 eval 选择预算。

来源：[Self-Consistency Improves Chain of Thought Reasoning](https://arxiv.org/abs/2203.11171)。

### Best-of-N 与 Verifier / Reranking

**机制**：生成多个候选，再由与成功标准相关的 verifier、执行结果、规则或评分器选择，而不是直接采用第一个答案。

**适合**：候选质量有差异，并且存在比模型自报 confidence 更可靠的选择信号，例如单元测试、编译器、约束检查、精确答案或经过校准的 rubric。

**不适合**：评分器只偏爱长度、措辞或与参考答案表面相似；没有外部正确性信号时，重排可能只是选择“最像正确”的错误答案。

**失效模式**：reward hacking、评分器偏差、候选缺乏多样性，以及生成与评分成本叠加。

```text
生成候选 → 运行测试 / 规则校验 → 丢弃失败候选
         → 对剩余候选按任务 rubric 评分 → 选择或返回 needs_review
```

来源：[Training Verifiers to Solve Math Word Problems](https://arxiv.org/abs/2110.14168)。

### Tree of Thoughts（ToT）

**机制**：把解题过程表示为状态搜索：扩展多个候选 thought，评价中间状态，保留或剪枝，并在需要时回溯。

**适合**：早期选择会强烈影响后续结果、需要 lookahead 或回溯，而且中间状态能够被合理评分的搜索问题。

**不适合**：线性推导、低延迟任务，或中间状态没有可靠评分函数的开放任务。

**失效模式**：分支数量导致成本快速增长；模型生成器和评分器共享偏差；错误剪枝移除正确路径；复杂编排并不优于更强的直接 baseline。

```text
state → 生成候选状态 → 评分 → 保留前若干候选
      → 继续扩展 / 回溯 → 达到解或预算上限
```

ToT 是搜索算法，不等于“列出三种想法”。使用前必须定义状态、扩展操作、评分、剪枝、预算和停止条件。

来源：[Tree of Thoughts](https://arxiv.org/abs/2305.10601)。

### ReAct

**机制**：在任务循环中交替选择动作、执行工具、读取观察结果并更新下一步决策。真正提高可靠性的部分来自外部观察和可恢复状态，而不只是输出 reasoning trace。

**适合**：答案依赖搜索、数据库、文件、API 或环境反馈的任务。

**不适合**：无需工具即可完成的简单生成；高风险动作没有授权与幂等保护。

**失效模式**：错误工具路由、把工具结果中的指令当成可信规则、观察结果未验证、无限循环或重复副作用。

```text
读取目标与状态 → 选择下一动作 → 调用工具
               → 验证观察结果 → 更新状态 → 完成或停止
```

生产实现见 [[12-tools-state-and-authorization|工具、状态与授权边界]]，不要要求输出完整内部 thought。

来源：[ReAct](https://arxiv.org/abs/2210.03629)。

### Program-Aided / Program of Thoughts

**机制**：模型负责理解问题并生成程序或表达式，代码执行器负责精确计算。PAL 和 Program of Thoughts 都把自然语言推理与可执行计算分离。

**适合**：算术、符号、表格、日期、约束和其他可以通过程序确定性求值的任务。

**不适合**：程序无法表示主要语义判断，或环境不能安全执行生成代码。

**失效模式**：模型生成错误程序；执行环境权限过大；结果类型正确但语义映射错误；只检查是否运行而不检查业务含义。

```text
模型：把问题转换为最小计算程序，并声明输入与单位。
程序：在受限环境执行并返回结果或错误。
模型：根据执行结果生成简短答案，不自行重算。
```

来源：[PAL](https://arxiv.org/abs/2211.10435)、[Program of Thoughts](https://arxiv.org/abs/2211.12588)。

### Retrieval-Grounded Prompting

**机制**：先获取与当前问题相关、带来源的材料，再要求模型只基于这些证据回答。它主要是 context/runtime 机制，而不是措辞技巧。

**适合**：知识可能变化、领域资料不在模型上下文、答案必须可追溯，或不同来源可能冲突。

**不适合**：纯计算或材料本身不足以回答的问题。检索到内容不代表内容正确。

**失效模式**：召回缺失、排序错误、过量噪声、来源冲突被隐藏、文档内提示注入，以及模型使用未授权知识补全缺口。

完整流程见 [[10-context-and-instruction-architecture#Retrieval 流程|Retrieval 流程]]。

## 条件性方法

以下方法有论文实验或实际用途，但效果更依赖任务、反馈质量或实现。它们应作为需要验证的候选方案，而不是默认最佳实践。

### Self-Refine

**模式**：初稿 → 模型反馈 → 根据反馈修订 → 达到标准或停止。

当任务有清晰 rubric、可比较草稿且反馈能够指出可操作差异时可能有效，例如压缩、风格约束和局部改写。纯自我反馈对事实或逻辑错误不稳定：同一模型可能重复原有偏差，也可能把正确答案改错。

优先把确定性反馈交给 schema、测试和代码，把事实反馈交给外部来源。限制最大轮数，并保存每轮指标，避免无止境“再检查一次”。

来源：[Self-Refine](https://arxiv.org/abs/2303.17651)。

### Reflexion

**模式**：Agent 根据环境反馈总结失败原因，把语言形式的经验写入后续回合状态。

只有存在真实环境信号，例如测试失败、游戏得分或工具结果时，反思才有校正依据。没有外部反馈的自由反思容易积累错误总结；持久记忆还需要版本、来源和淘汰机制。

来源：[Reflexion](https://arxiv.org/abs/2303.11366)。

### Chain-of-Verification（CoVe）

**模式**：先生成草稿，再规划验证问题，尽量独立回答验证问题，最后修订。

它的价值来自“验证与初稿解耦”。如果验证仍只依赖同一模型记忆，错误可能保持相关；事实任务应让验证问题触发 retrieval 或权威来源，而不是把第二次回答当证据。

来源：[Chain-of-Verification](https://arxiv.org/abs/2309.11495)。

### Generated Knowledge Prompting

**模式**：先生成与问题相关的背景知识，再使用这些知识完成下游推理。

它可能帮助模型激活相关常识，但生成知识不是外部证据，也可能先制造错误前提再进行一致推理。事实敏感任务优先 retrieval；只有可由答案或 verifier 检验的封闭任务才值得把它作为实验变量。

来源：[Generated Knowledge Prompting](https://arxiv.org/abs/2110.08387)。

### Analogical Prompting

**模式**：让模型自行生成相似问题及其解法，再利用这些类比解决当前问题。

适合没有人工 few-shot、但模型能够生成可验证同类例题的推理任务。风险是类比只在表面相似，或生成例题本身错误。应检查结构是否同构，并避免把生成示例当事实来源。

来源：[Large Language Models as Analogical Reasoners](https://arxiv.org/abs/2310.01714)。

### Multi-Agent Debate / 多角色审议

**模式**：多个模型实例生成观点、互相审查或投票。

它可能增加候选多样性，但“更多 agent”并不自动提供独立证据：相同模型、prompt 和训练数据往往产生相关偏差。只有角色拥有不同材料、工具、评价维度或独立 verifier 时，额外调用才有清晰价值。不要用多数票裁定事实。

来源：[Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325)。

### Role / Persona Prompting

角色对受众、语言、视角和输出风格有用，例如“面向初学者解释”或“以安全审查者视角列风险”。仅写“你是世界级专家”不能可靠增加知识或底层推理能力，也不能代替证据、工具和任务定义。

## 怎样选择

| 已观察到的失败 | 优先尝试 | 不应默认做 |
|---|---|---|
| 模型不理解分类边界或输出模式 | 最少的边界 Few-shot | 加大量容易示例 |
| 复合任务漏步骤 | Decomposition / Plan-and-Solve | 要求输出完整内部 CoT |
| 被局部细节带偏 | Step-Back | 生成空泛长篇原则 |
| 封闭推理结果随采样波动 | Self-Consistency 或 Best-of-N + verifier | 把多数票当事实 |
| 早期选择需要探索和回溯 | ToT，并显式定义评分与预算 | 对线性任务构建搜索树 |
| 需要实时事实或外部观察 | Retrieval / ReAct | 依赖模型记忆或假装执行 |
| 算术或符号计算错误 | PAL / Program of Thoughts / code | 让模型多次心算 |
| 初稿违反可检查 rubric | Self-Refine + 外部反馈 | 无停止条件地自我批评 |
| 事实陈述可能错误 | Retrieval + 来源验证 | Generated Knowledge 或纯 CoVe 自证 |
| 不知道哪种方法有用 | 保持直接 baseline，先建立 eval | 一次叠加所有技巧 |

## 最小实验协议

引入任何推理策略前：

1. 保存简单直接 prompt 的 baseline。
2. 用失败样例说明为什么需要新机制。
3. 一轮只加入一种主要策略。
4. 固定模型、版本、输入、sampling、工具和评分方式。
5. 同时测量答案质量、约束、延迟、token、费用和失败率。
6. 对随机策略重复运行并报告结果分布，不只挑最好结果。
7. 改善不足以覆盖成本或副作用时回滚。

策略的测试集必须包含它声称解决的失败。例如，评估 ToT 要包含需要搜索或回溯的题，而不是只比较简单平均分；评估 Self-Refine 要同时检查修好多少错误和改坏多少正确答案。详见 [[14-evaluation-and-iteration|Prompt 评估与迭代]]。

## 不应当作推理增强的做法

- 只添加“仔细思考”“不要犯错”或“你是世界级专家”。
- 用公开的冗长 rationale 代替答案正确性和外部证据。
- 让模型自报 `confidence`，却没有做概率校准。
- 让同一个模型重复确认同一个结论，却没有新证据或不同检查机制。
- 用更多 agent、更多 token 或更长链条自动代表更高质量。
- 同时叠加 CoT、ToT、Self-Consistency 和 Self-Refine，使结果无法归因。

## 检查表

- [ ] 直接 baseline 已运行，失败可复现。
- [ ] 所选策略直接作用于该失败，而不是因为它流行。
- [ ] 已明确它属于 prompt、sampling、workflow 还是 tool/runtime。
- [ ] 中间产物、评分、外部证据或停止条件可检查。
- [ ] 没有要求公开完整私有思维过程。
- [ ] 没有把多数意见、自我反馈或生成知识当事实证据。
- [ ] 质量改善与 token、延迟、费用和失败点一起比较。
- [ ] 模型或版本变化后会重新 eval。

## 主要来源

### 核心方法

- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)
- [Self-Consistency Improves Chain of Thought Reasoning in Language Models](https://arxiv.org/abs/2203.11171)
- [Least-to-Most Prompting Enables Complex Reasoning in Large Language Models](https://arxiv.org/abs/2205.10625)
- [Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091)
- [Tree of Thoughts](https://arxiv.org/abs/2305.10601)
- [Take a Step Back](https://arxiv.org/abs/2310.06117)
- [ReAct](https://arxiv.org/abs/2210.03629)
- [PAL: Program-aided Language Models](https://arxiv.org/abs/2211.10435)
- [Program of Thoughts Prompting](https://arxiv.org/abs/2211.12588)
- [Training Verifiers to Solve Math Word Problems](https://arxiv.org/abs/2110.14168)
- [OpenAI Reasoning Best Practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)

### 条件性方法

- [Self-Refine](https://arxiv.org/abs/2303.17651)
- [Reflexion](https://arxiv.org/abs/2303.11366)
- [Chain-of-Verification](https://arxiv.org/abs/2309.11495)
- [Generated Knowledge Prompting](https://arxiv.org/abs/2110.08387)
- [Large Language Models as Analogical Reasoners](https://arxiv.org/abs/2310.01714)
- [Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325)

## 相关笔记

- [[00-overview|提示词工程总览]]
- [[02-minimum-effective-prompt|最小有效 Prompt]]
- [[03-choose-the-right-lever|选择正确的工程杠杆]]
- [[10-context-and-instruction-architecture|上下文与指令架构]]
- [[12-tools-state-and-authorization|工具、状态与授权边界]]
- [[13-decomposition-and-agent-workflows|任务拆解与 Agent 工作流]]
- [[14-evaluation-and-iteration|Prompt 评估与迭代]]
