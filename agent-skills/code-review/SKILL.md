---
name: code-review
description: Review a commit, staged changes, unstaged changes, diff, patch, or files for functional correctness, regressions, data integrity, concurrency, security, performance, reliability, architecture risks, and missing tests. Use when the user provides a commit hash, asks to review staged or unstaged changes, or wants a thorough quality review of code behavior and production risk.
---

# Code Review

审查改动中的功能行为和系统质量，以 findings 形式识别影响功能正确性、性能、数据完整性、并发安全、安全边界、扩展性、可靠性、架构 contract 和 regression protection 的具体风险，并提供可验证的证据与最小修复方向。

## 1. 固定 Scope Manifest

严格按用户指定的入口确定范围，不混合 staged changes 和 unstaged changes：

- **Commit hash**：用 `git rev-parse --verify <hash>^{commit}` 验证并解析完整 SHA；使用 `git show --stat --oneline <hash>` 和 `git show --find-renames --format=fuller <hash>`。遇到 merge commit 时明确使用的 parent；不同 parent 会改变结论时再询问。
- **Staged changes**：只使用 `git diff --cached --stat` 和 `git diff --cached`。
- **Unstaged changes**：使用 `git diff --stat`、`git diff` 和 `git status --short`；只纳入与改动直接相关的 untracked files，并在结果中说明。
- **Diff、patch 或 files**：审查用户提供的材料及判断行为所需的直接代码上下文，不扩张到无关改动。

开始审查前建立同一份 Scope Manifest：

```yaml
scope_type: commit | staged | unstaged | diff | patch | files
repo_root: /absolute/path
comparison: exact command or base/head
scope_fingerprint: immutable identifier
changed_files: []
untracked_files: []
user_requirement: optional
commit_message: optional
```

Commit 使用完整 SHA；工作区、diff、patch 或 files 使用文件列表和内容的稳定 hash，纳入的 untracked file 必须包含内容 hash。所有 specialist 必须收到并返回同一个 fingerprint。主 agent 汇总前重新计算；范围变化时丢弃过期候选并重新检查。

只报告本次改动引入、暴露或显著恶化的问题。完成条件：准确说明审查对象、比较基线和 changed files，且范围非空。

## 2. 建立行为上下文

不要只读 diff 行。围绕每个 changed behavior 检查必要的调用方、被调用方、类型、schema、migration、配置、错误处理和现有 Tests。判断依据按以下顺序使用：

1. 用户明确给出的需求和业务规则。
2. 当前接口、调用路径、数据约束和 observable behavior。
3. 能明确表达意图的 commit message、Tests 和相邻实现。

记录重要行为的输入、状态、执行路径、数据边界、失败路径和预期结果。不要因为缺少额外材料而停止可以从代码验证的审查。

## 3. 分派 Specialist Tracks

对非微小改动创建 3 个只读 specialist subagent；可以并行时同时运行，容量不足时分批运行，但不得跳过 track。满足以下任一条件即视为非微小：包含多个 changed behavior；跨 module 或层；涉及持久化、transaction、并发、权限、cache、外部依赖、消息或 hot path；失败会影响用户、资金、数据或生产可用性。

| Track | 负责的 Lens |
|---|---|
| **Behavior & Trust** | Functional Correctness & Regression；Data Integrity & Concurrency；Security & Privacy |
| **Scale & Failure** | Performance & Scalability；Reliability & Operability |
| **Architecture** | Architecture & Design |

主 agent 负责 Tests Lens、关键 correctness 复查、Evidence Gate、去重、severity 校准和最终输出。仅当改动显然很小、单一且低风险时，主 agent 可以独立应用全部 Lens。

给 specialist 提供 Scope Manifest、读取范围的精确命令、用户需求和分配的 Lens；不要在 prompt 中复制多份大 diff。要求它：

- 只读检查，不修改代码，不发布评论，不继续创建 subagent。
- 沿执行路径验证问题，不按关键词或 checklist 机械匹配。
- 主动查找否定候选的 guard、约束、Tests 和调用条件。
- 只返回候选 finding；字段不完整的内容放入 verification gaps，不凑数。
- 返回 `NO_FINDINGS` 时仍列出已检查的 changed behaviors 和 verification gaps。

每个候选必须使用：

```yaml
scope_fingerprint: "..."
lens: "..."
severity_guess: P0 | P1 | P2 | P3
title: "..."
location: path/to/file.ext:L42
symbol: "..."
attribution: "本次改动如何引入、暴露或恶化问题"
trigger: "输入、状态或前置条件"
execution_path: "从入口到故障点的路径"
impact: "可观察结果或具体系统风险"
evidence: "代码、约束、调用方或 Test 证据"
existing_guard_or_test_checked: "已排除的保护"
minimal_fix_direction: "最小修复方向"
verification_gap: "仍未验证的部分，可为空"
```

## 4. 应用 Quality Lenses

### Functional Correctness & Regression

- 需求和业务规则、正常路径、边界输入、空值、空集合和异常路径。
- 状态转换、遗漏分支、错误恢复、side effect 顺序和隐藏逻辑漏洞。
- API、事件、配置和存储行为的 backward compatibility。
- 对已有调用方、共享状态和相邻功能造成的 regression。

必须说明哪条执行路径产生错误结果。未知业务意图放入 Open Questions，不能伪装成 finding。

### Data Integrity & Concurrency

