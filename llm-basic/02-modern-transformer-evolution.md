---
title: 现代 Transformer 的模块演进
aliases:
  - Transformer 现代架构
  - Transformer 模块优化
tags:
  - llm-basic
  - transformer
  - architecture
status: active
created: 2026-07-17
last_reviewed: 2026-07-17
sources:
  - https://arxiv.org/abs/1706.03762
  - https://arxiv.org/abs/1911.02150
  - https://arxiv.org/abs/2002.05202
  - https://arxiv.org/abs/2104.09864
  - https://arxiv.org/abs/2101.03961
  - https://arxiv.org/abs/2305.13245
  - https://arxiv.org/abs/2307.08621
  - https://arxiv.org/abs/2312.00752
---

# 现代 Transformer 的模块演进

> [!abstract] 本文回答什么
> 原始 Transformer 的哪些部分仍是主干？现代技术分别解决了计算、显存、带宽、训练稳定性和长序列中的什么问题？哪些是实现优化，哪些真正改了模型架构，哪些替代路线仍未全面取代 Transformer？

## 先看结论：不是一个“新架构”整体替换旧架构

截至 2026-07，现代通用大模型仍普遍保留以下骨架：

```text
离散或多模态输入表示
→ 重复的序列信息混合模块
→ 重复的逐位置非线性模块
→ 残差与归一化
→ 自回归输出
```

真正发生的是模块级演进：

| 原始部件 | 现代常见变化 | 变化性质 |
|---|---|---|
| MHA | GQA/MQA、KV 压缩、局部/稀疏 attention | 架构改变，主要降低推理资源 |
| Attention 计算 | IO-aware 分块、融合 kernel | 等价实现优化，不改变数学结果 |
| ReLU FFN | GELU、SwiGLU 等门控 FFN | 架构与激活改变 |
| Dense FFN | 稀疏 MoE | 容量与计算分离 |
| Post-Norm LayerNorm | Pre-Norm、RMSNorm、残差缩放 | 训练稳定性与效率改变 |
| 绝对位置 | RoPE、相对位置、长度扩展 | 位置表达改变 |
| 全局 quadratic attention | 局部、滑窗、稀疏、线性或状态空间模块 | 长序列替代/混合路线 |

> [!important] 判断一项技术时先问三个问题
> 它是否改变模型可学习的函数？是否只用更好的 kernel 计算同一函数？它降低的是训练计算、推理显存、内存带宽还是生成的串行轮次？

## 1. Attention 的两个不同瓶颈

设序列长度为 $n$，head 维度为 $d_h$。标准 attention 的 score matrix 为：

$$
S=QK^\top \in \mathbb{R}^{n\times n}
$$

这带来两个容易混淆的问题：

1. **训练或 prefill 的二次计算与中间状态**：所有 query 与所有 key 两两交互，核心计算量近似 $O(n^2d_h)$。
2. **自回归 decode 的 KV cache**：生成每个新 token 时，需要读取此前所有层保存的 key/value，瓶颈常从算力转为显存容量和内存带宽。

不同优化针对不同问题；“减少 attention 矩阵”和“减少 KV head”不是同一件事。

## 2. MHA、GQA 与 MQA：减少 KV Cache

Multi-Head Attention 中，每个 query head 都有独立的 key/value head。记 query head 数为 $H_q$，KV head 数为 $H_{kv}$：

| 结构 | $H_{kv}$ | 特点 |
|---|---:|---|
| MHA | $H_q$ | 表达自由度高，KV cache 最大 |
| GQA | $1 < H_{kv} < H_q$ | 多个 query head 共享一组 KV，质量与资源折中 |
| MQA | $1$ | 所有 query head 共享 KV，cache 最小 |

忽略批量、数据类型和其他状态，每层 KV cache 元素数近似为：

$$
N_{KV}=2nH_{kv}d_h
$$

其中 2 代表 key 和 value。把 $H_{kv}$ 从 $H_q$ 减少到更小的值，会按比例降低 KV cache、读取带宽和通信量。

这不是减少 query head；模型仍可保留多组 query 表达。代价是多个 query head 共享 KV 表示，可能降低部分表达自由度。GQA 是常见折中，而不是所有任务唯一最优解。

### 更进一步：压缩 KV 表示

另一条路线不是直接共享完整 KV head，而是把历史信息压缩为低维 latent，再在需要时投影成 attention 所需表示。抽象地写：

$$
c_i=W_c h_i, \qquad d_c \ll d_{KV}
$$

缓存 $c_i$ 而不是完整 key/value，可进一步减少 cache。其取舍是增加投影设计、实现复杂度，并可能损失被压缩的信息。核心思想仍是：==decode 阶段最昂贵的资源之一是反复读取历史表示==。

## 3. IO-aware Attention：数学不变，实现改变

标准写法看似必须显式生成 $n\times n$ attention matrix，但可以按块计算，并在片上高速存储中维护 softmax 统计量，避免把完整中间矩阵写回高带宽内存。

