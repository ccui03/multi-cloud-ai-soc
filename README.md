# Multi-Cloud AI SOC

面向多云、多厂商安全数据源的 AI 安全运营平台。首期以阿里云 WAF（SLS）和腾讯云 WAF（CLS）为切入点，建设可复用的数据接入、Schema 发现、字段治理、统一事件、检测关联和 AI 调查能力。

> 项目定位：多厂商 AI SOC，首期 WAF PoC  
> 规划版本：Project Plan v2.0  
> 当前状态：优先完善产品与项目计划，暂缓无计划依据的新增代码开发  
> 更新时间：2026-11-26

## 1. 产品目标

长期建设厂商可扩展的安全运营平台。新增厂商时主要扩展 Provider Adapter、Capability 声明和 Field Registry；Schema Profiler、Normalizer、检测关联和 Agent 工作流尽可能复用。

首期只承诺阿里云 WAF/SLS 和腾讯云 WAF/CLS。其他云厂商、商业 WAF 和本地 WAF 属于后续候选，按业务场景、数据可用性和成本排序接入。

## 2. 已确认约束

| 项目 | 决策 |
|---|---|
| 首期数据源 | 阿里云 WAF → SLS；腾讯云 WAF → CLS |
| 长期方向 | 多厂商 WAF，后续评估其他安全数据源 |
| SIEM | 不复用 QRadar；PoC 不部署独立传统 SIEM |
| 原始日志 | 默认留在厂商日志服务，不全量搬迁 |
| 接入方式 | Python Provider Adapter + 官方 SDK/API |
| Schema | 通用 Profiler + 厂商 Field Registry + 版本化 Normalizer |
| 数据库 | PostgreSQL + JSONB 起步 |
| Agent | LangGraph；只处理有限、脱敏、证据化上下文 |
| 部署 | 小规模低成本 PoC，Docker Compose 起步 |
| 响应 | 首期只读；后续写操作必须策略校验和人工审批 |

## 3. 项目路线

详细计划见 [Project Roadmap](docs/05-development-plan/roadmap.md)。

| 阶段 | 目标 |
|---|---|
| Phase 0 | 产品与需求规划 |
| Phase 1 | 数据源与能力验证 |
| Phase 2 | 多厂商接入基础 |
| Phase 3 | Schema 与标准化平台 |
| Phase 4 | 检测与关联分析 |
| Phase 5 | AI 调查与报告 |
| Phase 6 | SOC 工作台与运营闭环 |
| Phase 7 | 响应与企业化演进 |

## 4. 核心架构

```text
WAF Vendors / Log Sources
        |
Provider Adapters + Capability Registry
        |
Ingestion / Query Planner
        |
Schema Discovery + Field Registry
        |
Normalizer (Core Event + Vendor Extension)
        |
Detection + Correlation + Event/Case Service
        |
FastAPI / SOC UI
        |
LangGraph Triage / Investigation / Reporting
        |
Human Approval (future response phase)
```

## 5. 当前技术验证基础

- 项目代码骨架及部分 Adapter/接入模块已存在；代码存在不代表真实数据源验收通过。
- 阿里云 SLS 近期 GetLogs 联调返回 HTTP 403，需在 M1 核查 Region、Project/Logstore、RAM 权限和请求配置。
- 腾讯云 CLS 尚未进入本轮真实云端联调验证。
- PostgreSQL 持久化、Checkpoint 和基础增量采集模块已提交。
- 通用 Schema Profiler 第一版已提交，尚需执行测试和真实样本验证。
- 正式统一安全事件模型、完整 Field Registry 治理、检测关联和 Agent 工作流仍属于规划/待实现内容。

注意：代码存在不代表对应能力已完成验收。阶段验收以 Roadmap 中 Exit Criteria 和测试记录为准。

## 6. 项目文档

- [项目章程](docs/01-project-planning/project-charter.md)
- [M0 规划与设计基线（范围、场景、领域对象、安全与验收）](docs/01-project-planning/m0-baseline.md)
- [需求规格](docs/02-requirements/requirements.md)
- [总体架构](docs/03-architecture/architecture.md)
- [技术选型](docs/04-technology-selection/technology-stack.md)
- [项目路线图](docs/05-development-plan/roadmap.md)
- [项目执行计划（Milestones、Issues、Project Board）](docs/05-development-plan/project-execution-plan.md)
- [AI Agent 设计](docs/06-ai-agent/agent-design.md)
- [日志接入设计](docs/07-api-design/log-ingestion-design.md)
- [决策记录](docs/09-records/decision-log.md)

## 7. 开发与安全原则

