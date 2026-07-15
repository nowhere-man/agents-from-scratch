---
name: diagnosing-bugs
description: 用于困难 bug 和 performance regression 的诊断循环。用户说“diagnose”或“debug this”，或报告某项功能损坏、抛出异常、失败或缓慢时使用。
---

# 诊断 Bug

一套用于困难 bug 的严格方法。只有明确说明理由时才能跳过阶段。


## 阶段 1：建立 feedback loop

**这就是此 skill 的核心。** 其他内容都只是机械步骤。如果拥有针对该 bug 的 **tight** 通过/失败信号，也就是能在*这个* bug 上变为 red 的信号，就一定能找到原因；bisection、hypothesis testing 和 instrumentation 都只是在利用这个信号。没有这样的信号，再久地盯着代码也无济于事。

在这里投入远超其他阶段的精力。**要主动出击，要有创造性，拒绝放弃。**

### 构建方法：按以下顺序尝试

1. 在任何能触达 bug 的 seam 上编写 **failing test**：unit、integration 或 e2e。
2. 针对正在运行的 dev server 编写 **Curl / HTTP script**。
3. 使用 fixture input 进行 **CLI invocation**，将 stdout 与已知正确的 snapshot 进行 diff。
4. 编写 **headless browser script**（Playwright / Puppeteer）：驱动 UI，并对 DOM、console 和 network 进行断言。
5. **重放捕获的 trace。** 将真实的 network request、payload 或 event log 保存到磁盘，再通过隔离的代码路径重放。
6. **一次性 harness。** 启动系统的最小子集（一个 service、mocked dependency），通过单次 function call 执行 bug 路径。
7. **Property / fuzz loop。** 如果 bug 表现为“有时输出错误”，运行 1000 组随机输入并寻找 failure mode。
8. **Bisection harness。** 如果 bug 出现在两个已知状态（commit、dataset、version）之间，自动执行“在状态 X 启动、检查、重复”，以便使用 `git bisect run`。
9. **Differential loop。** 让相同输入分别经过旧 version 和新 version（或两套 config），再对输出进行 diff。
10. **HITL bash script。** 最后的手段。如果必须由人点击，使用 `scripts/hitl-loop.template.sh` 驱动*用户*，使 loop 仍然结构化。将捕获的输出反馈给自己。

建立正确的 feedback loop，bug 就已经解决了 90%。

### Tighten loop

将 loop 视为产品。拥有一个 loop 后，进一步将它 **tighten**：

- 能否让它更快？（cache 初始化结果、跳过无关初始化、缩小测试范围。）
- 能否让信号更准确？（对具体症状进行断言，而不是只断言“没有 crash”。）
- 能否让它更 deterministic？（固定时间、设置 RNG seed、隔离 filesystem、冻结 network。）

一个耗时 30 秒且 flaky 的 loop 几乎等同于没有 loop；一个耗时 2 秒且 deterministic 的 loop 才是 tight，这是强大的 debugging 能力。

### Non-deterministic bug

目标不是得到干净的 repro，而是获得**更高的复现率**。循环触发 100 次、并行执行、增加压力、缩窄 timing window、注入 sleep。复现率为 50% 的 flaky bug 可以 debug，1% 则不行；持续提高复现率，直到能够 debug。

### 确实无法建立 loop 时

停止并明确说明情况。列出已经尝试的方法。向用户请求：(a) 可复现问题的环境访问权限；(b) 已捕获的 artifact（HAR file、log dump、core dump、带时间戳的 screen recording）；或 (c) 添加临时 production instrumentation 的权限。没有 loop 时，**不要**继续提出 hypothesis。

### 完成标准：能够变为 red 的 tight loop

当 loop 达到 **tight** 且 **red-capable** 时，阶段 1 才算完成：你可以给出**一条命令**，可以是 script 路径、test invocation 或 curl；你已经**至少运行过一次**该命令（粘贴 invocation 及其输出），且它满足：

- [ ] **Red-capable**：驱动实际的 bug 代码路径，并断言**用户描述的确切症状**，因此能在该 bug 存在时变为 red，修复后变为 green。不能只“无错误运行”，必须能够*捕获这个特定 bug*。
- [ ] **Deterministic**：每次运行的判定相同（对于 flaky bug，按上述方法固定一个较高的复现率）。
- [ ] **Fast**：耗时数秒，而不是数分钟。
- [ ] **Agent-runnable**：可以无人值守地运行；仅可通过 `scripts/hitl-loop.template.sh` 让人参与 loop。

