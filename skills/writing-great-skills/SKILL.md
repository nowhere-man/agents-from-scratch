---
name: writing-great-skills
description: 高质量编写和编辑 skill 的 reference，包含使 skill 行为可预测的词汇和原则。
disable-model-invocation: true
---

Skill 的存在，是为了从 stochastic system 中约束出 determinism。**Predictability** 是根本价值：agent 每次运行都采用相同的*过程*，而不是产生相同的输出。下文的每个 lever 都服务于它。

所有**粗体术语**都在 [`GLOSSARY.md`](GLOSSARY.md) 中定义；请在那里查阅完整含义。

## Invocation（调用）

有两种选择，各自承担不同成本：

- **model-invoked** skill 保留 **description**，因此 agent 可以自主触发它，其他 skill 也能调用它（你仍然可以输入其名称）。它会产生 **context load**：description 每个 turn 都位于 context window 中。实现方式：省略 `disable-model-invocation`，并编写面向 model、包含丰富触发表述的 description（“Use when the user wants…，mentions…”）。
- **user-invoked** skill 使 agent 无法访问其 description：只有你输入其名称时才能调用，其他 skill 也无法调用。它没有 context load，但会消耗 **cognitive load**：*你*就是必须记住它存在的 index。实现方式：设置 `disable-model-invocation: true`；`description` 改为面向人，只保留一行摘要并删除触发条件列表。

只有当 agent 必须自主调用该 skill，或另一个 skill 必须调用它时，才选择 model-invocation。如果它始终只由人手动触发，就设为 user-invoked，不承担 context load。

当 user-invoked skills 的数量超出人的记忆能力时，累积的 cognitive load 应通过 **router skill** 解决：使用一个 user-invoked skill 列出其他 skills，并说明各自在何时使用。

## 编写 description

Model-invoked **description** 有两项职责：说明该 skill 是什么，并列出应触发它的 **branch**。每个词都会增加 **context load**，因此 description 比正文更需要严格 pruning：

- **将 skill 的 leading word 前置**：description 正是在这里完成 invocation 工作。
- **每个 branch 只保留一个 trigger。** 用同义词重复描述同一个 branch 属于 **duplication**；“使用 TDD 构建功能……要求 test-first development”是同一个 branch 写了两次。将它们 collapse，只保留真正不同的 branch。
- **删除正文中已经包含的身份说明。** Description 只保留 trigger，以及必要的“当另一个 skill 需要……”调用条款。

## Information hierarchy（信息层级）

Skill 由两类内容构成：**steps** 和 **reference**。两者可以自由组合：skill 可以全部由 steps 构成、全部由 reference 构成，或同时包含两者。核心决策是使用哪一类，以及各自位于 **information hierarchy** 的哪个位置。该 hierarchy 按 agent 对材料的即时需求程度排序：

1. **In-skill step**：`SKILL.md` 中按顺序执行的 action，是首要层级，即 agent 按顺序做什么。每个 step 都以 **completion criterion** 结束，该条件告诉 agent 工作已经完成。Completion criterion 必须*可检查*（agent 能否区分完成和未完成？）；必要时还必须*穷尽*（应写“每个修改过的 model 都已纳入”，而不是“生成变更列表”）。含糊的 criterion 会诱发 **premature completion**。
2. **In-skill reference**：`SKILL.md` 中按需查阅的定义、规则或事实。它常常是合理的扁平 peer set（例如 review 的所有规则位于同一层级），这是一种良好结构，不是问题。*此 skill 完全由 reference 构成。*
3. **External reference**：从 `SKILL.md` 移到单独文件中的 reference，通过 **context pointer** 访问，只在 pointer 触发时加载。它涵盖从*已披露的* reference（例如仍属于该 skill 的同级文件 `GLOSSARY.md`），到完全位于 skill system 外部、可由任何 skill 指向的 **external reference**。

严格的 completion criterion 会推动全面的 **legwork**，即 agent 在任务内部进行的深入工作。这与 skill 是否包含 step 无关，因为“每条规则都已应用”可以约束扁平 reference，正如“每个 step 都已完成”可以约束 sequence。

下移的内容太少，顶层会膨胀；下移过多，则会隐藏 agent 实际需要的材料。如何平衡这两者，就是该决策的全部。

