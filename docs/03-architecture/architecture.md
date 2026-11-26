# 总体技术架构（Architecture）

- 版本：0.1
- 状态：候选架构，待 PoC 验证

## 1. 逻辑架构

```text
Cloud WAF / Security Sources
        |
        v
Cloud Log Adapters
(API / SLS / CLS / Event Stream / Object Storage)
        |
        v
Ingestion & Message Pipeline
        |
        v
Raw Event Storage ----> Parser / Normalizer ----> OpenSearch
                                |                    |
                                v                    v
                         Detection Rules ------> Alert / Case API
                                                     |
                                                     v
                                             LangGraph Workflow
                                      +--------------+--------------+
                                      |              |              |
                                  Triage Agent  Investigation   Reporting
                                      |              |
                                      +------ Threat Intel Tools
                                                     |
                                                     v
                                           Human Approval Gate
                                                     |
                                                     v
                                           Response Connectors
                                           (WAF / Cloud APIs)
```

## 2. 分层说明

### 数据接入层
每个云厂商单独实现 Adapter，负责认证、分页/游标、限流、重试、断点续传和原始数据落地。不要把厂商 API 逻辑耦合进 Agent。

### 数据处理层
解析厂商日志，生成规范化字段，同时保留完整 raw_event。记录 parser_version 和 schema_version，便于重放和修正。

### 检测与检索层
先使用规则、查询和聚合识别可疑行为。OpenSearch 是候选检索引擎；是否需要 Kafka 取决于数据量、吞吐和可靠性要求。

### AI Agent 层
LangGraph 编排有状态工作流。Agent 通过明确授权的工具获取有限数据，不直接持有云平台管理员凭据。模型输出使用结构化 Schema，并要求提供证据引用。

### 事件与响应层
事件管理可先由自建轻量 API 实现，也可评估 TheHive。响应流程可评估 Shuffle 或自建审批流程。避免多个系统重复承担同一工作流职责。

## 3. 安全边界

1. 原始日志属于不可信输入，URL、User-Agent、Header 和请求参数可能包含恶意提示词。
2. LLM 只负责分析和建议，不能自行决定执行高风险操作。
3. 读操作和写操作使用不同工具身份与凭据。
4. 写操作必须经过策略校验；高风险操作必须人工审批。
5. 封禁类操作需考虑共享出口、CDN、NAT、可信扫描器、TTL 和自动解封。
6. 所有工具调用记录调用人/工作流、参数摘要、结果和关联事件 ID。

## 4. 初期部署建议

PoC 阶段优先使用 Docker Compose 或单机容器环境，减少运维复杂度。待吞吐、高可用和团队协作需求明确后，再决定是否部署到 Kubernetes。

## 5. 待验证问题

- 每个云 WAF 的日志出口、字段、API 限额和费用。
- Kafka 是否为 PoC 必需，还是后续规模化再引入。
- OpenSearch 与现有 SIEM 的职责边界。
- TheHive、Shuffle 是否引入，或先实现最小事件/审批模块。
- LLM 部署方式、数据合规要求和调用成本。
