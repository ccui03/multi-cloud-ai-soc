# M0 规划与设计基线（M0 Baseline）

- 版本：1.0-draft
- 日期：2026-11-26
- 状态：待项目负责人评审；本文件是 M0 的统一评审基线，不代表所有提案已获最终批准
- 适用阶段：M0–M7
- 关联跟踪：[M0 Issue #1](https://github.com/ccui03/multi-cloud-ai-soc/issues/1)

## 1. 文档目的与决策优先级

本文件将产品范围、P0 场景、领域对象、分析任务、AI 输出、安全边界和 PoC 验收口径收敛为一份可评审基线。

如历史规划文档中存在冲突，执行时按以下优先级解释：
1. 本文件中标记为 **Accepted** 的决策；
2. 对应 Decision Log 中状态为 Accepted 的决策；
3. 本文件中标记为 **Proposed** 的建议，须经项目负责人确认后生效；
4. 其他历史文档中的通用规划描述。

本文件不代表启动新一轮业务代码开发。M0 的产出是明确、可验证、可追踪的产品与技术基线。

## 2. 产品定位与 MVP 范围

### 2.1 产品定位

首期产品定位为 **AI 驱动的多云 WAF 日志威胁分析工具**。重点验证：从阿里云和腾讯云 WAF 日志中提取安全证据，进行预筛选、行为聚合和 AI 辅助研判，并输出可追溯的判断与建议。

长期方向仍是多厂商 AI SOC，但首期不以建设完整传统 SOC 工作台为目标。

### 2.2 Accepted：首期范围

| 领域 | 首期范围 |
|---|---|
| 数据源 | 阿里云 WAF → SLS；腾讯云 WAF → CLS |
| 数据访问 | 只读 API；源端过滤优先；按时间窗口增量查询和按需回查 |
| 日志类型 | WAF 访问日志、安全检测/防护日志分别建模；具体可用性以 M1 验证为准 |
| 接入 | Python Provider Adapter，统一查询契约、能力声明和错误处理 |
| Schema | Schema Profiler、Field Registry、字段语义证据和版本化映射 |
| 处理 | Normalized Event、确定性检测、去重、Alert Group、Incident Candidate |
| AI | 基于 Evidence Pack 的 LangGraph 研判、证据解释、反证和策略建议 |
| 触发方式 | 手动分析 + 定时自动分析；统一 Analysis Task 和同一分析引擎 |
| UI | 最小日志查询、日志详情、AI 分析面板、结果/证据定位和任务状态 |
| 存储 | PostgreSQL + JSONB；原始日志默认留在 SLS/CLS |
| 部署 | 小规模低成本 PoC；Docker Compose / 单机起步 |

增量查询建议从每数据源约 5–15 分钟的调度粒度进行验证；历史补采按 1 天或 7 天切片评估。它们是验证起点，不是未经测量的生产承诺。实际窗口、重叠时长和频率须依据日志延迟、查询成本、限流和数据量配置。

### 2.3 首期明确不做

- 不复用或替换 QRadar，不建设独立传统 SIEM。
- 不全量复制 SLS/CLS 原始日志，不建设通用日志湖。
- 不自动封禁 IP，不自动修改 WAF 规则或策略，不执行云端写操作。
- 不建设完整 SOAR、工单/案件生命周期和复杂审批工作流。
- 不把复杂 Dashboard、报表中心、可视化定制作为 MVP 阻塞项。
- 不面向公网提供生产级多租户 SaaS，不承诺生产级 HA。
- 不预先部署 Kafka、Redis、OpenSearch、ClickHouse、TheHive、Shuffle、Kubernetes 或图数据库；只有容量/性能证据证明必要时才重新评估。
- 不把 QRadar、其他安全设备或其他云厂商列入首期数据源。

### 2.4 MVP 最小用户流程

1. 用户选择 WAF 数据源、时间范围和可选过滤条件。
2. 系统执行权限、查询范围和预算校验，并显示范围/限制。
3. Provider Adapter 在源端过滤并分页查询；记录查询完整性、截断和错误状态。
4. 系统标准化事件、去重、预筛选并聚合行为。
5. 达到分析条件的 Alert Group / Incident Candidate 生成 Evidence Pack。
6. LangGraph 基于证据执行研判；需要时通过受控只读工具补充有限上下文。
7. 系统保存结论、证据引用、版本、成本和审计记录；用户可追溯到原始日志。
8. 定时任务复用同一流程；无候选时允许只保存扫描结果而跳过 LLM。

## 3. P0 威胁场景

以下 5 个场景是 **Proposed P0 baseline**，建议作为首期最小覆盖集合，待项目负责人确认。场景是否能由某一数据源识别，必须以 M1 真实字段和日志类型验证为前提。

| ID | 场景 | 分析目标 | 最低验收要求 |
|---|---|---|---|
| P0-01 | SQL Injection | 识别 SQL 注入尝试和相关请求行为 | 结论引用请求/规则/检测证据；区分检测命中、最终 WAF 动作和后端影响 |
| P0-02 | XSS | 识别跨站脚本攻击尝试 | 结论引用可验证的请求特征或规则证据；不能仅凭规则名称定性 |
| P0-03 | Command / Path Probing | 识别命令注入、路径遍历、敏感文件和常见路径探测 | 识别具体行为类别；保留原始路径证据并执行敏感信息脱敏 |
| P0-04 | Scanner / Abnormal Access | 识别扫描器、自动化探测和异常高频访问 | 结合时间窗口、路径多样性、请求频率和目标分布；不能仅凭单 IP 直接认定恶意 |
| P0-05 | Business False Positive | 识别可能属于正常业务的 WAF 误报/过度拦截 | 必须寻找正向业务证据；不能因为缺少攻击证据就判定正常；证据不足输出 inconclusive |

P1 候选：Bot/自动化流量细分、跨阶段攻击关联、基线偏差和更复杂的异常检测。若 P0-04 的真实样本足以覆盖 Bot 行为，可将其作为子类型纳入，不因此扩大首期范围。

### 3.1 每个场景必须具备的测试样本

- 恶意/攻击尝试样本。
- 正常业务或授权测试样本。
- WAF 拦截、观察/测试模式、放行或动作未知的样本（以源端实际能力为准）。
- 字段缺失、枚举未知、查询截断或证据冲突样本。
- 对应的人工标签、证据和标注理由。

不得将 WAF 命中直接当作攻击成功；不得将 WAF 拦截直接当作后端未受影响的充分证据。

## 4. 核心领域对象与关系

### 4.1 领域对象定义

| 对象 | 定义 | 生命周期/职责 | 是否作为 AI 直接输入 |
|---|---|---|---|
| Raw Record | SLS/CLS 中的源端原始记录 | 权威原始证据；默认不全量复制 | 否，按需回查 |
| Normalized Event | 一条经过字段映射的标准化 WAF 事件 | 保存稳定核心字段、vendor extensions、来源和映射版本 | 作为证据，不默认逐条全量输入 |
| Detection Signal | 厂商告警、确定性规则或统计检测产生的单个信号 | 记录规则、命中原因、严重性、版本和证据引用 | 进入聚合 |
| Alert Group | 按多维特征和时间窗口归并的一组相关 Signal/Event | 降噪、组织相似行为；保留成员引用和聚合理由 | 是，初步分诊对象 |
| Incident Candidate | 将一个或多个 Alert Group 按关联证据组合出的疑似攻击活动 | 表示待调查候选，不等同于已确认安全事件 | 是，主要调查对象 |
| Evidence Pack | 面向一次研判的版本化证据快照 | 包含范围、统计、时间线、样本、反证、未知项、来源和截断状态 | 是，Agent 的主要事实输入 |
| Analysis Task | 一次手动或定时分析的执行实例 | 管理触发方式、范围、状态、预算、Checkpoint 引用、版本、结果和审计 | 否，是执行容器 |

**Security Incident 的边界：** MVP 中不建设完整案件生命周期。Incident Candidate 是算法/分析阶段对象；经人工确认后，可标记或提升为 Security Incident。不能把 Candidate 自动显示为“已确认攻击事件”。案件负责人、工单流转、处置 SLA 等属于后续范围。

### 4.2 对象处理链

```text
Raw Record
   ↓
Normalized Event
   ↓
Detection Signal
   ↓
Alert Group
   ↓
Incident Candidate
   ↓
Evidence Pack
   ↓
LangGraph Investigation
   ↓
Verdict / Recommendation / Human Review
```

Analysis Task 贯穿并管理上述处理过程。一个任务可以处理多个候选对象；一个候选对象也可以在不同时间由不同任务重新分析，需保存分析版本和证据快照。

### 4.3 关联原则

- 稳定且可信的 Request ID / Session ID 可作为强关联依据，但须验证其唯一性和来源语义。
- Host、时间窗口、规则/攻击类型、路径模板和行为特征可组合关联。
- 单独 IP、User-Agent 或时间邻近只能作为弱关联，不得单独证明同一攻击者或同一事件。
- 保存关联键、时间窗、成员引用、关联理由、强弱等级、规则版本和人工修正记录。
- IP 可能来自 NAT、代理、CDN 或共享出口；关联逻辑必须考虑这些情况。

## 5. Analysis Task：手动与定时统一流程

### 5.1 两种触发方式

| 属性 | Manual | Scheduled |
|---|---|---|
| 触发者 | 用户 | Scheduler |
| 范围来源 | 用户选择数据源、时间范围、过滤条件或对象引用 | 数据源配置、Checkpoint 和调度窗口 |
| 执行流程 | 统一 Query/Analysis Worker | 统一 Query/Analysis Worker |
| 分析引擎 | 相同 | 相同 |
| 结果结构 | 相同 | 相同 |
| 自动响应 | 不允许 | 不允许 |

Scheduler 只负责创建任务，不直接查询日志、不调用 LLM，也不持有云凭据。

### 5.2 状态机

```text
queued → running → completed
                  ↘ completed_with_warnings
                  ↘ failed
                  ↘ cancelled

queued/running → waiting_for_budget → queued/running
```

状态定义：
- `queued`：等待 Worker。
- `running`：执行查询、预筛选、聚合或 AI 调查。
- `waiting_for_budget`：预算不足，等待预算窗口或人工调整。
- `completed`：任务范围内步骤完整成功。
- `completed_with_warnings`：任务完成，但有明确记录的部分失败、截断或数据质量警告。
- `failed`：任务未达到成功条件。
- `cancelled`：用户或管理员取消。

每个任务至少记录：task_id、trigger_type、source_ids、scope/time_range、filter/query_plan、idempotency_key、status、budget、checkpoint_ref、query_count、sample_count、truncation/data_quality、workflow_version、evidence_ref、result_ref、model/prompt version、cost、error summary 和 audit metadata。

### 5.3 Checkpoint 与幂等

- Checkpoint 按数据源隔离；成功水位与调度状态、任务状态分离。
- 只有查询完整性符合成功条件且必要结果持久化后，才推进 last_successful_window_end。
- 失败或部分失败不得静默推进成功水位。
- 通过窗口重叠吸收迟到日志，通过稳定 Fingerprint 和任务幂等键处理重复记录/重复调度。
- 重叠时长、增量间隔和回溯切片须在 M1 根据真实延迟、API 限制和成本测量后定值。
- 暂停、恢复、取消、重试和补跑均需幂等、预算控制和审计。

## 6. AI 研判输出契约

### 6.1 Verdict

采用五级结论：

| 值 | 定义 |
|---|---|
| `confirmed_malicious` | 有充分、可追溯证据支持恶意活动，关键替代解释已排除 |
| `likely_malicious` | 多项证据支持恶意行为，但仍存在关键证据缺口 |
| `likely_legitimate` | 现有证据更支持正常业务/授权测试/误报，但仍有未确认点 |
| `confirmed_legitimate` | 有可信业务或授权上下文确认正常，攻击解释不成立 |
| `inconclusive` | 证据不足、字段语义未知、查询不完整或证据相互矛盾 |

### 6.2 必须区分的维度

1. 是否观察到攻击尝试。
2. WAF 是否检测到攻击特征。
3. WAF 模块动作和最终动作分别是什么。
4. 是否处于观察/测试模式。
5. HTTP 响应状态是什么。
6. 请求是否到达后端（true / false / unknown）。
7. 是否存在业务系统 compromise 证据（confirmed / suspected / not_observed / unknown）。

HTTP 状态不能代替 WAF 动作；缺失 final action 不能默认 allow；未知枚举必须保留 unknown。WAF 命中、拦截或 HTTP 状态均不能单独证明 compromise。

### 6.3 最小结构化结果

```json
{
  "verdict": "likely_malicious",
  "threat_types": ["sql_injection"],
  "severity": "high",
  "confidence": 0.82,
  "facts": [],
  "inferences": [],
  "unknowns": [],
  "supporting_evidence_ids": [],
  "counter_evidence_ids": [],
  "attack_attempt": "observed",
  "waf_detection": "detected",
  "waf_action": "unknown",
  "backend_reached": "unknown",
  "compromise_status": "unknown",
  "recommendations": [],
  "human_review_required": true,
  "analysis_scope": {},
  "data_quality": {},
  "model_version": "",
  "prompt_version": "",
  "workflow_version": ""
}
```

字段枚举需由实现时的 JSON Schema 固化；以上为 M0 语义基线。Confidence 是未校准的模型信心估计，不是统计意义上的恶意概率。Severity、Confidence 和业务影响必须分开。

每条建议必须关联事件/候选、厂商产品、规则/路径范围、证据、预期收益、误放风险、验证方法和回滚考虑；首期仅生成建议，不记录为已执行。

## 7. 安全、权限与审计边界

| 控制项 | M0 要求 |
|---|---|
| 云凭据 | 仅由后端 Adapter/Secret 配置使用；不进入 Prompt、Evidence Pack 或模型上下文 |
| Agent 工具 | Allowlist，只读；无任意 SQL、任意 DSL 或云端写 API |
| 后端授权 | 每次查询和工具调用重新校验用户、数据源、时间范围和对象权限 |
| 查询保护 | 时间范围、结果条数、分页、超时、频率和预算硬限制 |
| 敏感数据 | 按字段分级；Cookie、Authorization、Token、密码、个人敏感字段默认脱敏/排除 |
| 不可信输入 | URL、Header、User-Agent、Cookie、参数、Body、响应片段和日志文本均是不可信数据，不得作为系统指令 |
| Prompt Injection | 证据内容与指令分离；模型不能因日志文本改变角色、权限或工具范围 |
| 审计 | 记录用户/触发器、范围、查询摘要、结果量、工具调用、模型/Prompt/Workflow 版本、成本和结果 |
| 数据保留 | 原始日志由 SLS/CLS 保留；项目库只保存必要标准化数据、引用、证据快照和结果，保留期限待成本/合规评审 |
| 响应 | 不自动封禁、不自动修改 WAF；未来响应需独立审批、TTL、回滚和审计设计 |

所有安全控制必须由后端实施；前端隐藏按钮不构成安全边界。

## 8. PoC 验收方案

### 8.1 测试数据集

建立以 Alert Group / Incident Candidate 为单位的人工标注数据集。初始建议收集数百个代表性行为组，实际数量根据可用日志和标签覆盖决定，不将“数百”设为硬性 M0 门槛。

数据集至少覆盖：
- 五个 P0 场景及正常业务/授权测试；
- 两家 Provider 和可用日志类型；
- WAF 不同动作、观察模式和未知动作；
- 字段缺失、未知枚举、重复/迟到日志；
- 查询失败、分页不完整、截断和证据冲突；
- Prompt Injection 和恶意日志文本。

标注包含来源、时间范围、脱敏版本、标签、支持证据、反证、标注人、复核状态和争议说明。按攻击活动/时间段/目标划分调试集与独立测试集，避免近重复样本泄漏。

### 8.2 指标体系

| 层次 | 指标 |
|---|---|
| 数据接入 | API 成功率、分页完整性、查询延迟、迟到日志分布、失败恢复 |
| Schema/标准化 | 关键字段映射准确率、字段覆盖率、未知字段可追踪率、动作语义准确率 |
| Prefilter | 恶意行为召回率、过滤比例、候选率、每千条日志成本 |
| Aggregation | Precision/Recall、错误合并率、漏合并率、降噪率 |
| Evidence Pack | 证据覆盖率、引用有效率、抽样代表性、截断识别率 |
| AI | 各 Verdict Precision/Recall/F1、误报率、Inconclusive Rate、人工修订率 |
| Grounding | Evidence Grounding Rate、无依据结论比例、引用有效率 |
| End-to-End | 端到端召回、人工调查耗时变化、单次分析时延、每千条日志成本、单次 Token 成本 |
| 安全 | 越权工具调用成功数（目标为 0）、敏感字段泄漏数（目标为 0）、审计覆盖率 |

### 8.3 对照实验

至少对比：
1. 确定性规则/统计基线；
2. 规则 + 聚合 + Evidence Pack；
3. 完整 LangGraph 研判。

Accuracy 不作为唯一指标；类别不平衡时报告 Precision、Recall、F1、PR 曲线和混淆矩阵，并按 Provider、场景和数据质量分层。

### 8.4 目标值与预算原则

- M0 不虚构准确率、召回率、延迟或费用数值目标。
- M1 获取真实日志量、查询返回量、延迟、分页、限流和计费数据后，制定可执行的查询预算。
- 模型确定后，用代表性 Evidence Pack 测量 Token 和单次成本，再制定模型预算。
- 预算至少分为每数据源查询频率/时间跨度/返回量/每日查询预算，以及每任务/每日模型 Token 或费用预算。
- 所有预算必须是后端强制限制，而非仅 UI 提示。
- **在查询和模型预算未配置前，定时自动分析保持关闭；手动查询/分析也必须受临时硬上限约束。**
- 超预算必须明确等待、暂停、失败或降级为 stats-only，并记录原因；不得静默丢弃。

## 9. M0 Exit Criteria

以下全部满足才可关闭 M0：

- [x] 项目负责人确认 MVP 范围和明确不做事项。
- [x] 项目负责人确认 P0 场景及其最低验收要求。
- [x] Normalized Event、Detection Signal、Alert Group、Incident Candidate、Evidence Pack、Analysis Task 的边界明确。
- [x] 手动/定时统一任务流程、状态机、Checkpoint 和幂等原则明确。
- [x] 五级 Verdict、严重性、置信度、证据/反证/未知项结构明确。
- [x] 凭据、只读工具、后端授权、脱敏、Prompt Injection 和审计边界明确。
- [x] 测试集构建方法、分层指标和对照实验明确。
- [x] 查询/模型预算的配置机制和“预算未设定则定时任务关闭”的规则明确。
- [x] 未决事项和复核条件记录到 Decision Log。

**M0 评审结果（2026-11-26）：通过。** 项目负责人已明确确认 MVP 产品范围、五个 P0 场景、Incident Candidate 与 Security Incident 边界、预算门禁；DEC-017、DEC-018、DEC-019 已更新为 Accepted。M0 仅确认规划和设计基线，不代表 M1 的 SLS/CLS 真实数据源验证已通过，也不代表 M0 之外的实现能力已经交付。

## 10. M0 未决事项与后续阶段

| 项目 | 当前状态 | 解决阶段/条件 |
|---|---|---|
| 阿里云 SLS 真实查询权限与 403 | 未通过当前验证 | M1：检查 Region、Project/Logstore、RAM 权限和请求配置 |
| 腾讯云 CLS 真实联调 | 尚未开始/未确认 | M1：单独验证 API、日志主题、字段和成本 |
| 两家 WAF 可用日志类型与字段语义 | 未完整验证 | M1：官方文档 + 脱敏样本 + 查询测试 |
| 5–15 分钟增量调度、1/7 天回溯切片 | 验证起点 | M1：依据延迟、成本和限流确定配置 |
| 具体查询预算上限 | 待实测 | M1 后按真实日志量和计费制定 |
| 模型供应商、模型版本和 Token 单价 | 待选型/测量 | M5 前完成对比与成本测试 |
| 置信度校准和各场景指标阈值 | 待标注数据 | M5/M7：基于独立测试集确定 |
| 数据库保留期限 | 待成本/合规评审 | M2/M7 前确定最小必要保留策略 |

## 11. M0 评审结论记录

项目负责人评审时逐项记录：
- MVP 范围：Accepted / Changes Requested
- P0 场景：Accepted / Changes Requested
- 领域对象：Accepted / Changes Requested
- Analysis Task：Accepted / Changes Requested
- AI Verdict：Accepted / Changes Requested
- Security Boundary：Accepted / Changes Requested
- PoC Evaluation & Budget：Accepted / Changes Requested

所有 Changes Requested 必须写明修改内容、责任项和复核条件；未决的真实数据问题不能伪装为 M0 已验证事实。
