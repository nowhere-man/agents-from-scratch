# HTML 报告格式

架构 review 渲染为操作系统临时目录中的单个独立完整 HTML 文件。Tailwind 和 Mermaid 均通过 CDN 引入。Mermaid 可以可靠处理 graph-shaped diagram；手工 div 和 inline SVG 用于更具编辑设计感的 visual（mass diagram、cross-section）。混合使用两者，不要所有内容都依赖 Mermaid，否则会显得千篇一律。

## Scaffold

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>架构 review — {{repo name}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      /* 为 Tailwind 无法简洁覆盖的内容添加少量自定义样式：
         seam 虚线、手绘感箭头等。 */
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Header

Repository 名称、日期和紧凑的图例：实线框 = module，虚线 = seam，红色箭头 = leakage，深色粗框 = deep module。不要写引言段，直接展示候选对象。

## 候选对象 card

Diagram 承载主要信息。文字应少而直白，自然使用 `/codebase-design` skill 中的术语。

每个候选对象对应一个 `<article>`：

- **标题**：简短，说明 deepening，例如“合并 Order intake pipeline”。
- **Badge 行**：推荐强度（`Strong` = emerald、`Worth exploring` = amber、`Speculative` = slate），以及 dependency 类别 tag（`in-process`、`local-substitutable`、`ports & adapters`、`mock`）。
- **文件**：monospace 列表，使用 `font-mono text-sm`。
- **Before / After diagram**：核心内容，分两列并排放置。参见下方 pattern。
- **问题**：一句话说明痛点。
- **解决方案**：一句话说明变更。
- **收益**：bullet，每条不超过 6 个词。例如“测试只经过一个 interface”“Pricing 逻辑不再泄漏”“删除 4 个 shallow wrapper”。
- **ADR callout**（如适用）：在 amber 色调的 box 中显示一行文字。

不要写解释段落。如果 diagram 需要一个段落才能理解，重新绘制 diagram。

## Diagram pattern

选择适合候选对象的 pattern，并混合使用。不要让所有 diagram 看起来相同，多样性是目标的一部分。

### Mermaid graph（dependency / call flow 的主力）

当重点是“X 调用 Y，Y 调用 Z，看这有多混乱”时，使用 Mermaid `flowchart` 或 `graph`。用 Tailwind 样式的 card 将其包裹，避免显得突兀。使用 `classDef` 将 leakage edge 设为红色，将 deep module 设为深色。Sequence diagram 非常适合表达“before：6 次 round-trip；after：1 次”。

```html
<div class="rounded-lg border border-slate-200 bg-white p-4">
  <pre class="mermaid">
    flowchart LR
      A[OrderHandler] --> B[OrderValidator]
      B --> C[OrderRepo]
      C -.leak.-> D[PricingClient]
      classDef leak stroke:#dc2626,stroke-width:2px;
      class C,D leak
  </pre>
</div>
```

### 手工 box-and-arrow（Mermaid 布局不合适时）

用带 border 和 label 的 `<div>` 表示 module。用 inline SVG `<line>` 或 `<path>` 表示箭头，并在 relative container 上 absolute positioning。需要让“after”diagram 表现为一个粗边框 deep module，且内部结构呈灰色时，使用这种方式；Mermaid 无法正确表现这种视觉权重。

### Cross-section（适合分层 shallowness）

堆叠 horizontal band（`h-12 border-l-4`），展示一次调用经过的各个 layer。Before：6 个不执行实际工作的 thin layer。After：1 个标明合并后职责的 thick band。

### Mass diagram（适合“interface 与 implementation 同样宽”）

每个 module 使用两个 rectangle，一个表示 interface surface area，一个表示 implementation。Before：interface rectangle 几乎与 implementation rectangle 一样高（shallow）。After：interface rectangle 较矮，implementation rectangle 较高（deep）。

### Call graph collapse

Before：将 function call tree 渲染为嵌套 box。After：将同一棵树折叠为一个 box，当前已属于内部的调用以淡化样式显示在其中。

## 样式指南

- 采用简洁的 editorial 风格，而不是 corporate dashboard。使用充足的 whitespace。标题可选择 serif（`font-serif` 与 stone/slate 搭配良好）。
- 谨慎使用颜色：使用一种 accent color（emerald 或 indigo），再用红色表示 leakage，用 amber 表示 warning。
- Diagram 高度保持在约 320px，使 before/after 无需滚动即可舒适地并排显示。
- Diagram 内的 module label 使用 `text-xs uppercase tracking-wider`，应呈现 schematic，而不是 UI 元素。
- 唯一的 script 是 Tailwind CDN 和 Mermaid ESM import。报告其余部分保持 static，不包含 app code；除 Mermaid 自身渲染外，不添加 interactivity。

## 首要推荐章节

使用一个较大的 card，只包含候选对象名称、一句理由，以及指向该候选对象 card 的 anchor link。

## 语气

使用直白、简洁的语言，但架构名词和动词必须直接来自 `/codebase-design` skill。不能以简洁为由偏离术语。

**必须准确使用：** module、interface、implementation、depth、deep、shallow、seam、adapter、leverage、locality。

**绝不替换为：** component、service、unit（代替 module）；API、signature（代替 interface）；boundary（代替 seam）；layer、wrapper（本意为 module 时）。

**符合此风格的表述：**

- “Order intake module 是 shallow 的：interface 几乎与 implementation 相同。”
- “Pricing 跨 seam 发生泄漏。”
- “Deepen：一个 interface，一个测试位置。”
- “两个 adapter 证明该 seam 合理：prod 使用 HTTP，测试使用 in-memory。”

**收益 bullet** 使用 glossary 术语说明收益：*“locality：bug 集中在一个 module”*、*“leverage：一个 interface，N 个 call site”*、*“interface 缩小；implementation 吸收 wrapper”*。不要写*“更易维护”*或*“代码更整洁”*，这些词不在 glossary 中，没有使用价值。

不要含糊其辞，不要铺垫，不要写“值得注意的是……”。一句话可以变成 bullet，就写成 bullet；一个 bullet 可以删除，就删除。某个词不在 `/codebase-design` glossary 中时，先从 glossary 中寻找合适词汇，再考虑创造新词。
