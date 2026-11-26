# 项目执行计划（Project Execution Plan）

- 版本：1.1
- 日期：2026-11-26
- 仓库：`ccui03/multi-cloud-ai-soc`
- 状态：执行规划基线；阶段主跟踪 Issues 已创建，GitHub Milestones / Projects Board 尚未创建
- 原则：当前先完善规划与任务拆解；除非用户明确确认恢复开发，否则不启动新一轮代码实现。

## 1. 执行管理方式

本项目采用三层管理：

1. **Roadmap / Milestones**：按阶段定义可验收的里程碑和 Exit Criteria。
2. **Issues**：将里程碑拆成有明确产出、依赖和验收标准的工作项。
3. **GitHub Projects**：跟踪 Issue 状态、优先级、阶段、工作领域和估算。

Roadmap 描述“先做什么、为什么、达到什么结果”；Milestone 描述“一阶段何时算完成”；Issue 描述“具体要完成什么工作”。

### 1.1 建议的 Project Board 状态

| Status | 使用条件 |
|---|---|
| Backlog | 已记录，但依赖/范围/验收条件尚未准备好 |
| Ready | 目标、范围、验收条件和依赖已明确，可以开始 |
| In Progress | 正在执行 |
| Review / Testing | 交付物已提交，正在评审或验证 |
| Blocked | 被外部依赖、权限、数据或决策阻塞 |
| Done | 验收条件全部满足，证据已附在 Issue |

### 1.2 建议的 Project 字段

| 字段 | 类型/取值 | 用途 |
|---|---|---|
| Status | 上述状态 | 工作流 |
| Priority | P0 / P1 / P2 / P3 | 优先级 |
| Milestone | M0–M7 | 里程碑归属 |
| Area | Product / Data Source / Adapter / Schema / Detection / Agent / UI / Evaluation / Security / DevOps | 工作领域 |
| Work Type | Planning / Design / Development / Testing / Documentation | 工作类型 |
| Estimate | XS / S / M / L / XL | 粗略工作量，开始执行前再估算 |
| Dependency | Issue 链接 | 前置工作 |

建议建立三个 View：
- **Board**：按 Status 分组，日常执行。
- **Roadmap**：按 Milestone 分组，查看阶段进展。
- **Table**：按 Priority、Area、Estimate 筛选和批量维护。

## 2. 里程碑定义

里程碑按能力和交付物定义，不预设日历日期。每个里程碑必须满足退出标准才能关闭。

| Milestone | 名称 | 目标 | 关闭条件 |
|---|---|---|---|
| M0 | 规划与设计基线 | 冻结 MVP 范围、架构、数据语义、安全边界和验收指标 | P0 需求、核心场景、数据契约、风险和验收计划获确认 |
| M1 | 首期数据源验证 | 验证 Alibaba WAF/SLS、Tencent WAF/CLS 的可用数据和 API 能力 | 两数据源关键查询能力、字段样本、成本限制和差距均有记录 |
| M2 | 多云接入与统一事件 | Adapter 契约、能力声明、Schema Profiler、Field Registry、Normalizer | 两个 Adapter 通过契约测试；统一事件映射可追溯且有回归测试 |
| M3 | 预筛选与行为聚合 | 规则检测、统计预筛选、去重、Alert Group 和 Incident Candidate | 代表性场景可形成可解释聚合结果，错误合并/漏合并可评估 |
| M4 | Evidence Pack | 生成版本化、可追溯、受控抽样的 AI 输入证据包 | 证据可定位，样本与总体清楚区分，反证/未知/截断信息完整 |
| M5 | AI 研判引擎 | LangGraph 证据调查、威胁分类、报告和评估 | 五级结论、证据引用、反证和成本评估通过基准集验证 |
| M6 | 分析任务与 MVP UI | 手动/定时任务共用引擎；完成最小日志查询与 AI 分析闭环 | 用户能查询、发起分析、查看进度/结果并跳转证据 |
| M7 | PoC 验收与优化 | 安全、准确率、成本、稳定性和可演示性验收 | PoC 验收报告、已知限制、下一阶段建议和演示流程完成 |

