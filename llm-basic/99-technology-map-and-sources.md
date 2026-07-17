---
title: 截至 2026 年中的技术地图与来源
aliases:
  - LLM Technology Map and Sources
  - 2026 LLM 技术地图
tags:
  - llm-basic
  - sources
  - technology-map
status: active
created: 2026-07-17
last_reviewed: 2026-07-17
---

# 截至 2026 年中的技术地图与来源

> [!important] 一句话核心
> 现代 LLM 的演进并不是一条单线的“更大模型”路线，而是在表示与注意力、位置与长上下文、稀疏容量、推理服务、后训练和多模态输入之间持续权衡；具体产品能力变化快，必须与稳定原理分开记录和验证。

## 如何使用这张地图

本文的核验日期是 2026-07-17。它提供阅读入口和产品比较方法，不把任一厂商的临时规格、价格、排行榜或营销表述提升为跨模型结论。实现某个 Agent 时，应再访问目标模型的当前模型卡和 API 文档，并在自己的样本上评估。

| 层 | 关键技术 | 解决的核心问题 | Agent 开发者最该关心的结果 |
|---|---|---|---|
| 基础架构 | Transformer、Decoder-only、MHA、FFN | 如何在序列中混合信息并生成后续 token | context、输出串行性、长输入的资源与可靠性 |
| 位置与长输入 | RoPE、上下文扩展、in-context learning、KV cache、GQA/MQA | 如何表达顺序、以示例临时塑形行为并降低自回归服务成本 | 长窗口不是可靠记忆；示例不是训练/授权；首 token、内存和检索 eval |
| 容量与服务 | MoE、FlashAttention、推测解码、批处理/缓存 | 在成本与延迟受限下提高容量和吞吐 | 端到端成本/延迟实测，避免从架构名称推断能力 |
| 后训练 | SFT、RLHF/PPO、DPO、GRPO、KTO、SimPO | 将预训练模型调整为更可用、偏好对齐的助手 | 指令和安全倾向不是权限或事实保证 |
| 多模态 | ViT、CLIP、投影、cross-attention、视觉 token | 把画面、文本和其他模态联结 | 明确输入覆盖与跨模态证据；不能假定模型“看见全部” |
| 视频理解 | 时序位置、帧采样、token 压缩、长视频记忆/检索 | 在有限预算下处理动作、顺序和长时长 | 采样覆盖、时间定位、计数/因果边界与审计证据 |

对应正文：[[01-transformer-and-token-flow|架构与 token]]、[[02-training-alignment-and-behavior|训练与对齐]]、[[03-context-memory-and-long-inputs|长输入]]、[[04-inference-and-modern-architecture|推理服务]]、[[10-multimodal-video-input-and-fusion|多模态融合]]、[[11-video-temporal-reasoning-and-long-video|视频时序建模]]。

## 基础与长上下文来源

