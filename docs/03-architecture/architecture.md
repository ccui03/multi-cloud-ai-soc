# 总体技术架构（Architecture）

- 版本：2.0
- 状态：目标架构基线（分阶段实现）
- 日期：2026-11-26

## 1. 架构目标

构建厂商可插拔、核心分析能力可复用的 WAF AI SOC。首期接入阿里云 WAF/SLS 和腾讯云 WAF/CLS；后续可扩展其他云 WAF、商业 WAF 和本地安全设备。

## 2. 核心架构原则

1. 厂商差异只进入 Provider Adapter、Provider Capability 和 Field Registry。
2. Schema Discovery 负责发现结构，不负责猜测安全语义。
3. Normalizer 输出统一核心字段，同时保留 vendor extensions 和 provenance。
4. 检测、关联、调查和 Agent 只消费统一事件契约，不直接依赖厂商原始字段。
5. 原始日志默认留在源端；项目侧存储必要事件、引用、状态和证据。
6. 先确定性查询/规则/统计，再调用 LLM。
7. 所有数据源访问只读起步；响应写操作独立授权并受人工审批控制。

## 3. 目标逻辑架构

```text
              WAF / Security Data Sources
       +-------------+-------------+----------------+
       |             |             |                |
   Alibaba WAF   Tencent WAF   Other WAFs     Future Sources
       |             |             |                |
      SLS           CLS       Vendor APIs/Logs    Vendor APIs
       +-------------+-------------+----------------+
                             |
                    Provider Adapter Layer
             Auth / Query / Pagination / Retry / Limits
                             |
                    Source Capability Registry
                             |
                    Ingestion & Query Planner
                             |
             +---------------+----------------+
             |                                |
       Schema Discovery                 Raw Evidence Reference
       Profile / Drift                         |
             |                                 |
       Field Registry                          |
       (vendor + product + log type)            |
             |                                 |
             +---------------+-----------------+
                             |
                     Normalization Engine
                 Core Event + Vendor Extension
                             |
                  Dedup / Enrichment / Rules
                             |
             +---------------+----------------+
             |               |                |
          Detection       Correlation      Event Store
             |               |                |
             +---------------+----------------+
                             |
                    Alert / Case Service
                             |
                       FastAPI / UI
                             |
                      LangGraph Workflow
              Triage / Investigation / Reporting
                             |
                 Evidence-backed Recommendations
                             |
                 Human Approval (future phase)
                             |
                 Provider Response Connector
```

## 4. 分层职责

| 层 | 核心职责 | 扩展方式 |
|---|---|---|
| Provider Adapter | 认证、查询、分页、错误映射、速率限制 | 每厂商/日志服务一个适配器 |
| Capability Registry | 声明时间过滤、分页、聚合、回查等能力及限制 | 按厂商/API 声明能力，不假设一致 |
| Schema Discovery | 字段路径、类型、覆盖率、共现和变化检测 | 通用引擎 |
| Field Registry | 字段语义、模块、敏感级别、标准映射、证据来源 | 每厂商/产品/日志类型配置 |
| Normalizer | 类型转换、时间标准化、动作语义、统一事件 | 通用引擎 + 厂商映射插件 |
| Detection & Correlation | 规则、阈值、聚合、实体和时间关联 | 通用规则 + 特定数据源扩展 |
| Event / Case Service | 事件生命周期、案例、证据、处理记录 | 统一业务模型 |
| AI Workflow | 分诊、调查、报告和建议 | 基于标准工具和统一事件 |
| Response Gateway | 策略校验、审批、执行、TTL、回滚和审计 | 后续按厂商独立连接器 |

## 5. 数据处理流程

### 5.1 接入与画像
- 为每个数据源建立独立配置和只读凭据引用。
- Adapter 负责受限时间查询和分页。
- Schema Profiler 对脱敏样本或受控采样结果生成字段画像。
- 自动报告字段覆盖率、类型、枚举分布和同记录共现关系。
- 新字段、类型变化和未知枚举进入 Schema Change Review，不自动修改正式语义映射。

### 5.2 字段注册与标准化
- Field Registry 以 provider + product + log_type + schema_version 为边界。
- 每个映射记录官方文档依据、样本证据、语义状态和测试用例。
- Normalizer 将已确认字段转换为统一事件；未知字段放入 vendor extension。
- 原始字段不被覆盖；动作分类与测试模式、规则命中和最终动作分别保存。
- 解析失败进入可观测的异常记录，不静默丢弃。

