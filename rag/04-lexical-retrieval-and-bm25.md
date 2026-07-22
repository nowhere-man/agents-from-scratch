---
title: 倒排索引与 BM25：把精确词变成可解释分数
aliases:
  - BM25 原理
  - Lexical Retrieval
tags:
  - rag
  - bm25
  - information-retrieval
  - search
status: active
created: 2026-07-22
last_reviewed: 2026-07-22
sources:
  - https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html
  - https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/similarities/BM25Similarity.html
---

# 倒排索引与 BM25：把精确词变成可解释分数

> [!abstract] 本章学习终点
> 你应该能从“分词 → 倒排表 → 词频/文档频率 → BM25 公式 → 一次数值计算”完整走一遍，并能解释 BM25 为什么擅长错误码、版本号和精确数字，却不懂同义表达。

上一章说到，dense retrieval 可能把“海外住宿额度”和“travel lodging allowance”放得很近，但也可能忽略 v5、40123 或 180 这样的精确字符。本章回到信息检索的另一条主线：**一个词出现在哪里、出现多少次、在全库有多稀有。**

## 从正排文本到倒排索引

### 正排和倒排是什么

正排结构以文档为中心：

~~~text
文档 1 → [东京, 住宿, 上限, 180]
文档 2 → [东京, 机票, 上限, 900]
~~~

如果 query 是“住宿 上限”，系统需要逐份文档扫描。**倒排索引**反过来以词项为中心：

~~~text
东京   → [文档 1, 文档 2]
住宿   → [文档 1]
上限   → [文档 1, 文档 2]
180    → [文档 1]
~~~

箭头右侧的列表叫 **postings list（倒排列表）**。真实实现还会保存每个文档中的词频、位置、字段和偏移量：

~~~yaml
term: 住宿
postings:
  - doc_id: policy-v5-chunk-03
    tf: 2
    positions: [4, 17]
    field: body
~~~

在线查询大致分四步：

1. 用与建索引相同的 analyzer（分词、规范化、停用词等）处理 query；
2. 找到每个 query term 的 postings list；
3. 合并候选文档；
4. 为每个候选计算相关性分数并排序。

因此，搜索“v5”能否命中，不首先是模型问题，而是 analyzer 是否把 v5 保留成可搜索词的问题。

## BM25 要回答的三个直觉问题

对一个 query term，BM25 需要估计：

1. **它在当前文档出现了吗？**没有就没有该词的贡献；
2. **出现多次是否更相关？**通常是，但重复到一定程度后收益递减；
3. **这个词在整个语料中有多稀有？**越稀有，区分力通常越强。

它还要防止一个问题：长文档天然有更多机会包含 query 词，不能只因为文档长就占优势。因此 BM25 还做文档长度归一化。

## 先理解四个量

### 词频 TF

设 query term 为 $t$，文档为 $D$：

$$
f(t,D)=\text{term }t\text{ 在 }D\text{ 中的出现次数}
$$

在“东京 住宿 上限”中，某个 chunk 出现两次“住宿”，其 TF 为 2。TF 只看当前文档，不知道这个词在其他文档是否常见。

### 文档频率 DF

$$
df(t)=\text{包含 }t\text{ 的文档数量}
$$

如果全库 1000 个 chunk 中有 900 个包含“政策”，它的区分力低；如果只有 3 个包含“api-v2”，它更能帮助定位。

### 文档总数 N

$$
N=\text{索引中的文档或 chunk 总数}
$$

BM25 的 IDF 由 N 和 df 共同决定。这里的“文档”通常是索引单元，不一定是用户看到的整份 PDF。

### 文档长度与平均长度

$$
|D|=\text{当前文档的 token 数或词项数}
$$

$$
\operatorname{avgdl}
=\text{所有文档的平均长度}
$$

如果一个 chunk 比平均值长很多，BM25 会对它的词频贡献做一定折扣。

## BM25 的常见公式

常见形式为：

$$
\operatorname{BM25}(D,Q)
=
\sum_{t\in Q}
\operatorname{IDF}(t)
\cdot
\frac{f(t,D)(k_1+1)}
{f(t,D)+k_1\left(1-b+b\frac{|D|}{\operatorname{avgdl}}\right)}
$$

其中：

$$
\operatorname{IDF}(t)
=
\ln\left(
1+
\frac{N-df(t)+0.5}{df(t)+0.5}
\right)
$$

符号逐个对应到“东京住宿”的搜索：

- $Q$：查询中的词项集合，例如 东京、住宿、上限；
- $D$：一个待排序的 chunk；
- $f(t,D)$：词项在该 chunk 中出现几次；
- $N$：索引里有多少 chunk；
- $df(t)$：有多少 chunk 包含该词；
- $k_1$：TF 饱和速度；
- $b$：长度归一化强度。