如果发现自己在该命令存在之前就开始阅读代码并构建理论，**立即停止。直接跳到 hypothesis 正是此 skill 要防止的失败。** 没有 red-capable 命令，就不能进入阶段 2。

## 阶段 2：复现 + 最小化

运行 loop，观察它变为 red，也就是 bug 出现。

确认：

- [ ] Loop 产生的是**用户**描述的 failure mode，而不是刚好发生在附近的其他失败。Bug 错了，修复也会错。
- [ ] 该失败可以在多次运行中复现；对于 non-deterministic bug，复现率必须足够高，可以据此 debug。
- [ ] 已捕获确切症状（error message、错误输出、缓慢耗时），使后续阶段可以验证修复确实解决了该症状。

### 最小化

Loop 变为 red 后，将 repro 缩小为**仍会变为 red 的最小场景**。每次只删除一项 input、caller、config、data 或步骤，每次删除后重新运行 loop，只保留对失败不可或缺的内容。

这样做是因为：最小 repro 可以缩小阶段 3 的 hypothesis space（需要怀疑的 moving part 更少），并在阶段 5 成为干净的 regression test。

当**每个剩余元素都不可或缺**时，此步骤完成；删除其中任何一个元素，loop 都会变为 green。

完成复现**并且**完成最小化之前，不要继续。

## 阶段 3：提出 hypothesis

在测试任何 hypothesis 前，生成 **3-5 个按优先级排序的 hypothesis**。只生成一个 hypothesis 会使思维锚定在第一个看似合理的想法上。

每个 hypothesis 都必须**可证伪**：说明它产生的预测。

> 格式：“如果 <X> 是原因，那么 <改变 Y> 会使 bug 消失，或 <改变 Z> 会使 bug 恶化。”

如果无法陈述预测，该 hypothesis 只是一种感觉，应将其丢弃或进一步明确。

**测试前向用户展示排序后的列表。** 用户通常拥有可以立即改变排序的 domain knowledge（“我们刚刚部署了与第 3 项相关的变更”），或知道哪些 hypothesis 已被排除。这是成本低、节省时间多的 checkpoint。不要因此阻塞；如果用户暂时不在，按自己的排序继续。

## 阶段 4：Instrumentation

每个 probe 都必须对应阶段 3 中的某项具体预测。**每次只改变一个变量。**

工具优先级：

1. 如果环境支持，使用 **Debugger / REPL inspection**。一个 breakpoint 胜过十条 log。
2. 在能够区分 hypothesis 的位置添加 **targeted log**。
3. 绝不“记录所有内容再 grep”。

为**每条 debug log 添加 tag**，使用唯一前缀，例如 `[DEBUG-a4f2]`。这样最后只需一次 grep 即可完成清理。没有 tag 的 log 会残留，有 tag 的 log 必须删除。

**Performance 分支。** 对于 performance regression，log 通常不是正确工具。应先建立 baseline measurement（timing harness、`performance.now()`、profiler、query plan），然后 bisect。先测量，再修复。

## 阶段 5：修复 + regression test

在修复**之前**编写 regression test，但前提是存在**正确的 seam**。

正确的 seam 能让测试按 call site 中的实际发生方式执行**真实 bug pattern**。如果唯一可用的 seam 太 shallow（例如 bug 需要多个 caller，却只能进行 single-caller test；或 unit test 无法复制触发 bug 的调用链），在该处编写 regression test 会带来虚假的信心。

**如果不存在正确的 seam，这本身就是诊断结果。** 记录这一点。Codebase 架构阻止了对该 bug 的可靠约束，应在下一阶段标记此问题。

如果存在正确的 seam：

1. 在该 seam 处将最小 repro 转换为 failing test。
2. 观察测试失败。
3. 应用修复。
4. 观察测试通过。
5. 针对原始的未最小化场景，重新运行阶段 1 的 feedback loop。

## 阶段 6：清理 + post-mortem

宣布完成前必须满足：

- [ ] 原始 repro 不再复现（重新运行阶段 1 的 loop）
- [ ] Regression test 通过（或已记录缺少 seam）
- [ ] 已删除所有 `[DEBUG-...]` instrumentation（`grep` 该前缀）
- [ ] 已删除一次性 prototype（或将其移动到明确标记的 debug 位置）
- [ ] 在 commit / PR message 中说明最终证实正确的 hypothesis，使下一位 debugger 能从中学习

**然后询问：什么措施原本可以防止这个 bug？** 如果答案涉及架构变更（缺少良好的测试 seam、caller 相互纠缠、存在 hidden coupling），将具体情况交给 `/improve-codebase-architecture` skill。应在修复完成**之后**提出建议，而不是之前；此时掌握的信息比开始时更多。
