# Decision Log

记录已经确认的项目决策。未验证的实现细节应标记为 Proposed，不得写成已验证事实。

| 日期 | 决策 ID | 主题 | 状态 | 决策 |
|---|---|---|---|---|
| 2026-11-26 | DEC-000 | 使用 GitHub 管理项目文档与代码 | Accepted | GitHub Repository 为项目正式版本来源 |
| 2026-11-26 | DEC-001 | 首期云 WAF 数据源 | Accepted | 仅接入阿里云 WAF（SLS）和腾讯云 WAF（CLS） |
| 2026-11-26 | DEC-002 | SIEM 方案 | Accepted | 首期不复用 QRadar，也不部署独立传统 SIEM |
| 2026-11-26 | DEC-003 | 原始日志处理策略 | Accepted | 原始日志留在 SLS/CLS；不全量搬迁，优先源端过滤/聚合和按需回查 |
| 2026-11-26 | DEC-004 | PoC 资源规模 | Accepted | 采用小规模、低成本资源；Docker Compose 起步 |
| 2026-11-26 | DEC-005 | 日志接入架构 | Accepted | 使用统一 Python Adapter，分别封装 SLS 和 CLS |
| 2026-11-26 | DEC-006 | 首期数据访问权限 | Accepted | 只读查询；云端写操作不在首期默认范围 |
| 2026-11-26 | DEC-007 | 首期组件范围 | Accepted | 暂不部署 Kafka、OpenSearch、Redis、TheHive、Shuffle、Kubernetes；按需再评估 |

## 决策影响与复核条件

- DEC-003：若源端查询成本过高、查询延迟不满足或需要跨系统长期检索，再评估日志复制/专用搜索引擎。
- DEC-004：若并发、吞吐或可用性要求超出单机能力，再拆分服务或引入队列。
- DEC-005：若厂商 API 不支持预期分页/过滤能力，应调整 Adapter 契约并记录 ADR。
- DEC-007：任何新增基础设施必须说明解决的问题、资源消耗和更轻量替代方案。

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
