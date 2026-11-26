# 需求规格说明（Requirements）

- 版本：2.0
- 状态：规划基线；具体实现按 Roadmap 分阶段验收
- 日期：2026-11-26

## 1. 产品目标

建设面向多厂商 WAF 的统一安全运营平台。首期接入阿里云 WAF（SLS）和腾讯云 WAF（CLS），但数据模型、字段注册、检测、调查和 Agent 层必须保持厂商无关。未来新增厂商时，主要增加 Provider Adapter 和厂商字段定义，不重写通用分析流程。

## 2. 用户角色

- 安全分析人员：告警研判、事件调查、证据审阅和报告生成。
- 平台管理员：数据源、凭据引用、任务和系统设置管理。
- 安全工程师：字段映射、检测规则和关联规则维护。
- 审计人员：查看查询、Agent 工具调用、审批和响应记录。

## 3. 范围边界

### 首期
- 阿里云 WAF → SLS、腾讯云 WAF → CLS。
- 只读日志接入、批量 Schema 画像、字段映射和统一事件。
- 基础统计、规则检测、跨源检索和调查。
- LangGraph 告警分诊、调查辅助和证据化报告。
- 小规模、低成本 PoC。

### 后续候选
- 其他云厂商、商业 WAF 和本地 WAF。
- API Security、Bot、Firewall、IPS/IDS、DDoS 等安全数据源。
- 威胁情报、案例管理、响应自动化。

### 首期排除
- QRadar 集成或替换、独立传统 SIEM。
- 全量原始日志复制。
- 无审批的云端写操作。
- 强制引入 Kafka、OpenSearch、Redis、TheHive、Shuffle、Kubernetes。
- 生产级 HA、多租户 SaaS。

## 4. 功能需求

优先级：P0 = PoC 必须；P1 = 首期核心价值；P2 = 后续增强；P3 = 远期候选。

| ID | 功能 | 描述 | 优先级 |
|---|---|---|---|
| FR-001 | 数据源配置 | 配置厂商、账号/租户、Region、日志源和凭据引用 | P0 |
| FR-002 | 连接与权限检查 | 检查 API 连通性、授权范围和日志源可查询性 | P0 |
| FR-003 | 统一查询契约 | 统一时间、过滤、分页、排序、查询模式和结果状态 | P0 |
| FR-004 | Provider Adapter | 隔离各厂商 SDK/API、认证、分页、查询语法和错误 | P0 |
| FR-005 | 增量读取 | 每个数据源独立 Checkpoint，支持重叠窗口 | P0 |
| FR-006 | 历史回溯 | 指定时间范围、切片、分页、限额和任务恢复 | P0 |
| FR-007 | 可靠性控制 | 限速、退避重试、超时、断点恢复和幂等去重 | P0 |
| FR-008 | 原始证据管理 | 保留源记录标识、时间、来源和原始字段引用 | P0 |
| FR-009 | Schema Discovery | 批量识别字段路径、类型、覆盖率、枚举和共现关系 | P0 |
| FR-010 | Field Registry | 管理厂商字段语义、模块、类型、敏感级别、映射和版本 | P0 |
| FR-011 | Schema Evolution | 发现新增/消失字段、类型变化和未知枚举，生成变更报告 | P1 |
| FR-012 | 数据脱敏 | 按字段分类脱敏，禁止敏感原始内容无控制进入 LLM | P0 |
| FR-013 | 统一事件标准化 | 统一核心字段，保留 vendor extensions 和解析版本 | P0 |
| FR-014 | 事件检索 | 按时间、来源、IP、域名、动作、规则、事件类型检索 | P1 |
| FR-015 | 基础检测 | 基于确定性规则、阈值、聚合和异常指标生成发现 | P1 |
| FR-016 | 跨源关联 | 基于时间、实体、请求标识和攻击特征关联多数据源 | P1 |
| FR-017 | 告警分诊 | 分类、摘要、优先级建议、重复告警归并 | P1 |
| FR-018 | 攻击调查 | 查询相关事件、补充上下文、构建攻击时间线 | P1 |
| FR-019 | 证据化报告 | 输出结论、证据引用、置信度、不确定性和建议 | P1 |
| FR-020 | 审计 | 记录查询、工具调用、模型版本、输入摘要和输出 | P1 |
| FR-021 | 案例管理 | 事件状态、负责人、备注、证据和处理记录 | P2 |
| FR-022 | 威胁情报 | 将 IP/域名/URL 等实体与可信情报源关联 | P2 |
| FR-023 | 响应计划 | 生成带影响分析、风险和回滚方案的处置建议 | P2 |
| FR-024 | 人工审批响应 | 审批后调用厂商写 API，具备 TTL、回滚和审计 | P3 |
| FR-025 | 多厂商扩展 | 新增厂商时复用通用画像、标准化、检测和 Agent 层 | P0（架构要求） |
| FR-026 | 平台可观测性 | 监控查询量、延迟、失败、队列/任务、成本和模型使用 | P1 |

