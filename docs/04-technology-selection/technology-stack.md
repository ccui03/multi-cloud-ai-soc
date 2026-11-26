# 技术选型记录（PoC 基线）

- 版本：1.1
- 日期：2026-11-26
- 状态：首期范围已确认；具体 SDK/API 细节待验证

## 1. 首期技术栈

| 能力 | 首期选择 | 选择理由 / 验证重点 |
|---|---|---|
| WAF 日志存储与查询 | 阿里云 SLS、腾讯云 CLS | 原始日志继续留在云端 |
| 日志接入 | Python Adapter + 官方 SDK/API | 隔离厂商差异 |
| 后台任务 | Python worker / scheduler | 小规模 PoC，避免先部署消息队列 |
| Backend | FastAPI | 提供配置、查询和分析 API |
| Database | PostgreSQL + JSONB | 保存 Checkpoint、标准化事件、分析结果 |
| Agent Workflow | LangGraph | 组织有状态分析流程和人工介入 |
| Deployment | Docker Compose | 资源占用低、易于复现 |
| Frontend | 暂缓或轻量页面 | 先验证数据链路和分析价值 |

## 2. 首期明确不引入

| 技术 | 首期决定 | 重新评估条件 |
|---|---|---|
| QRadar | 不复用、不集成 | 当前 PoC 无此需求 |
| Kafka | 暂不部署 | 多消费者、吞吐、缓冲或重放需求出现 |
| OpenSearch | 暂不部署 | PostgreSQL 与源端查询无法满足检索/聚合需求 |
| Redis | 暂不部署 | 缓存、并发任务或共享状态成为瓶颈 |
| TheHive | 暂不部署 | 需要成熟事件生命周期管理 |
| Shuffle | 暂不部署 | 需要独立 SOAR 工作流 |
| MISP | 暂不部署 | 需要自托管情报平台且数据源明确 |
| Kubernetes | PoC 不部署 | 需要多节点、高可用或集群运维 |

## 3. Adapter SDK 选择原则

- 使用官方支持的 SDK 或 API。
- SDK 版本固定并在依赖文件中锁定。
- 厂商 SDK 只存在于对应 Adapter 模块。
- 查询语法通过 QueryRequest 转换，不在业务层散布厂商 DSL。
- 用 mock 响应和脱敏真实样本进行契约测试。
- 认证使用最小权限凭据，支持环境变量或 Secret 注入。

## 4. 后续候选

OCSF 可作为统一事件模型参考；OpenSearch、Kafka、Redis、MISP、TheHive、Shuffle 均可在 PoC 数据和性能验证后再评估。任何引入都需记录 ADR，说明新增组件解决的问题、资源成本和替代方案。
