# 研究发现与决策
<!--
  内容：Analytics session 的 knowledge base，存储 data source、hypothesis 和结果。
  原因：Context window 有限。此文件是分析工作的“external memory”。
  时机：任何发现之后更新，尤其是在运行 query 或查看 chart 后。
-->

## Data Source
<!--
  内容：连接的每个 data source，包括 schema 细节和质量备注。
  原因：了解数据来源及其限制，对于 reproducibility 至关重要。
  示例：
    | user_events | PostgreSQL production replica | 230 万行 | user_id, event_type, ts | 0.2% 的 user_id 为 null |
    | revenue.csv | Finance 团队导出 | 4.5 万行 | account_id, mrr, churn_date | 完整，无 null |
-->
| 来源 | 位置 | 大小 | 关键字段 | 质量备注 |
|--------|----------|------|------------|---------------|
|        |          |      |            |               |

## Hypothesis 日志
<!--
  内容：测试的每个 hypothesis、使用的方法和结果。
  原因：结构化跟踪可防止 p-hacking，并使推理可审计。
  示例：
    | H1：低活跃度用户的 churn > 50% | Chi-squared test | 已确认（p=0.003） | 高 |
    | H2：Feature X 与 retention 相关 | Pearson correlation | 已拒绝（r=0.08） | 高 |
-->
| Hypothesis | 测试方法 | 结果 | 置信度 |
|------------|-------------|--------|------------|
|            |             |        |            |

## Query 结果
<!--
  内容：运行的关键 query 及其揭示的内容。
  原因：Query 是易失的；如果不写下结果，context 重置时就会丢失。
  时机：每次重要 query 后立即记录，不要等待。
  示例：
    ### 按活跃度分组的 churn rate
    Query：SELECT activity_bucket, COUNT(*), AVG(churned) FROM user_segments GROUP BY 1
    结果：低活跃度 62% churn，中等 28%，高 8%
    解读：活跃度与 churn 之间存在显著负相关
-->
<!-- 为每个重要 query 记录 query、结果摘要和解读 -->

## 统计发现
<!--
  内容：包含所有相关 metric 的正式 statistical test 结果。
  原因：记录 p-value、effect size 和 confidence interval，可使结果可复现。
  示例：
    | Chi-squared（churn ~ activity） | p=0.003 | Cramer's V=0.31 | 拒绝 null hypothesis：不同活跃度分组的 churn 存在显著差异 |
    | Pearson（feature_x ~ retention） | p=0.42 | r=0.08 | 无法拒绝 null hypothesis：不存在有意义的 correlation |
-->
| 测试 | p-value | Effect Size | 结论 |
|------|---------|-------------|------------|
|      |         |             |            |

## 技术决策
<!--
  内容：分析方法选择及其理由。
  示例：
    | 对 revenue 使用 log transform | Right-skewed distribution，为 parametric test 做 normalization |
-->
| 决策 | 理由 |
|----------|-----------|
|          |           |

## 遇到的问题
| 问题 | 解决方案 |
|-------|------------|
|       |            |

## 资源
<!-- URL、文件路径、文档链接 -->
-

## Visual/Browser 发现
<!--
  关键：查看 chart、dashboard 或 browser result 后更新。
  Multimodal 内容不会持久保存在 context 中，应立即记录为文本。
-->
-

---
*每执行 2 次 view/browser/search 操作后更新此文件*
*这可以防止 visual 信息丢失*
