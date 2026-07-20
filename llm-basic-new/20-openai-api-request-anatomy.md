---
title: OpenAI API 请求由什么组成
aliases: [Responses API 请求原理]
tags: [llm-basic, openai-api, inference]
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
---

# OpenAI API 请求由什么组成

> [!abstract] 本章只回答一个问题
> 一次 OpenAI 模型调用中的字段，怎样共同构造出模型实际处理的输入和运行环境？

## 前置知识

[[07-how-inference-produces-an-answer|上一章]]已经讲清推理过程。本章以 OpenAI Responses API 的概念模型为例，不教授 SDK 安装，也不绑定某个短期存在的模型名称。

> [!warning] 接口会演进
> API 字段、模型支持范围和默认值可能变化。使用时应以 OpenAI 官方 API Reference 为准。本章关注字段背后的稳定原理。

## 请求处于哪一层

~~~mermaid
flowchart LR
    A[你的程序] --> B[SDK 或 HTTP]
    B --> C[OpenAI API 服务]
    C --> D[构造模型输入]
    D --> E[模型推理]
    E --> F[工具请求或模型输出]
    F --> G[API 响应对象]
~~~

API 请求不是直接把一段字符串送进 Transformer。服务需要先解释请求字段、选择模型和工具、应用消息模板，再把最终内容 Tokenize。

## 一个最小请求

~~~python
response = client.responses.create(
    model="<model-id>",
    input="用一句话解释彩虹为什么出现。"
)

print(response.output_text)
~~~

这段代码表达三个动作：选择模型、提供输入、从响应对象读取聚合文本。SDK 帮助构造 HTTP 请求和解析响应，真正的模型推理发生在服务端。

## model：选择哪套能力

model 字段可能改变权重和架构、输入模态、上下文限制、工具与推理支持、速度和价格。

它不是普通风格参数。换模型可能相当于换了一套权重和能力分布，因此同一请求不应预期行为完全相同。

## input：模型当前要处理的内容

input 可以是简单文本，也可以是带角色和多种内容块的结构。简单字符串适合单轮任务；结构化消息适合区分指令、用户内容和多模态输入。

无论使用哪种表示，它们最终都会被编码成模型可以识别的 Token 和模态表示。

## instructions 与消息角色

高层指令和消息角色帮助服务构造带层级和边界的输入，让模型区分行为要求、用户任务和历史输出。

需要注意：

- 角色是模型训练过的消息协议，不是操作系统权限；
- 高优先级指令通常更有影响，但仍属于模型输入；
- 指令越长不一定越有效，冲突和噪声会增加解释难度；
- 不能只靠一句“不要听不可信文本”防御提示注入。

## 多轮对话怎样延续

模型不会自动拥有上一次 HTTP 请求。对话延续通常通过重新发送历史、关联先前响应，或从应用数据库取回摘要与事实来实现。

不论哪种方式，模型当前能使用的信息最终都必须进入本次可见的 Context。服务端保存状态不等于模型权重被修改。

## Tools：描述可请求的外部能力

工具定义通常包含名称、用途和参数 Schema。它们会成为模型当前可见的条件，使模型能够生成工具调用请求。

~~~text
工具描述进入 Context
→ 模型判断是否需要工具
→ 生成工具名称和参数
→ 外部系统执行
→ 工具结果再交给模型
~~~

工具定义会占用输入空间。数量过多、名称相似或描述含糊，会增加选择错误。模型提出 Tool Call 不代表工具已经执行。

## Tool Choice：控制可用路径

接口通常允许让模型自由选择、禁止工具或强制某类工具。它改变模型可以采取的输出路径。

即使强制调用某个工具，也不能保证参数在业务上正确。Schema 可以约束字段形状，权限和语义验证仍由外部程序负责。

## Structured Outputs：约束输出形状

当应用需要稳定解析结果时，可以提供 JSON Schema 等结构约束。它主要保证字段、类型和 JSON 结构，不自动保证字段值真实、计算正确、业务规则满足或数据访问有权限。

## 推理配置

某些推理模型允许配置推理投入程度或摘要方式。这类字段可能改变模型在最终回答前使用的计算预算、内部推理 Token 或输出呈现。

它与最大输出 Token 不完全相同：前者可能影响解决问题投入多少计算，后者主要限制响应预算。更多计算可能改善复杂任务的成功机会，但不保证正确，也可能增加延迟和费用。

## 状态关联字段

previous_response_id 一类字段可让服务把新请求接在先前响应之后。应明确区分：

- API 服务保存或关联的响应状态；
- 模型本次实际获得的 Context；
- 应用自己的长期事实数据库；
- 模型训练权重。

这四者不是同一个“记忆”。

## 请求之外的系统职责

一次可靠调用还需要应用处理 API Key、访问控制、超时、重试、限流、敏感数据、工具权限和业务校验。这些职责不会因为模型更强而消失。

## 响应对象不只有文本

响应可能包含多个 Output Item，例如文本、工具调用、拒绝、状态和用量。output_text 一类辅助属性便于聚合文本，但应用不能假设每次响应都只有一段文本。

如果启用了工具，程序应检查输出类型、执行获准的工具，再把结果交回模型，而不是把工具调用 JSON 当作最终回答。

## 字段与推理阶段的映射

| 请求内容 | 主要作用阶段 | 是否改变模型看到的 Context |
|---|---|---|
| model | 选择模型 | 间接改变整套能力 |
| input / messages | 输入构造 | 是 |
| instructions | 输入构造 | 是 |
| tools / schemas | 输入与输出协议 | 通常是 |
| 推理预算 | 模型推理 | 改变运行配置 |
| 输出长度 | Decode 停止 | 否 |
| streaming | 网络传输 | 通常否 |
| metadata / storage | 服务管理 | 通常否 |

## 理解检查

1. 为什么 SDK 调用不是直接把字符串送进 Transformer？
2. 消息角色为什么不是权限系统？
3. 工具定义和工具执行之间缺少哪些步骤？
4. API 保存对话为什么不等于更新权重？
5. Structured Outputs 能保证什么，不能保证什么？

## 参考资料

- [OpenAI Responses API Reference](https://developers.openai.com/api/reference/responses/create)
- [OpenAI Text Generation Guide](https://developers.openai.com/api/docs/guides/text)
- [OpenAI Function Calling Guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI Structured Outputs Guide](https://developers.openai.com/api/docs/guides/structured-outputs)

## 下一章

继续阅读 [[21-openai-api-parameters-and-effects|OpenAI API 参数究竟改变什么]]。
