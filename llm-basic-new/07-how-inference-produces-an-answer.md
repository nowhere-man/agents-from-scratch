---
title: 一次推理怎样生成回答
aliases: [LLM 推理全过程]
tags: [llm-basic, inference, decoding]
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
---

# 一次推理怎样生成回答

> [!abstract] 本章只回答一个问题
> 用户提交一段文本后，从请求进入服务到回答结束，具体发生了什么？

## 前置知识

前面已经讲过 Token、Transformer、权重和助手模型。推理时使用已经训练好的固定权重，不执行反向传播。

## 一次请求的全流程

~~~mermaid
flowchart LR
    A[消息与配置] --> B[拼成模型输入]
    B --> C[Tokenization]
    C --> D[Prefill]
    D --> E[最后位置的 Logits]
    E --> F[选择下一个 Token]
    F --> G[Decode]
    G --> H{停止了吗}
    H -->|否| E
    H -->|是| I[返回回答]
~~~

## 1. 服务构造模型实际看到的输入

用户输入框中的文字不一定是模型的全部输入。一次调用还可能包含系统指令、历史消息、工具定义、检索材料和输出格式要求。服务会加入角色和边界标记，形成一个 Token 序列。

模型不会自动读取输入之外的聊天窗口、数据库或互联网。

## 2. Tokenization

Tokenizer 把完整输入转换成 Token ID。Token 数量影响上下文限制、Prefill 计算、KV Cache、费用和延迟。

Context Window 是一次推理容纳输入和输出 Token 的工作区。它不是长期记忆，也不保证放进去的信息都能被同样可靠地利用。

## 3. Prefill 处理全部输入

Prefill 把输入 Token 一起送过所有 Transformer 层。Causal Mask 保证每个位置只能读取自己和之前的位置，但硬件可以并行计算许多位置。

每层会产生新的隐藏状态，以及后续生成需要使用的 Key 和 Value。最后一个输入位置的隐藏状态被投影成词表 Logits，得到第一个输出 Token 的分布。

输入很长时，Prefill 通常显著影响首 Token 延迟。

## 4. KV Cache 避免重复计算

生成一个 Token 后，模型需要继续预测。历史位置在各层的 K/V 不会改变，因此系统把它们缓存起来。

下一轮只需要计算新 Token 的 Q/K/V，用新 Query 读取历史 K/V，再把新 K/V 追加到 Cache。

KV Cache 保存的是 Attention 使用的历史数值表示，不是长期记忆。它随并发、层数、序列长度、KV Head 数和数值精度增长。

## 5. 从 Logits 选择 Token

Logits 是词表中每个 Token 的原始分数。Softmax 把它们变成概率，解码策略再选择一个 Token。

### Temperature

$$
p_i=\operatorname{softmax}(z_i/T)
$$

它意味着：$T$ 较低时，高分 Token 的优势更明显；$T$ 较高时，候选概率更接近，采样更多样。

Temperature 不会增加知识，也不是严格的“创造力旋钮”。它改变的是从已有分布选词的随机程度。

### Top-p

Top-p 按概率从高到低选出累计概率达到阈值的最小集合，再只从这个集合采样。它过滤长尾候选，但不验证内容真假。

## 6. Decode 逐 Token 循环

Prefill 处理全部输入；Decode 每轮通常只处理刚生成的一个 Token，并读取历史 KV Cache。

下一步依赖上一步结果，所以整个回答难以完全并行生成。每一步还要读取大量历史 K/V，生成经常受内存带宽限制。输出越长，循环次数越多。

## 7. 什么时候停止

生成可能因结束 Token、停止序列、最大输出长度、工具协议、安全策略、超时或错误而停止。达到长度上限时，回答可能被截断，这不代表模型认为任务已经完成。

## Streaming 改变什么

流式返回把已生成片段陆续发送给客户端，改善感知延迟。它通常只改变结果的传输时机，不改变核心预测过程。

## 为什么相同输入可能得到不同回答

来源包括采样随机性、数值实现、模型或系统指令版本、隐藏模板、工具和检索结果变化。Temperature 为 0 可以减少采样差异，但不能让整个远程服务跨时间完全确定。

## 模型是否先想完再回答

普通自回归生成逐 Token 计算和输出。某些推理模型可能在最终答案前使用额外内部 Token、搜索或工具步骤，但仍要区分隐藏状态、模型生成的可读推理文本、服务保留的内部过程和最终答案。

可读“思考步骤”是生成文本，不是神经网络全部内部计算的完整转录。

## 常见推理优化

- **Prefix Cache**：复用相同前缀的部分计算，不是新增长期记忆；
- **Quantization**：用更少位数表示权重或 Cache，降低内存和带宽；
- **Speculative Decoding**：快速模型先提候选，目标模型批量验证，主要提升速度；
- **Continuous Batching**：动态组合不同请求，提高硬件利用率。

这些技术主要改变服务效率，不应自动解释成模型能力增强。

> [!important] 推理的本质
> 参数提供训练形成的计算规律，Context 提供本次请求的条件，推理系统执行前向计算和逐 Token 解码。

## 理解检查

1. Prefill 和 Decode 有什么不同？
2. KV Cache 保存什么，为什么能减少重复计算？
3. Temperature 改变了知识还是选词分布？
4. Streaming 为什么通常不改变核心预测？
5. 最大 Context Window 为什么不是可靠使用容量？

## 参考资料

- [Fast Transformer Decoding](https://arxiv.org/abs/1911.02150)
- [PagedAttention](https://arxiv.org/abs/2309.06180)
- [Speculative Decoding](https://arxiv.org/abs/2211.17192)
- [Lost in the Middle](https://arxiv.org/abs/2307.03172)

## 下一章

继续阅读 [[20-openai-api-request-anatomy|OpenAI API 请求由什么组成]]。
