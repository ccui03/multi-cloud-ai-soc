# Multi-Cloud AI SOC

面向多云环境的 AI 驱动安全运营平台。首期聚焦阿里云 WAF（SLS）与腾讯云 WAF（CLS），通过源端查询、轻量 Python Adapter 和 LangGraph 工作流，实现安全日志统一分析、攻击调查与报告生成。

> 项目状态：PoC Adapter 首版已提交，等待真实云账号联调  
> 当前文档版本：Project Baseline v1.1  
> 更新时间：2026-11-26  
> 文档语言：中文（技术名词保留英文）

## 1. 已确认的项目约束

| 项目 | 当前决定 |
|---|---|
| 首期数据源 | 阿里云 WAF → SLS；腾讯云 WAF → CLS |
| SIEM | 不复用 QRadar；PoC 不单独部署传统 SIEM |
| 日志获取 | 通过 SLS / CLS API 查询，不全量搬迁原始日志 |
| 分析位置 | 优先在 SLS / CLS 过滤、查询和聚合；AI SOC 负责跨云分析 |
| 部署规模 | 小规模、低成本 PoC |
| 初期部署 | Docker Compose / 单机容器优先 |
| 响应能力 | 首期以只读分析和处置建议为主；写操作默认关闭或人工审批 |

## 2. 项目目标

1. 统一查询阿里云 SLS 与腾讯云 CLS 中的 WAF 日志。
2. 建立厂商隔离的 Python Adapter 接口。
3. 支持增量采集、历史回溯、分页、重试、Checkpoint 和幂等去重。
4. 建立统一安全事件模型，同时保留原始厂商字段。
5. 使用确定性查询、聚合和规则筛选日志，避免把海量原始日志直接发送给 LLM。
6. 使用 LangGraph 实现告警分诊、攻击调查和报告生成。
7. 保留证据、分析过程和操作审计。

## 3. 首期范围

### In scope
- 阿里云 SLS 与腾讯云 CLS 的只读日志查询 Adapter
- 源端时间过滤、关键词/条件过滤和聚合查询（以实际服务能力验证为准）
- 按时间窗口增量查询和按需历史回溯
- 统一事件字段映射、原始事件保留
- PostgreSQL 保存 Checkpoint、标准化事件、分析结果和审计元数据
- LangGraph 安全分析 PoC
- Docker Compose 本地/单机部署

### Out of scope（首期）
- QRadar 集成或替换
- Kafka、OpenSearch、TheHive、Shuffle 等额外基础设施的强制部署
- 将全部原始 WAF 日志复制到 AI SOC
- 无审批的自动封禁或 WAF 策略修改
- 多云全面覆盖和生产级高可用
- 面向公网的多租户 SaaS

## 4. 初步技术基线

| 层次 | 首期方案 | 备注 |
|---|---|---|
| 云日志源 | Alibaba Cloud SLS / Tencent Cloud CLS | 原始日志留在源端 |
| 数据接入 | Python Adapter + 官方 SDK/API | 分别封装厂商查询差异 |
| 查询调度 | Python 定时任务/后台任务 | 初期不引入 Kafka |
| 统一事件模型 | 自定义轻量模型，参考 OCSF | 保留 raw_event 与 schema_version |
| 业务存储 | PostgreSQL + JSONB | Checkpoint、事件、分析结果 |
| API | Python + FastAPI | 数据源、查询、事件和分析接口 |
| Agent | LangGraph | 只通过受控只读工具访问日志 |
| 前端 | React（后续阶段） | PoC 可先用 API/简单页面验证 |
| 部署 | Docker Compose | 低资源单机 PoC |

OpenSearch、Kafka、Redis、TheHive、MISP、Shuffle 均作为后续候选，只有出现明确容量或功能需求时再引入。

## 5. 推荐数据流

```text
Alibaba WAF -> SLS -----> AliyunSLSAdapter --+
                                             |
                                             +--> Ingestion Service
                                             |       |
Tencent WAF -> CLS ----> TencentCLSAdapter -+       v
                                               Normalize / Deduplicate
                                                       |
                                      +----------------+----------------+
                                      |                                 |
                               PostgreSQL                     Query back to SLS/CLS
                         (checkpoint/events/results)          (investigation context)
                                      |
                                      v
                              FastAPI / LangGraph
                                      |
                          Triage / Investigation / Report
```

AI SOC 不必保存所有原始访问日志。优先由 SLS / CLS 执行时间范围、字段条件和聚合查询；将命中事件、必要上下文和聚合结果送入统一分析流程。调查时再按 IP、域名、URI、规则和时间范围回查源日志。

