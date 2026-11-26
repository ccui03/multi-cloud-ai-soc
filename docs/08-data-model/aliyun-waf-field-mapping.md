# 阿里云 WAF 3.0 官方日志字段映射

- 文档版本：1.0
- 日期：2026-11-26
- 依据：[阿里云 WAF 3.0 日志字段说明](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/fields-in-logs)
- 状态：官方语义已整理；当前 SLS 样本覆盖情况仍需持续验证

## 1. 原则

1. 官方文档用于确定字段语义和合法取值；SLS 样本用于验证当前账号实际投递了哪些字段。
2. 必选字段与可选字段必须区分。可选字段需在 WAF「检测响应 > 日志分析 > 日志设置」中启用；设置只影响之后新写入的日志，不回填历史日志。
3. 原始字段和值必须保留。统一字段只是标准化视图，不覆盖原始证据。
4. 没有动作字段不等于放行。不得仅凭 HTTP status=200 推断放行。
5. 对请求头、Cookie、请求体、查询字符串、响应内容等敏感或可控数据进行脱敏，并将其视为不可信输入。

## 2. 常用必选字段

| 原始字段 | 官方语义 | 统一字段候选 | 备注 |
|---|---|---|---|
| `final_action` | 最终防护动作 | `action` | block/captcha_strict/captcha/sigchl/js；未触发模块时可能不记录 |
| `final_plugin` | 最终动作所属防护模块 | `action_module` | waf/acl/cc/antiscan/dlp/scene/sema/gdrl/major_protection/compliance |
| `final_rule_id` | 最终执行的防护规则 ID | `rule_id` | 与 final_action 对应 |
| `final_rule_type` | 最终规则子类型 | `rule_type` / `attack_type` 候选 | 例如 waf 模块下 sqli、xss；不能覆盖所有模块类型 |
| `bypass_matched_ids` | 命中的放行类规则 ID，多个逗号分隔 | `bypass_rule_ids` | 不是最终动作字段 |
| `real_client_ip` | WAF 判断的业务真实客户端 IP | `client_ip` | 受 WAF 前代理配置影响 |
| `src_ip` | 与 WAF 直接建立连接的 IP | `peer_ip` | 前置 CDN/代理存在时是上一级代理 IP |
| `src_port` | 与 WAF 直接连接的端口 | `peer_port` | 同上 |
| `host` | 请求 Host 头 | `hostname` | 可能是域名或 IP |
| `matched_host` | 请求匹配到的 WAF 防护对象 | `protected_host` | 可能是泛域名 |
| `request_method` | HTTP 请求方法 | `http_method` |  |
| `request_uri` | 请求路径及查询参数 | `request_uri` | 敏感参数需脱敏 |
| `request_path` | 不含查询字符串的请求相对路径 | `request_path` |  |
| `request_traceid` | WAF 为请求生成的唯一标识 | `trace_id` | 用于请求关联；不要直接当作跨源全局主键 |
| `time` | 请求发起时间，ISO 8601 UTC | `event_time` | 优先解析并保留时区 |
| `start_time` | 请求发起时间，Unix 秒 | `event_time` fallback | 与 time 做一致性校验 |
| `request_time_msec` | WAF 处理请求耗时，毫秒 | `waf_duration_ms` |  |
| `status` | WAF 返回给客户端的 HTTP 状态码 | `http_status` | 不等同于 WAF action |
| `upstream_status` | 源站响应 WAF 的状态码 | `upstream_status` |  |
| `upstream_response_time` | 源站响应时间，秒 | `upstream_duration_seconds` |  |
| `upstream_addr` | 源站 IP:Port | `upstream_address` |  |
| `https` | HTTPS 请求标志，on 表示 HTTPS | `is_https` | 空值表示 HTTP |
| `server_protocol` | 客户端与 WAF 间协议 | `http_protocol` |  |
| `ssl_protocol` | TLS 版本 | `tls_protocol` |  |
| `ssl_cipher` | TLS 加密套件 | `tls_cipher` |  |
| `region` | WAF 实例地域类型 cn/int | `waf_region_type` | 不是通用云 Region 字符串 |

