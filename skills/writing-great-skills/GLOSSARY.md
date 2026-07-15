# Glossary：构建优秀 Skills

这是描述优秀 skill 构成要素的 domain model。Skill 的存在，是为了从 stochastic system 中约束出 determinism；根本价值是 **Predictability**，下文每个术语都是作用于它的 lever。本文是 [`writing-great-skills`](SKILL.md) 披露的 reference。

术语按 axis 分组：**Invocation**（如何调用 skill）、**Information Hierarchy**（如何组织内容）、**Steering**（如何塑造 agent 的 runtime behavior）和 **Pruning**（如何保持精简）。每个 **failure mode** 都放在能够解决它的 lever 旁，并标记为 _failure mode_。

任何定义中的**粗体术语**也在此 glossary 中定义，可按 heading 查找。

## Predictability

Skill 让 agent 每次运行都采用相同*方式*的程度：过程相同，而不是输出相同（brainstorming skill 应当*可预测地*产生分歧；token 会变化，行为不会）。这是其他所有术语服务的根本价值；成本和可维护性是它的表现，而不是与它竞争的目标。

_避免使用_：consistency、reliability、robustness、output-determinism

## Invocation（调用）

如何调用 skill，以及该选择需要承担的两种 load。

### Model-Invoked

保留 **description** 字段的 skill，agent 因此可以看到并自主触发它；人仍然可以输入其名称，所以 model-invocation 始终*包含*用户调用。不存在 model-only 状态：description 只会增加 agent 的发现能力，绝不会取消人的调用能力。它以每个 turn 上永久的 **context load** 换取可发现性。其他 skill 也可以调用它，因为使 agent 能发现它的 description 同时也使它可调用。内容全部为 **reference** 的 model-invoked skill 也可以作为共享 reference 的存放位置：其他 skill 可以调用它，因此多个 skill 需要的 reference 能放在一处。只有当 agent 必须自主调用 skill 时才选择 model-invocation；如果它只会由人手动触发，删除 description，不承担 context load。

_避免使用_：ability、tool、capability

### User-Invoked

删除 **description** 的 skill：agent 看不到它，只有人输入其名称才能调用（user-_only_；**model-invoked** 则是 user-_and-agent_）。它放弃 agent discoverability，以换取零 **context load**。因为没有 description，除人之外任何对象都无法调用它，其他 skill 也不能触发它。

_避免使用_：procedure、workflow、command

### Description

Skill 的 machine-readable trigger，也是 **model-invoked** skill 被迫始终加载的唯一 **context pointer**。它是否存在本身*就是* invocation axis：保留它，skill 就是 model-invoked（其他 skill 也能调用）；删除它，skill 就是 **user-invoked**，只能由人调用。它是 model-invoked skill 的 **context load** 来源。

_避免使用_：frontmatter、summary

### Context Pointer

保存在 agent context 中的一项 reference，它为 context 之外的材料命名，并编码访问该材料的条件。**Description** 是顶层 context pointer（context window → skill）；指向 disclosed file 的 pointer 是下一层的同类对象。决定 agent *何时*以及*多可靠地*访问材料的是 pointer 的措辞，不是目标本身。将必需材料放在措辞薄弱的 pointer 后方会产生 variance bug：先修正措辞，只有在强化措辞仍然失败时，才 inline 该材料。

_避免使用_：link、reference、import

### Context Load

**Model-invoked** skill 对 agent context window 施加的成本，也就是始终加载的 **description** 所消耗的 token 和 attention。**User-invoked** skill 通过不设置 description 来避免该成本；它也是拆分出更多 model-invoked skill 时的制约因素。

_避免使用_：token cost、context bloat

### Cognitive Load

**User-invoked** skill 对人施加的成本，即人必须记在脑中的内容：存在哪些 skill，以及何时使用每个 skill（人就是 index）。**Model-invocation** 通过使 agent 能发现 skill 来消除该成本；它也是拆分出更多 user-invoked skill 时的制约因素。这不是必须最小化的成本：它是 human agency 的代价，也是部分 skill 保持 user-invoked 的原因。在需要人类判断的位置承担它，在不需要的位置消除它。

_避免使用_：human index、burden、overhead

### Router Skill