**Progressive disclosure** 是沿 hierarchy 向下移动：将内容从 `SKILL.md` 移到链接文件，使顶层保持清晰。实现方式：在 skill 目录中创建一个按所含内容命名并被链接的 `.md` 文件（此 skill 将完整定义披露到 `GLOSSARY.md`）。部分 skill 有多种用法，每种不同用法就是一个 **branch**，不同运行会沿 skill 中的不同路径前进。Branching 是最清晰的 disclosure 判断标准：每个 branch 都需要的内容 inline，只由部分 branch 访问的内容放到 pointer 后方。决定 agent 何时以及多可靠地访问材料的是 **context pointer** 的*措辞*，不是它的目标。

Hierarchy 决定一项内容位于*多低的位置*，**co-location** 则决定它到达该位置后*与什么放在一起*：将一个概念的定义、规则和 caveat 放在同一 heading 下，而不是分散各处，使 agent 读取其中一部分时也会同时获得相邻内容。

## 何时拆分

**Granularity** 表示 skill 的拆分精细程度。每次拆分都会消耗两种 load 中的一种，因此只有收益足以抵偿成本时才拆分。拆分有两种方式：

- **按 invocation 拆分**：当存在一个应单独触发 skill 的独特 **leading word**，或另一个 skill 必须调用它时，拆出一个 **model-invoked** skill。新的 **description** 会始终加载并产生 **context load**，因此独立调用必须值得这项成本。
- **按 sequence 拆分**：当后续 **step**（当前 step 的 **post-completion steps**）诱使 agent 匆忙结束当前 step（即 **premature completion**）时，拆分该组 **steps**。不让 agent 看到后续 step，可以促使它在当前任务上进行更多 **legwork**。

## Pruning（删减）

让每项含义都保留一个 **single source of truth**：只存放在一个权威位置，使行为变更只需编辑一处。

检查每一行的 **relevance**：它是否仍与该 skill 的行为相关？

然后逐句查找 **no-op**，不能只逐行检查：单独对每个句子运行 no-op test；未通过时，删除整个句子，而不是删减其中几个词。必须果断，大多数未通过的文字都应删除，而不是重写。

## Leading word

**Leading word** 是已经存在于 model pretraining 中的紧凑概念，agent 在运行 skill 时用它来思考，例如 _lesson_、_fog of war_、_tracer bullets_。它在文本中反复出现（但并非必须如此，一个强大的 leading word 可能只需出现一次），逐渐形成 distributed definition，并借助 model 已有的 prior，以最少 token 锚定一整片行为。

它从两个方面服务于 predictability。在正文中，它锚定*执行*：每次该词出现，agent 都会采用相同的行为。在 description 中，它锚定*调用*：当同一个词存在于 prompt、文档和代码中时，agent 会将这种共享语言与 skill 关联，从而更可靠地触发它。

寻找通过 refactor 使用 leading word 的机会。在三个位置分别写出的三元组（**duplication**），或用一个句子暗示一个想法的 description，都是迫切需要 **collapse** 为单个 token 的段落。例如：

- “快速、deterministic、低 overhead” -> _tight_：将一个阶段中反复说明的品质压缩为一个 pretrained word（一个 _tight_ loop）。
- “一个你信得过的 loop” -> _red_：将模糊的 gate 转换为可观察的 binary state（loop 在 bug 上变为 _red_，或者没有）。

这会带来两项收益：更少的 token，*以及*一个更明确、可供 agent 组织思维的 hook。假定每个 skill 都带有可以由 leading word 淘汰的重复表述，并找出它们。

## Failure mode

使用以下术语诊断用户在使用 skill 时可能遇到的问题。

- **Premature completion**：在 step 真正完成前就结束，注意力滑向*完成这件事*。防御顺序：先明确 completion criterion（成本低且局部）；只有当 criterion 无法避免地含糊，*并且*确实观察到匆忙结束时，才通过拆分（sequence cut）隐藏 post-completion steps。
- **Duplication**：相同含义出现在多个位置。它增加维护和 token 成本，并将某项含义在 hierarchy 上的显著程度抬高到超过其真实层级。
- **Sediment**：因为添加内容让人感觉安全、删除内容让人感觉有风险，而沉积下来的陈旧层。任何缺少 pruning 纪律的 skill 默认都会走向这种结果。
- **Sprawl**：skill 过长，即使每一行都仍然有效且独一无二。它损害可读性和可维护性，并浪费 token。解决方法是 information hierarchy：将 **reference** 披露到 pointer 后方，并按 **branch** 或 sequence 拆分，使每条路径只携带自身需要的内容。
- **No-op**：model 默认已经遵守的一行内容，因此付出 load 却没有传达任何有效指令。测试方式：与默认行为相比，它是否改变行为？弱 leading word（agent 本来就大致会做到全面时，仍写 _be thorough_）属于 no-op；修复方法是使用更强的词（_relentless_），而不是换一种 technique。
