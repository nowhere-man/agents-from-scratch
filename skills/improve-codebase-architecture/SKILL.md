---
name: improve-codebase-architecture
description: 扫描 codebase 中的 deepening 机会，以可视化 HTML 报告展示，再针对用户选中的候选对象进行深入 grilling。
disable-model-invocation: true
---

# 改进 Codebase 架构

找出架构摩擦并提出 **deepening 机会**，即将 shallow module 转变为 deep module 的 refactor。目标是提高可测试性和 AI 可导航性。

此命令以项目的 domain model 为依据，并建立在共享设计词汇之上：

- 运行 `/codebase-design` skill，获取架构词汇（**module**、**interface**、**depth**、**seam**、**adapter**、**leverage**、**locality**）及其原则（删除测试、“interface 是测试表面”、“一个 adapter = 假设性 seam，两个 adapter = 真实 seam”）。每项建议都必须准确使用这些术语，不要偏移到“component”“service”“API”或“boundary”。
- `CONTEXT.md` 中的 domain language 为良好的 seam 命名；`docs/adr/` 中的 ADR 记录了此命令不应重新争论的决策。

## 流程

### 1. 探索

首先读取项目的 domain glossary（`CONTEXT.md`），以及所涉及区域的所有 ADR。

然后使用 Agent 工具并设置 `subagent_type=Explore`，遍历 codebase。不要遵循僵化的 heuristic；自然地探索，并记录遇到摩擦的位置：

- 在哪些位置，理解一个概念需要在许多小型 module 之间来回跳转？
- 哪些 module 是 **shallow** 的，也就是 interface 与 implementation 几乎同样复杂？
- 哪些位置仅为了可测试性而提取了 pure function，但真正的 bug 隐藏在调用方式中，因而缺少 **locality**？
- 哪些 tightly coupled module 跨越 seam 发生泄漏？
- Codebase 的哪些部分未经测试，或难以通过当前 interface 测试？

对任何疑似 shallow 的对象应用**删除测试**：删除它会使复杂性集中，还是仅仅移动复杂性？所需的信号是“会集中”。

### 2. 以 HTML 报告展示候选对象

将独立完整的 HTML 文件写入操作系统临时目录，避免在 repository 中生成文件。通过 `$TMPDIR` 解析临时目录，不存在时回退到 `/tmp`（Windows 使用 `%TEMP%`）；写入 `<tmpdir>/architecture-review-<timestamp>.html`，使每次运行都生成新文件。为用户打开文件：Linux 使用 `xdg-open <path>`，macOS 使用 `open <path>`，Windows 使用 `start <path>`；同时告知用户绝对路径。

报告通过 **CDN 引入 Tailwind** 完成布局和样式，并通过 **CDN 引入 Mermaid**，用于 graph、flow 或 sequence 能可靠表达结构的 diagram。将 Mermaid 与手工 CSS/SVG visual 混合使用：关系呈 graph 形态（call graph、dependency、sequence）时使用 Mermaid；需要更具编辑设计感的效果（mass diagram、cross-section、collapse animation）时，使用手工 div/SVG。每个候选对象都要有 **before/after 可视化**。充分使用视觉表达。

为每个候选对象渲染一个 card，包含：

- **文件**：涉及哪些文件或 module
- **问题**：当前架构为何造成摩擦
- **解决方案**：使用直白语言描述将发生的变更
- **收益**：用 locality 和 leverage 解释，并说明测试会如何改进
- **Before / After diagram**：并排放置、自定义绘制，展示 shallowness 和 deepening
- **推荐强度**：`Strong`、`Worth exploring`、`Speculative` 三者之一，渲染为 badge

报告末尾添加 **首要推荐**章节，说明应优先处理哪个候选对象及其原因。

**Domain 使用 `CONTEXT.md` 词汇，架构使用 `/codebase-design` 词汇。** 如果 `CONTEXT.md` 定义了“Order”，应说“Order intake module”，而不是“FooBarHandler”或“Order service”。

**ADR 冲突**：如果候选对象与现有 ADR 冲突，只有当实际摩擦严重到值得重新审视该 ADR 时才展示它。在 card 中明确标记，例如 warning callout：_“与 ADR-0007 冲突，但值得重新讨论，因为……”_。不要列出 ADR 所禁止的每个理论 refactor。

完整 HTML scaffold、diagram pattern 和样式指南参见 [HTML-REPORT.md](HTML-REPORT.md)。

此时**不要**提出 interface。文件写入后，询问用户：“你想深入探索其中哪一个？”

### 3. Grilling loop

用户选择候选对象后，运行 `/grilling` skill，与用户一起遍历设计树：约束、dependency、deepened module 的形态、seam 后方的内容，以及保留哪些测试。

随着决策逐渐明确，立即处理相应 side effect。运行 `/domain-modeling` skill，在过程中持续更新 domain model：

- **用 `CONTEXT.md` 中不存在的概念为 deepened module 命名？** 将该术语加入 `CONTEXT.md`。如果文件不存在，仅在此时创建。
- **在对话中明确了含糊术语？** 当场更新 `CONTEXT.md`。
- **用户基于不可忽略的理由拒绝候选对象？** 提议编写 ADR，并这样询问：_“需要我将此决定记录为 ADR，避免未来的架构 review 再次提出它吗？”_ 只有当未来的探索者确实需要该理由来避免提出相同建议时，才提供此选项。跳过短期理由（“目前不值得做”）和不言自明的理由。
- **希望探索 deepened module 的替代 interface？** 运行 `/codebase-design` skill，并使用其 design-it-twice 并行 sub-agent 模式。
