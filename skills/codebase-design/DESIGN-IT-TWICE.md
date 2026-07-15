# Design It Twice

当用户希望为选定的 deepening 候选对象探索替代 interface 时，使用此并行 sub-agent 模式。该模式基于 Ousterhout 的“Design It Twice”：第一个想法通常不会是最佳方案。

使用 [SKILL.md](SKILL.md) 中的词汇：**module**、**interface**、**seam**、**adapter**、**leverage**。

## 流程

### 1. 界定问题空间

生成 sub-agent 前，面向用户说明所选候选对象的问题空间：

- 任何新 interface 都必须满足的约束
- 它依赖哪些 dependency，以及这些 dependency 属于哪个类别（参见 [DEEPENING.md](DEEPENING.md)）
- 用于说明约束的大致代码草图。它不是提案，只用于使约束具体化

向用户展示这些内容，然后立即进入第 2 步。用户阅读和思考的同时，sub-agent 并行工作。

### 2. 生成 sub-agent

使用 Agent 工具并行生成至少 3 个 sub-agent。每个 sub-agent 都必须为 deepened module 设计一个**截然不同**的 interface。

通过独立的技术简报 prompt 每个 sub-agent。简报包含文件路径、coupling 细节、[DEEPENING.md](DEEPENING.md) 中的 dependency 类别，以及 seam 后方的内容。该简报独立于第 1 步面向用户的问题空间说明。为每个 agent 指定不同的设计约束：

- Agent 1：“最小化 interface，最多设置 1-3 个 entry point。最大化每个 entry point 的 leverage。”
- Agent 2：“最大化灵活性，支持多种 use case 和扩展方式。”
- Agent 3：“针对最常见的 caller 进行优化，使默认情况极其简单。”
- Agent 4（如适用）：“围绕 ports & adapters 设计跨 seam dependency。”

简报中同时包含 [SKILL.md](SKILL.md) 词汇和 `CONTEXT.md` 词汇，使每个 sub-agent 的命名与架构语言和项目 domain language 保持一致。

每个 sub-agent 输出：

1. Interface（type、method、param，以及 invariant、顺序和错误模式）
2. 展示 caller 如何使用该 interface 的示例
3. Implementation 在 seam 后方隐藏的内容
4. Dependency 策略和 adapter（参见 [DEEPENING.md](DEEPENING.md)）
5. Trade-off：哪些部分 leverage 较高，哪些部分较低

### 3. 展示并比较

依次展示各项设计，使用户能够逐一理解，然后使用文字进行比较。根据 **depth**（interface 上的 leverage）、**locality**（变更集中的位置）和 **seam placement** 进行对比。

比较后给出自己的推荐：说明你认为哪项设计最强，以及原因。如果不同设计的元素适合组合，提出 hybrid 方案。必须明确表达判断，用户需要有力的解读，而不是一份选项菜单。