### M0 — 规划与设计基线

详细执行基线见 [M0 规划与设计基线](../01-project-planning/m0-baseline.md)。M0 的评审以该文件的 Exit Criteria 为准；当前 M0 Issue #1 保持开放，直至项目负责人确认所有 Proposed 决策并完成退出标准。


**范围**
- 明确首期仅 Alibaba WAF → SLS、Tencent WAF → CLS。
- 确认产品第一版聚焦 AI 威胁分析，不扩展成完整传统 SOC。
- 冻结手动分析 + 定时自动分析两种触发方式，共用同一分析引擎。
- 确认统一事件、告警组、事件候选、Evidence Pack、Analysis Task 的边界。
- 明确只读权限、日志脱敏、Prompt Injection 防护、查询预算和模型预算。
- 定义 P0 场景、评估指标、PoC 成本上限和退出条件。

**建议 Issues**
- M0-01：确认 MVP 用户、核心流程和范围内/范围外清单。
- M0-02：确认首期 WAF 日志类型和安全场景优先级。
- M0-03：评审统一领域对象和数据流。
- M0-04：确认手动/定时分析任务状态机与预算边界。
- M0-05：定义威胁 verdict、严重性、置信度和证据标准。
- M0-06：定义脱敏、权限、审计和不可信日志内容安全要求。
- M0-07：定义 PoC 测试集、指标和成本预算。

**退出标准**
- 每个 P0 需求都有可验证验收条件。
- 核心对象、触发模式和只读边界无重大歧义。
- 首期数据源、场景和预算得到确认。

### M1 — 首期数据源验证

**范围**
- Alibaba SLS：查询语法、时间过滤、分页、返回限制、错误、延迟和计费影响。
- Tencent CLS：验证对应能力；不将阿里云接口行为假定为腾讯云行为。
- 获取脱敏样本，分析字段覆盖率、类型、枚举、共现和日志延迟。
- 验证访问日志、安全告警日志和审计日志是否可用，分别记录。
- 建立 Vendor Capability Matrix 和已知差异。

**建议 Issues**
- M1-01：整理 Alibaba WAF/SLS 官方字段文档和字段语义证据。
- M1-02：采集并脱敏 Alibaba WAF 代表性日志样本。
- M1-03：验证 Alibaba SLS 查询、分页、时间范围和成本限制。
- M1-04：整理 Tencent WAF/CLS 官方字段文档和能力说明。
- M1-05：采集并脱敏 Tencent WAF 代表性日志样本。
- M1-06：验证 Tencent CLS 查询、分页、时间范围和成本限制。
- M1-07：建立跨厂商 Capability Matrix、差距和风险清单。

**退出标准**
- 两数据源至少一条端到端只读查询路径经过真实环境验证。
- 关键字段含义有官方文档或真实样本依据；不确定项标记 Unknown。
- 查询成本、限流、分页和日志延迟风险已记录。

### M2 — 多云接入与统一事件

**范围**
- 统一 Provider Adapter 契约和 Capability Registry。
- Schema Profiler 自动发现字段路径、类型、覆盖率、枚举、共现和变化。
- Field Registry 管理字段定义、语义证据、敏感级别和版本。
- Normalizer 生成稳定核心字段、厂商扩展字段和 provenance。
- Fingerprint 去重；Checkpoint 与查询任务解耦。
- 适配器契约测试、字段映射测试和回归样本。

**建议 Issues**
- M2-01：评审 Provider Adapter 接口和错误模型。
- M2-02：定义 Capability Registry 数据结构和能力声明。
- M2-03：定义 Schema Profile 输出契约和 Schema Drift 规则。
- M2-04：定义 Field Registry 字段语义、证据和版本治理。
- M2-05：冻结统一 WAF Security Event Schema。
- M2-06：定义厂商动作语义映射（检测命中/模块动作/最终动作/测试模式）。
- M2-07：定义 Fingerprint、幂等和迟到日志处理。
- M2-08：完成 Alibaba 映射包和回归测试。
- M2-09：完成 Tencent 映射包和回归测试。

