---
type: Roadmap
---

# AI Agents Roadmap

## LLM 基础

目标：知道 LLM 为什么能工作、为什么会错、能力边界在哪。

- **Transformer**：attention、token、embedding、position encoding（RoPE / ALiBi）、decoder-only、KV Cache
- **训练流程**：pretraining → SFT → RLHF / DPO / KTO / ORPO / **GRPO**（DeepSeek-R1）/ RLAIF / Constitutional AI
- **推理参数**：temperature、top_p、max tokens、streaming、latency、吞吐、上下文窗口
- **模型类型**：base / instruction / **reasoning model（o1、R1 风格 long-CoT）** / embedding / reranker / reward model
- **Inference-Time Scaling**：Best-of-N、Self-Consistency 投票、Process Reward Model (PRM)、Speculative Decoding
- **能力边界**：幻觉、上下文遗忘、长文衰减（Lost in the Middle）、时序理解弱点、工具误用、非确定性
- **Scaling Law、涌现能力**

---

## Prompt Engineering

目标：能稳定让模型按业务格式输出。

- system / developer / user 指令分层
- Zero-shot / Few-shot / 反例 / 风格迁移
- **CoT、Self-Consistency、Self-Refine、Step-Back、Least-to-Most**
- **JSON Mode、JSON Schema、Structured Output**
- **Constrained Decoding**：Outlines、guidance、Pydantic / Zod
- Prompt 版本管理、prompt diff、prompt regression test
- **文案生成专项**：角色、语气、节奏、素材事实、禁止编造、改写与续写边界

---

## Context Engineering

目标：会设计"喂给模型什么上下文"，而不是只会写 prompt。

- 上下文预算：进 prompt / 检索 / 丢弃 三分
- 摘要压缩、分层上下文、滑动窗口、conversation state
- **Lost in the Middle 现象与缓解**（重要文档放头尾）
- **Prompt Caching**（Anthropic / OpenAI / Gemini / DeepSeek，命中能省 50–90%）
- **Semantic Cache**（按语义相似度命中）
- **长上下文 vs RAG 的取舍决策框架**
- 多模态上下文：关键帧、字幕、ASR、OCR、镜头边界、人物、动作、音频事件
- **Context ≠ Memory**：context 是本次推理材料，memory 是跨任务状态


---

## 多模态专项

- **视频切分**：shot detection、scene detection、keyframe extraction
- **ASR**：语音转文字、说话人分离（diarization）、时间戳
- **OCR**：字幕、屏幕文字
- **视觉理解**：人物、动作、场景、物体、情绪、镜头运动
- **音频理解**：音乐、笑声、尖叫、环境声、情绪转折
- **Temporal Grounding**：某事发生在第几秒到第几秒
- **Dense Captioning**：每个片段细粒度描述
- **多模态 Embedding**：CLIP、SigLIP、Jina-CLIP、Nomic Embed Vision
- **多模态模型选型**：Qwen2.5-VL、Gemini 1.5 / 2.5（长视频原生）、GPT-4o、InternVL、LLaVA-Video、Apollo、MiniCPM-V、VideoChat、LongVU
- **视频 token 成本控制**：抽帧策略、clip、低/高 FPS、token merging、缓存
- **长视频压缩思路**：VideoChat、LongVU、Video-Salmonn

---

## RAG

目标：让模型基于可更新资料和案例写作，而不是凭参数记忆。

### 基础
- Embedding、chunking 策略（固定 / 语义 / 递归）、metadata
- 向量库：pgvector、Qdrant、Milvus、Weaviate、LanceDB、Chroma

### 进阶
- **Hybrid Search**（BM25 + 向量加权融合）
- **Reranker**：Cohere Rerank、bge-reranker、Jina Reranker（**RAG 提质 ROI 最高的一步**）
- Query Rewriting、Multi-Query、RAG-Fusion、HyDE
- Parent-Child / Small-to-Big / Sentence-Window

### 自适应 / 结构化
- **Self-RAG、CRAG**（判断要不要检索 / 检索结果是否可信）
- **Agentic RAG**（让 agent 自己决定检索路径）
- **GraphRAG（微软）**、LightRAG、Knowledge Graph + LLM

### 多模态 RAG（与你项目最相关）
- **ColPali / ColQwen**（视觉文档 / 关键帧检索）
- 视频帧 + 字幕 + 音频联合检索
- Video Moment Retrieval（时间戳级证据回链）

