# 任务计划：[Analytics 项目描述]
<!--
  内容：Data analytics 或探索 session 的路线图。
  原因：Analytics workflow 的阶段与软件开发不同；hypothesis testing、data quality check
       和 statistical validation 无法映射到通用构建周期。
  时机：开始任何数据探索前先创建此文件，每个阶段后更新。
-->

## 目标
<!--
  内容：用一句清晰的话描述要了解或生成的内容。
  示例：“使用最近 90 天的活动数据，确定哪些用户群体的 churn risk 最高。”
-->
[用一句话描述分析目标]

## 当前阶段
<!--
  内容：当前正在执行哪个阶段（例如“Phase 1”“Phase 3”）。
  原因：快速确认当前位置，随进度更新。
-->
Phase 1

## 阶段

### Phase 1：Data Discovery
<!--
  内容：连接 data source、理解 schema、评估 data quality。
  原因：不良数据会产生不良分析。此阶段防止在不可靠输入上浪费精力。
-->
- [ ] 确定并连接 data source
- [ ] 在 findings.md 中记录 schema 和字段描述
- [ ] 评估 data quality（null、duplicate、outlier、date range）
- [ ] 估算 dataset 大小和 query performance
- **Status:** in_progress

### Phase 2：Exploratory Analysis
<!--
  内容：Distribution、correlation、outlier、初始 pattern。
  原因：测试 hypothesis 前理解数据形态，可以防止错误结论。
-->
- [ ] 计算关键变量的 summary statistic
- [ ] 可视化 distribution 和关系
- [ ] 确定 outlier 和 anomaly
- [ ] 在 findings.md 中记录初始 pattern
- **Status:** pending

### Phase 3：Hypothesis Testing
<!--
  内容：形式化 hypothesis、运行 statistical test、验证研究发现。
  原因：从“看起来像 X”转变为“可以有把握地判断 X”，需要结构化测试。
-->
- [ ] 将 exploratory phase 得到的 hypothesis 形式化
- [ ] 选择合适的 statistical test
- [ ] 运行测试并将结果记录到 findings.md
- [ ] 使用 holdout data 或替代方法验证研究发现
- **Status:** pending

### Phase 4：综合与报告
<!--
  内容：总结研究发现、创建 visual、记录结论。
  原因：不能清晰沟通的分析是无效工作。此阶段生成 deliverable。
-->
- [ ] 总结关键发现及支持证据
- [ ] 创建最终 visual
- [ ] 记录结论和建议
- [ ] 记录限制和需要进一步研究的领域
- **Status:** pending

## Hypothesis
<!--
  内容：正在研究的问题，以可测试的 hypothesis 表述。
  原因：显式 hypothesis 可防止 fishing expedition，并使分析保持聚焦。
  示例：
    1. 最近 30 天登录次数 < 3 的用户，churn rate > 50%（H1）
    2. Feature X adoption 与 retention 相关（r > 0.3）（H2）
-->
1. [要测试的 hypothesis]
2. [要测试的 hypothesis]

## 已做决策
<!--
  内容：分析决策及其理由，例如测试选择、filtering criteria。
  示例：
    | 使用 median 而不是 mean | Revenue 数据严重 right-skewed |
    | 只保留最近 90 天 | 更早的数据使用不同的 tracking schema |
-->
| 决策 | 理由 |
|----------|-----------|
|          |           |

## 遇到的错误
<!--
  内容：遇到的每个错误、发生在第几次尝试，以及解决方式。
  示例：
    | Raw table query timeout | 1 | 添加 date partition filter |
    | user_events 中的 join key 为 null | 2 | 使用 inner join 代替 left join，并记录 data loss |
-->
| 错误 | 尝试 | 解决方案 |
|-------|---------|------------|
|       | 1       |            |

## 备注
- 随进度更新阶段状态：pending -> in_progress -> complete
- 重大分析决策前重新读取此计划
- 记录所有错误，它们有助于避免重复
- 立即将 query 结果和 visual 发现写入 findings.md
