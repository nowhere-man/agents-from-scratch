---
title: 截至 2026 年 7 月的技术地图与一手来源
aliases:
  - LLM 技术地图
  - 大模型原理来源索引
tags:
  - llm-basic
  - sources
  - technology-map
status: active
created: 2026-07-17
last_reviewed: 2026-07-17
---

# 截至 2026 年 7 月的技术地图与一手来源

> [!abstract] 使用方式
> 本文只按技术路线组织，不比较具体模型或厂商。论文用于说明方法与实验，不证明某项技术已成为所有生产模型的默认选择。正文中的“现代”表示截至核验日期仍有代表性的主流或前沿路线。

## 稳定主干与演进方向

| 层 | 稳定主干 | 现代演进方向 | 需要避免的误解 |
|---|---|---|---|
| 输入 | 子词 token、embedding | 多模态 token、动态分辨率、专用编码器 | token 是语义原子 |
| 序列混合 | causal self-attention | GQA/MQA、KV 压缩、局部/稀疏/线性 attention、状态空间混合 | 新路线已全面取代 attention |
| 逐位置计算 | Dense FFN | 门控 FFN、稀疏 MoE | expert 是可解释人格 |
| 稳定结构 | 残差、归一化 | Pre-Norm、RMSNorm、残差缩放 | 归一化只是无关实现细节 |
| 位置 | 位置编码 | RoPE、相对位置、长度扩展 | 支持长位置等于可靠长 context |
| 预训练 | next-token prediction | 数据治理、配比、长序列、多阶段/多模态目标 | 参数是训练文档数据库 |
| 后训练 | SFT | 偏好优化、可验证奖励、安全与工具训练 | 对齐产生确定性规则 |
| 推理执行 | prefill + decode + KV cache | 分块 kernel、paged cache、continuous batching、量化、推测解码 | 运行更快等于能力更强 |
| 推理时计算 | 单次采样 | 多候选、搜索、验证、工具反馈 | 更多 token 必然更正确 |
| Agent | 模型条件生成 | Harness、state、tools、policy、eval | Assistant Model 就是 Agent |

## 来源选择规则

1. 优先原始论文、技术报告和标准文档。
2. 论文证明“在其设定下有效”，不证明通用最优或生产采用率。
3. 将算法、开源实现、特定硬件 kernel 和产品能力分开。
4. 不根据具体模型名称反推未公开架构。
5. 动态结论应注明核验日期，并在更新时重新检查来源。

## Transformer 与基本训练目标