### 5.3 检测、关联与调查
- 常规高流量日志优先在源端过滤和聚合。
- 规则引擎处理阈值、频率、异常和已知攻击特征。
- 关联层基于实体、时间窗口、请求标识和攻击特征生成关联线索。
- Agent 根据调查计划调用只读工具补充证据，不直接读取无限量原始日志。

## 6. 统一事件模型

统一模型采用“稳定核心 + 厂商扩展 + 来源证据”：
- Core：event_id、provider、vendor_product、source_id、event_time、event_type、severity、action、action_module。
- Network/HTTP：source_ip、destination、host、path、method、status、request_id（按敏感策略处理）。
- Security semantics：rule_id、rule_type、detection_result、final_action、test_mode、action_effectiveness。
- Provenance：source_record_id、raw_reference、schema_version、parser_version、mapping_status。
- Vendor extension：保存未映射但保留价值的原始字段，采用 JSONB 或等效结构。

重要：action、final_action、module_action、test_mode、HTTP status 是不同概念，不应压缩成单一 allow/block 字段。字段缺失和未知枚举均不得默认推断为 allow。

## 7. 数据存储策略

- 源端日志平台是原始日志的权威存储。
- PostgreSQL 用于数据源配置元数据、任务状态、Checkpoint、标准化事件、告警、案例、分析结果和审计。
- 原始日志正文默认不全量复制；按调查和留存需求存必要脱敏片段或源端引用。
- 统一事件保留策略按数据量、法规和调查价值配置。
- 未来若 PostgreSQL 检索/聚合能力不足，再评估 ClickHouse/OpenSearch；若吞吐与解耦需求明确，再评估消息队列。

## 8. AI 与安全边界

- Agent 不直接持有厂商云凭据，只调用受控服务工具。
- 工具采用 allowlist、严格参数 Schema、时间窗口和结果数限制。
- LLM 输入仅包含必要的脱敏字段、统计结果和事件证据。
- 原始日志中的任意文本均视为不可信内容，需防止 Prompt Injection。
- 输出包含 evidence IDs、推理依据、置信度和不确定性。
- 首期不允许 Agent 执行写操作。

## 9. 部署演进

- PoC：Docker Compose、单机、PostgreSQL；不强制引入 Kafka/OpenSearch/Redis/Kubernetes。
- Pilot：按任务量拆分 API/Worker，完善指标、备份、迁移和密钥管理。
- Production：根据容量、HA、租户隔离和合规要求评估队列、分析存储、集群部署和灾备。

## 10. 架构验收

- 新增厂商不要求修改通用 Profiler、事件核心模型和 Agent 主流程。
- 不支持的厂商查询能力必须显式声明，不得伪装成支持。
- 未知字段和语义映射变更有报告、有版本、有回归测试。
- 每条标准化事件均可追踪来源和解析版本。
- AI 调查可回溯其使用的事件、查询和工具调用。


---

## 11. 分层攻击研判架构（v2.1 补充）

### 11.1 核心处理链
WAF 日志源 → Provider Adapter → Schema Discovery / Field Registry → Normalizer → Normalized Events → 确定性检测与统计 → Alert Signals → Alert Aggregation → Alert Groups → Incident Correlation → Security Incident Candidates → Evidence Pack Builder → LangGraph AI Analyst → Verdict / Confidence / Rationale → Policy Recommendation → Human Review / Manual Execution → Feedback。

### 11.2 对象关系与边界
- Normalized Event 忠实表达来源记录的安全相关事实，保留原始来源引用。
- Alert Signal 由厂商告警、确定性检测规则或统计异常产生；普通访问日志不自动等于告警。
- Alert Group 对重复、相似或同一行为簇的告警进行降噪组织，保留成员关系和聚合规则版本。
- Security Incident 对一个或多个告警组及相关事件进行更高层关联，是主要研判对象。
- Investigation 记录调查问题、时间范围、查询、证据、模型/提示版本和人工修改。
- Policy Recommendation 是建议对象，不是厂商配置变更任务。

关联关系必须有 provenance、原因和置信度。不能把同一 IP 作为唯一充分条件；需组合时间邻近、目标 Host/路径、规则/攻击类型、请求模式等信号，并考虑 NAT、代理、CDN、共享出口和爬虫造成的误关联。

