# Decision Log

记录已确认的项目决策。尚未验证的实现细节必须标记为 Proposed 或 Unknown，不得写成已验证事实。

| 日期 | 决策 ID | 主题 | 状态 | 决策 |
|---|---|---|---|---|
| 2026-11-26 | DEC-000 | 使用 GitHub 管理项目 | Accepted | GitHub Repository 为项目正式版本来源 |
| 2026-11-26 | DEC-001 | 首期数据源 | Accepted | 首期只接入阿里云 WAF（SLS）和腾讯云 WAF（CLS） |
| 2026-11-26 | DEC-002 | SIEM 方案 | Accepted | 不复用 QRadar；PoC 不部署独立传统 SIEM |
| 2026-11-26 | DEC-003 | 原始日志处理 | Accepted | 原始日志默认留在源端；优先源端过滤/聚合和按需回查，不全量搬迁 |
| 2026-11-26 | DEC-004 | PoC 资源规模 | Accepted | 采用小规模、低成本资源，Docker Compose 起步 |
| 2026-11-26 | DEC-005 | 接入架构 | Accepted | 使用统一 Provider Adapter，厂商 SDK/API 差异封装在 Adapter |
| 2026-11-26 | DEC-006 | 首期权限 | Accepted | 首期只读；云端写操作不在默认范围 |
| 2026-11-26 | DEC-007 | 首期基础设施 | Accepted | 暂不部署 Kafka、OpenSearch、Redis、TheHive、Shuffle、Kubernetes；有明确需求和容量证据后再评估 |
| 2026-11-26 | DEC-008 | 多厂商扩展方式 | Accepted | 采用 Provider Adapter + Capability Registry + Field Registry + 通用 Schema Profiler / Normalizer；新增厂商不复制通用分析逻辑 |
| 2026-11-26 | DEC-009 | 产品范围演进 | Accepted | 产品长期定位为多厂商 AI SOC；首期以 WAF 为切入点，其他安全数据源分阶段规划，不提前承诺全部接入 |
| 2026-11-26 | DEC-010 | 规划优先于新增开发 | Accepted | 当前优先完善产品需求、场景、数据模型、验收指标和路线图；暂停无明确计划依据的功能开发 |
| 2026-11-26 | DEC-011 | 安全语义治理 | Accepted | 自动 Schema 分析只发现结构和统计关系；安全语义必须由官方文档、样本证据和测试共同确认，未知值不得猜测 |

| 2026-11-26 | DEC-012 | AI 研判基本对象 | Accepted | 告警先聚合为 Alert Group，再关联形成 Security Incident；Incident 是主要 AI 研判对象，必要时按需下钻单条日志 |
| 2026-11-26 | DEC-013 | WAF 策略调整权限 | Accepted | AI 只生成有证据的策略优化建议，由安全人员人工审核和执行；当前不提供自动封禁或 WAF 策略写入 |
| 2026-11-26 | DEC-014 | 研判结论分类 | Accepted | 采用 confirmed_malicious、likely_malicious、likely_legitimate、confirmed_legitimate、inconclusive，允许证据不足，不强制二元判断 |

## 决策影响与复核条件

- DEC-003：若源端查询成本、延迟或可用性不满足要求，再评估日志复制和专用分析存储。
- DEC-004：若吞吐、并发或可用性超出单机能力，再拆分服务或引入队列。
- DEC-005/008：新厂商接入时，先评估其 API 能力与统一契约差异；必要时扩展 capability，不强制所有厂商行为完全一致。
- DEC-007：新增基础设施必须说明解决的问题、资源消耗、容量依据和更轻量替代方案。
- DEC-009：新增数据源必须有明确用户场景、数据可用性、成本和维护责任。
- DEC-011：字段映射需记录来源、语义状态、版本和回归用例。

## 决策记录模板

### DEC-XXX：标题

- 日期：
- 状态：Proposed / Accepted / Superseded
- 背景：
- 备选方案：
- 决策：
- 原因：
- 影响：
- 复核条件：


| 2026-11-26 | DEC-015 | 日志分析启动方式 | Accepted | 第一版同时支持手动分析与定时自动分析；两者统一创建 Analysis Task 并复用同一预筛选、聚合、Evidence Pack 和 AI 研判工作流。定时分析只发现和报告，不执行 WAF 写操作。 |

## DEC-015 补充说明
- 手动分析用于用户指定范围的调查和验证；定时分析用于按数据源持续检查新增日志。
- Scheduler 只创建任务；统一 Worker/Analysis Service 执行查询和 AI 分析。
- 每数据源独立 Checkpoint，采用重叠窗口和 Fingerprint 幂等去重处理迟到/重复日志。
- 查询和模型调用均受预算限制；无候选时允许跳过 LLM。
- 复核条件：真实日志量、延迟、SLS/CLS 查询成本和模型成本测量后，再确定默认调度间隔、窗口及预算。
