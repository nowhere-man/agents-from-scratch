# 示例：使用文件进行规划

以下示例中的 `<plan-dir>` 均指项目根目录下的 `.planning/YYYY-MM-DD-<topic>/`。

## 示例 1：研究任务

**用户请求：**“研究代码库中的 authentication token refresh 实现并编写技术摘要”

### Loop 1：创建计划
```bash
Write <plan-dir>/task_plan.md
```

```markdown
# 任务计划：Authentication Token Refresh 实现研究

## 目标
梳理代码库中的 token refresh 流程、关键模块和 failure handling，并创建技术摘要。

## 阶段
### Phase 1：创建本计划
- **Status:** in_progress
### Phase 2：定位实现与调用链
- **Status:** pending
### Phase 3：综合代码研究发现
- **Status:** pending
### Phase 4：交付技术摘要
- **Status:** pending

## 关键问题
1. 哪些 module 负责签发、刷新和存储 token？
2. Token refresh 的调用链和状态转换是什么？
3. 失败、重试和并发 refresh 如何处理？

## 状态
**当前处于 Phase 1**：正在创建计划
```

### Loop 2：研究
```bash
Read <plan-dir>/task_plan.md           # 刷新目标
Bash 'rg -n "refreshToken|refresh_token|token refresh" .'
Read <匹配到的实现文件>
Write <plan-dir>/findings.md           # 保存实现位置、调用链和 failure handling
Edit <plan-dir>/task_plan.md           # 将 Phase 2 标记为完成
```

### Loop 3：综合
```bash
Read <plan-dir>/task_plan.md           # 刷新目标
Read <plan-dir>/findings.md            # 获取代码研究发现
Write token_refresh_implementation_summary.md
Edit <plan-dir>/task_plan.md           # 将 Phase 3 标记为完成
```

### Loop 4：交付
```bash
Read <plan-dir>/task_plan.md           # 验证完成状态
Deliver token_refresh_implementation_summary.md
```

---

## 示例 2：Bug 修复任务

**用户请求：**“修复 authentication module 中的登录 bug”

### task_plan.md
```markdown
# 任务计划：修复登录 Bug

## 目标
确定并修复阻止成功登录的 bug。

## 阶段
### Phase 1：理解 bug report
- **Status:** complete
### Phase 2：定位相关代码
- **Status:** complete
### Phase 3：确定 root cause（当前）
- **Status:** in_progress
### Phase 4：实现修复
- **Status:** pending
### Phase 5：测试并验证
- **Status:** pending

## 关键问题
1. 出现了什么 error message？
2. 哪个文件处理 authentication？
3. 最近发生了什么变更？

## 已做决策
- Auth handler 位于 src/auth/login.ts
- 错误发生在 validateToken() function 中

## 遇到的错误
- [Initial] TypeError: Cannot read property 'token' of undefined
  → Root cause：未正确 await user object

## 状态
**当前处于 Phase 3**：已找到 root cause，正在准备修复
```

---

## 示例 3：功能开发

**用户请求：**“在设置页面添加 dark mode toggle”

### 三文件模式实践

**task_plan.md:**
```markdown
# 任务计划：Dark Mode Toggle

## 目标
在设置中添加可用的 dark mode toggle。

## 阶段
### Phase 1：研究现有 theme system
- **Status:** complete
### Phase 2：设计实现方案
- **Status:** complete
### Phase 3：实现 toggle component（当前）
- **Status:** in_progress
### Phase 4：添加 theme switching 逻辑
- **Status:** pending
### Phase 5：测试并完善
- **Status:** pending

## 已做决策
- Theme 使用 CSS custom property
- 将偏好存储在 localStorage 中
- Toggle component 位于 SettingsPage.tsx

## 状态
**当前处于 Phase 3**：正在构建 toggle component
```

**findings.md:**
```markdown
# 研究发现：Dark Mode 实现

## 现有 Theme System
- 位置：src/styles/theme.ts
- 使用：CSS custom property
- 当前 theme：只有 light

## 要修改的文件
1. src/styles/theme.ts：添加 dark theme 颜色
2. src/components/SettingsPage.tsx：添加 toggle
3. src/hooks/useTheme.ts：创建新 hook
4. src/App.tsx：用 ThemeProvider 包裹

## 颜色决策
- Dark background：#1a1a2e
- Dark surface：#16213e
- Dark text：#eaeaea
```

**dark_mode_implementation.md：**（deliverable）
```markdown
# Dark Mode 实现

## 已做变更

### 1. 添加 dark theme 颜色
文件：src/styles/theme.ts
...

### 2. 创建 useTheme hook
文件：src/hooks/useTheme.ts
...
```

---

## 示例 4：错误恢复模式

操作失败时，不要隐藏：

### Before（错误）
```
操作：读取 config.json
错误：找不到文件
操作：读取 config.json  # 静默重试
操作：读取 config.json  # 再次重试
```

### After（正确）
```
操作：读取 config.json
错误：找不到文件

# 更新 <plan-dir>/task_plan.md：
## 遇到的错误
- 找不到 config.json → 将创建默认 config

操作：写入 config.json（默认 config）
操作：读取 config.json
成功！
```

---

## 决策前读取模式

**进行重大决策前，始终读取计划：**

```
[已经执行许多 tool call……]
[Context 正在变长……]
[原始目标可能已被遗忘……]

→ 读取 <plan-dir>/task_plan.md          # 将目标重新带回 attention！
→ 现在进行决策               # 目标在 context 中是最新的
```

这就是 Manus 可以处理约 50 次 tool call 而不偏离目标的原因。计划文件充当“目标刷新”机制。