| 主题 | 一手来源 | 本系列使用的结论 |
|---|---|---|
| Transformer | [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | attention、multi-head、FFN、残差和位置构成原始序列建模框架 |
| 子词切分 | [SentencePiece](https://arxiv.org/abs/1808.06226) | 字符串通过数据驱动词表变成 token；token 不等于词 |
| 自回归规模化 | [Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361) | loss 与容量、数据和计算呈经验规律，不直接保证具体任务 |
| 计算最优训练 | [Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556) | 参数量与训练 token 需要平衡 |
| In-context learning | [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) | context 示例可临时塑形行为，不是参数更新 |

对应正文：[[01-token-embedding-and-transformer|Token、Embedding 与 Transformer]]、[[04-from-data-to-base-model|从数据到基础模型]]。

## Attention、FFN、位置与混合架构

| 主题 | 一手来源 | 技术特点 |
|---|---|---|
| MQA | [Fast Transformer Decoding](https://arxiv.org/abs/1911.02150) | 共享 KV head，减少自回归 decode 的 cache 与带宽 |
| GQA | [GQA: Training Generalized Multi-Query Transformer Models](https://arxiv.org/abs/2305.13245) | 以多组 KV 在 MHA 与 MQA 间折中 |
| IO-aware attention | [FlashAttention](https://arxiv.org/abs/2205.14135) | 分块与 IO 优化，数学上计算同类 attention |
| 更高效的 IO-aware attention | [FlashAttention-2](https://arxiv.org/abs/2307.08691) | 改进并行划分和工作分配 |
| 门控 FFN | [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202) | 乘法门控增强逐位置非线性变换 |
| 稀疏 MoE | [Switch Transformers](https://arxiv.org/abs/2101.03961) | 总容量与每 token 激活计算分离 |
| RMSNorm | [Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467) | 只按均方根缩放，简化归一化 |
| RoPE | [RoFormer](https://arxiv.org/abs/2104.09864) | 对 query/key 旋转以表达相对位置 |
| 线性偏置位置 | [Train Short, Test Long: ALiBi](https://arxiv.org/abs/2108.12409) | 直接对 attention score 加距离偏置 |
| 选择性状态空间 | [Mamba](https://arxiv.org/abs/2312.00752) | 以输入相关状态更新实现线性序列建模 |
| 混合状态空间 | [Transformers are SSMs](https://arxiv.org/abs/2405.21060) | 探索状态空间与 attention 类机制的统一/混合 |
| Masked diffusion 语言模型 | [Discrete Diffusion Modeling by Estimating the Ratios of the Data Distribution](https://arxiv.org/abs/2310.16834) | 以迭代去噪/解遮挡代替严格左到右生成 |
| Diffusion LLM 高效推理综述 | [Accelerating Masked Diffusion Large Language Models](https://arxiv.org/abs/2607.12829) | 截至 2026-07 的并行解码、步数与缓存优化路线综述 |

对应正文：[[02-modern-transformer-evolution|现代 Transformer 的模块演进]]。

## Context 与推理系统

| 主题 | 一手来源 | 技术特点 |
|---|---|---|
| 长 context 利用退化 | [Lost in the Middle](https://arxiv.org/abs/2307.03172) | 信息位置影响长输入任务表现 |
| Paged KV cache | [Efficient Memory Management for LLM Serving with PagedAttention](https://arxiv.org/abs/2309.06180) | 以分页思想降低 KV 分配碎片 |
| Speculative decoding | [Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192) | draft 提议、target 验证，保持目标分布的加速路线 |
| 并行候选验证 | [Accelerating Large Language Model Decoding with Speculative Sampling](https://arxiv.org/abs/2302.01318) | 使用小模型候选减少大模型串行步骤 |
| KV cache 量化 | [KIVI](https://arxiv.org/abs/2402.02750) | 使用低比特表示降低长 context KV 内存 |
| KV cache 驱逐 | [H2O](https://arxiv.org/abs/2306.14048) | 保留高影响 token，减少 cache；存在信息选择风险 |
| 推理时搜索 | [Tree of Thoughts](https://arxiv.org/abs/2305.10601) | 通过多候选、评估与搜索扩展运行时计算 |

对应正文：[[03-inference-context-and-efficiency|推理、Context 与效率]]。

## 指令、偏好与强化学习后训练

| 主题 | 一手来源 | 技术特点 |
|---|---|---|
| SFT + RLHF | [Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155) | 示范建立 Assistant 行为，偏好 reward 继续优化 |
| DPO | [Direct Preference Optimization](https://arxiv.org/abs/2305.18290) | 直接从 chosen/rejected 学习相对偏好 |
| KTO | [KTO](https://arxiv.org/abs/2402.01306) | 使用二元 desirable/undesirable 反馈 |
| 组内相对优化 | [Group Relative Policy Optimization 原始技术来源](https://arxiv.org/abs/2402.03300) | 用同组 reward 构造相对优势，适合可验证奖励研究 |
| SimPO | [SimPO](https://arxiv.org/abs/2405.14734) | 无显式参考模型的简化偏好目标 |
| Constitutional feedback | [Constitutional AI](https://arxiv.org/abs/2212.08073) | 用规则和模型反馈生成修订与偏好信号 |

对应正文：[[05-from-base-model-to-assistant-model|从基础模型到 Assistant Model]]。

> [!warning] 方法选择没有脱离数据的默认答案
> SFT、偏好优化和 RL 方法解决的是不同数据与目标如何转成参数更新。训练样本、reward/verifier、覆盖、安全目标和 eval 决定最终行为，不能从算法名称推出“更对齐”或“更会推理”。

## 能力、校准与失败机制

| 主题 | 一手来源 | 本系列使用的结论 |
|---|---|---|
| 涌现能力观察 | [Emergent Abilities of Large Language Models](https://arxiv.org/abs/2206.07682) | 某些任务指标随规模呈非线性变化 |
| 涌现指标分析 | [Are Emergent Abilities of Large Language Models a Mirage?](https://arxiv.org/abs/2304.15004) | 离散 metric 可制造突变观感，应看连续指标 |
| Chain-of-Thought prompting | [Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903) | 中间文本可扩展部分任务计算，但不是正确性证明 |
| Self-consistency | [Self-Consistency Improves Chain of Thought Reasoning](https://arxiv.org/abs/2203.11171) | 多轨迹投票可能提高可聚合答案的成功率 |
| 间接注入 | [Not what you've signed up for](https://arxiv.org/abs/2302.12173) | 外部数据中的指令可影响工具增强模型 |
| 语言模型校准 | [Language Models (Mostly) Know What They Know](https://arxiv.org/abs/2207.05221) | 校准依赖任务与表达方式，不能把自然语言信心当通用概率 |

对应正文：[[06-capabilities-and-their-origins|模型能力及其来源]]、[[07-limitations-and-failure-mechanisms|能力边界与失败机制]]、[[08-using-assistant-models-in-agents|在 Agent 中正确使用 Assistant Model]]。

## 多模态与视频

| 主题 | 一手来源 | 技术特点 |
|---|---|---|
| 图像 patch Transformer | [An Image is Worth 16x16 Words](https://arxiv.org/abs/2010.11929) | 把图像切成 patch 序列 |
| 图文对比对齐 | [CLIP](https://arxiv.org/abs/2103.00020) | 匹配图文拉近、非匹配推远 |
| 图文生成对齐 | [Visual Instruction Tuning](https://arxiv.org/abs/2304.08485) | 将视觉编码器表示接入语言模型并进行指令训练 |
| 时空 attention | [TimeSformer](https://arxiv.org/abs/2102.05095) | 分解或联合建模空间和时间 |
| 视频遮挡建模 | [VideoMAE](https://arxiv.org/abs/2203.12602) | 以时空 patch 自监督学习视频表示 |
| 音频事件数据 | [AudioSet](https://research.google.com/audioset/) | 音频事件分类与语音识别是不同任务 |

对应正文：[[09-multimodal-language-models|多模态大模型专项]]。

## 术语状态说明

正文使用三种措辞，避免伪造确定性：

- **常见主干**：在现代通用模型中具有广泛代表性的结构或机制。
- **重要路线**：有充分研究与实现价值，但采用取决于场景。
- **替代/混合探索**：旨在替代部分 Transformer 组件，尚不能概括为通用全面替代。

不使用“截至 2026 所有模型都已采用”“某技术彻底淘汰另一技术”一类无法由公开技术路线支持的表述。

## 更新协议

1. 先判断新内容改变的是架构、训练目标、执行优化还是 Agent 系统。
2. 找到原始来源，记录它解决的问题、实验条件和限制。
3. 不因单篇论文或单个实现就把路线标成行业默认。
4. 更新正文对应模块的“问题 → 机制 → 收益 → 代价”。
5. 检查所有 wikilink、公式和 Mermaid。
6. 更新 `last_reviewed`，并在目标 Agent 任务上保留独立 eval。

## 阅读入口

- [[00-overview|面向 Agent 开发的 LLM 基础]]
- [[02-modern-transformer-evolution|现代 Transformer 的模块演进]]
- [[05-from-base-model-to-assistant-model|从基础模型到 Assistant Model]]
- [[08-using-assistant-models-in-agents|在 Agent 中正确使用 Assistant Model]]
