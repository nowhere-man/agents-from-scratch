---
name: planning-with-files
description: "面向 AI coding agent 的 Manus 风格持久化文件规划：将 task_plan.md、findings.md 和 progress.md 保存在本地。用户要求规划、拆解或组织多步骤项目、研究任务，或任何需要至少 5 次 tool call 的工作时使用。"
---

# 使用文件进行规划

像 Manus 一样工作：使用持久化 Markdown 文件作为“磁盘上的工作记忆”。

## 路径约定

- `<SKILL_DIR>` 表示当前 `SKILL.md` 所在目录的绝对路径。Codex 会提供 skill 文件位置；它是文档占位符，不是预设 environment variable，执行命令时必须替换为实际路径。
- 所有 shell command 都从项目根目录运行，使 `.planning/` 始终创建在项目根目录。
- 本文中的 `scripts/`、`templates/` 和 `examples.md` 均相对于 `<SKILL_DIR>`。

## 首先：恢复任务状态

开始复杂任务前，从项目根目录运行 `sh "<SKILL_DIR>/scripts/resolve-plan-dir.sh"`。如果返回计划目录，立即读取其中的 `task_plan.md`、`progress.md` 和 `findings.md`；如果没有返回结果，按“快速开始”创建计划。

> 此流程只恢复磁盘上的任务状态，不恢复之前的 conversation context。执行 `/clear` 或开始新任务后，需要再次触发或显式选择此 skill。

## 重要：文件的存放位置

- **Skill 资源**位于 `<SKILL_DIR>`
- **模板**位于 `<SKILL_DIR>/templates/`
- **你的规划文件**固定放在项目根目录的 `.planning/YYYY-MM-DD-<topic>/` 中

| 位置 | 存放内容 |
|----------|-----------------|
| `<SKILL_DIR>` | 模板、script、示例 |
| `.planning/YYYY-MM-DD-<topic>/` | `task_plan.md`、`findings.md`、`progress.md` |

## 快速开始

执行任何复杂任务之前：

1. **运行 `sh "<SKILL_DIR>/scripts/init-session.sh" "<topic>"`**：创建 `.planning/YYYY-MM-DD-<topic>/`
2. **决策前重新读取计划**：在 attention window 中刷新目标
3. **每个阶段结束后更新**：标记完成状态并记录错误

> **注意：** 不要在项目根目录或 skill 安装目录直接创建规划文件。

## 核心模式

```
Context Window = RAM（易失、有限）
Filesystem = Disk（持久、无限）

→ 所有重要内容都写入磁盘。
```

## 文件用途

| 文件 | 用途 | 更新时机 |
|------|---------|----------------|
| `task_plan.md` | 阶段、进度、决策 | 每个阶段结束后 |
| `findings.md` | 研究、发现 | 任何发现之后 |
| `progress.md` | Session log、测试结果 | 整个 session 期间 |

## 关键规则

### 1. 先创建计划
绝不在没有 `task_plan.md` 的情况下开始复杂任务。此规则不可妥协。

### 2. 两次操作规则
> “每执行 2 次 view/browser/search 操作后，立即将关键发现保存到文本文件。”

这可以防止 visual/multimodal 信息丢失。

### 3. 决策前读取
进行重大决策前读取计划文件，使目标保持在 attention window 中。

### 4. 行动后更新
完成任何阶段后：
- 将阶段状态从 `in_progress` 标记为 `complete`
- 记录遇到的所有错误
- 记录创建或修改的文件

### 5. 记录所有错误
每个错误都要写入计划文件。这会积累知识并防止重复。

```markdown
## 遇到的错误
| 错误 | 尝试 | 解决方案 |
|-------|---------|------------|
| FileNotFoundError | 1 | Created default config |
| API timeout | 2 | Added retry logic |
```

### 6. 绝不重复失败操作
```
if action_failed:
    next_action != same_action
```
记录已经尝试的操作，改变处理方式。

### 7. 完成后继续
所有阶段完成后，如果用户要求执行其他工作：
- 向 `task_plan.md` 添加新阶段（例如 Phase 6、Phase 7）
- 在 `progress.md` 中记录新的 session 条目
- 照常继续规划 workflow

