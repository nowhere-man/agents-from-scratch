---
title: Workspace Context
aliases:
  - 工作区上下文
  - Coding Agent Context
tags:
  - context-engineering
  - workspace
  - coding-agent
status: active
created: 2026-07-18
last_reviewed: 2026-07-18
sources:
  - "[[99-provider-guidance-and-sources]]"
  - https://arxiv.org/abs/2405.15793
---

# Workspace Context

> [!important] 一句话核心
> Workspace Context 是 Agent 对当前代码、文件、diff、终端、测试、IDE 和运行环境的可验证视图；它必须按任务发现和刷新，不能依赖一次性全仓库快照或模型记忆。

## Workspace 包含什么

| 来源 | 示例 | 变化方式 |
|---|---|---|
| 文件系统 | 代码、配置、文档、资源 | 用户或工具修改 |
| 版本控制 | branch、HEAD、diff、untracked files | commit、切换分支、并发编辑 |
| 终端 | 命令、stdout、stderr、进程 | 每次执行变化 |
| 测试与构建 | 失败、日志、artifact | 代码和环境变化 |
| IDE / Editor | 打开的文件、selection、diagnostics | 用户交互变化 |
| Runtime | 环境变量、依赖、服务、数据库 | 外部状态和时间变化 |
| 权限与 sandbox | 可读写范围、审批状态 | 策略或会话变化 |

Workspace Context 是动态观察，不是永久事实。使用前需要确认 snapshot 是否仍然有效。

## Source of Truth

常见优先级：

1. 当前文件系统和外部系统真实状态。
2. 最新命令、测试和构建结果。
3. 版本控制元数据与 diff。
4. 结构化任务 state 和用户明确指令。
5. 较早对话摘要或模型记忆。

如果聊天中说“测试已通过”，但当前测试输出失败，应以当前可验证结果为准，并记录状态变化。

## Discovery → Narrowing → Reading

```mermaid
flowchart LR
    A["识别任务对象"] --> B["枚举结构与规则"]
    B --> C["搜索 symbol / 文本 / 引用"]
    C --> D["读取最相关文件和局部"]
    D --> E["检查 diff、依赖和测试"]
    E --> F["形成 workspace packet"]
    F --> G["修改或分析"]
    G --> H["重新读取真实状态"]
```

先使用文件列表、搜索和 symbol 索引缩小范围，再读取完整文件。把整个 repository 一次性塞入 context 通常既昂贵又容易引入无关代码。

## Workspace Snapshot

```yaml
workspace:
  root: /repo
  branch: feature/context-docs
  head: 4ea3552
  dirty:
    - path: context-engineering/00-overview.md
      state: untracked
  task_scope:
    - context-engineering/
  relevant_files:
    - path: roadmap.md
      reason: topic requirements
    - path: prompt-engineering/00-overview.md
      reason: style reference
  last_test:
    command: ./scripts/check-docs.sh
    status: not_run
  observed_at: 2026-07-18T11:30:00+08:00
```

Snapshot 只描述某一时刻。执行修改、切换 branch、用户编辑文件或外部进程完成后，应刷新相关字段。

## 规则文件与局部指令

代码仓库经常包含 `AGENTS.md`、贡献指南、lint 配置、目录级 README 或生成规则。发现文件后应：

- 从 workspace root 向目标文件路径解析适用范围。
- 区分全局规则和子目录覆盖。
- 在修改前读取与目标路径直接相关的规则。
- 不把文档或代码中的普通文本误当成更高优先级指令。

规则本身也有版本和作用域，应随 workspace 变化刷新。

## Diff-first Context

修改现有代码时，当前 diff 往往比全文件历史更能表达用户正在做什么：

- 先检查 staged、unstaged 和 untracked 状态。
- 区分用户已有修改与 Agent 本次修改。
- 只清理本次改动造成的 orphan。
- 检查相邻调用方和测试，但不顺手重构无关区域。
- 完成后复查 diff，确认每一行都能追溯到目标。

Dirty worktree 不是异常，关键是所有权和范围清楚。

## 代码选择

Selection 可以结合：