**退出标准**
- 同一套核心契约适用于两个 Provider。
- 不支持或未知的字段/能力不会被默认猜测。
- 原始来源、字段扩展和映射版本可追溯。
- Schema 变化能被发现并进入审查流程。

### M3 — 预筛选与行为聚合

**范围**
- 数据质量检查、去重、受控白名单和基础安全规则。
- SQLi、XSS、命令注入、路径探测、敏感文件探测、扫描、高频异常等首批规则。
- 滑动窗口统计、趋势变化和基线偏差。
- Alert Signal → Alert Group → Incident Candidate 分层。
- 多维关联，避免仅依赖源 IP；保存关联理由和强弱等级。
- 风险分数仅用于排序，不等同于恶意概率。

**建议 Issues**
- M3-01：定义 Detection Signal Schema 和规则元数据。
- M3-02：定义预筛选规则配置、版本和白名单审计。
- M3-03：实现/验证数据质量与重复事件处理策略。
- M3-04：设计首批确定性检测规则和测试样本。
- M3-05：定义滑动窗口统计与异常检测指标。
- M3-06：定义 Alert Group 聚合键、窗口和去重规则。
- M3-07：定义 Incident Candidate 关联强度和关联理由。
- M3-08：定义人工拆分、合并纠正和反馈记录。
- M3-09：建立预筛选召回率、聚合错误率评估方案。

**退出标准**
- P0 场景可产生有来源、有规则、有理由的告警组/事件候选。
- 关联依据可解释；弱关联不会单独触发强关联结论。
- 能统计过滤率、候选召回率、错误合并和漏合并。

### M4 — Evidence Pack

**范围**
- 版本化 Evidence Pack Schema。
- 总体统计、实体、检测结果、时间线、代表样本、反证、未知项和 provenance。
- 分层抽样：高风险、规则/攻击类型多样性、时间分布、反证和随机样本。
- 明确总体记录数、抽样数、样本覆盖、查询截断和数据质量。
- 敏感字段脱敏；日志正文作为不可信数据。

**建议 Issues**
- M4-01：定义 Evidence Pack JSON Schema 和版本策略。
- M4-02：定义事件/告警组/事件候选证据引用格式。
- M4-03：设计代表性样本抽样与反证抽样方法。
- M4-04：定义总体/样本/截断/查询完整性元数据。
- M4-05：定义字段脱敏和 LLM 可见性策略。
- M4-06：构建典型攻击与正常业务 Evidence Pack 样例。
- M4-07：建立 Evidence Pack 完整性和引用有效性测试。

**退出标准**
- Agent 可仅凭 Evidence Pack 获得足够调查上下文。
- 每条关键证据都可定位回事件或源端记录。
- 不会把样本当成全量，也不会把未知字段解释为确定事实。

### M5 — AI 研判引擎

**范围**
- LangGraph 固定工作流：证据验证、威胁假设、证据分析、反证、条件补充查询、分类、报告、持久化审计。
- 只读工具：查询安全日志、事件详情、行为上下文、WAF 规则元数据、历史基线、关联候选。
- 统一五级 verdict：confirmed_malicious、likely_malicious、likely_legitimate、confirmed_legitimate、inconclusive。
- 分开描述攻击尝试、WAF 检测、WAF 最终动作、请求是否到达后端和是否有入侵成功证据。
- 输出 severity、confidence、evidence、counter-evidence、unknowns、recommendations。
- 评估数据集、人工标注和成本/时延度量。

**建议 Issues**
- M5-01：定义 LangGraph State 和节点输入/输出契约。
- M5-02：设计 Evidence Validation 与数据充分性检查节点。
- M5-03：设计 Threat Hypothesis、Evidence Analysis 和 Counter-Evidence 节点。
- M5-04：设计按需上下文补充和只读工具接口。
- M5-05：定义 Verdict、Severity、Confidence 和报告 JSON Schema。
- M5-06：建立 Prompt Injection、敏感数据和工具越权测试。
- M5-07：建立人工标注指南和候选级基准数据集。
- M5-08：设计规则基线、规则+聚合、完整 Agent 三组对照评估。
- M5-09：定义模型版本、Prompt 版本、工作流版本和审计记录。