### 评测
- RAGAS、TruLens：召回率、命中率、Faithfulness、引用准确性、Context Precision/Recall

### 你项目的核心索引
- 风格案例库 / 爆点案例库 / 素材事实库 / 标题文案模板库

**产出**：输入"视频主题 + 风格类型" → 检索 5 个相似爆款解说案例 → 生成文案。

---

## Tool Use / Function Calling

目标：模型不只生成文本，还能调用业务能力。

- Function / Tool Calling 流程：请求 → tool call → 应用执行 → 回填结果 → 最终答案
- JSON Schema、Strict Mode、参数校验
- **Parallel Tool Calls**（一次响应里并行调多工具，省 latency）
- 工具选择、工具权限、工具失败重试、错误恢复
- **Tool Retrieval**：工具数量爆炸时，先用向量检索筛工具再交给模型
- **Code Execution Sandbox**：E2B、Daytona、Modal Sandbox、Riza（视频处理脚本、ffmpeg 调用要用）
- **Computer Use / Browser Use**：Anthropic Computer Use、OpenAI Operator、browser-use（爬热点用）
- **MCP（Model Context Protocol）**：Anthropic 推的统一协议，server 暴露 resources / prompts / tools，事实标准
- **A2A Protocol**（Google 推的 Agent 间互通）：了解即可

---

## Agent 核心

目标：理解 Agent = 带状态、工具、计划、反馈的执行系统。

### Agent Loop
- observe → think/plan → act → observe
- Harness Engineering：把 prompt + 工具 + 状态 + 日志 + 评测 + 人审 + 回滚包装成可运行系统（Claude Code、Codex CLI、Cursor Agent 是范式参考）

### 推理范式
- **ReAct**（Reason + Act 交错）
- **Plan-and-Execute / Plan-and-Solve**
- **Reflection / Self-Critique**
- **Reflexion**（带 episodic memory 的反思）
- **Tree of Thoughts (ToT)**
- **Graph of Thoughts (GoT)**
- **LATS**（Language Agent Tree Search，结合 MCTS）

### 协同模式
- Router / Supervisor / Worker
- Handoff
- **Deterministic Workflow vs Autonomous Agent 决策框架**

### Skill 化
- **Anthropic Skills**：能力打包成可发现、按需加载的 skill 包
- CrewAI Tasks / Roles

**产出**：单 Agent 跑通"分析视频素材 → 选择文案策略 → 检索案例 → 生成文案 → 自评 → 修改 → 输出"。

---

## Memory 管理

目标：跨任务、跨会话保持状态与个性化。

- **短期记忆**：当前任务 state、对话历史压缩、Sliding Window、Summary Buffer
- **长期记忆**：用户偏好、风格偏好、历史案例
- **三分法**：Episodic（事件）/ Semantic（事实）/ Procedural（流程）
- 记忆写入策略与遗忘机制
- **Memory 框架**：Mem0、Zep、Letta（前 MemGPT）

**产出**：跨视频的"风格记忆" + "用户偏好记忆"双层。

---

## 工作流框架

目标：知道什么时候用框架、什么时候不用。

**学习顺序**：

1. **不用框架**，手写最小 agent loop（已在阶段 7 做过）
2. **LangGraph** ⭐：状态机 / 图 / 持久化 / 人审 / 恢复，生产级首选
3. **LangChain**：当集成层和工具箱用，**不要把业务核心绑死**
4. **LlamaIndex**：偏数据 / RAG / context augmentation
5. **AutoGen**（微软）：multi-agent team、group chat、swarm、GraphFlow
6. **CrewAI**：role-based agents、Flows + Crews，**贴合文案多角色场景**
7. **OpenAI Agents SDK / Claude Agent SDK**：官方轻量
8. **Pydantic AI**：类型安全 Python 工程化
9. **Smolagents（HF）/ Agno（前 Phidata）/ Haystack**：备选
10. **n8n / Dify / Coze / FastGPT**：低代码工作流，串集成、给非技术同事用

**核心决策原则**：**多数业务用单 Agent + 多 Tool 就够，不要为了多 Agent 而多 Agent**——多 Agent 引入通信成本、上下文割裂、调试困难。

**产出**：同一个"视频文案 Agent"用手写版 + LangGraph 版各实现一遍，对比复杂度。

