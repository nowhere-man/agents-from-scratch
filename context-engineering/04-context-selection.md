---
title: Context Selection
aliases:
  - 上下文筛选
  - Context Filtering
tags:
  - context-engineering
  - selection
status: active
created: 2026-07-18
last_reviewed: 2026-07-23
sources:
  - "[[context-engineering/99-provider-guidance-and-sources]]"
---

# Context Selection：决定模型这一刻该看什么

> [!abstract] 本篇学习终点
> 面对来自对话、Memory、Retrieval、Tool 和 Workspace 的候选材料，先做不能被相关性抵消的硬过滤，再围绕当前子问题保留充分、权威、互补且可解释的证据，并输出 Selected、Rejected、Uncertain 三类结果。

## 窗口有限以后，选择才真正发生

SSO 任务当前步骤是“比较成功与失败请求的 token audience”。系统发现了这些候选：

1. 用户最新补充：只有 mobile SSO 失败；
2. 运行手册 v4 的 audience 约定；
3. 已被 v4 替代的运行手册 v1；
4. mobile 失败请求日志；
5. web 成功请求日志；
6. 一个没有时间戳的历史 incident 摘要；
7. 当前认证代码与用户已有 diff；
8. 与普通密码登录有关的 2,000 行日志；
9. tool 查询超时产生的错误 envelope；
10. Memory 中“这个项目以前使用 api-v1”的旧经验。

把它们全部放入模型既超预算，也会制造冲突。可是固定取相似度最高的前五条同样危险：五条可能都在重复失败日志，却缺少成功请求和正式规则。

这里的语义相似度，是文本或向量表示在表述上有多接近；它只能说明“像不像”，不能说明权限、版本或证据是否充分。Context Selection 解决的是：==为当前决策定义信息需求，再从所有候选中保留足够支持、反驳或暴露缺口的最小集合。==

## 先区分 Retrieval、Selection 和 Assembly

这三个阶段经常被统称为“找上下文”，但失败原因不同：

- **Retrieval** 从大型外部集合中召回候选，例如从知识库找到运行手册章节；
- **Selection** 综合全部来源做权限过滤、比较、去重和取舍；
- **Assembly** 把已经选中的内容按边界、顺序和预算渲染成最终输入。

Conversation、Memory、Tool 和 Workspace 的材料不一定经过向量检索，却仍然需要 Selection。因此 Selection 不是 Retrieval 的别名。

保持阶段独立有一个直接好处：模型漏掉关键规则时，可以判断是根本没有召回、被 Selection 错误拒绝，还是在 Assembly 中被放错位置。

## 第一步不是评分，而是定义证据需求

当前子问题是比较 audience。完成它至少需要：

- 一个失败请求的实际 audience；
- 一个成功请求或正式配置作为对照；
- 当前有效的 expected audience 规则；
- 每项材料对应的环境、客户端、时间和版本；
- 仍未确认的信息。

这份需求叫 Evidence Requirement。它比“找最相关内容”更具体，因为它说明了完成结论所需的角色。

如果只找到失败日志，没有 expected audience，系统应产出缺口，而不是因为失败日志足够相似就提前得出根因。

## 先做硬过滤：有些条件不能用分数补偿

下面这些候选即使语义高度相关，也不能直接进入选择池：

- 当前用户无权访问的生产数据；
- tenant、project 或 task ID 不匹配的材料；
- 被明确禁止的来源；
- 已撤销、过期或版本不兼容的文档；
- 不允许发送给目标模型的敏感字段；
- tool 调用失败却伪装成普通文本的 payload；
- 已失效的 workspace snapshot；
- checksum、schema 或对象 ID 校验失败的内容。

对候选清单做硬过滤后：

- 运行手册 v1 因 superseded by v4 被拒绝；
- tool 查询超时保留为错误 observation，但不能当成日志证据；
- 无权访问的生产客户字段被移除或脱敏；
- 与旧 branch 对应的代码 snapshot 被拒绝。

权限和版本不是“负分项”。一个越权但很相关的文档，不能靠高相关性重新进入模型。

## 再做软选择：比较材料对当前决策的价值

通过硬过滤后，可以用多个维度比较剩余候选：

- **相关性 $R$**：是否直接回答 audience 子问题；
- **权威性 $A$**：正式手册、真实日志还是模型推断；
- **新鲜度 $F$**：版本和观察时间是否匹配；
- **用途 $U$**：能否支持当前要做的比较或验证；
- **独特信息 $D$**：是否补充了已选材料没有的角色；
- **成本 $C$**：token、读取延迟和处理成本；
- **风险 $K$**：冲突、误导、敏感性或不确定性。

可以用概念评分解释排序：

$$
S = w_rR + w_aA + w_fF + w_uU + w_dD - w_cC - w_kK
$$

计算过程分三步：

1. 针对当前子问题，为每个候选估计各维度；
2. 根据任务风险和 eval 选择权重；
3. 在覆盖 Evidence Requirement 的前提下选取组合，而不是只取单项最高分。

输出 $S$ 只用于比较候选。它不会自动证明材料有权访问，也不会证明证据集合已经充分。高风险场景仍需确定性规则、覆盖检查或人工复核。

## 沿主线完成一次实际选择

