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