---

## 多 Agent + HITL + Guardrails

目标：让系统可控、可审、可挡。

### 多 Agent 模式（确认必要再上）
- Supervisor（主管-下属）
- Swarm（去中心化）
- Hierarchical
- Debate / Society of Mind
- Router / Handoff

### Human-in-the-Loop
- 高风险节点暂停
- **Interrupt + Resume**（LangGraph interrupt 是范式参考）
- **三态流**：Approve / Edit / Reject
- Tool Permission：哪些自动执行、哪些必须审批

### Guardrails — 内容侧
- 输入校验、输出校验
- 版权 / 事实 / 敏感内容检查
- 框架：**NeMo Guardrails、Llama Guard、Guardrails AI**

### Guardrails — 对抗安全
- **Prompt Injection**（直接 / 间接）
- **多模态注入**：图片 / 视频帧里嵌入恶意指令的间接注入风险
- Jailbreak 与防护
- 工具滥用防护、最小权限
- PII 脱敏

**产出**：文案系统加 3 个 gate：事实一致性 / 风格一致性 / 人工审核后发布。

---

## Eval / Observability / Debugging

目标：能判断系统有没有变好，而不是靠感觉。

### Observability
- 选一个上：**LangSmith、Langfuse、Arize Phoenix、OpenLLMetry、Helicone、Braintrust**
- Trace：每次模型输入 / 工具调用 / 输出 / 中间状态
- Cost / Latency / Token 监控

### Eval
- **自建评测集**（最关键）：固定测试视频、固定风格、固定业务标准
- Rubric：事实准确 / 爆点 / 连贯 / 节奏 / 可剪辑性 / 违禁风险
- **LLM-as-Judge**（要校准）+ **Pairwise Comparison** + Arena 风格人评
- **Eval 框架**：RAGAS、TruLens、promptfoo、DeepEval、Inspect AI
- **公开 Agent 基准**（借 rubric 思路）：GAIA、τ-bench、AgentBench、SWE-bench、WebArena、OSWorld
- **视频专项基准**：Video-MME、MVBench、LongVideoBench、TempCompass、MMMU
- Regression：prompt 改动不能破坏旧案例

**产出**：30–100 条视频片段评测集，每次 prompt / 模型升级必跑。

---


## 学习路线图详细补充


### 基础认知的原理清单

- **Transformer 架构**：理解 Self-Attention、Multi-Head Attention、位置编码、FFN 的原理即可，不需要手推梯度；同时掌握 BPE/SentencePiece、Token 不等于字或词，以及 Token 对成本和性能的影响。
- **训练与对齐**：理解 Pretrain -> SFT -> RLHF/DPO 三阶段的目的。对齐方法的适用性为：RLHF (PPO) 适合前沿模型和高安全要求；DPO 是通用对齐、领域微调的默认选择；GRPO 用于数学、代码等可验证任务；KTO 适用于只有好/坏二元反馈；SimPO 适用于无需参考模型且算力极受限的情况。
- **推理与边界**：理解 Context Window、Lost in the Middle、Temperature / Top-P / Top-K、KV Cache、推测解码、幻觉、知识截断、推理能力边界与涌现能力。
- **多模态原理**：学习 ViT、CLIP 如何将图像映射到文本空间，Early Fusion / Late Fusion / Cross-Attention / 视觉 Token 化，视频时序建模、帧采样、视觉 Token 压缩和自适应帧选择。关注从 ASR + CV + NLP 管线到原生多模态单次推理的趋势，以及 Gemini 2.5 Pro、GPT-5、Claude Opus 4、Qwen2.5-VL 的能力差异。

### 上下文栈与实践项目

#### 四层 Context Stack

1. **System Layer（宪法层）**：角色、人格与不可变约束。
2. **State Layer（状态层）**：当前任务、近期对话与 Agent Scratchpad。
3. **Memory Layer（记忆层）**：用户偏好、历史决策与已学到的事实。
4. **Retrieval / Tools Layer（检索和工具层）**：RAG 数据与工具返回值。

关键原则：上下文是稀缺资源，长窗口不等于更好；通过摘要压缩、元数据过滤后的选择性检索、子 Agent 上下文隔离和 LangSmith / Langfuse / Arize Phoenix 上下文审计控制质量、成本与污染。

本阶段可完成以下练习：