**退出标准**
- 结论引用可验证证据；无证据时可输出 Inconclusive。
- 模型不能调用写操作或访问云凭据。
- 有按场景划分的准确率、误报、证据依据、成本和时延评估。

### M6 — 分析任务与 MVP UI

**范围**
- 统一 Analysis Task，trigger_type 区分 manual/scheduled。
- 手动分析和定时分析调用同一个分析引擎。
- Scheduler 只创建任务；Provider Query Service 负责源端查询；Worker 负责预筛选、聚合和 Agent 调查。
- 每数据源独立 Checkpoint、重叠窗口、Fingerprint 幂等、失败重试和补采。
- PostgreSQL Task + 轻量 Worker 起步，不引入 Kafka/Redis。
- 最小 UI：日志查询、日志详情、AI 分析面板、结果与证据跳转、简易任务状态。
- 查询/模型预算、暂停/恢复、取消和审计。

**建议 Issues**
- M6-01：定义 Analysis Task Schema、状态机和幂等策略。
- M6-02：定义 Scheduler、Checkpoint 和窗口重叠策略。
- M6-03：定义 Worker 生命周期、重试、取消和失败恢复。
- M6-04：定义查询预算、模型预算和超预算降级策略。
- M6-05：设计手动分析 API 和范围预览交互。
- M6-06：设计定时分析配置和任务状态交互。
- M6-07：设计最小 Log Explorer 页面与详情。
- M6-08：设计 AI 分析面板、结果展示和证据定位。
- M6-09：定义最小身份认证、权限、脱敏和审计验收。
- M6-10：端到端验证手动与定时触发共用同一分析流程。

**退出标准**
- 手动与定时任务共用同一分析工作流。
- Checkpoint 仅在完整成功后推进；重叠和去重可处理迟到/重复数据。
- 超预算不会无限查询或调用模型；无候选任务不无条件调用 LLM。
- 用户可从日志查询发起分析，查看结果并定位证据。

### M7 — PoC 验收与优化

**范围**
- 功能、准确率、稳定性、权限、安全、成本和时延测试。
- 覆盖正常流量、误报、攻击尝试、拦截/放行语义、日志延迟、字段缺失和查询失败。
- 检查审计、敏感数据处理、Prompt Injection 防护和工具边界。
- 完成演示流程、已知限制、风险和下一阶段建议。

**建议 Issues**
- M7-01：建立端到端功能验收用例。
- M7-02：完成威胁分类与证据质量评估。
- M7-03：完成查询成本、Token 成本和时延评估。
- M7-04：完成权限、脱敏、Prompt Injection 和只读工具安全测试。
- M7-05：完成失败恢复、重复任务和日志迟到测试。
- M7-06：整理 PoC 演示脚本和测试报告。
- M7-07：形成下一阶段范围与技术债清单。

**退出标准**
- 核心 P0 场景均有测试结果和问题记录。
- 准确率、证据质量、成本和时延有可复现报告。
- 安全边界和未解决风险明确。
- 项目干系人确认 PoC 是否达到目标。

## 3. Issue 编写模板

每个 Issue 建议使用以下结构：

```markdown
## 背景
说明业务问题和当前限制。

## 目标
描述本 Issue 完成后可验证的结果。

## 范围
- 包含：
- 不包含：

## 方案/要求
说明接口、数据契约、约束或需要评审的设计。

## 依赖
列出前置 Issue、数据源、权限或外部条件。

## 验收标准
- [ ] 可验证条件 1
- [ ] 可验证条件 2
- [ ] 测试/文档证据已附上

## 风险与安全/成本影响
说明日志敏感性、权限、查询成本、Token 成本和失败影响。
```

## 4. 优先级规则

- **P0**：阻塞 MVP 或影响数据正确性、安全边界和核心研判可信度。
- **P1**：显著提升核心场景效果，但可在 P0 闭环后完成。
- **P2**：规模化、体验或高级能力。
- **P3**：暂不计划，仅保留记录。