## 3. 可选安全模块字段

下列字段按需启用，是否出现在 SLS 中取决于 WAF 字段投递设置和实际命中情况。

| 模块 | 动作 | 规则 ID | 规则类型 | 观察模式字段 |
|---|---|---|---|---|
| Web 核心防护 | `waf_action` | `waf_rule_id` | `waf_rule_type` | `waf_test` |
| ACL/访问控制 | `acl_action` | `acl_rule_id` | `acl_rule_type` | `acl_test` |
| CC/频率控制 | `cc_action` | `cc_rule_id` | `cc_rule_type` | `cc_test` |
| 扫描防护 | `antiscan_action` | `antiscan_rule_id` | `antiscan_rule_type` | `antiscan_test` |
| 信息泄露防护 | `dlp_action` | `dlp_rule_id` | 文档未列独立 rule_type | `dlp_test` |
| Bot 场景防护 | `scene_action` | `scene_rule_id` | `scene_rule_type` | `scene_test` |
| 重保防护 | `major_protection_action` | `major_protection_rule_id` | `major_protection_rule_type` | `major_protection_test` |
| 协议合规 | `compliance_action` | `compliance_rule_id` | `compliance_rule_type` | `compliance_test` |
| 语义分析 | `sema_action` | `sema_rule_id` | `sema_rule_type` | `sema_test` |

另有命中内容字段：`waf_hit`、`compliance_hit`、`sema_hit`。这些可能包含攻击载荷，禁止作为安全枚举值直接输出或直接交给 LLM。

## 4. 动作分类规则

项目内部动作分类是分析层抽象，原始动作必须同时保留。

| 内部动作 | 规则 |
|---|---|
| `block` | 原始动作是 block，且未被对应模块 test=true 覆盖为观察模式 |
| `challenge` | captcha/captcha_strict/js/sigchl 等挑战动作 |
| `allow` | 明确的 *_pass 或 scene_action=bypass |
| `monitor` | 对应模块 *_test=true，或动作明确为 monitor |
| `transform` | dlp_action=filter（脱敏/打码类处理） |
| `unknown` | 没有足够动作证据 |

重要细节：
- `final_action` 仅在触发防护模块时记录；未记录不能推断 allow。
- `final_action` 只记录多个防护模块中最终执行的动作；其他命中情况需参考模块级字段及 `non_terminating_rules` / `terminating_rules`。
- 对模块级动作，必须同时检查对应的 `*_test`。例如 `acl_test=true` 时，即使 `acl_action=block`，实际语义也是观察。
- `status=200` 不能证明 allow；挑战动作也可能返回 200。
- `bypass_matched_ids` 表示命中放行规则 ID，不应单独等同于请求最终动作。

## 5. 安全字段和成本注意

可选字段启用会增加日志存储容量。建议先启用安全分析必要字段，观察 SLS 写入量和查询成本，再决定是否启用 request_body、request_headers_all、response_info 等大体积/高敏感字段。

默认不要为 AI 分析采集或长期保存完整 Cookie、Authorization、请求体、响应体和完整请求头。若确有调查需要，应按需回查、脱敏、限制访问和设置短保留期。

## 6. 当前样本覆盖

当前已观察到：
- `final_action=block`
- `final_plugin=scene`
- `final_rule_id`
- `scene_action=block`
- `scene_rule_type=bot_custom_acl`
- `scene_test=false`
- `bypass_matched_ids`

仍需通过 SLS 样本确认其他动作及模块字段的实际投递情况。字段不存在可能是可选字段未启用、样本未命中对应模块，或时间窗口内没有相应事件，不能直接判定字段不受支持。