### 11.3 聚合与关联原则
1. 先确定性、后 AI：去重、窗口聚合、计数、频率、Top-N 和规则检测先完成。
2. 双层归并：Alert Group 负责相似告警降噪；Incident Correlation 负责跨告警组、跨域名/账号/云平台的活动关联。
3. 多维关联：时间、来源/目标实体、Host、路径模板、规则类别、请求 ID、行为序列及可信情报（如启用）。
4. 避免过度合并：支持拆分、撤销关联和人工纠正；记录关联规则版本。
5. 按需下钻：证据包先包含统计、样本摘要和事件引用；只有验证假设时才通过只读工具查询有限原始日志。
6. 保留未知：字段缺失、语义不明、代理/NAT 共享来源等均作为不确定性，不做强推断。

### 11.4 Evidence Pack
AI 的主要输入是有限、可追溯的证据包，而不是无限量原始日志。建议包含事件/告警组 ID、时间范围、数据源、数量和去重统计、规则/模块分布、动作分布、趋势、涉及实体摘要、代表性事件引用、source_record_id/raw_reference、字段语义状态、关联依据、反证、数据缺口、抽样方法以及 Schema/Normalizer 版本。证据包记录统计口径和抽样规则；模型不得把抽样样本误当作总体。

### 11.5 核心业务实体（逻辑模型）
| 实体 | 关键字段（概念级） | 作用 |
|---|---|---|
| normalized_event | event_id、source_id、event_time、core_fields、extensions、provenance | 标准化事实 |
| alert_signal | signal_id、event_ref、detector_id、reason、severity | 单次检测信号 |
| alert_group | group_id、group_key、window、member_refs、aggregation_version、stats | 告警降噪分组 |
| security_incident | incident_id、status、verdict、severity、confidence、time_range、entity_refs | 核心研判对象 |
| incident_relation | from_id、to_id、relation_type、reason、confidence、rule_version | 关联依据 |
| evidence_item | evidence_id、source_ref、query_ref、fact、supports_or_contradicts | 可追溯证据 |
| investigation | investigation_id、incident_id、workflow_version、model_version、status | 调查记录 |
| policy_recommendation | recommendation_id、incident_id、rule_scope、proposal、risk、validation、status | 人工审核建议 |
| analyst_feedback | feedback_id、target_ref、decision、reason、reviewer、outcome | 人工反馈 |

这些是逻辑实体，不代表 PoC 必须拆成独立数据库表；可根据查询和事务需求采用 PostgreSQL 关系表与 JSONB。

### 11.6 策略建议边界
Recommendation Service 只生成建议和审查材料，不持有厂商写凭据。建议需包含最小作用范围、业务影响、安全风险、测试步骤和回滚考虑。“建议已采纳”“人工已执行”“效果已验证”是不同状态，必须分别记录。当前不实现厂商策略写 API、自动封禁或自动规则例外；未来若讨论自动执行，必须重新进行独立架构决策。


---

## 12. Web 工作台与交互架构（v2.2 补充）

### 12.1 前后端分层
建议采用 React + TypeScript Web 前端，通过 FastAPI 统一 API 访问平台能力。前端不直接连接 PostgreSQL、SLS、CLS 或模型供应商。

逻辑结构：
- Web UI：Dashboard、Log Explorer、Alert Center、Incident Center、AI Copilot、Recommendation Center、Reports、Administration。
- API/BFF 层：身份认证、RBAC、数据范围、请求校验、分页、限流、查询预算和审计。
- Query Service：统一查询接口、Provider Capability 检查、查询计划、源端过滤/聚合、分页和结果归一化。
- Incident/Investigation Service：告警组、事件、时间线、证据和调查状态。
- Agent Service：LangGraph 会话、受控工具调用、Evidence Pack 和结构化输出。
- Recommendation Service：策略建议草稿、审核状态和人工执行记录。
- Audit/Usage Service：用户行为、查询审计、模型用量和成本。

### 12.2 UI 信息架构
主导航建议：总览、日志查询、告警中心、攻击事件、AI 助手、策略建议、报表、系统管理。

日志详情、告警组详情和事件详情提供统一的 AI Copilot 入口。AI 回答中的证据链接可返回对应日志、告警组或事件详情，形成双向导航。

