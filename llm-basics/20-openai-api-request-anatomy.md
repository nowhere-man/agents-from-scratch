---
title: OpenAI API 请求由什么组成
aliases:
  - Responses API 请求原理
tags:
  - llm-basic
status: active
created: 2026-07-18
last_reviewed: 2026-07-20
---

# OpenAI API 请求由什么组成

> [!abstract] 本章只回答一个问题
> 应用提交的一组 API 字段，怎样经过服务层解释，变成模型本次看到的 Context、可选择的输出路径和最终响应对象？

## 前置知识

[[07-how-inference-produces-an-answer|上一章]]从模型内部追踪了 Context、Prefill、Decode 和停止。本章把视角移到应用边界：程序并不是把一段字符串直接写进 Transformer，而是向 API 服务提交一个结构化请求。

本章以 OpenAI Responses API 的概念模型为例。接口会演进，字段支持范围和默认值应以官方 API Reference 为准；这里重点解释字段在稳定的数据流中负责哪件事。

## 1. 从最小请求开始

~~~python
response = client.responses.create(
    model="<model-id>",
    instructions="回答要准确、简洁。",
    input="请用一句话解释彩虹为什么出现。",
)

print(response.output_text)
~~~

从应用代码看，这次调用只有三个主要输入：选择一个模型、提供高层指令、提供当前任务。但它们不会原样作为三个 Python 变量进入模型。

~~~mermaid
flowchart LR
    A[应用构造请求] --> B[SDK 编码 HTTP]
    B --> C[API 服务验证和解释字段]
    C --> D[构造模型 Context 与运行配置]
    D --> E[模型 Prefill 和 Decode]
    E --> F[文本、Tool Call 或其他 Output Item]
    F --> G[API 服务组装 Response]
    G --> H[SDK 解析成对象]
~~~

SDK 负责把语言对象编码成 HTTP 请求，并把响应解析成对象；API 服务负责鉴权、字段验证、模型调度、输入模板和输出协议；模型只处理服务最终构造出的表示。

下面跟踪这三个字段分别走向哪里。

## 2. model 先决定使用哪套模型能力

model 不是一句进入 Context 的提示词，而是服务层的路由选择。换一个 model 可能同时改变：

- 使用的权重和架构；
- 支持的输入模态与工具能力；
- Context Window 和输出限制；
- 推理配置、速度和价格；
- 对相同输入的能力分布。

因此“换模型”不是普通的写作风格调节。它相当于替换了执行本次推理的核心概率模型，应用应在真实任务上重新评测。

model 通常不会作为自然语言 Token 告诉模型“你叫某某模型”；它主要在 Context 构造之前决定由谁计算。

## 3. instructions 与 input 共同构造本次 Context

在例子中：

- instructions 表达跨当前请求的高层行为要求：“回答要准确、简洁”；
- input 表达用户当前要完成的任务：“解释彩虹为什么出现”。

API 服务会按模型熟悉的消息协议加入角色和边界。模型实际看到的概念结构更接近：

~~~text
[高优先级指令]
回答要准确、简洁。

[用户输入]
请用一句话解释彩虹为什么出现。

[助手输出开始]
~~~

input 不只可以是简单字符串，也可以由消息和多种内容块组成，以区分文本、图像、文件等输入。无论使用哪种外部表示，服务最终都要将它们转换为模型能处理的 Token 或模态表示。

> [!warning] 消息角色不是操作系统权限
> 角色和优先级是模型训练过的输入协议，能显著影响行为，但仍属于模型要解释的条件。真正的身份、访问控制和业务权限必须由服务端代码强制执行。

指令越长不一定越强。相互冲突、重复或夹杂无关材料，会让当前任务更难解释。

## 4. 多轮对话仍要变成本次可见输入

假设用户下一轮追问：

> 那为什么通常在雨后看到？

模型不会因为处理过上一次 HTTP 请求，就自动在权重中记住“那”指的是彩虹。要延续对话，系统必须通过某种方式把必要历史重新关联到本次请求，例如：

1. 应用重新发送相关历史消息；
2. 请求关联一个先前 Response，由 API 服务恢复相应上下文；
3. 应用从自己的数据库取出事实或摘要，再放入 input。

三种方式的存储位置不同，但对模型而言，必要信息最终都必须成为本次能够读取的 Context。

需要区分四个对象：

| 对象 | 作用 |
|---|---|
| API 服务保存的 Response | 便于关联或检索先前调用 |
| 本次模型 Context | 当前前向计算实际可见的信息 |
| 应用长期数据库 | 保存业务事实、用户状态和历史 |
| 模型权重 | 训练形成的通用规律 |

API 保存对话不等于模型重新训练，也不等于所有历史都永远进入每次 Context。

## 5. 加入 Tools 后，请求多了一条可能的输出路径

现在把问题换成：

> 北京现在适合看彩虹吗？

回答需要实时天气。应用可以在请求中提供工具定义：

~~~python
response = client.responses.create(
    model="<model-id>",
    input="北京现在适合看彩虹吗？",
    tools=[{
        "type": "function",
        "name": "get_weather",
        "description": "查询指定城市的当前天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"],
            "additionalProperties": False
        }
    }]
)
~~~

