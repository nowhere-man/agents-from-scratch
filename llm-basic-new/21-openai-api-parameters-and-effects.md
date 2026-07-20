---
title: OpenAI API 参数究竟改变什么
aliases: [LLM API 参数原理]
tags: [llm-basic, openai-api, parameters]
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
---

# OpenAI API 参数究竟改变什么

> [!abstract] 本章只回答一个问题
> 一个参数究竟改变了模型输入、推理计算、Token 选择、停止条件，还是仅仅改变返回方式？

## 不要把所有参数都叫模型参数

API 参数是调用时提供的配置；模型参数是训练得到的权重。调整 API 的 temperature 不会改写模型权重。

判断字段时，先把它放进某一层：

~~~mermaid
flowchart LR
    A[输入构造] --> B[模型与推理配置]
    B --> C[解码选择]
    C --> D[停止条件]
    D --> E[输出协议]
    E --> F[传输与存储]
~~~

## 输入与指令参数

input、instructions、历史消息、工具定义和 Schema 会改变模型当前获得的条件，并影响 Token 数量、必要事实是否可见、指令冲突、工具选择和输出格式。

它们不会把新知识写入权重，但往往比采样参数更直接地影响任务结果。

## model：改变整套能力分布

选择不同模型可能改变权重、架构、训练方式、上下文范围、工具能力和推理机制。不要只根据名称猜测能力，应在真实任务和输入长度下评测。

## 推理投入参数

某些模型支持 reasoning effort 等推理配置。它可能让模型在最终答案前投入不同程度的内部计算。

| 较低投入 | 较高投入 |
|---|---|
| 延迟和成本较低 | 延迟和成本较高 |
| 适合简单或高吞吐任务 | 更适合复杂、多步任务 |
| 复杂问题可能考虑不足 | 成功机会可能提高但不保证正确 |

这不是“智商等级”，也不是所有模型都支持相同字段。

## temperature：改变概率分布的尖锐程度

Temperature 作用于 Logits 到概率的转换。较低值让高分候选更占优势，较高值让更多候选有机会被采样。

- 事实抽取和稳定格式通常不需要很高随机性；
- 开放式构思可能从多样候选中受益；
- 提高 Temperature 不能弥补证据缺失；
- 降低 Temperature 不能消除幻觉，只会让输出更集中。

部分模型不允许任意设置该值，应以模型参考为准。

## top_p：改变候选集合

Top-p 只保留累计概率达到阈值的高概率候选集合。值低时集合通常更小，值高时保留更多长尾候选，集合大小会随每一步的概率分布变化。

Temperature 和 Top-p 都影响采样。实践中通常先调整一个，而不是同时大幅修改两个，否则很难定位变化来源。

## 最大输出 Token：改变生成预算

max_output_tokens 一类字段限制响应的最大输出预算。它影响最坏情况下的延迟和费用，也可能导致回答截断。

它不是期望长度：模型可以提前结束。对于包含内部推理 Token 的模型，预算与最终可见文本长度也不一定一一对应。

## Stop：控制停止模式

支持 Stop 的接口或模型会在生成指定模式时结束。它只控制停止，不验证前面内容是否完整正确。Stop 还可能在正常内容中出现，造成提前结束。

严格结构优先使用正式的结构化输出机制，而不是只靠停止字符串拼接协议。

## Tool Choice：改变允许的输出路径

Tool Choice 可以允许模型自行决定、禁止工具或要求使用工具。它不保证模型填对参数、工具执行成功或结果被正确理解。外部程序仍需验证权限、参数和执行结果。

## Parallel Tool Calls

并行工具调用允许一轮提出多个互不依赖的调用，可能减少往返时间。应用必须处理调用依赖、返回顺序、部分失败、写冲突和每个调用的权限。

它改变工具交互方式，不改变工具本身的真实能力。

## Structured Output / Text Format

格式配置约束输出遵循文本或 JSON Schema，显著降低解析失败。正确流程仍是：

~~~text
Schema 约束结构
→ 解析输出
→ 业务规则校验
→ 查询真实数据
→ 决定是否接受或执行
~~~

结构正确不能证明字段值正确。

## stream：改变传输方式

Streaming 逐步发送响应事件，让用户更快看到内容。客户端需要处理增量事件、断线和不完整结果。

它通常不改变模型权重、Context 或 Token 概率，不能理解成“开启边想边答模式”。

## store、metadata 与用户标识

这类字段用于保存、检索、观测、安全或业务关联，通常不直接改变模型推理。应按官方文档确认具体隐私和保留行为，不要放入密钥或不必要的个人数据。

## Seed 与确定性

某些接口或模型可能提供 Seed 或近似复现能力。固定 Seed 只能控制部分随机来源，模型版本、后端实现和上下文变化仍可能带来差异。

它适合测试中的“尽量复现”，不是永久字节级一致性合同。若当前接口不支持，就不要假设字段存在。

## 参数影响总表

| 参数类别 | 改变什么 | 不改变什么 |
|---|---|---|
| 输入与指令 | 模型看到的 Context | 训练权重 |
| model | 权重、能力和支持特性 | 外部事实是否真实 |
| 推理投入 | 运行时计算预算 | 正确性保证 |
| Temperature / Top-p | Token 采样分布 | 模型知识来源 |
| 输出长度 / Stop | Decode 预算与停止 | 回答是否完整正确 |
| Tool Choice | 可用调用路径 | 权限和执行成功 |
| Structured Output | 输出结构 | 字段语义真实性 |
| Streaming | 传输时机 | 核心推理分布 |
| Store / Metadata | 服务管理 | 通常不改变推理 |

## 一个可靠的调参顺序

结果不好时，不要先盲调 Temperature：

1. 任务和成功标准是否清楚；
2. 必要事实是否在输入或工具中；
3. 指令、历史和工具描述是否冲突；
4. 模型是否支持所需能力；
5. 推理与输出预算是否足够；
6. 结构约束是否匹配消费方；
7. 最后再调整采样多样性。

## 理解检查

1. 为什么 API 参数不等于模型权重？
2. Temperature 和 reasoning effort 改变的是同一层吗？
3. 为什么最大输出长度可能截断回答？
4. Structured Output 后为什么仍需业务验证？
5. Streaming 和逐 Token 生成是什么关系？

## 参考资料

- [OpenAI Responses API Reference](https://developers.openai.com/api/reference/responses/create)
- [OpenAI Reasoning Guide](https://developers.openai.com/api/docs/guides/reasoning)
- [OpenAI Function Calling Guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI Streaming Guide](https://developers.openai.com/api/docs/guides/streaming-responses)

## 下一章

继续阅读 [[30-llm-capabilities-boundaries-and-agents|模型能力、边界与 Agent]]。