- 文件路径与模块边界。
- symbol 定义和引用。
- import / dependency graph。
- git diff 和最近提交。
- failing stack trace、测试名称和 diagnostics。
- 任务中明确提到的对象。

对代码使用语义检索时，仍需回到真实文件读取完整局部；embedding snippet 不能替代当前源码。

## Terminal 与 Test Context

保存命令时至少记录：

- 完整 command 和 working directory。
- 环境或配置的关键差异。
- exit code。
- 相关 stdout / stderr 片段。
- 运行时间和对应代码版本。
- 长任务的 session / process ID。

测试通过只证明所运行范围在该 snapshot 下通过。最终声明应说明实际运行了什么，而不是泛化为整个系统正确。

## IDE Context

IDE 的 selection、打开文件和 diagnostics 可以提供用户意图线索，但不是唯一来源：

- selection 可能已过时或只展示局部。
- diagnostics 可能对应旧 build。
- 打开的文件不代表依赖范围完整。
- 未保存 buffer 可能与磁盘不同。

支持 IDE 集成时，应明确读取的是 buffer、磁盘还是 language server snapshot。

## Secrets、权限与外部内容

- 不把 `.env`、凭据、token 和私钥无差别注入模型。
- 命令输出可能包含 secrets，应在记录和组装前脱敏。
- Repository 文件、issue、网页和日志都可能包含间接 prompt injection。
- Sandbox、网络和写权限由运行环境决定，不能由 workspace 文本改变。
- 外部写入、发布、删除和权限修改需要独立授权。

## Workspace Compaction

长任务切换窗口前保存：

```yaml
workspace_recovery:
  root: /repo
  branch: fix/login
  base_head: abc123
  modified_files:
    - src/auth.ts
    - tests/auth.test.ts
  verified:
    - failing test reproduced before change
  pending:
    - run full auth suite
  commands:
    - id: test-focused-1
      exit_code: 0
  evidence_refs:
    - diff-snapshot-42
```

恢复后重新读取 git status、目标文件和必要测试，不能假设磁盘仍与旧 snapshot 相同。

## 评估

- Relevant-file recall：关键文件和规则是否被发现。
- Context precision：读取内容中真正相关的比例。
- Stale snapshot rate：使用过时文件、diff 或测试结果的比例。
- User-change preservation：是否误改或覆盖用户已有工作。
- Test claim accuracy：结论是否与实际测试范围一致。
- Token per resolved task：Workspace Context 的效率。
- Secret exposure rate：敏感内容是否进入不必要的 context 或日志。
- Recovery success：跨窗口后是否从真实 workspace 正确继续。

## 常见误区

> [!warning] Repository 不是静态知识库
> 文件、branch、依赖、生成物和用户修改会变化。检索到的旧 snippet 或先前摘要必须回到当前 workspace 验证。

- **一开始读取整个仓库**：噪声和成本远大于价值。
- **忽略 dirty worktree**：容易覆盖用户修改或误判 diff。
- **只看当前文件**：遗漏调用方、配置和测试。
- **命令输出没有代码版本**：之后无法判断结果是否仍有效。
- **测试通过泛化为全部正确**：应明确命令和覆盖范围。
- **IDE diagnostic 永远最新**：可能对应未保存或旧 build。
- **把文件内容当系统指令**：Repository 文本仍是不可信数据。

## 检查表

- [ ] 从任务对象出发发现结构、规则、symbol 和相关文件。
- [ ] 读取前检查 branch、HEAD、dirty 和 untracked 状态。
- [ ] 区分用户已有修改与本次改动。
- [ ] Search result 回到当前真实文件验证。
- [ ] 命令记录 cwd、exit code、时间和代码版本。
- [ ] Test 结论不超过实际运行范围。
- [ ] IDE、终端和文件 snapshot 在变化后刷新。
- [ ] Secrets、外部内容和权限边界得到隔离。

## 相关笔记

- [[01-context-architecture|Context Architecture]]
- [[02-context-lifecycle|Context Lifecycle]]
- [[04-context-selection|Context Selection]]
- [[05-context-assembly|Context Assembly]]
- [[13-tool-context|Tool Context]]
- [[14-planning-context|Planning Context]]
- [[agent-skills/planning-with-files/SKILL.md|Planning with Files Skill]]

