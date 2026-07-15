---
name: codebase-design
description: 用于设计 deep module 的共享词汇。用户希望设计或改进 module 的 interface、寻找 deepening 机会、决定 seam 的位置、提高代码的可测试性或 AI 可导航性，或其他 skill 需要 deep-module 词汇时使用。
---

# Codebase 设计

设计 **deep module**：将大量行为置于小型 interface 之后，把 interface 放在清晰的 seam 上，并能通过该 interface 进行测试。凡是设计或重构代码，都应使用这套语言和原则。目标是为 caller 提供 leverage，为 maintainer 提供 locality，并让所有人都能进行测试。

## 术语表

必须准确使用以下术语，不要替换为“component”“service”“API”或“boundary”。统一语言正是这套词汇的意义。

**Module**：任何具有 interface 和 implementation 的事物。该定义刻意与规模无关，可以是 function、class、package，也可以是跨 tier 的切片。_避免使用_：unit、component、service。

**Interface**：caller 正确使用 module 必须了解的一切：不仅包括 type signature，还包括 invariant、顺序约束、错误模式、必需配置和性能特征。_避免使用_：API、signature（含义过窄，只指 type 层面的表面）。

**Implementation**：module 内部的内容，即其代码主体。它不同于 **Adapter**：一个事物可以是 implementation 很大的小型 adapter（例如 Postgres repository），也可以是 implementation 很小的大型 adapter（例如 in-memory fake）。讨论重点是 seam 时使用“adapter”，其他情况使用“implementation”。

**Depth**：interface 上的 leverage，即 caller（或测试）每学习一个单位的 interface，可以使用多少行为。大量行为位于小型 interface 之后时，module 是 **deep**；interface 与 implementation 几乎同样复杂时，module 是 **shallow**。

**Seam**（Michael Feathers）：无需在该处编辑代码就能改变行为的位置，也就是 module 的 interface 所在的*位置*。seam 放在哪里是一项独立的设计决策，与其后方放置什么不同。_避免使用_：boundary（该词还承载 DDD 中 bounded context 的含义）。

**Adapter**：在 seam 处满足 interface 的具体事物。它描述的是*角色*（填补哪个位置），而不是实质（内部是什么）。

**Leverage**：caller 从 depth 中获得的收益，即每学习一个单位的 interface 就能获得更多能力。一份 implementation 可以在 N 个 call site 和 M 个测试中产生回报。

**Locality**：maintainer 从 depth 中获得的收益，即变更、bug、知识和验证集中在一处，而不是分散到各个 caller。修复一次，处处生效。

## Deep 与 shallow

**Deep module** = 小型 interface + 大量 implementation：

```
┌─────────────────────┐
│    小型 Interface   │  ← 方法少，参数简单
├─────────────────────┤
│                     │
│  Deep Implementation│  ← 隐藏复杂逻辑
│                     │
└─────────────────────┘
```

**Shallow module** = 大型 interface + 少量 implementation（应避免）：

```
┌─────────────────────────────────┐
│       大型 Interface            │  ← 方法多，参数复杂
├─────────────────────────────────┤
│  薄弱 Implementation            │  ← 仅作传递
└─────────────────────────────────┘
```

设计 interface 时，询问：

- 能否减少方法数量？
- 能否简化参数？
- 能否在内部隐藏更多复杂性？

## 原则

- **Depth 是 interface 的属性，不是 implementation 的属性。** Deep module 内部可以由小型、可 mock、可替换的部分组成，只是这些部分不属于 interface。Module 既可以有 **internal seam**（implementation 私有，由自身测试使用），也可以在 interface 处有 **external seam**。
- **删除测试。** 设想删除该 module。如果复杂性随之消失，它只是 pass-through；如果复杂性重新出现在 N 个 caller 中，它就发挥了应有价值。
- **Interface 是测试表面。** Caller 和测试跨越同一个 seam。如果想越过 interface 测试其内部，module 的形态可能有误。
- **一个 adapter 意味着假设性的 seam，两个 adapter 意味着真实的 seam。** 除非确实有事物会跨 seam 发生变化，否则不要引入 seam。

## 面向可测试性进行设计

良好的 interface 使测试自然发生：

1. **接收 dependency，不要创建 dependency。**

   ```typescript
   // 可测试
   function processOrder(order, paymentGateway) {}

   // 难以测试
   function processOrder(order) {
     const gateway = new StripeGateway();
   }
   ```

2. **返回结果，不要产生 side effect。**

   ```typescript
   // 可测试
   function calculateDiscount(cart): Discount {}

   // 难以测试
   function applyDiscount(cart): void {
     cart.total -= discount;
   }
   ```

3. **较小的 surface area。** 方法越少，需要的测试越少；参数越少，测试准备越简单。

## 关系

- 一个 **Module** 只有一个 **Interface**（它向 caller 和测试提供的表面）。
- **Depth** 是 **Module** 的属性，以其 **Interface** 为衡量基准。
- **Seam** 是 **Module** 的 **Interface** 所在的位置。
- **Adapter** 位于 **Seam** 上，并满足 **Interface**。
- **Depth** 为 caller 产生 **Leverage**，为 maintainer 产生 **Locality**。

## 不采用的表述

- **将 Depth 定义为 implementation 行数与 interface 行数之比**（Ousterhout）：这会鼓励填充 implementation。这里改用 depth-as-leverage。
- **将“Interface”理解为 TypeScript 的 `interface` 关键词或 class 的 public method**：含义过窄。这里的 interface 包含 caller 必须了解的每项事实。
- **“Boundary”**：该词还承载 DDD 中 bounded context 的含义。应使用 **seam** 或 **interface**。

## 进一步深入

- **根据 dependency 对一组 module 进行 deepening**：参见 [DEEPENING.md](DEEPENING.md)，其中介绍 dependency 类别、seam 纪律以及“替换而非叠加”的测试策略。
- **探索替代 interface**：参见 [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md)，其中要求启动并行 sub-agent，以数种截然不同的方式设计 interface，再根据 depth、locality 和 seam 位置进行比较。