工具定义告诉模型：当前有一个名为 get_weather 的外部能力，它适合什么任务，需要什么参数。服务会把这些信息编码进模型可见的工具协议中，因此工具名称、描述和 Schema 也会占用输入空间。

模型此时可以生成两类候选输出：直接文本，或类似下面的 Tool Call：

~~~json
{
  "name": "get_weather",
  "arguments": {"city": "北京"}
}
~~~

到这里，模型只提出了一个结构化请求。真正的流程还缺少外部执行：

~~~mermaid
flowchart LR
    A[模型生成 Tool Call] --> B[应用解析和校验参数]
    B --> C[检查权限和业务规则]
    C --> D[应用执行真实工具]
    D --> E[把 Tool Result 交回模型]
    E --> F[模型结合结果生成回答]
~~~

如果天气工具返回“刚下过雨，西侧阳光充足”，模型才能据此生成最终解释。模型没有直接访问天气服务，Tool Call 也不能证明执行成功。

## 6. tool choice 控制哪条路径可以被选择

接口通常允许应用让模型自行选择工具、禁止工具，或要求使用特定工具。这类配置改变的是模型当前允许走的输出路径。

例如强制使用 get_weather，可以避免模型完全跳过实时查询；但它仍不能保证：

- city 参数语义正确；
- 当前用户有查询或执行权限；
- 工具服务可用；
- 工具结果可信；
- 模型最终解释正确。

Schema 可以约束参数形状，外部程序仍要负责权限、业务语义、超时、重试和错误处理。

## 7. Structured Outputs 约束返回形状

如果调用方不是把回答展示给人，而是要交给程序处理，可以要求模型返回符合 JSON Schema 的结构，例如：

~~~json
{
  "can_see_rainbow": true,
  "reason": "雨后空气中有水滴且有阳光"
}
~~~

格式约束可以显著减少 JSON 无法解析、字段缺失和类型错误，但它只解决“输出长什么样”。正确接收结果的流程仍应是：

~~~text
Schema 约束结构
→ 应用解析
→ 校验字段之间的业务关系
→ 对照真实数据或工具结果
→ 决定是否接受
~~~

合法的 true 仍可能是错误判断，合法的日期和金额也可能来自模型编造。

## 8. 有些字段不进入 Context，而是改变运行方式

到目前为止，instructions、input 和 tools 都会直接或间接成为模型本次可见条件。但请求中还有另一类字段，它们主要控制推理服务：

- 推理投入配置可能改变模型在最终回答前使用多少内部计算；
- 最大输出 Token 改变 Decode 的预算上限；
- 采样配置改变从 Logits 选择 Token 的方式；
- streaming 改变响应事件怎样传输；
- store、metadata 等字段用于保存、关联或观测调用。

这些字段不能笼统理解为“都拼进 Prompt”。有的改变模型看到什么，有的改变模型怎样运行，有的只改变 API 服务怎样管理结果。下一章会沿请求生命周期逐类展开。

## 9. Response 不是“模型返回的一段字符串”

模型生成完成后，API 服务会组装 Response。它可能包含多个 **Output Item**：

- 一段或多段文本；
- Tool Call；
- 拒绝信息；
- 完成或未完成状态；
- 用量、停止原因和其他元数据。

output_text 一类辅助属性只是帮助应用聚合文本。启用工具后，程序不能假设每次都有最终文本，也不能把 Tool Call JSON 直接显示成任务结果。

应用应先检查输出类型和状态：如果是 Tool Call，进入执行与回传循环；如果是文本，才将它作为候选答案处理；如果响应被截断或失败，则进入对应恢复逻辑。

## 10. 一次完整 API 调用到底分了哪些责任

回看最小请求，可以得到清楚的分工：

| 层 | 负责什么 | 不负责什么 |
|---|---|---|
| 应用 | 构造任务、保管密钥、权限、工具执行、业务验证 | 不直接运行模型权重 |
| SDK / HTTP | 序列化请求、传输和解析响应 | 不决定回答是否正确 |
| API 服务 | 验证字段、选择模型、构造协议、调度推理、组装 Response | 不替应用证明业务事实 |
| 模型 | 根据 Context 和配置生成文本或 Tool Call 候选 | 不自动执行工具或保存真实状态 |

因此一次可靠调用还需要处理 API Key、访问控制、超时、重试、限流、敏感数据、工具权限和结果校验。这些职责不会因为模型更强而消失。

> [!important] 请求字段的核心分类
> 先问这个字段是在选择模型、构造 Context、开放输出路径、控制推理与停止，还是只管理传输和服务状态。知道它位于哪一层，才知道它真正能改变什么。

## 参考资料

- [OpenAI Responses API Reference](https://developers.openai.com/api/reference/responses/create)
- [OpenAI Text Generation Guide](https://developers.openai.com/api/docs/guides/text)
- [OpenAI Function Calling Guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI Structured Outputs Guide](https://developers.openai.com/api/docs/guides/structured-outputs)
