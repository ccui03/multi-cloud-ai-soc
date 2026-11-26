# 需求规格说明（Requirements）

- 版本：1.1
- 状态：PoC 基线
- 日期：2026-11-26

## 1. 用户角色

- 安全分析人员：查看事件、调查证据、生成报告。
- 项目管理员：配置数据源、查询参数和运行设置。
- 审计人员：查看查询、分析和审批记录。

## 2. 范围与约束

- 首期只支持阿里云 WAF → SLS、腾讯云 WAF → CLS。
- 不集成 QRadar，不部署独立 SIEM。
- 原始日志默认留在 SLS / CLS；AI SOC 不执行全量日志搬迁。
- 首期小资源 PoC，优先单机 Docker Compose。
- 首期只读分析；云端写操作不在默认范围内。

## 3. 功能需求

| ID | 功能 | 描述 | 优先级 |
|---|---|---|---|
| FR-001 | 数据源配置 | 配置 provider、endpoint、project/topic/logstore、region 和凭据引用 | P0 |
| FR-002 | 连接检查 | 检查 API 连通性、权限和数据源可查询性 | P0 |
| FR-003 | 统一查询请求 | 使用统一时间范围、过滤条件、分页参数 | P0 |
| FR-004 | SLS Adapter | 实现 SLS 查询、分页和错误映射 | P0 |
| FR-005 | CLS Adapter | 实现 CLS 查询、分页和错误映射 | P0 |
| FR-006 | 增量读取 | 按数据源独立 Checkpoint 查询新日志 | P0 |
| FR-007 | 历史回溯 | 支持指定时间段（例如 1 天/7 天）回溯查询 | P0 |
| FR-008 | 断点恢复 | 保存分页游标/时间水位，失败后可恢复或安全重跑 | P0 |
| FR-009 | 重试与限速 | 对超时、限流和临时错误退避重试 | P0 |
| FR-010 | 去重 | 对重叠窗口和重复 API 结果幂等处理 | P0 |
| FR-011 | 事件标准化 | 统一关键字段并保留 raw_event | P0 |
| FR-012 | 源端过滤/聚合 | 尽可能将过滤、统计下推至 SLS / CLS | P1 |
| FR-013 | 安全事件检索 | 按时间、IP、域名、动作、规则等查询标准化事件 | P1 |
| FR-014 | AI 分诊 | 对筛选后的告警/事件摘要、分类和风险说明 | P1 |
| FR-015 | 攻击调查 | 按 IP、域名、URI、规则和时间范围回查两个云日志源 | P1 |
| FR-016 | 报告生成 | 输出时间线、证据、结论、不确定性和建议 | P1 |
| FR-017 | 审计 | 记录查询范围、结果摘要、Agent 工具调用和模型输出 | P1 |
| FR-018 | 响应审批 | 为后续云端写操作预留审批接口 | P2 |
| FR-019 | 多云扩展 | 后续增加其他厂商 Adapter | P2 |

## 4. 查询与采集要求

### 4.1 增量采集
- 初始轮询间隔建议从 5–15 分钟开始测试，不作为固定 SLA。
- 每个 provider/account/region/logstore（或 CLS topic）独立维护水位。
- 使用重叠时间窗口容忍日志到达延迟；重叠长度需通过实际日志延迟测量确定。
- Checkpoint 只能在当前窗口所有分页成功且结果已持久化后推进。
- 查询窗口采用明确的时间边界约定，避免边界事件遗漏。

### 4.2 历史回溯
- 支持用户指定 start_time/end_time。
- 支持 1 天、7 天等窗口，但必须按时间切片和分页执行。
- 查询应有最大时间范围、最大结果数、超时和并发限制。
- 历史回溯与常规增量任务使用不同任务 ID，避免互相推进 Checkpoint。

### 4.3 过滤和聚合
- 过滤表达式由 Adapter 转换为厂商查询语法；不得将未经校验的用户字符串直接拼接到查询语句。
- 常规分析优先查询拦截、告警或规则命中事件（具体字段和值以真实日志样本确认）。
- 正常访问日志优先在源端做计数、Top-N、时间序列或异常聚合；调查时再按需获取明细。
- 必须保留查询条件和时间范围，以便复现分析。

## 5. 统一事件模型（初步）

建议参考 OCSF，但 PoC 先实现轻量内部模型：

- identity：event_id、event_fingerprint、provider、account_id、region、source_name
- time：event_time、ingest_time、query_time
- network：source_ip、source_port、destination_ip、destination_port
- http：hostname、uri、uri_path、http_method、http_status、user_agent、request_id
- waf：action、rule_id、rule_name、severity、attack_type
- metadata：raw_event、schema_version、parser_version、source_record_id

字段为可选字段，实际映射必须基于 SLS / CLS 脱敏样例验证。原始字段不得因映射失败而丢弃。

## 6. 非功能需求

- 安全：只读最小权限、凭据不入库明文、不提交 Git。
- 可靠性：重试、分页、Checkpoint、幂等写入和可恢复任务。
- 成本：时间范围限制、源端过滤、聚合优先、LLM 输入预算。
- 可观测性：记录调用耗时、返回条数、错误码、重试次数和 Checkpoint。
- 可解释性：AI 结论必须引用事件 ID/查询证据；无证据时明确说明。
- 可维护性：厂商 SDK 细节不得泄漏到业务服务和 Agent 层。

## 7. 安全要求

- 日志中的 URL、User-Agent、Header、Cookie 和请求参数均为不可信内容。
- LLM 不得把日志文本解释为系统指令或工具授权。
- 首期 Adapter 仅提供只读查询工具。
- 云凭据通过 Secret/环境变量注入，日志中不得输出凭据。
- 数据脱敏后再传给外部模型；敏感字段应支持屏蔽。

## 8. 验收原则

P0 验收需覆盖：连接检查、时间范围查询、多页结果、限流/超时、断点恢复、重复数据、迟到数据、字段映射和原始字段保留。测试使用脱敏样本和模拟 API 响应。