## 5. Schema Discovery 与 Field Registry 要求

每个厂商/产品/日志类型都必须有独立的 Schema Profile 和 Field Registry。字段定义至少包括：
- 原始字段名、嵌套路径、数据类型和可空性。
- 字段说明、来源文档和语义置信状态（documented / observed / inferred / unknown）。
- 所属产品模块和日志类型。
- 是否敏感、脱敏方式和是否允许进入模型上下文。
- 候选统一字段、转换规则和转换版本。
- 观测覆盖率、枚举分布、首次/最近发现时间。

自动画像只能发现结构和统计关系，不能自行推断安全语义。未知字段和未知动作必须保留并标记 unknown，不得擅自映射为 allow、block 或攻击类型。

## 6. 统一事件模型要求

采用厂商无关的核心字段 + vendor extension：
- Identity：event_id、fingerprint、provider、vendor_product、account/tenant、region、source_id。
- Time：event_time、ingest_time、observed_time。
- Network：source/destination IP、port、protocol（可选）。
- HTTP/API：host、path、method、status、request_id（敏感值按策略处理）。
- Security：event_type、action、action_effectiveness、module、rule_id、rule_type、severity。
- Provenance：source_record_id、raw_reference、schema_version、parser_version、mapping_confidence。
- Extensions：厂商特有字段放入受控 JSON 扩展区，不污染通用核心字段。

必须区分：检测结果、规则动作、最终动作、测试/观察模式、HTTP 响应状态。不能仅凭 HTTP status 或字段缺失推断 allow/block。

## 7. AI Agent 需求

- Agent 仅处理经过筛选、脱敏和结构化的有限上下文。
- 工具调用必须有 allowlist、参数 Schema、时间范围和结果数限制。
- Agent 输出必须包含结论、证据 ID、理由、置信度、不确定性和人工复核标志。
- 日志、URL、User-Agent、Header、Cookie、请求参数和响应片段均视为不可信数据，不得解释为 Agent 指令。
- Agent 不持有云端管理员凭据；首期仅提供只读查询工具。
- 模型不得自行编造不存在的日志字段、规则或情报事实。

## 8. 非功能需求

- 安全：最小权限、凭据引用、加密传输、脱敏、审计和数据保留策略。
- 可扩展：厂商差异封装在 Adapter/Registry，核心模型和业务工作流稳定。
- 可靠性：分页、限速、重试、Checkpoint、幂等、迟到日志和可恢复回溯。
- 可观测：记录调用耗时、返回数、错误码、重试、成本和解析异常。
- 可解释：所有安全结论能够追溯到事件和查询证据。
- 成本：按数据源配置查询预算、采集上限、存储 TTL 和 LLM Token 预算。
- 可测试：每个厂商需有脱敏样例、契约测试、映射测试和回归测试。

## 9. 验收原则

每个新增厂商至少验收：
1. 连接、授权和查询范围正确。
2. 时间边界、分页和错误处理符合厂商 API 行为。
3. Schema Profile 可生成，敏感值不会泄漏。
4. 字段语义有来源依据，未知值保留 unknown。
5. 标准化事件保留来源和原始证据引用。
6. 共用检测/调查流程可处理该厂商事件。
7. 查询成本、数据量和失败恢复可观测。