### 12.3 AI 对话与工具调用边界
- Chat UI 只与 Agent API 交互；Agent 只能调用后端注册的只读查询工具。
- 工具层强制执行用户身份、角色、数据源范围、字段权限、时间范围、结果上限和成本预算。
- LLM 不直接生成并执行任意 SQL 或 SLS/CLS DSL；Query Planner 将意图映射为受限查询结构，再由 Provider Adapter 翻译为厂商查询。
- 对大范围/高成本查询可先返回计划、范围和估算，要求用户确认或缩小范围。
- 每次工具调用产生审计记录和证据引用；AI 回答必须绑定 Evidence Pack。
- 原始日志中的 URL、Header、Cookie、Body 均是不可信数据，不得作为模型指令；敏感字段在进入模型前按策略脱敏。
- AI 会话上下文与事件上下文需明确绑定，防止跨事件上下文混淆。

### 12.4 核心 API 领域（逻辑分组）
- Dashboard API：运营总览与统计。
- Logs API：日志查询、字段/过滤能力、记录详情。
- Alerts API：告警信号与告警组。
- Incidents API：事件队列、详情、关联和时间线。
- AI Sessions/Messages API：AI 会话与对话。
- Recommendations API：策略建议和人工审核状态。
- Reports API：报表生成与查询。
- Administration API：用户、角色、数据源和配置。
以上为规划级 API 边界，不代表已确定最终 REST 路由。

### 12.5 关键交互流程
**日志查询**：UI Filter → API AuthZ/Budget → Query Planner → Provider Adapter → Normalizer → Paginated Results → Log Detail / Incident Link。

**AI 对话**：Chat UI + Selected Context → Agent API → AuthZ → Query Plan → Read-only Tools → Evidence Pack → LangGraph Investigation → Structured Answer + Evidence Links → UI。

**策略建议**：Incident → Recommendation Draft → Human Review → External Manual Change → Record External Change Reference → Outcome Verification。

### 12.6 UI 架构安全
所有权限判断在后端执行；前端隐藏控件只改善体验，不构成安全边界。查询接口防止越权访问、过大时间范围、分页绕过和导出滥用。会话和证据按租户/数据源范围隔离。审计记录用户、动作、时间、查询范围、结果数量、工具调用、模型版本和建议状态变更。


---

## 13. UI 交互与会话上下文架构（v2.3）

### 13.1 前端布局
采用全局应用壳层（App Shell）：
- 左侧导航控制模块切换。
- 中央内容区承载 Dashboard、Log Explorer、Alert Center、Incident Center 等完整页面。
- 右侧 AI Drawer 为全局可展开面板。
- 独立 AI Workspace 复用同一会话与消息组件，但提供更大的对话、会话列表和证据浏览空间。

### 13.2 Context Envelope
前端传递给 Agent 的上下文应采用明确的数据结构，而不是把整个页面状态或任意 DOM 内容直接塞入 Prompt。概念字段包括：
- context_type：dashboard_filter / selected_logs / alert_group / incident / saved_query。
- source_refs：数据源和记录引用。
- scope：时间范围、租户/数据源范围、Host 等过滤范围。
- selection_mode：selected_records / filter_summary / object_reference。
- context_version：上下文快照版本。
- user_id / session_id：由服务端身份和会话系统确定，不信任前端自行声明的用户身份。

后端必须重新验证对象引用和用户授权。上下文只提供调查线索，不构成权限授予。对筛选条件传入的统计摘要和具体日志记录必须明确区分。

### 13.3 面板与独立页面会话一致性
- AI Drawer 和 AI Workspace 使用相同 Agent Session / Message / Investigation 标识。
- 面板“打开到独立页面”只改变呈现容器，不新建或复制调查。
- 会话保存当前上下文快照、活动事件引用、证据引用和查询审计引用。
- 切换业务页面不会自动改变已有会话上下文；用户主动添加新上下文时记录变更。
- 多事件调查必须显式显示活动事件和各事件关联关系，避免证据混用。

### 13.4 UI 状态与后端任务
长时间调查由后端任务状态驱动，至少区分 queued、running、waiting_for_user、completed、failed、cancelled。前端关闭面板不等于取消任务；用户需明确取消。重连或重新打开面板时根据 session/task 状态恢复展示。具体实时通信可在 UI 原型和技术验证后选择 SSE 或其他方案。