不同搜索库可能采用略有不同的 IDF 平滑、字段处理或 query term 权重。公式给的是机制，不应把某个实现的分数当成跨库可比较的概率。

## 一次完整数值演算

为了看清每一项，先用英文词项表示中文概念：

| 文档 | 文本摘要 | 长度 |
|---|---|---:|
| D1 | tokyo hotel daily allowance 150 | 5 |
| D2 | tokyo travel policy hotel allowance 180 | 6 |
| D3 | singapore hotel allowance 120 | 4 |
| D4 | tokyo airfare policy | 3 |

查询为：

~~~text
tokyo hotel allowance
~~~

共有 $N=4$ 个文档，平均长度：

$$
\operatorname{avgdl}=(5+6+4+3)/4=4.5
$$

三个 query term 都出现在 D1、D2、D3 中，因此：

$$
df(tokyo)=df(hotel)=df(allowance)=3
$$

采用 $k_1=1.2$、$b=0.75$，每个词的 IDF 约为：

$$
\ln\left(1+\frac{4-3+0.5}{3+0.5}\right)
=\ln(1.4286)\approx0.357
$$

### D1 的分数

D1 长度是 5，长度项：

$$
1-b+b\frac{|D1|}{\operatorname{avgdl}}
=0.25+0.75\frac{5}{4.5}
\approx1.083
$$

每个词只出现一次，所以 TF 饱和项：

$$
\frac{1(1.2+1)}
{1+1.2(1.083)}
\approx0.957
$$

D1 包含三个 query term，因此总分约为：

$$
3\times0.357\times0.957\approx1.024
$$

### D2 的分数

D2 长度是 6，长度项为：

$$
0.25+0.75\frac{6}{4.5}=1.25
$$

每词 TF 饱和项为：

$$
\frac{2.2}{1+1.2(1.25)}=0.88
$$

总分约为：

$$
3\times0.357\times0.88\approx0.942
$$

D2 虽然包含同样三个词，但更长，长度归一化让它略低于 D1。不是“短文档永远更好”，而是 BM25 在覆盖词项和文档长度之间做平衡。

### D3 与 D4

D3 只有 hotel 和 allowance 两个词，长度为 4，分数约为：

$$
2\times0.357\times
\frac{2.2}{1+1.2(0.25+0.75\times4/4.5)}
\approx0.748
$$

D4 只有 tokyo 一个词，长度为 3，分数约为：

$$
1\times0.357\times
\frac{2.2}{1+1.2(0.25+0.75\times3/4.5)}
\approx0.413
$$

最终排序大致是：

$$
D1 > D2 > D3 > D4
$$

这个小例子展示了 BM25 的可解释性：D1/D2 覆盖全部 query term；D3 缺少 tokyo；D4 只命中一个词；文档长度只是在这些匹配之上做修正。

## 为什么 TF 不会无限加分

如果一个文档把“hotel”重复 20 次，朴素 TF 会让它显得极其相关；但重复可能只是模板、垃圾文本或不自然堆词。BM25 的分式会饱和：

以长度项固定为 1.0、$k_1=1.2$ 为例：

| TF | 饱和项 |
|---:|---:|
| 1 | $2.2/2.2=1.00$ |
| 2 | $4.4/3.2\approx1.38$ |
| 5 | $11/6.2\approx1.77$ |
| 20 | $44/21.2\approx2.08$ |

从 1 次到 2 次有明显收益，从 5 次到 20 次的增益已经小很多。$k_1$ 越大，TF 饱和越慢；具体数值应在领域数据上调，而不是照抄默认值。

## 为什么稀有词更有用：IDF

IDF 把“大家都说的词”和“能区分文档的词”分开：

- 若 $df(t)$ 接近 $N$，IDF 较小；
- 若 $df(t)$ 很小，IDF 较大；
- 只在一个 chunk 出现的错误码或版本号，通常比“政策”“费用”更有区分力。

这也是 BM25 对 exact match（精确匹配）特别有用的原因。需要注意，IDF 的“稀有”只描述分布，不代表该词事实重要；一个拼写错误的随机字符串也可能很稀有。

## $b$ 做了什么：长度归一化

长度因子是：

$$
1-b+b\frac{|D|}{\operatorname{avgdl}}
$$

- $b=0$：完全不做长度归一化；
- $b=1$：按文档与平均长度的比例充分归一化；
- 中间值：折中。

对自然语言段落，较长文档拥有更多机会碰到 query 词，归一化通常有帮助。对固定格式的日志、代码或字段值，长度和相关性未必有同样关系，盲目使用高 $b$ 可能压低真正重要的长 chunk。

