# 任务计划：[简要描述]
<!--
  内容：这是整个任务的路线图，可将其视为“磁盘上的工作记忆”。
  原因：执行 50 多次 tool call 后，原始目标可能被遗忘。此文件使目标保持清晰。
  时机：开始任何工作前先创建此文件。每个阶段完成后更新。

  AUTONOMOUS 变体：此模板用于长时间、multi-agent 或无人值守运行
  （autonomous 或 gated mode）。它保留标准 task_plan.md 的每个章节，使
  check-complete 的阶段计数和状态 pattern 保持不变，并添加 Run Contract、
  可选的逐阶段协调行和 model-routing 提示。没有 mode marker 和新 flag 时，
  行为与标准模板完全相同。
  （此注释刻意避免使用字面 phase-heading marker，防止文字说明增加阶段计数；
  下方只有五个真实阶段使用 heading marker。）
-->

## Run Contract
<!--
  内容：本次运行遵循的规则。Orchestrating agent 在运行开始时读取一次，gate 会遵守。
        除非显式设置 mode，否则这些规则不会改变 v2 行为；这里全部采用默认值时，
        等同于 legacy semantics。
  原因：无人值守运行需要在 artifact 中声明 termination 和 ownership 规则，
        不能只存在于会被 compaction 删除的 chat history 中。
  时机：初始化时填写。init-session --autonomous / --gated 会写入这些字段所映射的
        .mode 文件。手动编辑时，使此 block 与 .planning/<id>/.mode 保持同步。
-->
- **Mode:** gated
  <!-- autonomous = 低 recitation、无 completion gate。gated = completion gate 激活（Stop
       hook 可以保持 turn，直到 in_progress 阶段清除）。省略 mode（或没有 .mode 文件）
       表示普通 legacy behavior。 -->
- **Gate cap:** 20
  <!-- Gate 放弃并允许 turn 结束前的最大连续 block 数。
       计数存放在 .planning/<id>/.stop_blocks 中，在 init-session 时重置。这是主要的
       runaway guard，不依赖任何未记录的 host 字段。 -->
- **Stall window:** 1 tick
  <!-- 如果 run-ledger 自上次 gate block 后没有进展（没有新的 ledger line），
       gate 会将运行视为 stalled 并允许 turn 结束，而不是在没有进展的阶段上循环。 -->
- **Attestation policy:** default-on
  <!-- Autonomous 和 gated mode 默认开启 attestation：初始化时计算 task_plan.md 的 hash，
       hook 拒绝注入偏离 attested hash 的计划内容。任何有意编辑后，使用
       scripts/attest-plan.sh 重新 attest。这使 AcceptanceCheck 命令可以安全运行：
       只有来自 attested plan 且在 allowlist 中的命令能到达 gate。 -->
- **Single-writer rule:** orchestrator 拥有此文件。
  <!-- Orchestrating agent 是 task_plan.md 的唯一 writer。Worker subagent 绝不编辑它；
       它们向各自的 per-agent ledger（.planning/<id>/ledger-<agent>.jsonl）append，
       并写入自己的 findings.md 章节。Status 变更在 write lock 下通过
       scripts/phase-status.sh 执行。progress.md 只由 orchestrator 写入。
       这可以消除多个 agent 并行运行时的 last-writer-wins corruption。 -->

## 目标
<!--
  内容：用一句清晰的话描述要实现的目标。
  原因：这是你的方向。重新阅读可使注意力集中在最终状态。
  示例：“创建一个支持添加、列出和删除功能的 Python CLI 待办事项应用。”
-->
[用一句话描述最终状态]

## 当前阶段
<!--
  内容：当前正在执行哪个阶段（例如“Phase 1”“Phase 3”）。
  原因：快速确认任务位置，随进度更新。
-->
Phase 1

## 阶段
<!--
  内容：将任务拆分为 3-7 个合理阶段，每个阶段都应可以完成。
  原因：将工作拆成阶段可以避免负担过重，并使进度可见。
  时机：每个阶段完成后更新状态：pending → in_progress → complete

  AUTONOMOUS 扩展（全部可选，省略时默认采用 legacy behavior）：
  - **DependsOn:** 列出解除本阶段阻塞前必须完成的阶段。
  - **Owner:** 指定负责本阶段的 agent（multi-agent 运行）。
  - **AcceptanceCheck:** gate 可以运行的 shell 命令，用于判断阶段是否完成。
  这些行与现有 - **Status:** 行并列，绝不替代它，因此 check-complete 仍按原方式
  统计阶段 heading 和 complete-status 行。
-->

### Phase 1：需求与探索
<!--
  内容：理解需要完成的工作并收集初始信息。
  原因：在不理解任务的情况下开始会浪费精力。此阶段可防止这种情况。
-->
- [ ] 理解用户意图
- [ ] 确定约束和需求
- [ ] 将研究发现记录到 findings.md
- **Status:** in_progress
- **Owner:** orchestrator
  <!-- 内容：哪个 agent 执行本阶段。Single-agent 运行时省略。
       原因：在 multi-agent 运行中，orchestrator 通过写入 Owner 行认领阶段，
            防止两个 worker 处理同一阶段。 -->
