# WAF 日志接入设计（SLS / CLS）

- 文档版本：1.0
- 日期：2026-11-26
- 状态：接口设计基线；具体 SDK/API 参数以 Phase 0 验证为准

## 1. 目标

定义统一 Python Adapter 契约，屏蔽阿里云 SLS 与腾讯云 CLS 的认证、查询语法、分页和错误差异。上层采集服务和 Agent 不直接依赖厂商 SDK。

## 2. 设计原则

- 原始日志留在 SLS / CLS；不执行全量日志搬迁。
- 统一接口只表达通用查询语义，不暴露厂商 DSL。
- 查询必须有明确时间范围和结果限制。
- 支持分页、重试、速率控制、Checkpoint 和幂等写入。
- 历史回溯与增量采集使用独立任务，不共用推进水位。
- Adapter 首期只读，不提供封禁或修改 WAF 策略方法。

## 3. 建议目录

```text
src/
└── ingestion/
    ├── adapters/
    │   ├── base.py
    │   ├── aliyun_sls.py
    │   └── tencent_cls.py
    ├── models/
    │   ├── query.py
    │   ├── records.py
    │   └── result.py
    ├── services/
    │   ├── ingestion_service.py
    │   ├── query_planner.py
    │   └── checkpoint_service.py
    └── repositories/
        └── checkpoint_repository.py
```

## 4. 统一接口模型

### QueryRequest

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| source_id | str | 项目内数据源唯一标识 |
| start_time | datetime | 查询开始时间，统一 UTC |
| end_time | datetime | 查询结束时间，统一 UTC |
| filters | dict | 白名单字段条件，不直接传任意 DSL |
| page_size | int | 单页请求大小，受 Adapter 上限约束 |
| cursor | str / None | 不透明分页游标 |
| query_mode | enum | incremental / backfill / investigation |
| request_id | str | 查询任务/请求追踪 ID |

### FetchPage

| 字段 | 类型 | 说明 |
|---|---|---|
| records | list[RawWAFRecord] | 当前页原始记录 |
| next_cursor | str / None | 下一页不透明游标 |
| has_more | bool | 是否还有下一页 |
| source_id | str | 数据源标识 |
| request_id | str | 请求追踪 ID |
| query_start / query_end | datetime | 实际查询窗口 |
| provider_request_id | str / None | 厂商请求 ID（如有） |

### RawWAFRecord

- provider：aliyun / tencent
- source_id
- event_time（解析前可为空）
- raw：原始 JSON/dict
- source_record_id（如源端提供）
- fingerprint（项目计算的幂等键）

### Adapter 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class QueryRequest:
    source_id: str
    start_time: datetime
    end_time: datetime
    filters: dict[str, Any]
    page_size: int = 500
    cursor: str | None = None
    query_mode: str = "incremental"
    request_id: str = ""


@dataclass
class FetchPage:
    records: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool
    source_id: str
    request_id: str


class BaseWAFAdapter(ABC):
    @abstractmethod
    def health_check(self) -> bool:
        """验证凭据、权限和目标日志源可访问。"""
        raise NotImplementedError

    @abstractmethod
    def fetch_page(self, request: QueryRequest) -> FetchPage:
        """查询一页日志；cursor 对上层保持不透明。"""
        raise NotImplementedError
