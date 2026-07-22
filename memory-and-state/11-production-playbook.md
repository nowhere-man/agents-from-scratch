---
title: Agent Memory 与 State 生产落地手册
aliases:
  - Production Agent Memory State
  - Memory State Checklist
tags:
  - agents
  - memory
  - state
  - production
  - operations
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[memory-and-state/99-sources|资料与来源]]"
---

# Agent Memory 与 State 生产落地手册

> [!abstract] 本篇学习终点
> 你将能把前面的原则转成分阶段实施路线、上线门槛、SLO（Service Level Objective，服务等级目标）、故障处理和迁移策略；知道何时保持简单、何时引入专用 Memory 产品或 durable workflow engine。

## 阶段一：先做一个可验证的单 Agent

目标不是“拥有长期记忆”，而是证明一条闭环：

```text
用户输入
→ State snapshot
→ 选择性 Memory retrieval
→ Context packet
→ 工具/模型候选
→ observation 验证
→ Event + Snapshot 原子提交
→ 可回查 artifact
```

推荐最小技术栈：SQLite/PostgreSQL、文件或对象 artifact、一个全文/向量索引（可先不用）、结构化日志。先写 10–20 条多轮/崩溃测试，再考虑框架。

## 阶段二：补齐生产边界

- tenant/user/project/task scope 全链路传递；
- State schema version、CAS 和迁移脚本；
- 外部副作用的 idempotency key、reconcile 和 unknown 状态；
- outbox/inbox、队列重试、dead-letter queue（无法继续处理、等待人工的死信队列）和人工升级；
- artifact checksum（内容校验和）、敏感级别、保留/删除；
- trace 中记录 selected/rejected/uncertain context；
- Memory 写入 policy、用户查看/纠正/删除入口；
- 评测集和故障注入门禁。

这一阶段完成前，不要把“模型回答很好”当作上线信号。

## 阶段三：按压力选择专用组件

| 压力/需求 | 可能的升级 | 触发条件 |
|---|---|---|
| 长 thread token/延迟增长 | session limit、摘要、compaction | p95 token 和延迟超预算 |
| 语义 memory 规模变大 | pgvector/Qdrant/Milvus/Pinecone 等 | SQL 检索或索引延迟成为瓶颈 |
| 多跳时间事实 | Zep/Graphiti/图层 | 关系查询质量显著影响任务 |
| 快速接入 user/project memory | Mem0 或同类服务 | 自建抽取/去重成本高且风险可控 |
| 可读项目约定与 agent identity | Letta/MemFS 或 Git-backed notes | 需要人工审计、版本和跨设备同步 |
| 跨小时等待/审批/复杂重试 | Temporal/同类 durable workflow | 进程重启恢复和定时器成为主要故障源 |
| 多模型/多工具生态 | LangGraph、Agents SDK、ADK、Microsoft Agent Framework | 需要统一 loop、HITL、tracing 或部署 |

升级时保留自己的 Contract 和 source of truth；不要把业务数据不可逆地锁进某个 SDK 序列化格式。

## 上线门槛：四类检查

### 正确性

- [ ] 每个完成 step 都有可回查 evidence；
- [ ] State version 单调，CAS 冲突不会静默覆盖；
- [ ] unknown 不会被摘要/模型转成成功；
- [ ] 恢复后不会跳过未验证步骤；
- [ ] 结果中的数值、时间和单位能回到 source。

### 安全与治理

- [ ] 每次查询带 tenant/subject scope；
- [ ] Memory 不能改变 policy/authorization；
- [ ] 外部内容标记为 data，注入攻击有测试；
- [ ] secrets/PII 有字段 allowlist、加密和脱敏；
- [ ] 删除传播到索引、cache、artifact、备份和异步队列；
- [ ] 高风险动作有批准者、范围、时间和审计事件。

### 可靠性

- [ ] tool retry 有分类、预算和退避；
- [ ] 非幂等动作有 idempotency/reconcile；
- [ ] worker lease 过期有 fencing；
- [ ] outbox/inbox 可重投且不重复副作用；
- [ ] checkpoint 可恢复，必要时可从事件重放；
- [ ] 数据库、索引和 artifact 有备份/恢复演练。

### 运营

- [ ] 监控 p95/p99 延迟、token、成本、错误、恢复和泄漏；
- [ ] trace 能看到 State version、Memory IDs、tool status 和 stop reason；
- [ ] prompt/model/embedding/framework 版本可关联到 run；
- [ ] 有人工升级和暂停入口；
- [ ] 有回滚、降级和只读模式。

## SLO 不要只写“回答成功率”

可以定义一组更接近真实风险的目标：