一种 **user-invoked** skill，职责是指向其他 user-invoked skills，列出每个 skill 的名称和使用时机，使人只需记住一个 skill，而不是多个。它只能提示，不能触发这些 skill：user-invoked skill 没有 **description**，因此只有人能调用。当 user-invoked skills 增多时，它是解决 **cognitive load** 的方法。

_避免使用_：dispatcher、menu、registry、index、router procedure

### Granularity

Skill 的拆分精细程度。更细的拆分会消耗两种 load 中的一种：更多 **model-invoked** skill 消耗 **context load**（更多 description 挤入 window 并争夺 attention）；更多 **user-invoked** skill 消耗 **cognitive load**（人需要记住并调用更多 skill）。两种 cut 指导拆分。按 **invocation** 拆分时，在存在独特 **leading word** 可以触发 skill 的位置拆出 model-invoked skill；该 trigger word 必须是 prompt 中实际使用的词。按 **sequence** 拆分时，在某个 step 的 **post-completion steps** 需要隐藏的位置拆分一组 **steps**，因为将该 step 隔离到自己的 context 中会清除后续步骤。也要警惕反向操作：合并 sequence 会向每个 step 暴露其 post-completion steps，诱发 premature completion。

_避免使用_：chunking、modularity

## Information Hierarchy（信息层级）

如何组织 skill 内容，以及每项内容位于 hierarchy 的多低位置。

### Information Hierarchy

按 agent 对内容的即时需求程度对 skill 内容进行排序。它是由两种 cut 形成的单一 hierarchy：位于文件内或 pointer 后方，以及属于 step 或 reference。层级如下：

- **Steps**：位于文件内，首要层级
- **Reference**：位于文件内，次要层级
- **Reference**：已披露，位于 **context pointer** 后方

没有 **steps** 的 skill 只使用后两个层级，通常是合理的扁平 peer set（例如 review 的每条规则都在同一层级），这是一种良好结构，不是问题。Information hierarchy 独立于 invocation：无论 skill 全部由 steps 构成、全部由 reference 构成，还是同时包含两者，它都可以是 model-invoked 或 user-invoked。Skill 包含 step 时，本应披露却仍位于文件内的 reference 会埋没 step，使 agent 是否关注 step 变成随机事件；这不仅影响可读性，也是 variance lever。保持 hierarchy 顶层清晰，并尽可能将内容下移。

_避免使用_：structure、organization、layout

### Steps

Agent 按顺序执行的 action。Skill 包含 step 时，它们是内容的首要层级，也是应位于 `SKILL.md` 中的部分。并非每个 skill 都有 step：skill 可以全部由 steps 构成（`tdd`）、全部由 **reference** 构成（review），或同时包含两者，这与 invocation 无关。每个 step 都以 **completion criterion** 结束，该 criterion 可能清晰，也可能含糊。

_避免使用_：workflow、instructions、choreography

### Reference

Agent 按需查阅的材料，包括定义、事实、参数、示例和条件性指令。Skill 包含 **steps** 时，reference 次于 steps；skill 不包含 step 时，reference 就是全部内容；reference 也可以完全位于任何 skill 之外，参见 **External Reference**。它通过 **context pointer** 访问，是 **progressive disclosure** 的首要候选对象。

_避免使用_：supporting material、docs、background

### External Reference

位于 skill system 外部的 **reference**：一个普通文件，没有 **description**、没有 **steps**、不可调用，但任何 skill 都能指向它。它适合存放无需自行触发的共享 reference，也是两个 **user-invoked** skill 可以使用的唯一共享位置，因为两者都没有 description，无法相互触发。

_避免使用_：doc、resource、knowledge base

### Progressive Disclosure

沿 hierarchy 向下移动 **reference**，将其移出 `SKILL.md` 并放到 **context pointer** 后方，使顶层保持清晰。它的首要目的不是优化 token，而是保护 **information hierarchy**。**Branching** 为这种移动提供依据：只有部分 branch 需要的内容予以披露，每条路径都需要的内容 inline；如果 pointer 无法可靠地为必需材料触发，先强化其措辞，只有仍然失败时才将材料移回 inline。

_避免使用_：lazy loading、chunking

### Co-location

将 agent 需要同时获取的材料放在同一位置：一个概念的定义、规则和 caveat 放在一个 heading 下，而不是散布在文件各处，使 agent 读取其中一部分时也能获得相邻内容。它是 **Information Hierarchy** 在文件内部的搭档：hierarchy 决定一项内容位于*多低的位置*，co-location 决定它到达该位置后*与什么放在一起*。**Reference** 正文没有唯一正确的格式；判断标准是 skill 应当像为 agent 编写的文档一样易读，成组材料能做到这一点，分散材料则不能。它不同于 **Duplication**：duplication 在两个位置重复同一含义，而分散是将一个含义拆碎到多个位置。