```

建议 Adapter 同步接口先实现，若实际 SDK 为异步或查询任务需要轮询，可在服务层统一封装 async wrapper；不要在没有验证前把接口设计复杂化。

## 5. 厂商实现职责

### AliyunSLSAdapter

负责：
- 初始化 SLS 客户端和只读认证。
- 将 QueryRequest 转换为 SLS 的时间范围与查询表达式。
- 调用查询 API，处理查询任务状态（若所选 API 采用异步查询）。
- 将 SLS 分页/offset/token 转换为不透明 cursor。
- 解析返回记录为统一 RawWAFRecord。
- 将厂商异常映射为内部异常类别。

### TencentCLSAdapter

负责：
- 初始化 CLS 客户端和只读认证。
- 将 QueryRequest 转换为 CLS 检索请求。
- 处理 CLS 分页/上下文游标。
- 将返回记录转换为统一 RawWAFRecord。
- 将厂商异常映射为内部异常类别。

注意：SLS 与 CLS 的分页机制、查询完成状态、时间精度、最大时间窗口和最大返回量可能不同。不要假设两个平台拥有相同的 cursor 语义；统一 cursor 应由 Adapter 编码并保持不透明。

## 6. 过滤条件设计

业务层传递白名单结构化条件，例如：

```json
{
  "action": ["block"],
  "source_ip": ["203.0.113.10"],
  "hostname": ["example.test"],
  "attack_type": ["SQL_INJECTION"]
}
```

Adapter 根据厂商字段映射转换为各自查询表达式。要求：
- 只允许配置过的字段名和运算符。
- 对值进行正确转义/参数化，避免查询注入。
- 不接受 LLM 生成的任意原始查询语句直接执行。
- 查询条件和转换后的查询摘要写入审计记录。
- 字段名/枚举值需根据真实日志样本校准，以上仅为接口示例。

## 7. 增量采集与 Checkpoint

Checkpoint 建议以以下组合键隔离：

`provider + account/project + region + logstore/topic + stream`

至少保存：
- source_id
- watermark_time
- last_success_at
- last_request_id
- status
- updated_at

处理流程：

1. 读取数据源 Checkpoint。
2. 计算查询区间：从 watermark 减去 overlap，到当前安全结束时间。
3. 执行查询并完整遍历所有分页。
4. 每页记录先幂等写入数据库。
5. 所有页面成功后，在事务中推进 watermark。
6. 任一页面失败则不推进 watermark，任务可重试。

建议起始轮询间隔先测试 5–15 分钟；overlap 初始可设为数分钟到十几分钟，但最终值需根据真实日志延迟分布确定。时间全部统一为 UTC，明确 start/end 是否闭区间，边界去重由 fingerprint 兜底。

## 8. 历史回溯

- 支持用户指定时间范围，初始场景可测试过去 1 天或 7 天。
- Query Planner 将长窗口切成小区间，避免单次超大查询。
- 历史任务有独立 backfill_job_id，不修改实时 Checkpoint。
- 记录总窗口、当前窗口、分页游标、处理数量和失败信息。
- 支持暂停、恢复和安全重跑。
- 对查询条数、并发、总时长和时间范围设置上限。

## 9. 重试、限流与错误模型

内部错误类别建议：
- AuthenticationError：凭据无效或签名错误，不自动无限重试。
- PermissionDenied：缺少目标日志源查询权限。
- RateLimited：触发限流，指数退避并加入随机抖动。
- QueryTimeout：查询超时，可缩小时间窗口重试。
- InvalidQuery：查询语法/字段错误，不重试，记录表达式摘要。
- CursorExpired：游标失效，从安全时间窗口重跑并依赖幂等去重。
- ProviderUnavailable：厂商服务临时不可用，有限次数退避重试。

重试次数、退避上限和并发数配置化；避免对认证/权限/语法错误重试。

## 10. 幂等与去重

优先使用源端稳定唯一 ID。若没有，计算 fingerprint：
- provider
- source_id
- event_time
- request_id（若有）
- source_ip
- hostname
- uri / uri_path
- action
- rule_id
- 对稳定原始字段做规范化哈希

PostgreSQL 对 fingerprint 建唯一约束，使用 upsert/冲突忽略。不要只使用时间戳作为唯一键。需测试同一条日志重复返回、不同日志字段相同和字段缺失的场景。

## 11. 数据处理与 AI 边界

- 源端先过滤和聚合；LLM 不接收无差别原始日志流。
- 对高频源 IP、规则、域名、URI 做 SQL/日志服务聚合，输出统计摘要。
- 触发调查后按事件条件回查必要明细。
- 对模型隐藏 Cookie、Authorization、敏感查询参数和个人信息。
- 日志文本作为不可信证据，绝不作为 Agent 指令。
- Agent 工具只暴露预定义查询参数，不暴露任意 SDK client 或云凭据。

## 12. 配置示例（不含真实密钥）

```yaml
sources:
  - source_id: aliyun-waf-prod
    provider: aliyun_sls
    region: cn-hangzhou
    project: <sls-project>
    logstore: <waf-logstore>
    credential_ref: ALIYUN_WAF_READONLY

  - source_id: tencent-waf-prod
    provider: tencent_cls
    region: ap-guangzhou
    topic_id: <cls-topic-id>
    credential_ref: TENCENT_WAF_READONLY

ingestion:
  poll_interval_seconds: 600
  overlap_seconds: 600
  default_page_size: 500
  max_backfill_days: 7
  max_concurrent_queries: 2
```

配置中的 region、字段和参数仅为示例；真实值应来自用户环境和 SDK/API 验证。密钥只能通过 Secret 或环境变量注入，不能写入 YAML 或 Git。

## 13. 测试计划

- Adapter contract tests：两个 Adapter 满足同一接口。
- Mock tests：分页、空结果、限流、超时、权限错误、游标过期。
- Integration tests：使用脱敏真实数据验证查询语法与字段。
- Checkpoint tests：失败不推进、成功后推进、历史任务不影响增量水位。
- Idempotency tests：重叠窗口重复查询无重复事件。
- Security tests：过滤字段白名单、查询值转义、凭据脱敏、日志 Prompt Injection 隔离。

## 14. Phase 0 必须验证的云服务细节

本设计不预设两家服务的具体 API 参数。编码前分别确认：
1. 官方 SDK/API 名称和版本。
2. 查询时间范围与时间精度。
3. 分页参数及游标生命周期。
4. 查询是否同步或异步。
5. 单次返回条数、最大查询窗口、并发和限流。
6. 字段索引要求与查询成本。
7. WAF 日志的 action、attack type、rule、source IP 等真实字段。
8. 只读 RAM/CAM 权限范围。