在线 softmax 的核心合并关系可以抽象为：对不同块维护最大值 $m$ 和指数和 $l$，再稳定合并。最终结果仍等价于：

$$
\operatorname{softmax}(S)V
$$

变化在数据搬运顺序和 kernel 融合，而不在模型学习的函数。因此：

- 通常显著减少中间显存和内存 IO；
- 可以允许更长序列或更大 batch；
- 不会因为名字中有 Attention 就自动提高模型能力；
- 仍不能消除全局 attention 的理论二次计算量。

## 4. 局部、滑动窗口与稀疏 Attention

如果每个 token 只连接邻近 $w$ 个位置，复杂度由全局 attention 的 $O(n^2)$ 变为近似：

$$
O(nw), \qquad w \ll n
$$

稀疏 attention 则定义一个连接集合 $\Omega$，只计算允许的 $(i,j)$：

$$
S_{ij}=\begin{cases}
q_i^\top k_j, & (i,j)\in\Omega \\
-\infty, & \text{otherwise}
\end{cases}
$$

它们的优势是长序列成本更可控；代价是远距离 token 不能在单层直接交互。可以混入少量全局层、全局 token、分块摘要或检索机制补偿。

> [!warning] 支持长输入不等于保留全部信息
> 任何局部、稀疏、压缩或淘汰策略都在定义“哪些历史连接值得保留”。成本下降来自少算、少存或少读；因此必须评估关键事实被删掉或无法传播的风险。

## 5. 线性 Attention：改变计算顺序或核函数

标准 attention 的 softmax 相似度可近似为特征映射的内积：

$$
\exp(q^\top k) \approx \phi(q)^\top\phi(k)
$$

于是可利用结合律先聚合 key/value：

$$
\operatorname{Attn}(q_i)\approx\frac{\phi(q_i)^\top\left(\sum_j\phi(k_j)v_j^\top\right)}{\phi(q_i)^\top\left(\sum_j\phi(k_j)\right)}
$$

核心变化是避免显式构造所有 query-key 对，使序列维度更接近线性。代价是 softmax attention 被近似或替换，可能影响精确内容寻址、稳定性与通用性。它是重要路线，但不能简单说“已经取代 attention”。

## 6. FFN：从普通前馈层到门控与 MoE

### 门控 FFN

现代 FFN 常加入乘法门控。一个典型形式是：

$$
\operatorname{SwiGLU}(x)=\left(\operatorname{SiLU}(xW_g)\odot xW_u\right)W_d
$$

- $W_g$ 产生门控分支。
- $W_u$ 产生内容分支。
- $\odot$ 是逐元素乘法。
- $W_d$ 投影回隐藏维度。

公式说明：输入的不同特征可以动态控制哪些中间特征通过，而不是只对单一路径做固定激活。它通常以参数和计算布局变化换取更好的训练效果。

### 稀疏 Mixture-of-Experts

Dense FFN 对每个 token 使用同一组参数。MoE 准备 $E$ 个 expert，router 为每个 token 只选择 top-$k$：

$$
g(x)=\operatorname{softmax}(W_rx)
$$

$$
y=\sum_{e\in\operatorname{TopK}(g(x))}g_e(x)E_e(x)
$$

这使总参数容量与每个 token 激活的计算量分离。总参数可以很大，但每个 token 只经过少数 expert。

MoE 带来的不是“多个可解释人格”：expert 是训练形成的参数子网络。主要工程取舍包括 router 负载均衡、expert 容量、跨设备通信、训练稳定性和 serving 复杂度。

## 7. Norm 与残差：从 Post-Norm 到更稳定的深层结构

原始 Post-Norm 可简化为：

$$
h'=\operatorname{Norm}(h+F(h))
$$

Pre-Norm 则是：

$$
h'=h+F(\operatorname{Norm}(h))
$$

Pre-Norm 为残差主路径提供更直接的梯度传播，通常更适合训练很深的网络。现代架构也会使用残差缩放、额外归一化或特殊初始化来控制深度增加后的信号幅度。

### RMSNorm

LayerNorm 同时减均值并按方差缩放；RMSNorm 只按均方根缩放：

$$
\operatorname{RMSNorm}(x)=\gamma\odot\frac{x}{\sqrt{\frac{1}{d}\sum_{i=1}^{d}x_i^2+\epsilon}}
$$

它控制向量尺度，但不显式居中，计算更简单。它已成为常见选择，但并不意味着 LayerNorm 在所有结构中失效。

## 8. 位置表示：从绝对位置到相对关系

### RoPE

RoPE 对 query/key 的二维分量按位置旋转：

$$
\begin{pmatrix}x'_{2i}\\x'_{2i+1}\end{pmatrix}=
\begin{pmatrix}\cos(m\theta_i)&-\sin(m\theta_i)\\\sin(m\theta_i)&\cos(m\theta_i)\end{pmatrix}
\begin{pmatrix}x_{2i}\\x_{2i+1}\end{pmatrix}
$$