这里的 `top-k` 指固定取评分最高的前 $k$ 条；它只能作为起点，不能替代 Evidence Requirement 的覆盖检查。实际选择结果可以保存为：

```yaml
selection:
  task_id: sso-login-fix-42
  question: 比较成功与失败请求的 token audience
  selected:
    - id: user-scope-mobile
      role: scope
      reason: 用户明确限定只有 mobile SSO 失败
      priority: p0
    - id: runbook-sso-v4#audience
      role: expected_rule
      reason: 当前有效的正式 audience 约定
      priority: p0
    - id: log-sso-mobile-20260722
      role: failing_case
      reason: 与失败客户端、时间和部署版本匹配
      priority: p0
    - id: log-sso-web-success-20260722
      role: control_case
      reason: 提供相同部署下的成功对照
      priority: p1
    - id: auth-code-audience-check@snapshot-18
      role: implementation
      reason: 当前代码实际使用的 audience 来源
      priority: p0
  rejected:
    - id: runbook-sso-v1
      reason: superseded_by_runbook_sso_v4
    - id: password-login-logs
      reason: 与当前 SSO audience 子问题无关
  uncertain:
    - id: incident-summary-2025
      reason: 缺少环境、时间和原始 evidence reference
  gaps:
    - identity_service_runtime_config_version
```

这份结果做了四件事：

- 明确每项材料在论证中承担什么角色；
- 记录拒绝原因，便于定位漏选；
- 保留尚不能判断的候选，而不是强行二选一；
- 把未找到的信息作为 gap 输出。

Selection 的完成条件不是“选够 top-k”，而是 Evidence Requirement 得到满足，或剩余缺口被明确记录。

## 为什么必须保留冲突、否定和缺失

如果系统只保留支持“audience 错误”的材料，会产生 confirmation bias（只寻找支持已有猜测、忽略反例的偏差）。

主线中还要保护：

- web 请求使用同一配置却成功这一反例；
- 数据库异常已经排除这一否定结论；
- 运行手册只适用于 mobile client 的限定条件；
- 身份服务运行时配置版本尚未确认这一未知项；
- 两个可信来源在 expected audience 上的冲突。

多个权威来源冲突时，Selection 应保留：

```yaml
conflict:
  field: expected_audience
  claims:
    - value: api-v2
      source: runbook-sso-v4
    - value: api-v1
      source: identity-config-observation
  resolution: pending_runtime_version_check
```

不要在 Selection 阶段悄悄把它们平均、合并或选成单一事实。后续模型和程序需要看到冲突结构，才能决定补充查询或使用哪条优先规则。

## 去重为什么不能只看语义相似

两段日志都说 “invalid audience”，可能是：

- 同一个事件被重复导出；
- 两个不同客户端遇到同类错误；
- 同一请求在不同服务留下的链路记录；
- 新旧部署发生的相同症状。

只有第一种适合直接去重。其余差异可能决定根因。

去重可以按层次进行：

1. 稳定 ID、URL（网页地址）、版本或 content hash 完全相同；
2. 规范化后正文相同；
3. 语义相似，但保留来源、时间和限定条件；
4. 同一事件的多来源记录合并为事件组，而不是删除来源。

目标是减少重复权重，不是抹平证据差异。

## Selection 怎样处理多模态材料

多模态材料指文字之外的图片、音频、视频或扫描文档。如果任务改为排查录屏中的登录失败，多模态只改变候选提取方式，Selection 的核心契约不变。

例如用户问“点击登录后哪一步出现错误”，候选可能包括：

- 视频关键帧；
- OCR（图像文字识别）提取的错误码；
- ASR（语音转文字）中用户的描述；
- network trace 的时间段；
- UI（User Interface，用户界面）事件。

系统应围绕同一问题选择能对齐的时间片，而不是固定抽取更多帧。一个结果需要保留 modality、time range、frame 或 span ID，后续由 [[context-engineering/05-context-assembly|Context Assembly]] 按时间或对象对齐。

多模态全量抽取是成本策略，不是完成条件。

## 怎样评估 Selection

先为一组真实任务标出完成结论必需的 Evidence Requirement，再测量：

- **Precision**：选中材料中真正有用的比例；
- **Coverage / Recall**：必需证据角色被覆盖的比例；
- **Hard-filter accuracy**：权限、版本和敏感性过滤是否正确；
- **Redundancy**：重复材料占比；
- **Conflict preservation**：可信冲突是否被保留；
- **Gap accuracy**：材料不足时是否正确报告缺口；
- **Token utility**：单位 token 带来的任务质量提升；
- **Selection stability**：等价任务是否保留一致的关键证据。

只看最终答案可能掩盖 Selection 失败：模型可能依靠参数知识猜中。需要同时检查选中的 evidence ID 和拒绝原因。

## 用三个问题检查本篇

1. 为什么运行手册 v1 即使与问题高度相关，也不能靠高相似度通过硬过滤？
2. 失败日志已经明确写着 invalid audience，为什么还需要成功对照或正式规则？
3. Rejected 与 Uncertain 有什么区别，它们为什么都值得保留原因？

下一篇不再决定内容，而是把这些 Selected 项目渲染成模型能正确区分规则、状态、证据和动作的输入。见 [[context-engineering/05-context-assembly|Context Assembly]]。
