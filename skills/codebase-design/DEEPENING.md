# Deepening

如何根据 dependency，安全地 deepen 一组 shallow module。本文使用 [SKILL.md](SKILL.md) 中的词汇：**module**、**interface**、**seam**、**adapter**。

## Dependency 类别

评估 deepening 候选对象时，对其 dependency 进行分类。类别决定如何跨 seam 测试 deepened module。

### 1. In-process

纯计算、in-memory state、无 I/O。始终可以 deepen：合并这些 module，并直接通过新 interface 进行测试。不需要 adapter。

### 2. Local-substitutable

具有本地测试替代品的 dependency（例如用 PGLite 替代 Postgres、使用 in-memory filesystem）。存在替代品时即可 deepen。测试 deepened module 时，在 test suite 中运行该替代品。Seam 位于内部；module 的 external interface 上不设置 port。

### 3. Remote but owned（Ports & Adapters）

跨 network boundary 的自有 service（microservice、internal API）。在 seam 处定义 **port**（interface）。Deep module 拥有逻辑；transport 作为 **adapter** 注入。测试使用 in-memory adapter，production 使用 HTTP/gRPC/queue adapter。

推荐表述：*“在 seam 处定义 port，为 production 实现 HTTP adapter，为测试实现 in-memory adapter。这样，即使跨网络部署，逻辑仍位于一个 deep module 中。”*

### 4. True external（Mock）

无法控制的第三方 service（Stripe、Twilio 等）。Deepened module 将 external dependency 作为注入的 port 接收；测试提供 mock adapter。

## Seam 纪律

- **一个 adapter 意味着假设性的 seam，两个 adapter 意味着真实的 seam。** 除非至少有两个合理的 adapter（通常为 production + test），否则不要引入 port。只有单个 adapter 的 seam 只是 indirection。
- **Internal seam 与 external seam。** Deep module 既可以有 internal seam（implementation 私有，由自身测试使用），也可以在 interface 处有 external seam。不要仅仅因为测试使用 internal seam，就通过 interface 将其暴露。

## 测试策略：替换，不叠加

- 一旦 deepened module 的 interface 上已有测试，shallow module 的旧 unit test 就成为冗余，应将其删除。
- 在 deepened module 的 interface 上编写新测试。**Interface 是测试表面。**
- 测试通过 interface 断言可观察结果，而不是 internal state。
- 测试应能经受内部 refactor：它们描述行为，而不是 implementation。如果 implementation 变化时测试也必须变化，说明测试越过了 interface。