- 为文案创作场景设计包含角色、风格、约束和输出格式的完整 System Prompt。
- 用 CoT + Few-shot 设计视频内容描述模板，并对比 Temperature / Top-P 对创意性的影响。
- 实现固定 JSON Schema 的视频分析输出。

### 多模态 RAG 的场景架构

视频库经帧提取和 CLIP 写入多模态向量数据库；文案素材库经文本 Embedding 写入文本向量数据库；用户查询经混合检索汇合两路结果，经过重排序、上下文组装后交给 LLM 生成文案。

基础链路是 Query -> Embedding -> 向量搜索 -> 拼接上下文 -> LLM 生成。入门可使用 ChromaDB；生产可考虑 Pinecone、Weaviate、Milvus、pgvector。多模态 RAG 还应覆盖图片或视频帧的 CLIP Embedding 检索。可参考 LangChain RAG 教程、LlamaIndex 官方文档和 [Pinecone Learning Center](https://www.pinecone.io/learn/)。

### Tool Use 与 MCP 细化

Function Calling 的完整循环是：LLM 输出函数调用 -> 应用代码执行 -> 结果回传给 LLM -> LLM 继续推理。工具定义使用 JSON Schema 描述函数签名、参数和返回值；需要支持并行调用，以及失败后的重试和降级。

MCP 的通信路径为 **MCP Host（Claude / Cursor 等 AI 应用）<-> MCP Client（协议转换）<-> MCP Server（数据库、API、文件等工具和数据）**。三个核心原语：

| 原语 | 作用 | 示例 |
|:---|:---|:---|
| Tools | 可执行函数 | 查数据库、发消息、调用 API |
| Resources | 只读数据 | 文件内容、API 日志、文档 |
| Prompts | 可复用模板 | 引导 Agent 完成特定工作流 |

学习路径：理解 MCP 将 N x M 集成问题化为 N + M；搭建暴露数据库查询工具的 Server；用 Claude Desktop 或 Cursor 作为 Host 连接；落实认证、授权与注入防护。MCP 是由 Anthropic 发起并交由 Linux 基金会下 AAIF 治理的生态标准，月 SDK 下载量已超过 1.1 亿；A2A 与 MCP 互补，适合持续关注。

### Agent 与 Harness 设计细化

所有 Agent 都可以归纳为 **Think -> Act -> Observe** 循环。Harness 是 Model 的运行身体，至少负责：工具执行与路由、上下文压缩与窗口管理、状态持久化与检查点、错误恢复、安全护栏、输入输出解析与验证、日志追踪可观测性、反馈循环和终止条件。

| Harness 维度 | 关键措施 | 目的 |
|:---|:---|:---|
| 循环控制 | 最大迭代次数、超时、死循环检测 | 防止无限循环和失控成本 |
| 工具路由 | 选择验证、参数校验、权限控制 | 防止误用和越权 |
| 上下文压缩 | 摘要、旧消息裁剪、工具输出压缩 | 防止上下文膨胀 |
| 错误恢复 | 指数退避、熔断、模型降级 | 应对真实 API 失败 |
| 输出解析 | 结构化验证、格式修复、类型检查 | 处理非法 JSON |
| 安全边界 | 注入检测、敏感信息过滤、操作审计 | 抵御恶意工具输出 |
| 终止与成本 | 完成检测、置信阈值、人工升级、Token/API 预算、模型路由 | 让 Agent 知道何时停止并可控运行 |

实践时至少验证：`max_iterations + timeout` 的死循环防护、失败工具的重试和降级、超过 N 轮自动摘要、非法 JSON 的修复或重试，以及 Token 预算超限后的终止或小模型切换。

状态管理还应支持检查点（保存、暂停和恢复 Agent 状态）、LangGraph 的 Time Travel 回溯能力，以及以有限状态机或有向状态图描述 Agent 工作流。Human-in-the-Loop 应提供审批门控、随时中断并纠偏、对输出的反馈循环，以及不确定时向人类升级的机制。

编排层级可分为：Tier 1 原语层（LangGraph、LlamaIndex Workflows、PydanticAI，图与状态机）；Tier 2 框架层（CrewAI、AutoGen、OpenAI Agents SDK，快速多 Agent）；Tier 3 平台层（Harness AI、企业 Agent 平台，治理、可观测性和 HITL）。推荐参考 [LangChain ReAct Agent 教程](https://python.langchain.com/docs/how_to/agent_executor/)、[LangGraph 官方教程](https://langchain-ai.github.io/langgraph/)、[ReAct](https://arxiv.org/abs/2210.03629)、[Reflexion](https://arxiv.org/abs/2303.11366) 与 Martin Fowler 的 Agent 架构文章。

### 视频到文案 Agent 的参考管线

视频输入先经均匀采样、关键帧检测或场景边界抽帧，送至多模态 LLM，输出视频摘要、场景描述、情感分析和关键信息，再由文案生成 Agent 产出多平台版本。其组件分别为：视频理解模块、品牌调性 RAG、实时热点工具、文本 LLM 文案生成、抖音/小红书/B站的多版本适配，以及人工审核门控。

视频理解的现实约束：30 FPS 可达到每小时百万级 Token，必须结合自适应帧选择、视觉 Token 压缩和关键事件检测；Gemini 2.5 Pro 擅长小时级长视频。阶段产出包括端到端“视频 -> 文案”原型、固定采样与智能采样对比、接入品牌素材库的风格一致性，以及“生成初稿 -> 人类修改 -> Agent 学习偏好”的 HITL 闭环。

### 框架选型与多 Agent 补充

框架全景：LangGraph 用于生产级有状态工作流；CrewAI 用于角色分工清晰的快速原型；PydanticAI 用于类型安全生产系统；LlamaIndex Workflows 适合数据密集、RAG 为中心的管线；Microsoft Agent Framework 面向 Azure/.NET；OpenAI Agents SDK 与 Google ADK 分别适合绑定其模型生态；n8n 适合低代码自动化。建议先深入 LangGraph，再以 CrewAI 感受多 Agent 协作，其余按具体需求学习。

可选协作模式包括顺序链、Router、Supervisor、Debate / Competition、Hierarchical 与 Swarm。面向视频文案的结构可以由 Supervisor 调度 Video Analysis Agent、RAG Research Agent、Copywriter Agent 和 Quality Review Agent，汇总后向用户输出，并接受用户反馈修改。

### 生产化、技术栈与里程碑补充

生产评估不仅看最终输出，还要评估轨迹，即推理步骤、工具调用序列和状态变化是否合理；同时评估 Token、调用次数、端到端延迟，以及注入、工具安全和数据泄露。可使用 LangSmith、Arize Phoenix、Braintrust、DeepEval；参考 τ-Bench（工具可靠性和策略遵守）、AgencyBench（长期推理与深度工具调用）、WebArena（Web 操作）和 SWE-Bench（软件工程）。

可观测性覆盖完整调用链 Tracing、结构化决策日志、成本/延迟/错误率/成功率 Monitoring，以及循环或选错工具时的 Debugging。可靠性措施包括重试与超时、熔断、备用模型降级、Guardrails、Prompt 注入防护。部署层还应覆盖 SSE / WebSocket 流式输出、`asyncio` 与消息队列长任务、Prompt 版本管理和 A/B 测试。

| 层次 | 推荐选型 |
|:---|:---|
| 多模态 LLM | Gemini 2.5 Pro（长视频）、Qwen2.5-VL（开源自部署） |
| 文本 LLM | Claude Opus 4（深度推理与文案）、GPT-5（通用） |
| Agent 框架 | LangGraph（生产）+ CrewAI（原型验证） |
| 向量数据库 | Milvus / Pinecone（生产）、ChromaDB（开发） |
| Embedding | text-embedding-3-large / BGE-M3 |
| 可观测性 | LangSmith / Arize Phoenix |
| 协议 | MCP |
| 部署 | FastAPI + Docker + 消息队列 |

| 阶段检查点 | 完成标志 |
|:---|:---|
| 基础认知 | 能解释 Transformer，并比较主流多模态模型的能力边界 |
| LLM 交互 | 完成文案 System Prompt 与上下文栈设计 |
| RAG | 搭建文本和视频帧检索的多模态 RAG 原型 |
| Tool Use + MCP | 完成工具链并封装为 MCP Server |
| Agent + Harness | 用 LangGraph 实现 ReAct Agent 和含循环控制、错误恢复的 Harness |
| 多模态 Agent | 搭建端到端“视频 -> 文案”原型 |
| 多 Agent | 完成 Supervisor 协作系统 |
| 生产化 | 增加评估、可观测性与安全防护并部署 |
