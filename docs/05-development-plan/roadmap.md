# 开发路线图（Roadmap）

- 版本：1.1
- 日期：2026-11-26
- 原则：先验证日志 API 和真实样本，再实现统一采集；按 PoC 结果调整周期。

## 1. 阶段规划

| 阶段 | 目标 | 主要任务 | 交付物 |
|---|---|---|---|
| Phase 0 | 数据源验证 | 确认 SLS/CLS Project、Logstore/Topic、字段、索引、权限、API 限额 | 脱敏样本、字段字典、API 验证记录 |
| Phase 1A | Adapter 基础 | QueryRequest、FetchPage、BaseWAFAdapter、配置模型 | 统一接口与单元测试 |
| Phase 1B | SLS Adapter | 认证、查询、过滤、分页、错误映射 | 可运行 AliyunSLSAdapter |
| Phase 1C | CLS Adapter | 认证、查询、过滤、分页、错误映射 | 可运行 TencentCLSAdapter |
| Phase 1D | 可靠采集 | 增量窗口、Checkpoint、重试、限速、去重、迟到日志 | Ingestion Service |
| Phase 1E | 统一模型 | 字段映射、raw_event 保留、版本管理 | Normalized WAF Event |
| Phase 2 | 检测与调查 API | 聚合、规则、事件查询和关联 | 基础安全事件服务 |
| Phase 3 | AI 分析 | LangGraph 分诊、调查、证据化报告 | AI Investigation PoC |
| Phase 4 | 运营闭环 | 审批接口、审计和只读/模拟响应 | 安全响应演示 |
| Phase 5 | 平台化 | UI、部署、监控、压力与成本测试 | 端到端 PoC |

## 2. Phase 0 任务清单

- [ ] 确认阿里云 SLS Project、Logstore、Region 和查询权限。
- [ ] 确认腾讯云 CLS Topic、Region 和查询权限。
- [ ] 获取两家 WAF 各 100–500 条脱敏日志样本。
- [ ] 整理两种日志的字段字典和时间字段。
- [ ] 分别验证 API 查询、过滤、分页和时间范围边界。
- [ ] 测量日志延迟、日均量、查询耗时和调用限制。
- [ ] 确认运行环境和 PoC 预算。

## 3. Phase 1 验收标准

- 两个 Adapter 遵循相同接口。
- 可按明确的 start_time/end_time 查询。
- 多页结果无遗漏；失败后可从安全位置恢复。
- 限流/超时会退避重试，不无限重试。
- Checkpoint 按数据源隔离，历史回溯不推进增量水位。
- 使用重叠窗口补采迟到日志，并通过幂等键去重。
- 原始字段保留，映射失败可追踪。
- 输出查询耗时、条数、错误和成本相关指标。

## 4. 建议首批 GitHub Issues

1. 验证 SLS WAF 日志查询 API 与权限。
2. 验证 CLS WAF 日志查询 API 与权限。
3. 建立脱敏 WAF 日志样本与字段字典。
4. 定义统一 QueryRequest / FetchPage / FetchResult。
5. 实现 BaseWAFAdapter 与 HealthStatus。
6. 实现 AliyunSLSAdapter。
7. 实现 TencentCLSAdapter。
8. 实现 PostgreSQL Checkpoint Repository。
9. 实现增量窗口、重试、分页恢复与幂等去重。
10. 建立标准化事件模型和契约测试。

## 5. 里程碑

- M0：两端 API 均能只读查询真实脱敏日志。
- M1：统一 Adapter 完成双云查询。
- M2：增量采集与历史回溯可恢复、可审计。
- M3：标准化事件可用于跨云检索与关联。
- M4：LangGraph 能基于真实证据生成调查结果。