- 先确定业务场景和验收标准，再开发功能。
- Schema 自动分析负责发现结构，不负责猜测安全语义。
- 未知字段/枚举保留并标记 unknown，不擅自推断 allow/block。
- 标准化事件保留原始来源、字段扩展和解析版本。
- 先规则、统计和查询，再调用 LLM。
- URL、User-Agent、Header、Cookie、请求参数和响应片段均是不可信数据。
- Agent 不持有云凭据，不拥有默认写权限。
- 记录查询成本、数据量、存储增长和 LLM Token 消耗。
- 不提交密钥、Token 或未脱敏真实日志。

本仓库已有代码和本地运行说明以各模块文档为准；当前阶段优先做规划和设计评审。


## 8. 核心业务流程（已确认）

平台采用分层攻击研判：
1. WAF 日志标准化为统一事件。
2. 确定性检测产生告警信号。
3. 相似告警聚合为 Alert Group。
4. 一个或多个告警组关联形成 Security Incident。
5. AI 基于 Evidence Pack 进行分诊、调查和研判，必要时下钻查询少量原始日志。
6. 输出威胁结论、证据、置信度、反证和 WAF 策略优化建议。
7. 安全人员人工审核并在厂商控制台/既有变更流程中执行；平台记录反馈和效果。

当前策略边界：**AI 只提供建议，不自动封禁 IP、不自动修改 WAF 策略、不执行云端写操作。**

核心研判结论包括真实恶意、疑似恶意、疑似正常业务、已确认正常业务和证据不足。详细场景与验收要求见 [Use Cases](docs/02-requirements/use-cases.md)。


## 9. Web SOC 管理工作台

MVP 不以完整 SOC 工作台为目标。首期 UI 只实现日志查询、日志详情、AI 分析面板、分析结果/证据定位和必要的任务状态；复杂 Dashboard、完整告警/案件中心、策略审批和报表中心暂缓。

UI 与 AI 共用后端权限和查询服务。AI 对话仅通过受控只读工具访问日志和事件；WAF 策略仍由人工在外部控制台或变更流程执行。


## 10. UI 交互模式

保留“独立页面 + 上下文联动”和右侧 AI 面板的交互方向；MVP 先实现从日志查询/详情进入 AI 分析、查看结果并定位证据的最小闭环。独立 AI 页面和复杂会话管理按实际需要后续实现。


## 11. MVP 产品重点：简易 UI + AI 威胁分析

第一版不建设完整传统 SOC 工作台，优先验证 AI 读取和分析 WAF 日志、发现威胁的核心价值。

最小 UI 包含：
- **日志查询**：选择数据源、时间范围和常用条件，分页查看日志。
- **日志详情**：查看标准化字段、必要原始字段和来源。
- **AI 分析**：对选中日志或受控查询结果发起分析，并支持多轮追问。
- **分析结果**：展示威胁类型、结论、严重性、置信度、证据、反证和建议。
- **简易总览**：显示数据源状态和威胁分析概况（可后续补充）。

保留已确定的“独立页面 + 上下文联动”和右侧可展开 AI 面板，但第一版只实现日志到 AI 分析再到证据定位的最小交互闭环。复杂 Dashboard、工单、报表、策略审批和高级管理功能暂缓。

核心流程为：日志查询 → 统计/规则预筛选 → AI 分析聚合行为 → 按需下钻原始日志 → 输出带证据的威胁判断。不要把全部原始日志无差别发送给 LLM。AI 必须区分事实、推断和未知，明确查询范围、样本数量和数据截断情况；证据不足时允许输出 Inconclusive。AI 首期只读，不自动封禁或修改 WAF 策略。

MVP 成功标准是代表性攻击样本能被正确识别、判断有证据可追溯、误报与不确定性可度量、单次分析成本可控，而不是 UI 页面数量。

## 12. 核心分析引擎技术设计

核心技术基线见 [核心分析引擎技术设计](docs/07-core-analysis-engine/core-analysis-engine-design.md)，覆盖日志预筛选、攻击行为聚合、Evidence Pack、LangGraph 研判节点/只读工具、威胁判断标准及准确率评估。该文档为规划基线，阈值、时间窗口、抽样规模和准确率目标均须经真实日志与人工标注数据验证；当前不代表这些能力已全部实现。


## 13. M0 规划与设计基线

M0 的统一评审入口为 [M0 规划与设计基线](docs/01-project-planning/m0-baseline.md)。历史需求与当前 MVP 范围存在冲突时，以该文件中已确认的决策为准；标记 Proposed 的内容须经项目负责人确认后生效。
