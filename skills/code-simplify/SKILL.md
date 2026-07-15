---
name: code-simplify
description: Review recently changed or explicitly scoped code for behavior-preserving simplification, clarity, consistency, and maintainability opportunities.
---

# Code Simplify

审查改动中的代码表达与局部结构，以 findings 形式指出能够在保持 observable behavior、public contract、side effect，以及失败条件、错误类型和错误返回方式不变的前提下，使代码更清晰、更简单、更一致、更易维护的具体改进。

## 1. 固定 Scope Manifest

严格按用户指定的入口确定范围，不混合 staged changes 和 unstaged changes：

- **Commit hash**：用 `git rev-parse --verify <hash>^{commit}` 验证并解析完整 SHA；使用 `git show --stat --oneline <hash>` 和 `git show --find-renames --format=fuller <hash>`。
- **Staged changes**：只使用 `git diff --cached --stat` 和 `git diff --cached`。
- **Unstaged changes**：使用 `git diff --stat`、`git diff` 和 `git status --short`；只纳入相关 untracked files，并在结果中说明。
- **Diff、patch 或 files**：审查用户提供的材料及判断简化是否等价所需的直接上下文。

记录 scope type、comparison、changed files 和稳定 fingerprint。只报告本次改动新增、暴露或显著恶化的书写问题，不清理相邻旧代码。

完成条件：能够准确说明审查对象、比较基线和 changed files，且范围非空。

## 2. 建立 Behavior Baseline

不要只读 diff 行。阅读完整函数、直接调用方、类型和相关 Tests，确认：

- public contract、输入输出和错误语义。
- side effect、执行顺序、状态变化和资源生命周期。
- exception、logging、serialization、timing 和并发语义。
- 当前代码中真正使用的 abstraction、config、helper 和 dependency。

高风险路径无法确认 behavior equivalence 时，不提交 simplification finding。完成条件：每个候选都有明确的行为边界和具体替代方向。

## 3. 应用 Simplification Lenses

### Removability & YAGNI

- dead code、不可达分支、冗余状态和重复条件。
- 未使用的 speculative flexibility、无人设置的 config 和纯转发层。
- single-implementation abstraction、不必要 dependency 和手写的 stdlib/native 能力。
- 没有提供行为、边界或复用价值的 indirection。

只有确认删除后 public contract、side effect 和错误语义不变时才报告。不要为假设的未来需求保留复杂度，也不要删除当前有效边界。

### Control Flow & Clarity

- 不必要 nesting、重复分支、中间状态和绕行控制流。
- 可以用 guard clause、明确 `if/else` 或 `switch` 表达的复杂条件。
- nested ternary、dense one-liner 和需要反复解码的 clever expression。
- 分散但强相关的局部逻辑，以及复述实现步骤的机械代码。

clarity 优先于最少行数。更短但更隐晦的写法不是 simplification。

### Naming & Comments

- 与实际含义、单位、生命周期或作用域不一致的命名。
- 复述代码、已经失真、解释错误实现或掩盖复杂度的 comment。
- 无法从上下文判断含义且容易误用的 magic number / magic string。

只报告会造成具体理解或修改成本的问题。个人措辞偏好、拼写风格和无影响的命名差异默认省略。

### Duplication & Cohesion

- 已造成 divergence、重复修复或不一致行为的重复逻辑。
- 同一局部任务被不必要地拆散，导致读者必须跨多层追踪。
- 一个局部函数混合无关步骤，且存在更直接、不增加 abstraction 的拆分或组织方式。

不要因代码形状相似就要求抽象。没有当前成本的 duplication 不是 finding；不要用新的 interface、factory 或 hierarchy 替代简单重复。

### Consistency & Native Idioms

- 与相邻代码已经稳定使用的表达方式无理由冲突。
- formatter、linter、compiler 或现有 helper 已经能确定处理的写法。
- 可用已有 helper、stdlib 或 native platform 能力直接替代的自定义实现。

不要套用固定语言偏好，例如一律使用 `function`、arrow function、显式 return type、特定 import 顺序或 try/catch 形式。不要重复 formatter 或 linter 已经会自动修复的纯格式问题。

## 4. 通过 Evidence Gate

每个 finding 必须同时满足：

- **归因**：由本次范围内的改动新增、暴露或显著恶化。
- **成本**：存在具体理解、修改、调试、重复修复或 dependency surface 成本。
- **等价**：能够说明更简单的替代方案，并证明 observable behavior、public contract、side effect、错误语义和执行顺序不变。
- **证据**：location、symbol 和相关使用点准确，且不存在需要保留当前结构的真实边界。
- **范围**：建议只触及必要代码，不扩张成架构重构或全仓 cleanup。

只有 smell、个人偏好、行数差异或“以后可能更灵活”不是 finding。不确定项放入 Open Questions，不用 hedging 包装成 P3。一个根因只保留一个 finding。

纯 simplification finding 不使用 P0 或 P1：

- **P2**：复杂度位于核心或高频修改路径，已经造成明显理解、修改、调试、重复修复或 dependency 成本，且存在清晰的 behavior-preserving 替代方案。
- **P3**：局部且低风险，但仍有具体成本和明确简化方向。

如果候选会改变功能、输出、安全控制、数据保护、性能特征、资源生命周期、public contract 或架构边界，不在本 skill 中报告；将其放入 Open Questions 并建议使用 `code-review`。

## 5. 验证候选

可行时运行不会修改文件的 formatter check、linter、compiler、Tests 或静态检查，以验证使用关系和 behavior baseline。不能运行时记录 verification gap，不假装已验证。

重新读取候选位置和直接调用方，确认建议不会：

- 删除有效 abstraction、trust-boundary validation、安全控制、必要错误处理或 regression Test。
- 合并无关职责、引入新的 dependency、config 或 speculative abstraction。
- 为减少行数而降低 clarity、debuggability 或可维护性。

完成条件：每个 finding 都能给出可执行的最小改写，并通过 Evidence Gate。

## 6. 输出

Findings 优先，按 P2 → P3 排序，不按 Lens 分成互不排序的报告：

```text
[P2][Control Flow & Clarity] 简短标题
path/to/file.ext:L42 — 当前具体成本。behavior-preserving 的最小简化方向。
```

- 默认一项一行；非显然等价关系使用一个短段落。
- 保留准确 file、line 和 symbol，不复述显而易见的 diff。
- 删除客套、表扬、无意义 hedging 和 emoji。
- Findings 后仅按需给出 Open Questions / Assumptions、简短 change summary 和 verification gaps。
- 没有 finding 时输出 `Lean already. Ship.` 并停止；若存在无法验证的候选或 residual risk，再附一行说明。