| 主题 | 一手来源 | 本系列采用的结论 |
|---|---|---|
| Transformer | [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | attention、multi-head、FFN 与位置机制构成序列建模基础 |
| RoPE | [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864) | 通过旋转 query/key 编入相对位置；不代表无限可靠长度外推 |
| MoE | [Switch Transformers](https://arxiv.org/abs/2101.03961) | 稀疏 expert 路由让总容量与每 token 激活计算分离 |
| GQA | [GQA: Training Generalized Multi-Query Transformer Models](https://arxiv.org/abs/2305.13245) | 分组共享 KV head 以折中质量与推理带宽/内存 |
| 推测解码 | [Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192) | draft/target 协同的推理加速，不是能力升级 |
| 长 context 退化 | [Lost in the Middle](https://arxiv.org/abs/2307.03172) | 长输入中的信息位置会影响利用率，须按任务实测 |
| In-context learning | [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) | context 中的示例可临时改变任务行为，不等于参数更新、长期记忆或授权 |

## 训练与对齐来源

| 主题 | 一手来源 | 适合建立的直觉 |
|---|---|---|
| RLHF / InstructGPT | [Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155) | 人类偏好/奖励可将基础模型调整为更符合指令的助手 |
| DPO | [Direct Preference Optimization](https://arxiv.org/abs/2305.18290) | 可直接从 chosen/rejected 偏好对学习相对偏好 |
| GRPO | [DeepSeekMath](https://arxiv.org/abs/2402.03300) | 同组相对奖励适合含可验证回报的推理训练研究 |
| KTO | [KTO: Model Alignment as Prospect Theoretic Optimization](https://arxiv.org/abs/2402.01306) | 可使用二元好/坏的反馈信号，而非严格偏好对 |
| SimPO | [SimPO: Simple Preference Optimization](https://arxiv.org/abs/2405.14734) | 以更直接的偏好优化目标简化训练形式 |

> [!warning] 不从论文标题推导生产默认项
> 上述论文说明方法与实验条件，不证明某方法在所有模型、语言、任务、安全目标或成本约束下最优。若你负责微调，需基于数据质量、奖励可验证性、安全需求和离线/在线 eval 选择；若你开发 Agent，重点是将模型当作会随训练和版本变化的依赖。

## 多模态与视频理解来源

| 主题 | 一手来源 | 本系列采用的结论 |
|---|---|---|
| ViT | [An Image is Worth 16x16 Words](https://arxiv.org/abs/2010.11929) | 图像可切为 patch 并用 Transformer 处理，细节与 token/成本存在权衡 |
| CLIP | [Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020) | 图文对比学习能建立共享表示；不是所有 VLM 的同义词 |
| LLaVA | [Visual Instruction Tuning](https://arxiv.org/abs/2304.08485) | 视觉编码器与语言模型对齐是视觉指令模型的一种典型路线 |
| VideoMAE | [VideoMAE](https://arxiv.org/abs/2203.12602) | 视频表征可利用时空 patch 与自监督预训练 |
| 时空注意力 | [TimeSformer](https://arxiv.org/abs/2102.05095) | 视频理解需要建模空间与时间，不是逐帧图像问答的简单相加 |
| 长视频记忆 | [MovieChat](https://arxiv.org/abs/2307.16449) | 稀疏记忆/压缩是长视频理解的重要方向，同时引入信息丢失风险 |
| 音频事件检测 | [Audio Set](https://arxiv.org/abs/1705.02315) | 音频事件分类与 ASR 是不同能力，视频系统应按任务分别评估 |

## 产品能力对比：正确的维护方式

用户 roadmap 提及 Gemini、GPT、Claude 与 Qwen。它们应作为待核验产品入口，而不是写入稳定正文的排行榜。每次选型需记录目标日期、地区/账户、模型版本、API 与输入方式；不同入口可能具有不同模态、文件、工具、上下文和速率限制。

| 产品/系列 | 当前应查的一手入口 | 选择前必须亲自核验 |
|---|---|---|
| OpenAI GPT 系列 | [OpenAI model guide](https://developers.openai.com/api/docs/guides/latest-model) 与目标模型页 | 当前模型 ID/快照、允许输入模态、文件/视频处理实际方式、context/输出限制、工具与 structured output 支持 |
| Google Gemini 系列 | [Gemini model documentation](https://ai.google.dev/gemini-api/docs/models) | 目标版本的视频/音频/图像输入、长上下文限制、文件处理、grounding/tool 功能和计费 |
| Anthropic Claude 系列 | [Claude models overview](https://platform.claude.com/docs/en/about-claude/models/overview) | 目标模型的视觉/文档能力、上下文、tool use、区域与 API 约束；不要从模型名推断视频支持 |
| Qwen2.5-VL | [Qwen2.5-VL model card](https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct) 与官方仓库/技术报告 | 具体 checkpoint、开源权重/推理栈、图像/视频预处理、语言、硬件和许可条件 |

截至本次核验，上表链接可访问；它们不会自动证明某项具体能力在你的账户和工作负载上可用。应以目标 API 的当前文档和最小真实请求复核。产品页持续变化，因此不在本文固化比较结论或 benchmark 数字。

## 每次新增或更新模型时的复查协议

1. 固定任务契约和代表性 eval 集，保留旧模型 baseline。
2. 从厂商官方模型页/API reference 获取模型 ID、输入模态、限制、定价/计费和弃用状态。
3. 单独验证输入预处理：视频是否原生接收，ASR、音频事件、字幕/OCR 是否被处理，统一时间轴和时间戳精度如何定义。
4. 在相同输入、prompt、tools/schema、采样设置下比较质量、状态原因码、证据回查率、人工复核负载、延迟和成本。
5. 将产品级观察与稳定机理分开记录；不能确认的事项标为未确认，而不是根据营销词补全。
6. 更新涉及笔记的 last_reviewed 和来源，不重写已被一手资料支持的稳定原理。

## 相关笔记

- [[00-overview|面向 Agent 开发的 LLM 基础认知]]
- [[02-training-alignment-and-behavior|训练、对齐与模型行为]]
- [[10-multimodal-video-input-and-fusion|视频输入与多模态融合]]
- [[20-agent-design-decision-guide|Agent 设计决策指南]]