建议初始排序：
1. M0 全部规划决策和验收标准。
2. M1 两家 WAF 数据源真实能力、样本和成本验证。
3. M2 统一事件语义与字段注册。
4. M3 预筛选和聚合。
5. M4 Evidence Pack。
6. M5 AI 研判与评估。
7. M6 手动/定时任务与简易 UI。
8. M7 PoC 验收。

M0/M1 未通过前，不应因为某个代码模块已经存在就跳过设计验收。

## 5. 依赖与关键风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 厂商字段语义不完整 | 错误归类 WAF 动作或威胁 | 文档/样本双重验证；未知值显式保留 |
| 查询成本或限流超预期 | PoC 成本失控、任务延迟 | 时间窗口、字段过滤、分页、预算和抽样 |
| 日志延迟与重复 | 漏采或重复分析 | Checkpoint、重叠窗口、Fingerprint、幂等任务 |
| 仅按 IP 关联 | NAT/CDN/共享出口导致误关联 | 多维关联、关联强度和理由 |
| LLM 被日志内容诱导 | Prompt Injection、越权工具调用 | 不可信内容隔离、只读工具、后端授权 |
| 证据抽样偏差 | 错误威胁判断 | 分层抽样、反证样本、总体/样本分离 |
| 过早引入复杂组件 | 部署和维护成本上升 | PoC 先 PostgreSQL + 轻量 Worker，按指标扩展 |

## 6. 计划维护规则

- 每次阶段评审更新 Roadmap、Milestone 和 Decision Log。
- Issue 只有在验收条件和证据齐全后才能 Done。
- 外部依赖未验证时保持 Blocked，不以假设代替验证。
- 新增厂商先完成 Capability Matrix、样本和字段语义评估，再估算接入工作量。
- 任何自动响应能力必须单独 ADR，明确审批、TTL、回滚和审计；不属于当前 MVP。
- 不为“看起来完整”而提前建设 Kafka、Redis、OpenSearch、ClickHouse、Kubernetes 或 SOAR。

## 7. GitHub 仓库落地说明

本文件定义了建议的 Milestone、Issue 和 Project Board 内容。GitHub 仓库文档更新不等于 GitHub Projects Board 或 Milestones 已自动创建；需在 GitHub 网页端按本文件建立对应对象，并将 Issues 关联到 Milestones/Project。

建议先建立 M0–M7 八个 Milestones，再按每个 Milestone 的 Issue 清单创建任务。不要一次性把所有开发任务设为 Ready；只有范围、依赖和验收条件已明确的工作才进入 Ready。当前阶段先处理 M0 规划评审和 M1 数据源能力验证。


---

## 8. 按步骤执行与进度跟踪（执行版）

本节是项目日常执行入口。每个 Milestone 按编号顺序推进；如果某一步依赖尚未满足，应标记 Blocked，不要跳过验收直接进入下一阶段。

### 8.1 八个 Milestone 的 GitHub 跟踪入口

