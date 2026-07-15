---
name: find-skills
description: 当用户询问“如何做 X”“查找用于 X 的 skill”“是否有 skill 可以……”，或表示希望扩展能力时，帮助用户发现并安装 agent skills。用户寻找可能以可安装 skill 形式存在的功能时使用。
---

# 查找 Skills

此 skill 帮助你从开放的 agent skills 生态系统中发现并安装 skills。

## 何时使用此 Skill

在用户有以下需求时使用此 skill：

- 询问“如何做 X”，且 X 可能是已有 skill 覆盖的常见任务
- 说“查找用于 X 的 skill”或“是否有用于 X 的 skill”
- 询问“你能做 X 吗”，且 X 是一种专业能力
- 表示希望扩展 agent 能力
- 希望搜索工具、模板或 workflow
- 提到希望在特定领域获得帮助（设计、测试、部署等）

## 什么是 Skills CLI？

Skills CLI（`npx skills`）是开放 agent skills 生态系统的 package manager。Skills 是模块化 package，通过专业知识、workflow 和工具扩展 agent 能力。

**主要命令：**

- `npx skills find [query] [--owner <owner>]`：以交互方式或按关键词搜索 skills，可选择限定 GitHub owner
- `npx skills add <package>`：从 GitHub 或其他来源安装 skill
- `npx skills check`：检查 skill 更新
- `npx skills update`：更新所有已安装的 skills

**浏览 skills：** https://skills.sh/

## 如何帮助用户查找 Skills

### 第 1 步：理解用户需求

用户寻求帮助时，确定：

1. 所属领域（例如 React、测试、设计、部署）
2. 具体任务（例如编写测试、创建动画、review PR）
3. 该任务是否足够常见，可能已有相应 skill

### 第 2 步：先检查排行榜

运行 CLI 搜索前，检查 [skills.sh 排行榜](https://skills.sh/)，确认该领域是否已有知名 skill。排行榜按总安装量对 skills 排名，优先展示最受欢迎且经过实践检验的选项。

例如，Web 开发领域的热门 skills 包括：
- `vercel-labs/agent-skills`：React、Next.js、Web 设计（每项安装量超过 100K）
- `anthropics/skills`：Frontend 设计、文档处理（安装量超过 100K）

### 第 3 步：搜索 Skills

如果排行榜未覆盖用户的需求，运行 find 命令：

```bash
npx skills find [query] [--owner <owner>]
```

例如：

- 用户询问“如何让我的 React 应用更快？”→ `npx skills find react performance`
- 用户询问“你能帮助我 review PR 吗？”→ `npx skills find pr review`
- 用户说“我需要创建 changelog”→ `npx skills find changelog`

### 第 4 步：推荐前验证质量

**不要仅根据搜索结果推荐 skill。** 始终验证：

1. **安装量**：优先选择安装量超过 1K 的 skills。对安装量低于 100 的 skill 保持谨慎。
2. **来源信誉**：官方来源（`vercel-labs`、`anthropics`、`microsoft`）比未知作者更可信。
3. **GitHub stars**：检查源 repository。对来自 stars 少于 100 的 repository 的 skill 持怀疑态度。

### 第 5 步：向用户展示选项

找到相关 skills 后，向用户提供：

1. Skill 名称及其功能
2. 安装量和来源
3. 可运行的安装命令
4. skills.sh 的详情链接

回复示例：

```
我找到了一个可能有帮助的 skill！“react-best-practices” skill 提供来自
Vercel Engineering 的 React 和 Next.js 性能优化指南。（安装量 185K）

安装命令：
npx skills add vercel-labs/agent-skills@react-best-practices

了解详情：https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### 第 6 步：提出代为安装

如果用户希望继续，可以为其安装 skill：

```bash
npx skills add <owner/repo@skill> -g -y
```

`-g` flag 表示全局安装（用户级），`-y` 表示跳过确认 prompt。

## 常见 Skill 类别

搜索时考虑以下常见类别：

| 类别            | 查询示例                                 |
| --------------- | ---------------------------------------- |
| Web 开发        | react, nextjs, typescript, css, tailwind |
| 测试            | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| 文档            | docs, readme, changelog, api-docs        |
| 代码质量        | review, lint, refactor, best-practices   |
| 设计            | ui, ux, design-system, accessibility     |
| 生产力          | workflow, automation, git                |

## 有效搜索的技巧

1. **使用具体关键词**：“react testing”比单独使用“testing”更好
2. **尝试替代词**：如果“deploy”无效，尝试“deployment”或“ci-cd”
3. **检查热门来源**：许多 skills 来自 `vercel-labs/agent-skills` 或 `ComposioHQ/awesome-claude-skills`

## 未找到 Skill 时

如果没有相关 skill：

1. 明确说明未找到现有 skill
2. 提出使用自身的通用能力直接帮助完成任务
3. 建议用户使用 `npx skills init` 创建自己的 skill

示例：

```
我搜索了与“xyz”相关的 skills，但没有找到匹配项。
我仍然可以直接帮助你完成这项任务。需要我继续吗？

如果你经常执行这类任务，可以创建自己的 skill：
npx skills init my-xyz-skill
```