_避免使用_：grouping、clustering、cohesion

### Sprawl

_Failure mode._ Skill 单纯过长，也就是 `SKILL.md` 行数过多，与内容是否陈旧或重复无关。即使所有行都有效且独一无二，skill 仍可能 sprawl。它会消耗可读性（agent 必须先读过更多内容才能行动，attention 也会分散到多余内容上）、可维护性（每多一行，就多一行需要保持 **relevant**）和 token。解决方法是 **information hierarchy**：将 **reference** 下移到 **context pointer** 后方，并按 **branch** 或 sequence 拆分，使每条路径只携带自身需要的内容。它不同于 **sediment**（陈旧内容累积造成的长度）和 **duplication**（重复含义造成的长度）；无论原因是什么，sprawl 指的都是长度本身。

_避免使用_：bloat、length、size、verbosity

## Steering（引导）

将 agent runtime behavior 塑造成趋向 **Predictability** 的 lever。

### Branch

Skill 的一种独特调用方式，也就是该 skill 处理的一种 case，使不同运行沿不同路径通过 skill。包含许多 step 的 skill 可能有许多 branch；线性 skill 则没有 branch。

_避免使用_：path、case、fork

### Leading Word

已经存在于 model pretraining 中的紧凑概念，也称 _Leitwort_，agent 在运行 skill 时用它来思考。它调用 model 已有的 prior，以尽可能少的 token 编码一项行为原则，例如 _lesson_、_proximal zone of development_、_fog of war_、_tracer bullets_。它以 token 而不是句子的形式反复出现，在 skill 中累积出 distributed definition，并锚定一整片行为。只要定义清晰，自创新词也可以生效，但虚构词无法调用 prior；pretrained word 免费提供的内容，需要为虚构词付出定义 token。优先使用已有词汇。

Leading word 从两个方面服务于 **predictability**。在正文中，它锚定**执行**：每次概念出现，agent 都会采用相同的行为；在扁平 reference 中，它让 attention 聚焦于一类需要查找的事物，使每次运行都调用正确的检查。在 **description** 中，它锚定**调用**，且作用不限于 skill 内部：当同一个词存在于 prompt、文档和 codebase 中时，agent 会将这种共享语言与 skill 关联，从而更可靠地触发它。应使用真正想调用该 skill 时实际使用的 leading word 来编写 description。

_避免使用_：keyword、term、motif

### Completion Criterion

告诉 agent 一项工作已经完成的条件，也就是 agent 用来判断的目标。两项属性使它成为 lever，而不仅是一项品质。它的**清晰度**（agent 能否区分完成与未完成？）抵抗 **premature completion**：含糊的界限（“已经理解”）会让 agent 宣布完成并滑向下一个 step；该 axis 需要 _steps_ 才能发挥作用，因为 premature completion 是 step 之间的 failure。它的**要求强度**（要求多少工作）决定 **legwork**：“每个修改过的 model 都已纳入”会强制全面工作，“生成变更列表”则不会。该 axis *不受* step 限制：它也能约束扁平 reference 正文，因此没有 step 的 skill 仍能设置穷尽标准（“每条规则都已应用”）。最强的 criterion 既可检查，又穷尽。

_避免使用_：done condition、exit condition、stopping rule

### Legwork

Agent 在单个 step 内部于幕后完成的工作，包括读取文件、探索 codebase、进行变更，以及自行挖掘所需内容，而不是把工作转交给用户。它位于 step structure 之下：不会单独写成 step，而是隐含在措辞中，由 agent 而不是 skill 控制。它与 **post-completion steps** 跨 step 的拉力相对，是 step 内部的对应概念。**Leading word**（_comprehensive_、_thorough_）或要求工作穷尽的 **completion criterion** 可以增加 legwork；这也包括对扁平 reference 应用要求强度 axis，它会推动完全由扁平 reference 构成的 skill 覆盖所有层级。缺少这种要求，或 **premature completion** 提前截断 step 时，legwork 都会变薄。

_避免使用_：scope、effort、diligence、coverage

### Post-Completion Steps