## 6. 仓库结构

```text
.
├── README.md
├── docs/
│   ├── 01-project-planning/
│   ├── 02-requirements/
│   ├── 03-architecture/
│   ├── 04-technology-selection/
│   ├── 05-development-plan/
│   ├── 06-ai-agent/
│   ├── 07-api-design/
│   ├── 08-deployment/
│   └── 09-records/
├── src/
│   ├── ingestion/
│   ├── api/
│   └── agents/
├── tests/
├── config/
└── docker/
```

## 7. 开发与安全原则

- 源端优先：尽量在 SLS / CLS 查询端过滤和聚合，避免无差别下载。
- 游标/时间窗口：记录每个数据源独立的 Checkpoint；使用重叠窗口容忍延迟日志。
- 幂等处理：至少一次读取，依靠稳定事件键/哈希去重；不要假设 API 返回天然 exactly-once。
- 规则优先：先过滤、聚合和关联，再让 LLM 分析有限上下文。
- 最小权限：云凭据只授予目标 Project/Logstore 或 Topic 的只读查询权限。
- 日志不可信：URL、User-Agent、Header、请求参数都视为不可信数据，不得作为 Agent 指令。
- 人工审批：首期不执行自动封禁；写操作必须经过策略校验和人工批准。
- 可审计：记录查询范围、过滤条件、数据源、事件证据、模型输出和审批/执行结果。
- 不提交密钥、Token、真实客户数据或未脱敏日志。

## 8. 项目阶段

| 阶段 | 目标 | 主要交付物 |
|---|---|---|
| Phase 0 | 需求和数据源确认 | 样例日志、权限清单、查询验证 |
| Phase 1 | SLS / CLS Adapter | 统一接口、分页、Checkpoint、测试 |
| Phase 2 | 事件标准化与检测 | 统一模型、去重、聚合与查询 |
| Phase 3 | AI 调查 | LangGraph 工作流、证据化报告 |
| Phase 4 | 审批与响应 PoC | 只读工具、审批门、审计 |
| Phase 5 | 平台化 | UI、监控、部署和性能验证 |

## 9. 本地运行 Adapter

建议使用 Python 3.10+。在仓库根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config/.env.aliyun.example .env.aliyun
Copy-Item config/.env.tencent.example .env.tencent
```

分别编辑两个 .env 文件，填写只读凭据、SLS Project/Logstore 或 CLS Topic ID。腾讯 CLS 的 `TENCENT_CLS_ENDPOINT` 使用 CLS 云 API Endpoint（通常为 `cls.tencentcloudapi.com`），Region 单独填写，例如 `ap-guangzhou`；不要填写 CLS 日志上传域名 `*.cls.tencentcs.com`。

先运行本地契约测试：

```powershell
pytest -q
```

再单独验证云端查询（默认查询最近 15 分钟、每次最多返回 5 条，不会打印日志正文或密钥）：

```powershell
python -m scripts.check_cloud_adapters --provider aliyun
python -m scripts.check_cloud_adapters --provider tencent
```

注意：Adapter 首版已经实现，但必须使用真实账号验证 Endpoint、CAM/RAM 权限、WAF 字段名和查询语法后，才能认为云端联调通过。当前过滤字段映射是可调整的初始值，不代表已验证适用于你的 WAF 日志。

## 10. 文档维护

- 新想法先记录为 Proposal，不自动成为正式需求。
- 确认的范围和约束更新到项目章程与需求文档。
- 架构决策记录在 `docs/09-records/decision-log.md`。
- 采集接口和查询约定记录在 `docs/07-api-design/log-ingestion-design.md`。
- 计划变更同步更新 Roadmap 和 Change Log。
- 每次文档变更应通过 Git commit 保留历史。


## 11. PoC 云凭据配置

SLS 与 CLS 使用独立环境变量文件：

- 阿里云模板：`config/.env.aliyun.example` → 本地复制为根目录 `.env.aliyun`
- 腾讯云模板：`config/.env.tencent.example` → 本地复制为根目录 `.env.tencent`

```bash
cp config/.env.aliyun.example .env.aliyun
cp config/.env.tencent.example .env.tencent
```

在本地分别填写凭据和日志源信息。真实 `.env.aliyun` / `.env.tencent` 已由 `.gitignore` 忽略，不得提交。模板文件只包含空值。Adapter 应显式加载各自文件，不要让两个 Adapter 共用一个默认 `.env`。详细说明见 [日志接入设计](docs/07-api-design/log-ingestion-design.md#16-独立环境变量文件poc)。
