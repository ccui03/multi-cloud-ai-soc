# 技术选型记录（候选清单）

| 能力 | 候选 | 当前建议 | 验证重点 |
|---|---|---|---|
| Agent Workflow | LangGraph | 优先 PoC | 状态持久化、人工中断恢复、可观测性 |
| Backend | FastAPI | 优先 PoC | API、认证、异步任务 |
| Search | OpenSearch | 候选 | 写入性能、查询、生命周期管理 |
| Queue | Kafka | 按规模决定 | 是否需要持久化缓冲、重放和多消费者 |
| Event Schema | OCSF | 候选 | WAF 字段映射覆盖率 |
| Case Management | TheHive | 待评估 | API、事件生命周期和集成成本 |
| Threat Intel | MISP | 待评估 | 情报源质量、更新频率和误报 |
| SOAR | Shuffle | 待评估 | 审批、凭据管理、审计和执行器 |
| Database | PostgreSQL | 候选 | 业务元数据和事务 |
| Cache/State | Redis | 候选 | 缓存、队列辅助和短期状态 |
| Frontend | React | 候选 | 告警、事件和调查工作台 |
| Deployment | Docker / Kubernetes | Docker 起步 | 部署复杂度和资源需求 |

## 选型原则

- 不因技术流行而引入组件；每个组件必须解决明确问题。
- 尽量复用已有 SIEM、日志平台和云服务。
- 先用最小端到端 PoC 验证，再扩展组件。
- 任何最终选型都应有 ADR，记录备选方案、决策依据和影响。