- transaction 边界、atomicity、consistency、读写顺序和失败回滚。
- race condition、lost update、重复请求、idempotency、乱序和重复消息。
- unique constraint、锁、version check 与应用层检查是否匹配。
- migration、backfill、默认值、兼容读写、数据覆盖和数据丢失。

不要仅因“可能并发”报告问题；指出共享资源、交错顺序和错误结果。

### Security & Privacy

- authentication、authorization、tenant isolation 和对象级权限。
- injection、不可信输入、路径或命令构造、反序列化和 SSRF 类边界。
- secret、token、PII 和业务敏感数据的存储、返回与日志泄漏。
- 可被滥用的资源消耗、权限提升和保护绕过。

只报告可到达的攻击路径或明确违反 trust boundary 的行为。

### Performance & Scalability

- loop I/O、N+1 query、重复计算、逐条处理与 batch 机会。
- query 形状、索引、排序、扫描范围和 algorithmic complexity。
- 无界集合、缺失分页、大对象复制、序列化和 memory pressure。
- blocking I/O、关键线程、connection/thread pool、锁竞争和高并发热点。
- cache key、命中价值、生命周期、一致性及 penetration、stampede、avalanche。

不要自动要求 cache、分页、索引或 batch。指出增长维度、hot path、资源放大和触发条件；纯 micro-optimization 不是 finding。调用方可控或随数据增长的 `N` 与逐项 I/O、无界 materialization、嵌套扫描或无限 key space 结合时，静态执行路径已足以证明 amplification；缺少生产规模只影响 severity 或 verification gap。

### Reliability & Operability

- timeout、cancellation、retry、backoff、retry budget 和 retry safety。
- 外部依赖、部分失败、fallback、degradation 和 error propagation。
- queue delivery semantics、ack 时机、poison message、重复消费和 shutdown。
- file、stream、connection、lock、goroutine/thread 等资源释放。
- 关键失败是否有可行动的 log、metric、trace 和告警信号。

跨 Lens 问题按主要可观察影响归类，不重复报告。

### Architecture & Design

- 分层、module boundary、domain boundary 和 dependency direction。
- Controller、service、domain、repository 和 integration 的职责归属。
- coupling、循环依赖、跨层数据泄漏、隐式 contract 和持久化边界。
- public contract、多个真实消费者和已经发生的行为 divergence。

只报告会破坏系统边界、contract、依赖方向或形成当前风险的设计问题。没有已验证当前消费者的 Architecture 候选最多为 P2；无法确认当前 contract 影响时放入 Open Questions。不要报告局部命名、方法长度、代码布局、纯重复形状或假设的未来扩展；这些不是 Architecture finding。

### Tests

主 agent 检查：

- changed behavior、关键边界和失败路径是否有能捕获 regression 的 Test。
- transaction、并发、重复请求、idempotency、权限和 tenant isolation 是否在风险适用时被覆盖。
- query 数量、分页边界、资源上限、timeout 和降级路径是否需要可重复验证。
- Test 是否真正经过修改路径，assertion 是否会在问题出现时失败。

实际 bug 对应的缺失 Test 通常并入同一个 finding。只有没有已证实 bug，但本次改动新增或改变权限、资金、不可逆 side effect、数据完整性或 migration、并发或 idempotency、对外 contract 等关键行为，且现有 Test 无法在 regression 时失败，才单独报告 Tests finding。

## 5. 执行 Evidence Gate

Specialist 输出只是候选。主 agent 必须回到代码和调用路径复核，每个最终 finding 同时满足：

- **归因**：由本次改动引入、暴露或显著恶化。
- **触发**：存在具体输入、状态、交错顺序或前置条件。
- **影响**：存在可观察错误、生产风险或系统边界破坏。
- **证据**：location、symbol 和执行路径准确，且已排除现有 guard、约束和 Test。
- **修复**：存在与问题规模相称的最小修复方向。

缺少 trigger、impact 或准确 location 的候选不得进入 Findings。不确定项放入 Open Questions；一个根因只保留一个 finding。

按主要影响选择 Lens：错误结果归 Functional，数据错误归 Data，越权归 Security，资源放大归 Performance，失败隔离归 Reliability，系统边界或 contract 归 Architecture。

按影响而非信心确定 severity：

- **P0**：广泛数据破坏、可直接利用的严重安全问题或核心系统不可用的 release blocker。
- **P1**：很可能发生的 correctness、安全、数据完整性问题，或核心业务规则缺失。
- **P2**：条件受限但真实的行为错误、明显 regression、可复现的扩展性问题或当前架构风险。
- **P3**：低影响但仍真实、可定位、可执行的质量风险；不包含 style、命名、comment、verbosity 或局部简化建议。

## 6. 验证与输出

可行时运行与改动直接相关、不会修改外部状态的 Tests、静态检查或 benchmark。不能运行时记录 verification gap。汇总前再次计算 fingerprint；不匹配时重新审查。

Findings 优先，按 P0 → P3 全局排序，不按 Lens 或 specialist 分割报告：

```text
[P1][Data Integrity & Concurrency] 简短标题
path/to/file.ext:L42 — 触发条件和影响。必要证据。最小修复方向。
```

- 默认一项一行；复杂执行路径使用一个短段落。
- 保留准确 file、line 和 symbol，不复述显而易见的 diff。
- 不拼接 specialist 原始报告，不输出无证据 checklist。
- Findings 后仅按需给出 Open Questions / Assumptions、简短 change summary 和 verification gaps。
- 没有 finding 时明确说明，并列出未运行的验证和 residual risk。
