# 总体技术架构（Architecture）

- 版本：1.1
- 状态：PoC 架构基线
- 日期：2026-11-26

## 1. 架构原则

1. SLS / CLS 是原始 WAF 日志的主存储和查询平台。
2. AI SOC 不全量搬迁原始日志；采用源端查询、筛选、聚合与按需回溯。
3. SLS 与 CLS 的 API/查询差异由 Python Adapter 隔离。
4. 规则和统计先处理，LLM 分析有限且有证据的数据。
5. 首期只读、低资源、可本地复现；不引入非必要基础设施。

## 2. 逻辑架构

```text
Alibaba Cloud WAF                         Tencent Cloud WAF
       |                                          |
       v                                          v
      SLS                                        CLS
 (raw log store)                            (raw log store)
       |                                          |
       +-------------------+----------------------+
                           |
                 Python Adapter Layer
             +-------------+--------------+
             |                            |
       AliyunSLSAdapter             TencentCLSAdapter
             |                            |
             +-------------+--------------+
                           |
                  Ingestion Service
       (query planner / scheduler / retry / checkpoint)
                           |
                Normalize / Deduplicate
                           |
             +-------------+------------------+
             |                                |
       PostgreSQL                       Query-on-demand
 (checkpoint, normalized                 back to SLS/CLS
  events, findings, audit)          (investigation context)
             |
         FastAPI
             |
      LangGraph Workflow
       |      |       |
     Triage Investigation Reporting
       |      |       |
       +-- read-only query tools --+
             |
       Evidence-based result
```

## 3. 数据流说明

### 3.1 常规增量处理
- Scheduler 为每个数据源读取独立 Checkpoint。
- 生成小时间窗口查询（初始测试 5–15 分钟轮询）。
- Adapter 将统一过滤条件转换为厂商查询请求。
- 结果分页读取、规范化、计算幂等键并写入 PostgreSQL。
- 当前窗口所有页面持久化成功后才推进 Checkpoint。
- 查询窗口可向前重叠，重复记录由幂等键处理。

### 3.2 历史回溯
- 调查员指定时间范围，例如过去 1 天或 7 天。
- Query Planner 将大窗口切分为较小区间，逐段分页。
- 历史任务不改变常规增量 Checkpoint。
- 保存查询任务、条件、进度和结果摘要，支持暂停/恢复。

### 3.3 源端分析与按需明细
- SLS / CLS 执行时间、字段和动作条件过滤。
- 对正常访问等高基数数据，优先在源端执行聚合/统计查询。
- AI SOC 获取命中明细、聚合结果或有限上下文。
- 对单个攻击源或事件，再按 IP、域名、URI、规则和时间窗口回查原始日志。

## 4. 组件职责（PoC）

| 组件 | 职责 | 首期是否部署 |
|---|---|---|
| SLS / CLS | 原始日志存储、查询、过滤、聚合 | 使用云端现有服务 |
| Python Adapters | SDK/API 封装、查询转换、分页、错误归一化 | 是 |
| Ingestion Service | 调度、Checkpoint、重试、幂等和标准化 | 是 |
| FastAPI | 数据源、查询、事件和分析 API | 是 |
| PostgreSQL | Checkpoint、事件、分析结果、审计元数据 | 是 |
| LangGraph | 告警分诊、调查和报告流程 | 是 |
| Kafka | 高吞吐持久化消息流 | 否，后续按需 |
| OpenSearch | 大规模全文检索/分析 | 否，先验证源端查询与 PostgreSQL |
| Redis | 缓存/分布式任务状态 | 否，出现需求后再引入 |
| QRadar / TheHive / Shuffle | SIEM/Case/SOAR | 否，首期不使用 |

## 5. 统一 Adapter 边界

上层服务只依赖统一的 QueryRequest、FetchPage、HealthStatus 等内部模型。Adapter 内部处理：
- SLS/CLS 认证和客户端初始化。
- Project/Logstore 或 Topic 等数据源定位。
- 时间过滤和厂商查询语法转换。
- 分页/游标和结果解码。
- API 错误、限流、超时的统一映射。
- 请求耗时和调用指标。

Adapter 不负责 LLM 调用、事件风险判断、响应决策或云端写操作。

## 6. 存储策略

PostgreSQL 仅保存项目分析需要的数据：
- 每个数据源的 Checkpoint 和采集任务状态。
- 标准化后的安全事件及必要 raw_event（可配置保留策略）。
- 聚合结果、告警/调查结果、证据引用。
- 查询审计、模型分析元数据。

不默认将所有原始访问日志复制到 PostgreSQL。若只需保留引用，可存 source、时间、查询条件和源记录标识；但需验证源端记录可稳定回查。

## 7. 安全边界

1. SLS / CLS 凭据采用只读权限，限制到指定 Project/Logstore 或 Topic。
2. Agent 只能调用只读查询工具，不直接持有云管理员凭据。
3. URL、User-Agent、Header、Cookie、请求参数等日志内容均是不可信数据。
4. 模型输出需结构化并引用事件证据，不能仅凭自然语言结论触发动作。
5. 首期不执行 WAF 策略修改或 IP 封禁。
6. 所有查询记录数据源、时间范围、过滤条件、调用者、耗时和结果摘要。

## 8. 部署架构

首期采用 Docker Compose，建议最小服务：
- api / worker（可先同一 Python 应用进程或分离容器）
- PostgreSQL
- 可选轻量调度器

不部署 Kubernetes、Kafka、OpenSearch 或 Redis，除非 PoC 测量证明必要。

## 9. 待验证事项

- SLS 与 CLS 的查询 API/SDK、分页语义、最大窗口和结果限制。
- 两个 WAF 日志字段、索引配置和查询语法。
- 迟到日志分布和适当的重叠窗口。
- 查询费用、API 限额、速率和并发限制。
- 源端聚合能力是否满足需要，以及聚合结果如何分页。
- PostgreSQL 在实际样本规模下的检索性能。