### 8. 使用简体中文记录
向 `task_plan.md`、`findings.md`、`progress.md` 及其他规划文档写入说明、发现、决策、进度和错误时，使用简体中文。Code、command、路径、API 名称以及翻译后会损失语义或精度的专业术语保留原文。

## 三次错误处理协议

```
尝试 1：诊断并修复
  → 仔细阅读错误
  → 确定 root cause
  → 应用针对性修复

尝试 2：替代方案
  → 错误相同？尝试不同方法
  → 换一个工具？换一个 library？
  → 绝不重复完全相同的失败操作

尝试 3：扩大范围重新思考
  → 质疑 assumption
  → 搜索解决方案
  → 考虑更新计划

失败 3 次后：向用户升级
  → 说明已经尝试的操作
  → 提供具体错误
  → 请求指导
```

## 读写决策矩阵

| 情况 | 操作 | 原因 |
|-----------|--------|--------|
| 刚写入文件 | 不要读取 | 内容仍在 context 中 |
| 查看了图片/PDF | 立即写入 findings | Multimodal 信息丢失前转为文本 |
| Browser 返回数据 | 写入文件 | Screenshot 不会持久保存 |
| 开始新阶段 | 读取 plan/findings | Context 陈旧时重新定位 |
| 发生错误 | 读取相关文件 | 修复需要当前状态 |
| 间隔后恢复 | 读取所有规划文件 | 恢复状态 |

## 何时使用此模式

**适用于：**
- 多步骤任务（至少 3 步）
- 研究任务
- 构建或创建项目
- 跨越大量 tool call 的任务
- 任何需要组织的工作

**不适用于：**
- 简单问题
- 单文件编辑
- 快速查询

## 模板

复制以下模板开始工作：

- [templates/task_plan.md](task_plan.md)：阶段跟踪
- [templates/findings.md](findings.md)：研究存储
- [templates/progress.md](progress.md)：Session 记录

## Scripts

用于自动化的辅助 script。以下路径均相对于 `<SKILL_DIR>`，执行时使用实际绝对路径：

- `scripts/init-session.sh`：在 `.planning/YYYY-MM-DD-<topic>/` 下初始化三个规划文件，并将其设为 active plan。
- `scripts/set-active-plan.sh`：切换 active plan pointer（`.planning/.active_plan`）。传入 plan ID 以切换；不传参数则显示当前计划。
- `scripts/resolve-plan-dir.sh`：解析 active plan 目录。依次检查 `$PLAN_ID` 环境变量、`.planning/.active_plan`、按 mtime 排序的最新有效计划目录。
- `scripts/check-complete.sh`：验证 active plan 的所有阶段均已完成。

### 并行任务 workflow

在同一 repository 中同时处理多个任务时：

```bash
# 将此值替换为当前 SKILL.md 所在目录的实际绝对路径
SKILL_DIR="/absolute/path/to/planning-with-files"

# 启动任务 A
sh "$SKILL_DIR/scripts/init-session.sh" "Backend Refactor"
# → .planning/2026-01-10-backend-refactor/task_plan.md

# 在第二个 terminal 中启动任务 B
sh "$SKILL_DIR/scripts/init-session.sh" "Incident Investigation"
# → .planning/2026-01-10-incident-investigation/task_plan.md

# 切换 active plan
sh "$SKILL_DIR/scripts/set-active-plan.sh" 2026-01-10-backend-refactor

# 或将 terminal 固定到指定计划
export PLAN_ID=2026-01-10-backend-refactor
```

每个 session 都从自身隔离的计划目录读取。

## 高级主题

- **真实示例：** 参见 [examples.md](examples.md)

## Anti-pattern

| 不要 | 应改为 |
|-------|------------|
| 使用 TodoWrite 持久保存 | 运行 `sh "<SKILL_DIR>/scripts/init-session.sh" "<topic>"` 创建三个规划文件 |
| 只陈述一次目标，然后遗忘 | 决策前重新读取计划 |
| 隐藏错误并静默重试 | 将错误记录到计划文件 |
| 将所有内容塞入 context | 将大量内容存入文件 |
| 立即开始执行 | 先创建计划文件 |
| 重复失败操作 | 跟踪尝试并改变处理方式 |
| 在 skill 目录中创建文件 | 在项目中创建文件 |
| 将 Web 内容写入 `task_plan.md` | 只将 external content 写入 `findings.md` |