$m$ 是位置，$\theta_i$ 是不同维度使用的频率。两个已旋转向量的点积自然包含相对位置差，因此适合 attention。

### 长度扩展

位置插值、频率重标定、分段缩放和长 context 继续训练等方法，目标是让模型在训练长度之外仍能处理位置。它们解决“位置表示失配”，却不能单独解决：

- 模型没在长序列上学过对应任务；
- attention 或 KV cache 资源不足；
- 中间位置的信息利用率下降；
- 证据跨很远距离时推理步骤增加。

因此 API 接受的最大长度不是可靠有效长度。

## 9. 状态空间模型：替代部分序列混合模块

状态空间模型用一个递归状态压缩历史：

$$
h_t=A_th_{t-1}+B_tx_t, \qquad y_t=C_th_t+D_tx_t
$$

- $h_t$ 是到位置 $t$ 为止的压缩状态。
- 每个新 token 只更新状态，不必显式读取所有历史 KV。
- 训练时可使用并行扫描等方法，推理时状态大小可以与序列长度近似无关。

它的优势是线性序列处理和高效流式推理；限制是历史被压入固定状态后，精确回看某个任意位置不像 attention 那样直接。

截至 2026-07，更准确的技术判断是：

- attention 仍是强大的内容寻址机制；
- 状态空间、卷积、线性 attention 等提供更便宜的序列混合；
- 混合架构让部分层承担长期压缩，部分 attention 层承担精确检索；
- 尚不存在一条在所有通用任务上无条件取代 Transformer 主干的路线。

## 10. 哪些技术真正改变能力

| 技术 | 模型函数是否变化 | 主要收益 | 主要代价 |
|---|---|---|---|
| IO-aware / fused attention | 否，通常数学等价 | 减少 IO 与中间显存 | 依赖硬件和 kernel |
| GQA/MQA | 是 | 降低 KV cache 与 decode 带宽 | KV 表达共享 |
| 局部/稀疏 attention | 是 | 长序列少算 | 远程连接受限 |
| 门控 FFN | 是 | 更强的特征选择 | 参数与计算布局变化 |
| MoE | 是 | 大容量、稀疏激活 | 路由、通信和负载均衡 |
| RMSNorm/Pre-Norm | 是 | 稳定和简化训练 | 需配合整体结构 |
| RoPE/长度扩展 | 是 | 相对位置与更长输入 | 不保证长 context 任务质量 |
| 状态空间/混合层 | 是 | 线性流式处理 | 历史压缩带来检索取舍 |
| Masked diffusion 生成 | 是，生成范式改变 | 多位置迭代更新、潜在并行性 | 多轮去噪、调度与 serving 生态不同 |

### 生成范式的替代探索

除了替换 Transformer 内部模块，还有路线直接改变“怎样生成序列”。Masked diffusion language model 从被遮挡或带噪序列开始，通过多轮并行修复得到完整输出，而不是严格从左到右每轮确认一个 token。抽象地写：

$$
x^{(T)} \rightarrow x^{(T-1)} \rightarrow \cdots \rightarrow x^{(0)}
$$

其中 $x^{(T)}$ 是高度遮挡或带噪序列，$x^{(0)}$ 是最终序列。它可能并行更新多个位置，并支持双向条件；代价是需要多轮迭代、置信度调度和不同的缓存/服务系统。

截至 2026-07，更稳妥的判断是：这是活跃且重要的生成范式探索，尤其关注并行解码效率，但尚不能概括为已替代自回归主干。它与状态空间路线不同：前者主要改变生成过程，后者主要改变序列混合与状态表示。

## 对 Agent 开发的含义

1. 不要从模型使用某种架构名直接推断任务能力；能力还取决于数据、后训练和推理策略。
2. 长 context 技术解决“可以计算”的问题，不自动解决“可靠找到并正确使用”的问题。
3. MoE 的总参数量不能直接换算为单次调用计算量，也不能直接与 dense 模型比较。
4. KV 优化主要影响并发、成本和延迟；不会让同一权重突然获得新知识。
5. Agent 选型应以目标任务 eval 为准，而不是以模块列表或最大 context 数字为准。

## 概念检查

- [ ] 能区分 attention 的 $n^2$ 中间计算问题与 decode KV cache 问题。
- [ ] 能根据 $H_{kv}$ 解释 MHA、GQA、MQA 的资源差异。
- [ ] 能说明 IO-aware attention 为什么不是能力升级。
- [ ] 能解释 MoE 如何把总参数与激活参数分开。
- [ ] 能说明状态空间模型的固定状态为何既是优势也是限制。
- [ ] 不使用“某模块已被彻底淘汰”这种缺少条件的结论。

## 继续阅读

- [[03-inference-context-and-efficiency|推理、Context 与效率]]
- [[04-from-data-to-base-model|从数据到基础模型]]
- [[99-technology-map-and-sources|技术地图与一手来源]]