### 13.5 页面与领域服务边界
UI 通过 API 调用 Dashboard、Query、Alert、Incident、Agent、Recommendation、Report 和 Administration 服务。Drawer 不拥有独立的日志查询权限或数据连接；它复用同一 Query Service 与 Agent Service。所有上下文解析、对象授权、查询预算和工具审计均在服务端完成。


---

## 14. 分析任务调度架构（v2.5）

### 14.1 统一任务入口
手动分析请求和 Scheduler 触发均创建统一 Analysis Task。任务元数据包括 task_id、trigger_type、source_ids、scope/time_range、filter/query_plan、idempotency_key、status、budget、checkpoint_ref、workflow_version、evidence_ref、result_ref 和审计信息。

### 14.2 逻辑流程

```text
Manual UI Request ─┐
                   ├─> Analysis Task API / Task Store
Scheduler ─────────┘              |
                                  v
                         Scope & Budget Guard
                                  |
                         Query Planner / Adapter
                                  |
                       Normalize / Dedupe / Profile
                                  |
                      Rule & Statistical Pre-filter
                                  |
                     Alert Group / Behavior Clusters
                                  |
                       Candidate Threshold Gate
                           /             \
                    No Candidate       Candidate
                       |                  |
                 Record Scan Result   Evidence Pack
                                          |
                                    LangGraph Analyst
                                          |
                               Verdict / Evidence / Report
                                          |
                                  Human Review in UI
```

### 14.3 Scheduler 与 Worker 职责
- Scheduler 只负责根据数据源配置和 Checkpoint 创建任务，不执行模型推理，也不直接访问厂商日志 API。
- Worker 从任务队列/任务表领取任务，调用统一 Query Service 和 Analysis Service。PoC 可先采用 PostgreSQL 任务表 + 单独 Worker/进程，不因定时任务立即引入 Kafka/Redis。
- Provider Adapter 仍由 Query Service 调用；云凭据不暴露给 Scheduler 或 LLM。
- 手动任务和定时任务使用相同的 Worker 执行路径，差异仅在触发来源和初始范围。

### 14.4 Checkpoint 与窗口
- Checkpoint 以数据源为隔离边界，至少区分 last_successful_window_end 与最近调度/任务状态。
- 每次任务读取 [previous_success_end - overlap, current_window_end] 的时间范围；重叠窗口用于吸收迟到日志，重复记录通过稳定 Fingerprint 幂等处理。
- 只有查询结果完整性达到任务成功条件且必要结果已持久化，才推进成功水位；部分失败不能误标成功。
- overlap 和运行频率应依据各源实际日志延迟、查询成本和限流测量调整。

### 14.5 预算与运行控制
按数据源设置最大查询频率、最大时间窗口、返回记录上限、单任务/每日查询预算、单任务/每日 LLM Token 或费用预算。任务超限时转为 waiting_for_budget、failed 或 completed_with_warnings，具体由可恢复性决定，并写明原因。支持暂停调度、恢复、手动补跑和任务取消。

PoC 部署不强制引入消息队列；先使用 PostgreSQL 持久化任务状态与轻量 Worker。只有并发、吞吐或可靠性数据证明有需要时再评估队列。

## 12. 核心分析引擎技术设计基线（v2.3）

核心分析链路、对象契约、预筛选、行为聚合、Evidence Pack、LangGraph 和评估方法统一以 [核心分析引擎技术设计](../07-core-analysis-engine/core-analysis-engine-design.md) 为详细设计依据。

架构约束补充：
- Prefilter 与行为聚合消费统一事件和已确认字段语义，不直接耦合 SLS/CLS 原始字段。
- Alert Group 与 Incident Candidate 分层；IP 不能作为唯一聚合或关联依据。
- Evidence Pack 是 AI 主要事实输入，必须携带总体/样本数量、抽样方法、截断状态、反证、未知项和来源引用。
- LangGraph 使用固定主流程和条件补充查询；工具由后端提供只读权限、查询预算、脱敏和审计。
- AI 输出必须区分攻击尝试、WAF 动作、后端到达和业务系统 compromise；未知状态不得推断。
- 规则版本、聚合版本、Evidence Pack 版本、模型/提示/工作流版本均需可追溯。
- 当前 PoC 继续采用 PostgreSQL + 轻量 Worker；新增队列、图数据库或专用分析存储必须有容量/效果证据。

以上为目标设计，具体窗口、阈值和性能目标待真实样本验证，不代表已实现。