<!--
  状态值：
  - pending：尚未开始
  - in_progress：当前正在执行
  - complete：该阶段已完成
-->

### Phase 2：规划与结构
<!--
  内容：决定处理问题的方式和采用的结构。
  原因：良好的规划可以避免返工。记录决策，以便记住选择理由。
-->
- [ ] 确定技术方案
- [ ] 必要时创建项目结构
- [ ] 记录决策及其理由
- **Status:** pending
- **DependsOn:** Phase 1
  <!-- 内容：本阶段开始前必须完成的阶段。没有 prerequisite 时省略。
       原因：gate 使用此字段区分“progressing”（某个未阻塞阶段为 in_progress）和
            “stuck”（每个 pending 阶段仍被未完成 dependency 阻塞），并在 gate reason
            中展示“stuck”，而不是继续循环。 -->

### Phase 3：实现
<!--
  内容：实际构建、创建或编写解决方案。
  原因：工作在此阶段完成。必要时拆成更小的子任务。
-->
- [ ] 逐步执行计划
- [ ] 执行前将代码写入文件
- [ ] 增量测试
- **Status:** pending
- **DependsOn:** Phase 2
- **Owner:** orchestrator

### Phase 4：测试与验证
<!--
  内容：验证所有内容都能正常工作并满足需求。
  原因：尽早发现问题可以节省时间。将测试结果记录到 progress.md。
-->
- [ ] 验证所有需求均已满足
- [ ] 将测试结果记录到 progress.md
- [ ] 修复发现的所有问题
- **Status:** pending
- **DependsOn:** Phase 3
- **AcceptanceCheck:** `python -m pytest tests/ -q`
  <!-- 内容：当本阶段 acceptance condition 成立时返回 0 的 shell 命令。
       原因：使 gated run 根据 artifact 而不是 transcript 确认“done”。
       安全：只有该命令在 attest 时加入 allowlist，gate 才会运行；gate 绝不运行
            unattested plan 中的任何命令。Tampered plan 无法将新命令偷渡进 gate，
            因为修改此行会破坏 attestation hash，hook 会拒绝该计划，直到重新 attest。
            这正是 autonomous 和 gated mode 默认开启 attestation 的原因。 -->

### Phase 5：交付
<!--
  内容：最终 review 并 handoff 给用户。
  原因：确保没有遗漏，deliverable 完整。
-->
- [ ] Review 所有输出文件
- [ ] 确保 deliverable 完整
- [ ] 向用户交付
- **Status:** pending
- **DependsOn:** Phase 4

## Model Routing
<!--
  内容：向 ORCHESTRATING agent 提供建议，说明每种阶段应 dispatch 到哪个 model tier。
        这是供 agent 读取的指导，不由 script 强制执行。Gate 和 hook 绝不读取此表。
  原因：将研究和 triage 交给 small-fast model，将繁重的构建和验证工作交给 frontier model，
        可使长时间运行更便宜，通常也更好。在计划中声明 routing，可使选择经受 compaction。
  时机：根据 host 实际提供的 model 调整 tier。下方名称仅为示例。
-->
| 阶段类型 | Tier | Model 示例 |
|------------|------|---------------|
| 研究 / triage / 探索 | small-fast | Sonnet |
| 构建 / implementation / 验证 | frontier | Opus 或 Fable 5 |

## 关键问题
<!--
  内容：任务期间需要回答的重要问题。
  原因：这些问题指导研究和决策，应在执行过程中回答。
  示例：
    1. 任务是否应跨 session 持久保存？（是，需要文件存储）
    2. 使用什么格式存储任务？（JSON 文件）
-->
1. [需要回答的问题]
2. [需要回答的问题]

## 已做决策
<!--
  内容：已经做出的技术和设计决策，以及背后的理由。
  原因：选择理由可能被遗忘。此表有助于记忆并说明决策依据。
  时机：每当做出重大选择（技术、方案、结构）时更新。
  示例：
    | 使用 JSON 存储 | 简单、human-readable、Python 内置支持 |
-->
| 决策 | 理由 |
|----------|-----------|
|          |           |

## 遇到的错误
<!--
  内容：遇到的每个错误、发生在第几次尝试，以及解决方式。
  原因：记录错误可以防止重复相同错误，对学习至关重要。
  时机：错误发生后立即添加，即使很快修复也一样。
  示例：
    | FileNotFoundError | 1 | 检查文件是否存在，不存在则创建空列表 |
    | JSONDecodeError | 2 | 显式处理空文件情况 |
-->
| 错误 | 尝试 | 解决方案 |
|-------|---------|------------|
|       | 1       |            |

## 备注
<!--
  提醒：
  - 随进度更新阶段状态：pending → in_progress → complete
  - 重大决策前重新读取此计划（attention manipulation）
  - 记录所有错误，它们有助于避免重复
  - 绝不重复失败操作，改用其他处理方式
  - Multi-agent：只有 orchestrator 写入此文件；worker 向各自 ledger append。
-->
- 随进度更新阶段状态：pending → in_progress → complete
- 重大决策前重新读取此计划（attention manipulation）
- 记录所有错误，它们有助于避免重复