当前 step 之后的 **steps**。当 agent 能看到它们时，它们会将 agent 向前拉入 **premature completion**；看到的越多，拉力越强。防御方式是将 step sequence 拆成两部分，从而隐藏后续 steps。

_避免使用_：horizon、fog of war、lookahead

### Premature Completion

_Failure mode._ Agent 的 attention 从工作本身滑向完成这件事，因而在当前 step 真正完成前就将其结束。这是 step 之间的 failure，需要存在 **steps** 才会发生；没有 step 的 skill 提前退出，不属于 premature completion，而是在要求未满足时 **legwork** 过薄。它是两种力量之间的拉锯：可见的 **post-completion steps**（向前的拉力）与 **completion criterion** 的清晰度（阻力；明确、可检查的标准能够稳住，含糊标准会让步）。含糊是必要条件：无论可见的后续 step 有多少，明确界限都能抵抗拉力，因此从不匆忙结束的 step 无需防御。两个 lever 可以稳住容易匆忙结束的 step，但必须按顺序使用：**先明确界限**，因为它局部且成本低。只有当 criterion 无法避免地含糊，*并且*确实观察到匆忙结束时，才**隐藏后续 steps**。隐藏只在真正的 context boundary 之间生效（user-invoked handoff 或 subagent dispatch）；inline model-invoked call 会将后续 step 留在 context 中，什么也不会清除。它是 legwork 过薄的一个原因，但两者不同：即使 step 完整运行到结束，legwork 仍可能过薄。

_避免使用_：premature closure、the rush、rushing、shortcutting

## Pruning（删减）

保持 skill 精简；每项 remedy 都与它解决的 failure 配对。

### Single Source of Truth

每项含义都只存在于一个权威位置的理想状态，使 skill 的行为变更只需修改一处。**Duplication** 违反了该状态。

_避免使用_：home、canonical location

### Duplication

_Failure mode._ 相同含义拥有多个 **single source of truth**。它增加维护成本（修改一处后，其他位置也必须修改）和 token 成本，并抬高显著程度：重复一项含义会使它在 hierarchy 上的权重超过真实层级。它是 **leading word** 的意外反面；leading word 通过重复一个 token 而不是含义，有意提高 attention。

_避免使用_：repetition、redundancy

### Relevance

一行内容是否仍与 skill 的行为相关，是判断保留哪些内容的 lens。一行内容失去 relevance，可能是因为它从未与任务相关（仅作说明，或本应披露的 **branch**），也可能是因为它已经陈旧：随着所描述的行为或世界发生变化而过时。较短的 skill 更容易保持 relevant，因为检查每一行的成本更低。它不同于 **no-op**：relevance 询问一行内容是否与任务相关，而不是它是否改变行为。

_避免使用_：load-bearing、staleness、freshness

### Sediment

_Failure mode._ 陈旧内容逐层沉积在 skill 中且从不清除，因为添加内容让人感觉安全，删除内容让人感觉有风险；陈旧且 irrelevant 的行不断累积，必须像取岩芯一样穿过它们，才能找到仍然有效的内容。这是任何缺少 pruning 纪律的 skill 默认会走向的结果；它是 **relevance** 的缓慢侵蚀，与 **duplication** 对含义的重复不同。

_避免使用_：accretion、bloat、cruft、rot

### No-Op

_Failure mode._ 一条不产生任何改变的指令，因为 model 默认已经会这样做；付出 load，只是告诉 agent 它本来就会做的事。测试方式：与默认行为相比，这一行是否改变行为？一行内容可以完全 **relevant**，但仍然是 no-op。使 **leading word** 免费的同一组 prior，也使 no-op 毫无价值。

Leading word 是一种 _technique_；No-Op 是对一行内容的 _verdict_，两者会交叉。弱到无法超越默认行为的 leading word 属于 no-op（agent 本来就大致会做到全面时，仍写 _be thorough_）；修复方法是使用能通过 verdict 的更强词（_relentless_），而不是换一种 technique。因此 No-Op test，也就是“与默认行为相比，它是否改变行为？”，同时也用于判断 leading word 的反复出现是否产生价值。这相对于 model，而不是 reader：两个人对于某一行是否属于 no-op 的分歧，实质是对默认行为的分歧；应通过运行 skill 来解决，而不是争论。

_避免使用_：redundant instruction、restating the obvious、belaboring