## 中文和代码中的 analyzer 决定 BM25 上限

BM25 不是直接对汉字“理解”。它接收 analyzer 输出的 term，所以中文分词质量是召回质量的一部分。

### 中文常见选择

1. **词语分词：**“海外差旅 / 住宿 / 上限”，适合自然语言；
2. **字或字 bigram：**对新词、专名更鲁棒，但索引更大，噪声更多；
3. **混合字段：**一个字段做词分词，另一个字段做字符/别名索引；
4. **领域词典：**把 api-v2、差旅标准、产品代号等作为不可拆词。

### 不要轻易删除的内容

- 数字和单位：180、USD、14 天；
- 版本和错误码：v5、40123；
- 连字符、下划线和大小写有业务含义的 ID；
- 否定词：不、不得、除非；
- 表格列名和标题路径。

英文常见的 lowercase、stemming 和 stopword 处理，也不能不加评估地套到代码或政策文本上。比如把 v5 当作普通字母、把 “not approved” 的 not 删除，都会改变检索含义。

## BM25 与 TF-IDF 的关系

TF-IDF 同样使用 TF 和 IDF，但常见实现对 TF 的处理更线性、对长度归一化较简单。BM25 可以看成针对文档检索经验做过改进的概率相关性模型：

- TF 有饱和；
- 长度归一化显式由 $b$ 控制；
- IDF 使用平滑项避免极端值；
- 参数可按语料调节。

BM25 不是神秘的机器学习黑箱；它的优势正是可解释、低延迟和对精确词项稳定。

## BM25 能做什么，不能做什么

### 擅长

- 错误码、订单号、版本号、函数名；
- 查询和文档共享的专有名词；
- 数字、单位和短语；
- 需要解释“为什么命中”的企业搜索。

### 不擅长

- “海外住宿额度”与“travel lodging allowance”没有共同词；
- 同义词、改写、跨语言表达；
- 需要跨多个段落综合推理；
- 词相同但语义角色不同的句子。

BM25 看见“东京”和“住宿”，却不知道这是普通员工还是实习生。metadata、结构化分块、dense retrieval 和 reranker 要在后续层补上。

## 常见扩展

### 字段权重和 BM25F

标题、正文、标签和代码字段的重要性不同。可以为标题字段更高权重，或使用 BM25F 在多个字段上联合计算。这样“东京”出现在标题时比只出现在脚注更有影响。

### 短语和位置查询

倒排列表保存词位置后，可以要求“每日 住宿 上限”按近邻顺序出现，减少只共享词但上下文无关的误召回。短语查询不是 BM25 本身，但常与 BM25 一起使用。

### 同义词与别名

可以在索引或查询时把“住宿上限”“酒店额度”“lodging cap”扩展为同义词集合。扩展词会增加召回，也可能引入噪声；应保留原始 query 并记录扩展来源。

## 调参与排错

不要直接以 BM25 分数阈值判断“相关/不相关”，因为分数会随语料、字段和 query 长度变化。优先在标注集上比较排序指标。

排错顺序：

1. analyzer 是否把关键词保留下来；
2. postings 中是否真的有正确 chunk；
3. query 和文档是否使用同一规范化规则；
4. chunk 长度是否造成过度归一化；
5. $k_1$、$b$ 是否在验证集上调过；
6. 是否需要标题 boost、短语或同义词；
7. 是否应与 dense retrieval 做混合。

## 一个最小的 BM25 接口

~~~python
def lexical_retrieve(query, index, filters, top_k=20):
    terms = analyzer(query)
    postings = index.lookup(terms, filters=filters)
    scored = []
    for doc_id, term_stats in postings.by_document():
        score = 0.0
        for term in terms:
            score += bm25_term_score(
                tf=term_stats[term].tf,
                df=index.document_frequency(term),
                doc_len=term_stats.doc_len,
                avgdl=index.average_doc_len,
                total_docs=index.total_docs,
                k1=1.2,
                b=0.75,
            )
        scored.append((doc_id, score))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]
~~~

真实搜索库会对 postings、跳表、缓存和并发做大量优化；这里保留公式和过滤顺序，方便把结果与实现对照。

> [!important] 关键结论
> BM25 的分数回答的是“这个 chunk 与 query 的词项匹配有多强”，不是“答案为真的概率”。它是 RAG 的一条召回通道，而不是事实验证器。

下一篇把 BM25 与 dense retrieval 放到同一条候选管线里，并解释为什么 reranker 往往是最值得优先尝试的质量升级：[[rag/05-hybrid-search-reranking|Hybrid Search、Reranker 与查询改写]]。