| Milestone | 主跟踪 Issue | 前置条件 |
|---|---|---|
| M0 规划与设计基线 | [Issue #1](https://github.com/ccui03/multi-cloud-ai-soc/issues/1) | 无 |
| M1 首期数据源验证 | [Issue #2 阿里云](https://github.com/ccui03/multi-cloud-ai-soc/issues/2)、[Issue #3 腾讯云](https://github.com/ccui03/multi-cloud-ai-soc/issues/3) | M0 通过 |
| M2 多云接入与统一事件 | [Issue #4](https://github.com/ccui03/multi-cloud-ai-soc/issues/4) | M0、M1 通过 |
| M3 预筛选与行为聚合 | [Issue #5](https://github.com/ccui03/multi-cloud-ai-soc/issues/5) | M2 通过 |
| M4 Evidence Pack | [Issue #6](https://github.com/ccui03/multi-cloud-ai-soc/issues/6) | M3 通过 |
| M5 AI 研判引擎 | [Issue #7](https://github.com/ccui03/multi-cloud-ai-soc/issues/7) | M4 通过 |
| M6 分析任务与 MVP UI | [Issue #8](https://github.com/ccui03/multi-cloud-ai-soc/issues/8) | M2–M5 具备可集成接口 |
| M7 PoC 验收与优化 | [Issue #9](https://github.com/ccui03/multi-cloud-ai-soc/issues/9) | M2–M6 集成完成 |

说明：以上 Issue 是每个阶段的主跟踪项，内部 checklist 用于追踪具体步骤。若某个步骤工作量较大、需要独立负责人或独立验收，再从主 Issue 拆分子 Issue。

### 8.2 每个阶段统一执行流程

1. **进入阶段前**：检查前置 Milestone 是否通过；确认输入资料、访问权限、样本和预算可用。
2. **拆解任务**：将主 Issue checklist 中的步骤逐项确认；较大的步骤拆成独立 Issue。
3. **开始工作**：只有目标、输入、验收标准和依赖明确的事项才设为 Ready / In Progress。
4. **过程记录**：每完成一个步骤，在 Issue 中勾选 checklist，并附上文档、测试结果、截图或报告链接。
5. **阶段评审**：对照本阶段 Exit Criteria 逐项验证；未通过项保留 Open 或标记 Blocked。
6. **关闭阶段**：全部验收项通过、交付物已归档、风险已记录后，才关闭主 Issue 和对应 Milestone。
7. **进入下一阶段**：更新 Roadmap / Decision Log，并确认下一阶段范围与依赖。

### 8.3 进度计算规则

- **步骤完成率** = 已完成 checklist 项数 ÷ checklist 总项数。
- **阶段完成率** = 阶段主 Issue 及其子 Issue 中已完成任务数 ÷ 任务总数。
- checklist 完成率仅表示任务执行进度，不代表质量验收通过。
- **Milestone 只有在 Exit Criteria 全部通过后才算完成**；不能仅凭百分比关闭。
- Blocked 任务仍计入未完成任务，并记录阻塞原因、所需决策和解除条件。
- 不建议以提交代码行数、Commit 数或 Issue 数作为项目完成度指标。

### 8.4 每周项目检查清单

每周进行一次轻量检查；开发阶段可根据任务密度提高频率。

- [ ] 更新所有进行中 Issue 的状态和 checklist。
- [ ] 检查是否存在超过一周无进展的 In Progress 项。
- [ ] 检查 Blocked 项的原因、责任人和下一步。
- [ ] 检查本阶段交付物是否有可访问链接和测试证据。
- [ ] 检查查询费用、模型 Token、任务失败率和数据质量是否异常。
- [ ] 检查范围变更是否需要更新 Requirements、Architecture 或 Decision Log。
- [ ] 确认下一周最多 1–3 个最高优先级工作项，避免同时铺开太多工作。

### 8.5 建议的项目看板使用方式

- Board 按 Status 分组，日常更新任务。
- Roadmap 按 Milestone 分组，观察阶段顺序和阻塞关系。
- Table 用于按 Priority、Area、Estimate 筛选。
- 每个 Issue 至少填写 Milestone、Priority、Area、Work Type；Estimate 在任务范围明确后填写。
- 初始只把 M0 评审和 M1 数据源验证放入 Ready；M2–M7 保持 Backlog，待前置条件满足再逐步推进。

### 8.6 当前项目启动顺序

当前阶段不以开发代码为第一目标，先完成规划和数据源验证：

1. 处理 Issue #1：评审并确认 MVP 范围、P0 场景、数据对象、安全边界和验收指标。
2. 处理 Issue #2：完成阿里云 WAF/SLS 字段语义、样本、查询能力和成本验证。
3. 处理 Issue #3：完成腾讯云 WAF/CLS 对应验证，形成与阿里云的差异矩阵。
4. M0 和 M1 通过 Exit Criteria 后，才将 Issue #4 移入 Ready。
5. M2 完成后再推进 M3，后续按依赖链逐阶段推进；M6 的任务/界面设计可提前细化，但集成验收依赖 M2–M5。

