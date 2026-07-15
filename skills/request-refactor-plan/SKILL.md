---
name: request-refactor-plan
description: 通过用户访谈创建由微小 commit 组成的详细 refactor 计划，然后将其提交为 GitHub issue。用户希望规划 refactor、创建 refactoring RFC，或将 refactor 拆分为安全的增量步骤时使用。
---

当用户希望创建 refactor request 时，将调用此 skill。你应执行以下步骤；如果认为某些步骤没有必要，可以跳过。

1. 请用户详细描述希望解决的问题，以及任何可能的解决思路。

2. 探索 repository，验证用户的陈述并理解 codebase 的当前状态。

3. 询问用户是否考虑过其他方案，并向其提供其他选项。

4. 围绕实现方案访谈用户，必须极其细致、全面。

5. 反复推敲并确定实现的确切范围，明确计划修改和不修改的内容。

6. 检查 codebase 中该区域的 test coverage。如果 test coverage 不足，询问用户的测试计划。

7. 将实现拆分为由微小 commit 组成的计划。牢记 Martin Fowler 的建议：“让每个 refactoring 步骤尽可能小，从而始终可以看到程序正常运行。”

8. 使用 refactor 计划创建 GitHub issue。Issue 描述采用以下模板：

<refactor-plan-template>

## 问题陈述

从开发者视角描述其面临的问题。

## 解决方案

从开发者视角描述问题的解决方案。

## Commits

一份很长且详细的实现计划。使用通俗语言编写计划，将实现拆分为尽可能小的 commits。每个 commit 完成后，codebase 都必须保持可运行状态。

## 决策文档

列出已经确定的实现决策，可以包括：

- 将构建或修改的 module
- 将修改的 module interface
- 开发者提供的技术澄清
- 架构决策
- Schema 变更
- API contract
- 具体交互

不要包含具体文件路径或代码片段，它们可能很快过时。

## 测试决策

列出已经确定的测试决策，包括：

- 描述优秀测试的标准（只测试外部行为，不测试实现细节）
- 将测试哪些 modules
- 测试的既有范例（即 codebase 中的同类测试）

## 范围之外

描述本次 refactor 范围之外的事项。

## 补充说明（可选）

关于此次 refactor 的其他说明。

</refactor-plan-template>
