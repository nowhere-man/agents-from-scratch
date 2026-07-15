# Reference：Manus Context Engineering 原则

此 skill 基于 Manus 的 context engineering 原则。Manus 是一家 AI agent 公司，Meta 于 2025 年 12 月以 20 亿美元收购了该公司。

## Manus 的 6 项原则

### 原则 1：围绕 KV-Cache 设计

> “KV-cache hit rate 是 production AI agent 最重要的单项指标。”

**统计数据：**
- Input-to-output token ratio 约为 100:1
- Cached token：$0.30/MTok；uncached token：$3/MTok
- 成本相差 10 倍

**实现：**
- 保持 prompt prefix 稳定（单个 token 的变更就会使 cache 失效）
- System prompt 中不要包含 timestamp
- 使用 deterministic serialization，使 context 只允许 append

### 原则 2：Mask，不要删除

不要动态删除工具，这会破坏 KV-cache；改用 logit masking。

**最佳实践：** 使用统一的 action prefix（例如 `browser_`、`shell_`、`file_`），使 masking 更容易。

### 原则 3：将 Filesystem 用作 External Memory

> “Markdown 是我位于磁盘上的‘工作记忆’。”

**公式：**
```
Context Window = RAM（易失、有限）
Filesystem = Disk（持久、无限）
```

**压缩必须可恢复：**
- 即使删除 Web 内容，也要保留 URL
- 删除文档内容时保留文件路径
- 绝不能丢失指向完整数据的 pointer

### 原则 4：通过 Recitation 操纵 Attention

> “在整个任务期间创建并更新 todo.md，将全局计划推入 model 最近的 attention span。”

**问题：** 大约 50 次 tool call 后，model 会忘记原始目标，即“lost in the middle”效应。

**解决方案：** 每次决策前重新读取 `task_plan.md`，使目标出现在 attention window 中。

```
Context 开头：[原始目标：距离很远，已被遗忘]
……大量 tool call……
Context 末尾：[最近读取的 task_plan.md：获得 ATTENTION！]
```

### 原则 5：保留错误内容

> “将错误尝试留在 context 中。”

**原因：**
- 带 stack trace 的失败操作使 model 隐式更新 belief
- 减少错误重复
- 错误恢复是“真正 agentic behavior 最清晰的信号之一”

### 原则 6：不要陷入 Few-Shot

> “一致性会滋生脆弱性。”

**问题：** 重复的 action-observation pair 会引发 drift 和 hallucination。

**解决方案：** 引入受控变化：
- 略微改变措辞
- 不要盲目复制粘贴 pattern
- 在重复任务中重新校准

---

## 3 种 Context Engineering 策略

基于 Lance Martin 对 Manus 架构的分析。

### 策略 1：Context Reduction

**Compaction：**
```
Tool call 有两种表示：
├── FULL：原始 tool content（存储在 filesystem 中）
└── COMPACT：只有 reference/文件路径

规则：
- 对陈旧的 tool result 应用 compaction
- 保留完整的近期结果，以指导下一项决策
```

**Summarization：**
- Compaction 的边际收益下降时应用
- 使用完整 tool result 生成
- 创建标准化 summary object

### 策略 2：Context Isolation（Multi-Agent）

**架构：**
```
┌─────────────────────────────────┐
│         PLANNER AGENT           │
│  └─ 向 sub-agent 分配任务       │
├─────────────────────────────────┤
│       KNOWLEDGE MANAGER         │
│  └─ Review 对话                 │
│  └─ 确定 filesystem 存储        │
├─────────────────────────────────┤
│      EXECUTOR SUB-AGENTS        │
│  └─ 执行分配的任务              │
│  └─ 拥有各自的 context window   │
└─────────────────────────────────┘
```

**关键洞察：** Manus 最初使用 `todo.md` 进行任务规划，但发现约 33% 的操作都用于更新该文件，因此改为由专用 planner agent 调用 executor sub-agent。

### 策略 3：Context Offloading

**工具设计：**
- 总共使用少于 20 个 atomic function
- 将完整结果存入 filesystem，而不是 context
- 使用 `glob` 和 `grep` 搜索
- Progressive disclosure：只在需要时加载信息

---

## Agent Loop

Manus 通过连续的 7 步 loop 运行：

```
┌─────────────────────────────────────────┐
│  1. 分析 CONTEXT                         │
│     - 理解用户意图                       │
│     - 评估当前状态                       │
│     - Review 近期 observation            │
├─────────────────────────────────────────┤
│  2. 思考                                 │
│     - 是否应更新计划？                   │
│     - 下一项合理操作是什么？             │
│     - 是否存在 blocker？                 │
├─────────────────────────────────────────┤
│  3. 选择工具                             │
│     - 选择一个工具                       │
│     - 确保参数可用                       │
├─────────────────────────────────────────┤
│  4. 执行操作                             │
│     - 工具在 sandbox 中运行              │
├─────────────────────────────────────────┤
│  5. 接收 OBSERVATION                     │
│     - 将结果 append 到 context           │
├─────────────────────────────────────────┤
│  6. 迭代                                 │
│     - 返回步骤 1                         │
│     - 持续执行直到完成                   │
├─────────────────────────────────────────┤
│  7. 交付结果                             │
│     - 向用户发送结果                     │
│     - 附上所有相关文件                   │
└─────────────────────────────────────────┘
```

---

## Manus 创建的文件类型

| 文件 | 用途 | 创建时机 | 更新时机 |
|------|---------|--------------|--------------|
| `task_plan.md` | 阶段跟踪、进度 | 任务开始时 | 阶段完成后 |
| `findings.md` | 发现、决策 | 任何发现之后 | 查看图片/PDF 后 |
| `progress.md` | Session log、已完成内容 | 在 breakpoint | 整个 session 期间 |
| 代码文件 | Implementation | 执行前 | 发生错误后 |

---

## 关键约束

- **Single-Action Execution（Manus 2025 原始约束）：** 每个 turn 只进行一次 tool call，不并行执行。此项记录 Manus 2025 年的 sandbox 实践。**2026 更新：** 现代 host（Claude Code、Codex CLI）支持并行 tool call 和 subagent，因此此约束不再按原文适用。协调点仍是计划文件，而不是每个 turn 一次调用的规则：并行调用和 subagent 通过磁盘上的持久化 Markdown 计划共享状态。
- **必须有计划：** Agent 必须始终知道目标、当前阶段和剩余阶段
- **文件就是记忆：** Context 易失，filesystem 持久
- **绝不重复失败：** 操作失败后，下一项操作必须不同
- **沟通是一种工具：** Message type：`info`（进度）、`ask`（阻塞）、`result`（终止）

---

## Manus 统计数据

| 指标 | 值 |
|--------|-------|
| 每项任务的平均 tool call 数 | 约 50 |
| Input-to-output token ratio | 100:1 |
| 收购价格 | 20 亿美元 |
| 收入达到 1 亿美元所用时间 | 8 个月 |
| 发布后的 framework refactor 次数 | 5 次 |

---

## 关键引述

> “Context window = RAM（易失、有限）。Filesystem = Disk（持久、无限）。所有重要内容都写入磁盘。”

> “if action_failed: next_action != same_action。记录已经尝试的操作，改变处理方式。”

> “错误恢复是真正 agentic behavior 最清晰的信号之一。”

> “KV-cache hit rate 是 production-stage AI agent 最重要的单项指标。”

> “将错误尝试留在 context 中。”

---

## 来源

基于 Manus 官方 context engineering 文档：
https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
