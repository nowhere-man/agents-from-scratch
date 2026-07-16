# 研究发现与决策
<!--
  内容：任务的 knowledge base，存储所有发现和决策。
  原因：Context window 有限。此文件是持久且无限的“external memory”。
  时机：任何发现之后更新，特别是执行 2 次 view/browser/search 操作后（两次操作规则）。
-->

## 需求
<!--
  内容：将用户请求拆分为具体需求。
  原因：使需求保持可见，避免忘记要构建的内容。
  时机：在 Phase 1（需求与探索）期间填写。
  示例：
    - Command-line interface
    - 添加任务
    - 列出所有任务
    - 删除任务
    - Python 实现
-->
<!-- 从用户请求中提取 -->
-

## 研究发现
<!--
  内容：Web 搜索、文档阅读或探索得到的关键发现。
  原因：Multimodal 内容（图片、browser result）不会持久保存，应立即写下。
  时机：每执行 2 次 view/browser/search 操作后更新本节（两次操作规则）。
  示例：
    - Python 的 argparse module 支持 subcommand，可用于整洁的 CLI 设计
    - JSON module 可以轻松处理文件持久化
    - 标准 pattern：python script.py <command> [args]
-->
<!-- 探索期间的关键发现 -->
-

## 技术决策
<!--
  内容：已经做出的架构和实现选择，以及理由。
  原因：技术或方案的选择理由可能被遗忘，此表保存这些知识。
  时机：每当做出重大技术选择时更新。
  示例：
    | 使用 JSON 存储 | 简单、human-readable、Python 内置支持 |
    | argparse + subcommand | 整洁的 CLI：python todo.py add "task" |
-->
<!-- 已做决策及理由 -->
| 决策 | 理由 |
|----------|-----------|
|          |           |

## 遇到的问题
<!--
  内容：遇到的问题及其解决方式。
  原因：与 task_plan.md 中的错误类似，但聚焦更广泛的问题，而不仅是代码错误。
  时机：遇到 blocker 或意外挑战时记录。
  示例：
    | 空文件导致 JSONDecodeError | 在 json.load() 前添加显式空文件检查 |
-->
<!-- 错误及其解决方式 -->
| 问题 | 解决方案 |
|-------|------------|
|       |            |

## 资源
<!--
  内容：有用的 URL、文件路径、API reference、文档链接。
  原因：便于以后查阅，不要让重要链接丢失在 context 中。
  时机：发现有用资源时添加。
  示例：
    - Python argparse 文档：https://docs.python.org/3/library/argparse.html
    - 项目结构：src/main.py、src/utils.py
-->
<!-- URL、文件路径、API reference -->
-

## Visual/Browser 发现
<!--
  内容：查看图片、PDF 或 browser result 后获得的信息。
  原因：关键！Visual/multimodal 内容不会持久保存在 context 中，必须记录为文本。
  时机：查看图片或 browser result 后立即记录，不要等待。
  示例：
    - Screenshot 显示登录表单包含 email 和 password 字段
    - Browser 显示 API 返回包含 "status" 和 "data" key 的 JSON
-->
<!-- 关键：每执行 2 次 view/browser 操作后更新 -->
<!-- Multimodal 内容必须立即记录为文本 -->
-

---
<!--
  提醒：两次操作规则
  每执行 2 次 view/browser/search 操作后，必须更新此文件。
  这可以防止 context 重置时丢失 visual 信息。
-->
*每执行 2 次 view/browser/search 操作后更新此文件*
*这可以防止 visual 信息丢失*
