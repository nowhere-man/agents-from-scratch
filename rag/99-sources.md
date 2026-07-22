---
title: RAG 论文、官方文档与延伸阅读
aliases:
  - RAG Sources
  - RAG 参考资料
tags:
  - rag
  - sources
  - references
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
---

# RAG 论文、官方文档与延伸阅读

> [!abstract] 本篇职责
> 这里保存本系列的论文和官方文档入口，并说明它们解决什么问题。稳定原理写在正文，易变化的 SDK、模型版本、部署能力和价格以官方文档为准。

## 怎样使用这份来源表

来源分三层：

1. **论文：**理解方法在什么任务、数据和实验条件下成立；
2. **官方文档：**核对当前 API、索引能力、部署和限制；
3. **本教程：**把概念按初学者的认知顺序串成一条数据流。

论文中的提升不是对所有业务语料的保证，官方功能列表也不是生产性能证明。部署前仍需使用自己的 gold evidence 和流量分布评测。

## RAG 与 Dense Retrieval

| 主题 | 来源 | 用途 |
|---|---|---|
| RAG 原始工作 | [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) | 理解参数记忆与非参数外部记忆的组合 |
| DPR | [Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906) | 理解双编码器 dense retrieval |
| Sentence Transformers | [Sentence Transformers Documentation](https://www.sbert.net/) | Embedding、bi-encoder、cross-encoder 实践入口 |
| Hosted embeddings | OpenAI text-embedding 系列、[Cohere Embed](https://docs.cohere.com/docs/embeddings)、[Voyage AI Embeddings](https://docs.voyageai.com/docs/embeddings) | 核对当前 API、维度、模型和数据策略 |
| Open embedding models | [BGE-M3](https://huggingface.co/BAAI/bge-m3)、[multilingual-e5](https://huggingface.co/intfloat/multilingual-e5-large)、[Jina Embeddings](https://huggingface.co/jinaai/jina-embeddings-v3) | 本地部署和多语言模型卡片 |
| HNSW | [Efficient and Robust Approximate Nearest Neighbor Search Using HNSW](https://arxiv.org/abs/1603.09320) | ANN 图索引的原理 |
| ColBERT | [ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction](https://arxiv.org/abs/2004.12832) | 了解 bi-encoder 与 cross-encoder 之间的 late interaction 路线 |

对应正文：[[rag/03-embeddings-vector-search|Embedding、向量相似度与 ANN]]。

## 词法检索与 BM25

| 来源 | 用途 |
|---|---|
| [Stanford IR Book：Okapi BM25](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html) | 公式、TF/IDF 与长度归一化 |
| [Lucene BM25Similarity](https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/similarities/BM25Similarity.html) | 核对 Lucene 具体实现和参数 |
| [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/) | 倒排索引、排名和评测基础 |

对应正文：[[rag/04-lexical-retrieval-and-bm25|倒排索引与 BM25]]。

## 查询扩展、重排与高级检索

| 主题 | 来源 | 用途 |
|---|---|---|
| HyDE | [Precise Zero-Shot Dense Retrieval without Relevance Labels](https://arxiv.org/abs/2212.10496) | 用假设文档 embedding 改善 zero-shot dense retrieval |
| RAG-Fusion | [RAG-Fusion Repository](https://github.com/Raudaschl/rag-fusion) | Multi-Query 与 RRF 的代表性实现思路 |
| Cross-Encoder | [Sentence Transformers Cross-Encoder](https://www.sbert.net/examples/applications/cross-encoder/README.html) | 理解 reranker 的联合编码 |
| Cohere Rerank | [Cohere Rerank Documentation](https://docs.cohere.com/docs/rerank) | 托管 rerank API |
| BGE Reranker | [BAAI bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 多语言自托管 reranker 示例 |
| Jina Reranker | [jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) | 多语言 reranker 示例 |

对应正文：[[rag/05-hybrid-search-reranking|Hybrid Search、Reranker 与查询改写]]。

## Self-RAG、CRAG 与 Agentic RAG

| 主题 | 来源 | 用途 |
|---|---|---|
| Self-RAG | [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511) | reflection tokens、检索与自我批评 |
| CRAG | [Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884) | retrieval evaluator 与纠正路径 |
| FLARE | [Active Retrieval Augmented Generation](https://arxiv.org/abs/2305.06983) | 生成过程中的主动检索 |
| LangGraph | [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) | 有状态图、checkpoint 和人工中断 |
| LlamaIndex Workflows | [LlamaIndex Workflows](https://docs.llamaindex.ai/en/stable/module_guides/workflow/) | 数据/RAG 取向的事件工作流 |

对应正文：

- [[rag/07-adaptive-rag-self-rag-crag|自适应 RAG：Self-RAG、CRAG 与主动检索]]
- [[rag/08-agentic-rag|Agentic RAG：让 Agent 规划检索路径]]

## 向量数据库官方入口

| 产品 | 官方入口 | 选型时重点核对 |
|---|---|---|
| pgvector | [GitHub / Documentation](https://github.com/pgvector/pgvector) | HNSW/IVFFlat、距离类型、Postgres 版本、过滤与事务 |
| Qdrant | [Documentation](https://qdrant.tech/documentation/) | payload filter、HNSW、分片、量化、部署 |
| Milvus | [Official GitHub](https://github.com/milvus-io/milvus) | 分布式架构、索引类型、资源规划；部署前再从仓库进入当前文档 |
| Weaviate | [Documentation](https://docs.weaviate.io/weaviate) | hybrid search、对象 schema、模块与托管形态 |
| LanceDB | [Documentation](https://docs.lancedb.com/) | Lance 格式、本地/云、多模态与过滤 |
| Chroma | [Documentation](https://docs.trychroma.com/docs/overview/introduction) | collection、embedding function、metadata 和部署边界 |

产品能力和名称会更新。本教程的比较只用于建立决策维度，不能替代当前官方文档和压测。

## GraphRAG 与结构化检索

| 来源 | 用途 |
|---|---|
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | 实体、关系、社区和全局/局部查询的参考实现 |
| [GraphRAG Paper](https://arxiv.org/abs/2404.16130) | 了解从文本构建图与社区摘要的研究思路 |

GraphRAG 适合跨文档关系和全局问题，但会增加抽取、图更新和评测成本。它可以成为 Agentic RAG 的一个工具，不是所有语料的默认索引。

## 评测与观测

| 来源 | 用途 |
|---|---|
| [RAGAS](https://docs.ragas.io/en/stable/) | RAG 数据集、context/answer 指标和评测流程 |
| [TruLens](https://www.trulens.org/) | trace、feedback functions 与 RAG 可观测性 |
| [BEIR](https://arxiv.org/abs/2104.08663) | 多数据集信息检索 benchmark 与 zero-shot 评测思路 |

对应正文：[[rag/09-evaluation-production|RAG 评测、可观测性、安全与生产取舍]]。

## 维护协议

每次更新本系列时检查：

- 链接是否仍指向官方或论文原页；
- 产品能力描述是否仍成立；
- 模型名称、上下文长度和许可是否变化；
- 正文有没有把特定实现写成通用原理；
- 新增方法是否解决了已经出现的上游问题；
- 评测结论是否说明数据集、模型和时间。

> [!warning] 截止时间
> 本页最后复核日期为 2026-07-22。价格、托管区域、SDK 参数和产品版本属于易变信息，实际部署前必须重新查看官方文档。

返回导读：[[rag/00-overview|RAG 与 Agentic RAG：从搜索到可验证回答]]。
