---
title: Agent Workspace 与隔离
aliases:
  - Agent Sandbox
  - Workspace Isolation
tags:
  - agents
  - harness
  - sandbox
  - workspace
  - security
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# Workspace 与隔离：文件、Shell、网络和凭证必须有硬边界

> [!abstract] 本篇学习终点
> 你将能为每个 run/tenant 设计 workspace root、文件与 symlink containment、Shell/进程生命周期、环境变量与网络策略；能区分命令 denylist 与真正 sandbox，并理解 workspace snapshot、provider session 和 State checkpoint 不是同一个对象。

## 为什么研究 Agent 也需要 Workspace

研究 Agent 不一定写代码，但它仍可能：

- 下载网页、PDF、CSV 和图片；
- 解压归档并运行解析器；
- 生成中间表格、缓存和最终报告；
- 启动浏览器、OCR 或数据处理进程；
- 使用登录 session 和临时凭证。

如果这些活动直接发生在应用宿主机的共享目录中，一次恶意归档、路径穿越或错误命令就可能读取其他租户数据、覆盖仓库或泄露密钥。

## Workspace 的身份与生命周期

每个 workspace 应绑定：

```yaml
workspace_id: ws-run-7f2a
tenant_id: acme
task_id: vendor-report-43
root: /sandboxes/acme/ws-run-7f2a
image_version: research-runtime-2026-07-20
network_policy: vendor-readonly-v3
credential_binding: cred-session-91
created_at: 2026-07-23T09:00:00+08:00
expires_at: 2026-07-24T09:00:00+08:00
```

短任务可使用 ephemeral workspace；长任务需要可恢复 snapshot，但仍应设置 TTL（Time To Live，存活期限）、配额和明确 cleanup。Artifact promotion 把需要长期保留的文件复制到受管存储，其余临时数据按策略销毁。

## 文件系统边界

仅拼接字符串判断 `path.startswith(root)` 不安全。正确流程是：

```text
用户/模型给出路径
→ 以固定 root 解析
→ canonicalize / realpath
→ 解析 symlink
→ 检查最终目标仍位于 root
→ 检查 allow/deny/protected policy
→ 执行 I/O
```

还要防止：

- `../` 与绝对路径逃逸；
- symlink 指向 root 外；
- ZIP/TAR archive traversal；
- 解压后生成 symlink 再写入；
- hard link、mount 或 bind mount 暴露宿主资源；
- TOCTTOU（Time Of Check To Time Of Use）：路径在校验后、使用前被替换；
- `.env`、key、credential 和 `.git` 被无意读取/覆盖。

文件写入可使用 `expected_hash` 或版本号做 optimistic concurrency，避免 Agent 基于旧读取覆盖用户的新修改。

## Allow、deny 与 protected pattern

| 策略 | 语义 | 例子 |
|---|---|---|
| allowlist | 只有匹配项可访问 | `reports/*.md`、`data/*.csv` |
| denylist | 匹配项总是拒绝 | `node_modules/**`、缓存目录 |
| protected | 可读但不可写 | `.git/**`、`.env*`、`*.key` |

Pattern 只是第二层；第一层仍是 canonical path containment。目录遍历工具也要过滤返回条目，不能通过 `list` 泄露一个无法直接读取的 secret 路径。

## Shell policy 不是 sandbox

拦截 `rm`、`sudo` 或重定向符可以改善体验，但不是硬安全：

```text
bash -c '...'
python -c '...'
解释器、编译器、下载器或环境变量间接执行
```

都可能绕过简单字符串 denylist。硬边界需要操作系统（OS）、容器或虚拟机（VM）sandbox：独立用户或 namespace、只读 mount、系统调用过滤（如 seccomp）、资源控制（如 cgroup）、网络 policy 和可销毁文件系统。

> [!warning] Working directory confinement 也不是完整隔离
> 进程即使从固定 `cwd` 启动，只要与宿主应用使用同一 OS identity，仍可能读取其他可访问路径。`cwd` 是导航起点，不是权限边界。

## 环境变量与凭证

子进程默认继承宿主环境时，模型生成的命令可能读取 API key、cloud credential 或 trace token。推荐：

1. 默认传入显式最小 `env`，而不是继承全部环境；
2. 仅提供运行所需 `PATH`、locale 和短期 credential；
3. credential 绑定 actor/run/audience/scope/expiry；
4. secret 通过 broker 或文件描述符按需注入，不进入 prompt/trace；
5. 工具结束立即撤销或过期。

变量名 denylist 只能作为补充，因为很难穷举所有 secret，且同 OS identity 仍可能从文件或 metadata service 读取凭证。

## 网络 egress

研究 Agent 最常见的泄露路径不是本地文件删除，而是把资料发往外部域名。网络 policy 应约束：

- 允许的域名/IP/端口和协议；
- DNS rebinding、redirect 与私有地址解析；
- SSRF（服务端请求伪造）到 metadata、localhost 和内部控制面；
- 上传请求与下载请求是否使用不同 policy；
- 每个域名的 rate/concurrency/size；
- proxy 层的审计、内容扫描和 credential 注入。

只在 prompt 中写“不要访问其他网站”没有强制力。

## 后台进程与 cleanup

Shell/浏览器工具要把每个进程绑定 run，并记录 PID/process group。Run 完成、失败或取消时：

```text
停止创建新进程
→ SIGTERM / graceful close
→ 等待有界 grace period
→ 必要时终止整个 process group
→ 收集最终 stdout/stderr/status
→ 删除临时 socket/file
→ 把未确认外部效果标为 unknown
```

后台 server、watcher 和 browser 不能因 Agent 忘记调用 stop 就永久泄漏。

## 资源限制

每个 workspace 至少设置：

- CPU、memory、process count；
- wall-clock 与单命令 timeout；
- disk/inode/artifact 大小；
- stdout/stderr 返回上限；
- 网络带宽、请求数和并发；
- 子 Agent、模型和工具预算。

对命令输出保留尾部通常比只保留头部更有用，因为错误栈和 exit code 常在末尾；但必须标明已截断并保存完整 Artifact。

## 三种容易混淆的 snapshot

| Snapshot | 包含什么 | 不包含什么 |
|---|---|---|
| State checkpoint | 任务进度、事件位置、approval、预算 | 实际文件系统内容 |
| Workspace snapshot | 文件、部分进程/环境元数据 | provider 侧会话与完整业务 State |
| Provider/session state | 模型服务保存的 thread/message/cache | 本地文件、工具副作用和平台授权 |

恢复时要分别恢复并验证它们的 identity。拥有 workspace snapshot 不代表 provider session 可继续；拥有 provider thread 也不代表文件版本仍一致。

## 多租户隔离检查

- [ ] 每个 workspace 绑定 tenant/task/run，默认不共享。
- [ ] 路径先 canonicalize，再做 root 和 policy 检查。
- [ ] archive、symlink、mount 与 credential path 有专门测试。
- [ ] Shell denylist 被明确标注为 UX filter，而非安全边界。
- [ ] 子进程使用最小 env 与短期 credential。
- [ ] 网络默认拒绝，按域名/动作开放。
- [ ] 资源配额、process-group cleanup 和 TTL 已实现。
- [ ] promotion、snapshot、restore 和 destruction 都进入审计。

下一篇说明怎样看见这些边界是否真的工作：[[harness/09-observability-and-evaluation|可观测性、评测与故障注入]]。