```yaml
slo:
  turn_success_rate: ">= 99% for low-risk reads"
  recovery_success_rate: ">= 99.5% for injected worker crashes"
  duplicate_side_effect_rate: "0 for idempotent operations"
  cross_scope_leakage_rate: "0"
  stale_memory_use_rate: "< 0.5%"
  p95_memory_retrieval_ms: "< 200"
  p95_state_commit_ms: "< 100"
  deletion_completion_window: "defined per data class"
```

阈值应按业务风险校准；“0”意味着要有检测和阻断，而不是假设不会发生。

## 事故处理：先保护事实，再解释答案

### 发现跨租户 Memory 泄漏

1. 立即切换 Memory retrieval 到只读/严格 source-table filter；
2. 保存受影响 trace IDs 和 memory IDs，限制扩散；
3. 检查向量、全文、cache、摘要和日志副本；
4. 修复查询/索引策略并回放泄漏测试；
5. 按治理要求通知、删除或重建派生数据；
6. 复盘为什么 scope 没有成为确定性约束。

### 发现重复外部副作用

1. 暂停相关 worker 或切换人工批准；
2. 按 idempotency key 对账外部系统；
3. 将 unknown/duplicate 状态写入 State，不覆盖历史事件；
4. 修复 outbox、lease 或 provider adapter；
5. 用 kill/retry/failover 测试验证。

### 发现错误 Memory 污染

1. 标记并隔离 memory IDs，不直接批量删除原始证据；
2. 查找支持事件、传播路径和使用过的任务；
3. supersede 或删除派生 memory，重建索引；
4. 提高 candidate policy/确认门槛；
5. 增加相同攻击样例到回归集。

## 迁移策略：事件和 Contract 优先

从框架 A 换到框架 B 时：

1. 导出 task snapshot、event、memory contract 和 artifact refs；
2. 保留原始 `source_ref`、scope、版本和时间，不只导出 prompt 文本；
3. 在新 adapter 中回放事件，比较 snapshot 和完成标准；
4. 双读/影子运行一段时间，比较 Memory 选择和工具序列；
5. 切换写 owner，保留旧数据只读和回滚窗口；
6. 最后再清理旧索引/缓存，验证删除传播。

如果只能迁移一段自然语言 summary，说明旧系统的 State/Memory Contract 不够好，应先补数据模型再迁移。

## 反模式速查

| 反模式 | 为什么危险 | 最小修复 |
|---|---|---|
| 全量聊天历史永久塞 prompt | 成本高、旧值冲突、敏感泄露 | State 投影 + 选择性 Memory + artifact 引用 |
| 所有内容自动写 Memory | 噪声、污染、删除困难 | candidate policy、scope、来源、确认 |
| 只有向量库没有 source table | 无法版本、撤销、审计 | SQL/source of truth + 可重建索引 |
| last-write-wins 覆盖 State | 丢步骤、越权、竞态 | CAS、字段 reducer、人工冲突 |
| timeout 直接重试写操作 | 重复副作用 | idempotency + reconcile + unknown |
| 两个 history owner 同时启用 | 重复上下文和顺序错乱 | 明确唯一 owner |
| 先上多 Agent/Temporal | 复杂度超过问题 | 先做单 Agent baseline 和故障测试 |

## 最终设计评审模板

在仓库中提交设计前，要求作者用一页回答：

```text
1. Task State 的 owner、schema、version 和提交 API 是什么？
2. Event、Snapshot、Checkpoint、Artifact 的关系是什么？
3. Memory 的类型、scope、source、validity、delete 传播是什么？
4. 本轮 Context 如何选择，预算超限如何降级？
5. 每个外部副作用的 idempotency/reconcile 方案是什么？
6. 两个 worker 冲突时谁合并，谁能否决？
7. 崩溃点、重试、暂停、恢复如何测试？
8. 如何测 write precision、retrieval usefulness、recovery 和 leakage？
9. 哪些数据不能进入模型、日志、向量索引或备份？
10. 未来更换框架时，哪些 Contract 和事件仍可读取？
```

如果第 1–4 题答不清楚，先不要优化 prompt；如果第 5–9 题答不清楚，先不要扩大自动化权限。

> [!success] 结课自测
> 画出研究 Agent 从用户输入到报告交付的全链路，并在每个箭头标注：owner、版本、失败状态、是否可重试、是否进入长期 Memory。能完成这张图，比背下任何框架的 API 更接近生产能力。

回到入口复习完整地图：[[memory-and-state/00-overview|Agent Memory 与 State 总览]]。版本敏感的官方链接集中在 [[memory-and-state/99-sources|资料与来源]]。
