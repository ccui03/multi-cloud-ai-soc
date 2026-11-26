# 核心分析引擎技术设计（Core Analysis Engine）

- 版本：1.0（规划基线）
- 日期：2026-11-26
- 状态：Proposed / 待真实日志验证
- 适用范围：首期阿里云 WAF（SLS）与腾讯云 WAF（CLS）
- 实施原则：先完善设计与验收标准；本文件不代表相关能力已经开发或验收。

## 1. 目标与设计原则

本设计定义从 WAF 原始日志到可审计 AI 威胁判断的核心分析链路：

Provider Query → Normalize → Prefilter → Behavior Aggregation → Evidence Pack → LangGraph Investigation → Verdict & Evaluation。

核心目标不是把所有日志交给 LLM，而是通过可解释、可重复的确定性处理，找到值得调查的行为对象，再让 AI 在有限证据和受控工具范围内完成假设分析。

设计原则：

1. **确定性优先**：去重、字段标准化、规则检测、统计聚合和预算控制由普通程序完成；LLM 不承担海量日志扫描。
2. **行为而非孤立日志**：主要研判对象是 Alert Group / Incident Candidate；单条事件是证据，不是默认的 AI 调用单位。
3. **厂商中立**：检测和聚合只消费统一事件及语义注册信息；厂商差异保留在 Adapter、Capability、Field Registry 和映射版本。
4. **证据优先**：AI 结论必须引用 Evidence Pack 中的证据 ID；缺少证据时允许 inconclusive。
5. **可追溯、可复现**：记录查询范围、过滤规则版本、聚合版本、抽样方法、字段映射版本、模型和提示版本。
6. **成本受控**：源端过滤优先；设置查询量、结果数、Token 和单任务/每日预算；没有候选时不调用 LLM。
7. **安全只读**：首期 Agent 只调用受控只读工具，不持有云凭据，不执行 WAF 封禁或策略写入。
8. **渐进演进**：PoC 先采用 PostgreSQL、Python 和轻量 Worker；只有容量数据证明必要时才引入消息队列、专用分析库或复杂聚类系统。

## 2. 核心处理对象与数据流

### 2.1 处理对象

| 对象 | 定义 | 主要用途 |
|---|---|---|
| Normalized Event | 一条标准化后的来源事实，含核心字段、扩展字段和 provenance | 检测与证据基础 |
| Detection Signal | 规则或统计检测产生的信号，含 detector、reason、severity、版本 | 表达单项可解释发现 |
| Alert Group | 在有限窗口和相似条件下归并的信号/事件集合 | 降噪、行为摘要 |
| Incident Candidate | 一个或多个 Alert Group 形成的待调查活动候选 | AI 主要研判对象 |
| Evidence Pack | 对候选对象的有限、结构化、可追溯证据集合 | LangGraph 输入 |
| Investigation | 一次可审计的 AI 调查执行及其工具调用、版本和结果 | 复现与评估 |
| Verdict | 对行为性质、严重性、置信度和未知项的结构化结论 | 展示、复核和指标统计 |

### 2.2 统一链路

1. Provider Adapter 按时间、字段和预算从 SLS/CLS 查询。
2. Normalizer 依据已确认的 Field Registry 生成统一事件；未知语义保持 unknown。
3. Fingerprint 去重并记录重复计数和来源。
4. Prefilter 执行基础过滤、确定性规则和统计异常检测。
5. Detection Signal 进入时间窗口和多维行为聚合。
6. 聚合结果根据风险和证据充分性形成 Incident Candidate。
7. Evidence Pack Builder 生成证据包；必要时通过受控工具按需补充有限日志。
8. LangGraph 执行假设、证据、反证和分类流程。
9. 保存 Verdict、证据引用、成本、版本和人工反馈。

手动分析和定时自动分析必须共用以上链路及数据契约，仅触发来源和查询范围不同。

## 3. 日志预筛选（Prefilter）

### 3.1 三层处理

**Layer A：基础数据质量与去重**
- 校验事件时间、数据源、必要标识和解析状态。
- 使用供应商稳定事件 ID（若存在）优先去重；否则使用规范化字段计算 Fingerprint。
- 记录 malformed、missing、duplicate 等质量状态，不静默丢弃。
- 仅过滤经过验证的健康检查、内部监控或明确范围外流量；白名单必须有来源、责任人、有效期和审计记录。
- 不得仅凭 HTTP 200、没有规则命中或 final_action 缺失将事件认定为正常。

**Layer B：确定性安全检测**
首期候选检测类别：
- SQL Injection、XSS、命令注入、路径穿越和敏感文件探测；
- 扫描/目录枚举、短时间大量不同 URI；
- 高频异常访问、认证入口异常尝试（仅在字段支持时）；
- WAF 规则命中、模块动作、最终动作和观察/测试模式的语义组合。

规则必须声明适用日志类型、所需字段、字段语义来源、规则版本、严重性、例外条件和测试样本。对未知字段或未确认枚举不作安全语义推断。供应商规则命中与本平台自定义特征检测分别记录。

**Layer C：统计异常**
PoC 优先采用可解释统计：
- Sliding Window：请求量、命中数、独立 URI 数、独立目标数；
- Rate of Change：与相邻窗口相比的增长幅度；
- Baseline Comparison：与同数据源/Host/时段历史基线比较；
- Robust Deviation：在样本量满足要求时评估 MAD；Z-Score 仅作为基线较稳定时的简单选项；
- Cardinality / Entropy：URI、User-Agent 或目标分布变化，须有足够样本且字段可信。

PoC 不以训练深度学习模型为前置条件。统计特征应保留样本量、基线窗口、缺失率和计算版本。

### 3.2 风险评分

可建立可解释的 0–100 候选排序分数，初始维度包括：
- 规则/检测信号强度；
- 请求频率和变化率；
- URI/目标多样性；
- WAF 处置语义（仅使用已确认字段）；
- 历史上下文和跨行为关联。

评分是排序与触发策略，不等于攻击概率，也不等于模型置信度。各特征应分别保存，便于解释与后续校准。初始权重和阈值为 Proposed，必须用标注样本校准；不得把示例阈值写成上线承诺。

### 3.3 预筛选输出

每个 Detection Signal 至少记录：
- signal_id、event_ref / source_ref；
- detector_id、detector_type、rule_version；
- observed_features、reason、severity；
- confidence_basis（若有）；
- required_fields、missing_fields；
- created_at、provider/source；
- exclusion/allowlist 命中及其依据（如适用）。

预筛选必须评估恶意行为召回率和过滤比例，避免高过滤率掩盖漏报。

## 4. 攻击行为聚合（Behavior Aggregation）

### 4.1 分层聚合模型

**A. 事件去重**：去除同一来源记录的重复投递，不把相似请求误当成同一事件。

**B. Alert Group 行为聚合**：按时间窗口和多个特征组织相似 Detection Signal / Event。

**C. Incident Candidate 关联**：将不同 Alert Group 按明确关系连接，形成更高层活动候选。跨 IP、跨 Host、跨云关联必须提供额外依据，不因单一字段相同就自动合并。

### 4.2 聚合维度

建议可配置的维度：
- source_ip（必须标记其语义来源及代理/CDN/NAT 风险）；
- target_host / site / source_id；
- URI template 或路径特征（不得把原始参数全文作为聚合键）；
- attack_type / detector_id / vendor_rule_id；
- HTTP method；
- User-Agent 或客户端指纹（仅作为辅助，需注意可伪造和缺失）；
- request_id / session 等稳定关联 ID（仅当来源确实提供）；
- event_time window。

不要将 source IP 作为唯一聚合键。NAT、代理、CDN、共享出口、扫描器和动态 IP 都可能导致错误关联。

### 4.3 时间窗口

PoC 可测试 1 分钟、5 分钟、15 分钟和 1 小时等窗口，用于不同时间尺度的请求速率、扫描和行为序列分析。窗口长度、滑动步长、迟到事件容忍和窗口重叠均为配置项，最终值由真实日志到达延迟、攻击节奏、查询成本和误合并/漏合并评估确定。

事件时间与采集时间应分别保留。迟到日志可进入允许的重算/修订流程；不得因为 checkpoint 前移而无声丢失。

### 4.4 聚合算法建议

PoC 默认：
1. Fingerprint 幂等去重；
2. 按可配置时间窗口进行多维分组；
3. 计算每组请求量、独立 IP/URI/Host 数、攻击类型分布、规则分布、动作分布和时间趋势；
4. 使用确定性相似条件生成候选关联边；
5. 以关联边及其原因形成 Incident Candidate。

关联条件应分级：
- 强关联：稳定 request/session ID、可信唯一事件关联标识；
- 中关联：同一目标、相近时间、相同攻击类型/路径模板和相似请求特征的组合；
- 弱关联：仅 IP、仅 User-Agent、仅时间邻近等，只作上下文，不足以自动合并。

可在后续阶段评估 DBSCAN/HDBSCAN 或图聚类，但必须先有标注样本和可比较基线。PoC 不要求部署图数据库；PostgreSQL 关系表可保存 group、relation、reason 和 version。

### 4.5 聚合结果可解释性

每个 Alert Group / Incident Candidate 必须保留：
- group_key、time_range、member_count、member_refs；
- aggregation_version、window_config；
- 聚合统计和代表性事件；
- 关联关系、关联原因、关联强度；
- 数据缺口和字段可信状态；
- 是否人工合并/拆分及修改记录。

支持人工纠正、拆分和撤销关联。评估指标包括重复降噪率、同活动聚合准确率、错误合并率和漏合并率。

## 5. Evidence Pack 设计

### 5.1 设计目标

Evidence Pack 是 AI 分析的唯一主要事实输入，内容有限、结构化、可追溯。Agent 不能把抽样日志误当成全量数据，也不能把不存在的字段或推断写成事实。

### 5.2 建议结构

| 模块 | 内容 |
|---|---|
| metadata | pack_id、candidate_id、created_at、schema_version、builder_version |
| scope | provider/source、查询时间范围、过滤条件摘要、时区、查询状态 |
| volume | 查询总数、过滤数、去重数、候选数、样本数、截断/分页状态 |
| entities | 源 IP、目标 Host、URI 模板、客户端摘要及字段来源/可信度 |
| statistics | 请求量、速率、唯一值计数、攻击类型、规则和动作分布 |
| detections | Detection Signal、检测器版本、触发理由和特征 |
| timeline | 事件时间序列、行为阶段及其证据引用 |
| representative_events | 经脱敏的代表性事件、evidence_id、source_record_ref |
| supporting_evidence | 支持某一假设的证据及其来源 |
| counter_evidence | 正常业务迹象、可信扫描器、测试模式或矛盾证据 |
| unknowns | 缺失字段、未知枚举、不可观测事实、查询限制 |
| provenance | Provider、日志库、查询引用、映射/解析/聚合版本 |
| security | 脱敏策略、内容长度限制、不可信字段标记 |

### 5.3 代表性事件抽样

不能只取前 N 条。建议组合：
- 风险分数最高的样本；
- 不同攻击类型/规则类别的样本；
- 时间线上最早、峰值和最新样本；
- 具有反向证据或动作差异的样本；
- 随机或分层抽样样本（用于减少选择偏差）。

每种抽样方式、每个样本的选择理由、总量与覆盖范围必须记录。大规模事件先提供统计和分层样本；仅在假设验证需要时按需回查源日志。

### 5.4 质量与安全约束

- 所有证据有稳定 evidence_id 和来源引用，AI 引用必须可解析。
- 区分总体统计和样本统计；明确 sample_count、population_count、truncated、coverage。
- 记录事件时间和采集时间、查询失败/部分成功、迟到日志等情况。
- 对 URL、Query、Header、Cookie、User-Agent、Body 等不可信内容脱敏、截断并标记为数据，不能作为指令执行。
- 不向 LLM 暴露云凭据、访问令牌或无关个人敏感数据。
- Evidence Pack 必须可版本化；同一任务可记录构建版本和内容摘要以支持复现。

## 6. LangGraph 研判工作流

### 6.1 工作流形态

采用固定主流程、有限条件分支和受控工具调用，不采用无边界的自由 Agent。人工分析和定时分析复用同一图和状态 Schema。

### 6.2 节点

1. **Evidence Validation**：验证 Evidence Pack Schema、来源引用、统计口径、字段语义、截断和缺失信息；不合格则输出数据质量问题或要求补充。
2. **Threat Hypothesis**：根据检测信号和行为摘要列出有限候选假设，不提前宣布结论。
3. **Evidence Analysis**：分析请求特征、规则语义、行为序列、目标和动作；逐项绑定 evidence_id。
4. **Counter-Evidence**：主动寻找正常业务、授权扫描、测试模式、可信来源、字段矛盾和替代解释。
5. **Context Enrichment（条件节点）**：仅在证据不足且预算允许时，调用只读工具补充有限日志/历史基线/规则元数据；达到预算或证据充分即停止。
6. **Threat Classification**：输出 verdict、threat_type、severity、confidence、attack_attempt、waf_action、backend_reached 和 compromise 状态，并区分事实/推断/未知。
7. **Report Generation**：生成结构化报告、证据引用、反证、未知项、建议和人工复核理由。
8. **Persist & Audit**：持久化状态、模型/提示/工作流版本、工具调用、成本、时延和结果。

失败分支应支持超时、工具失败、证据不足、预算耗尽、模型结构化输出校验失败和安全拒绝；不能用空结果伪装为无威胁。

### 6.3 只读工具目录

- query_security_logs：受控时间范围和条件查询；
- get_event_details：按授权引用读取单条事件；
- get_behavior_context：查询相关行为组/事件上下文；
- get_waf_rule_metadata：读取已验证的规则语义与版本；
- get_historical_baseline：读取受限历史统计；
- get_related_candidates：读取已存在的关联候选及关联依据。

所有工具必须由后端执行权限校验、参数 Schema 校验、查询预算、结果条数限制、脱敏、超时和审计。Agent 不直接获得 SLS/CLS 凭据；工具不能执行 WAF 写操作。

### 6.4 输出契约

最终输出至少包含：
- verdict：confirmed_malicious / likely_malicious / likely_legitimate / confirmed_legitimate / inconclusive；
- threat_types、severity、confidence；
- facts、inferences、unknowns；
- supporting_evidence_ids、counter_evidence_ids；
- attack_attempt；
- waf_action（保留供应商语义和 unknown）；
- backend_reached（true / false / unknown）；
- compromise_status（confirmed / suspected / not_observed / unknown；不得仅由 WAF 动作推断）；
- recommendations、human_review_required；
- analysis_scope、data_quality、model/workflow/prompt versions。

confidence 是模型给出的判断信心，未经过校准前不能称为真实概率。严重性、恶意置信度和业务影响是不同维度。

## 7. 威胁判断标准

### 7.1 Verdict 定义

| Verdict | 标准 |
|---|---|
| confirmed_malicious | 存在充分、可追溯的攻击证据，且关键替代解释已排除或明显不成立 |
| likely_malicious | 多项证据支持恶意行为，但关键上下文或结果证据不足 |
| likely_legitimate | 现有证据更支持正常业务、授权测试或误报，但仍有未确认点 |
| confirmed_legitimate | 有可信业务/资产/测试上下文支持正常行为，且攻击解释不成立 |
| inconclusive | 证据不足、字段语义不明、查询不完整或证据相互矛盾 |

### 7.2 必须分离的判断维度

- 攻击尝试是否存在；
- WAF 是否检测到攻击特征；
- WAF 最终执行的动作是什么；
- 请求是否到达后端；
- 是否存在业务系统被攻陷的证据。

WAF 命中不代表攻击成功；WAF 拦截不代表曾经攻陷后端；HTTP 状态码不能单独证明 WAF 动作或 compromise。缺失字段一律保留 unknown。

### 7.3 严重性

严重性应结合攻击类型、目标资产重要性、暴露面、行为规模/持续时间、潜在影响和可验证结果评估。不能仅凭攻击规则名称或模型 confidence 自动决定严重性。首期输出建议级别和理由，人工可复核。

## 8. 准确率评估与持续优化

### 8.1 标注数据集

建立以 Alert Group / Incident Candidate 为单位的人工标注集，而非仅用孤立日志。PoC 可先收集数百个代表性行为组，逐步扩充；数量和标签分布由实际数据决定。标签至少覆盖五种 verdict，并覆盖 SQLi、XSS、命令注入、路径探测、扫描、正常业务误报、授权测试、不同 WAF 动作和字段缺失场景。

标注记录包含：样本来源、时间范围、脱敏版本、标注人、标签、证据、争议说明和复核状态。争议样本允许 inconclusive。按攻击活动/时间段/目标划分训练调试集与独立测试集，避免近重复样本泄漏。

### 8.2 分层指标

| 模块 | 指标 |
|---|---|
| Prefilter | 恶意行为召回率、过滤比例、候选率、每千日志成本 |
| Aggregation | Precision/Recall、错误合并率、漏合并率、降噪率 |
| Evidence Pack | 证据覆盖率、来源可追溯率、抽样代表性、截断识别率 |
| LangGraph | 各 verdict Precision/Recall/F1、误报率、Inconclusive Rate |
| Grounding | Evidence Grounding Rate、无依据结论比例、引用有效率 |
| WAF Semantics | Action Interpretation Accuracy |
| End-to-End | 端到端召回率、误报率、人工修订率、分析时延、单次/每千日志成本 |

所有指标按攻击类型、Provider、日志类型、WAF 动作和数据质量分层报告。Accuracy 不作为唯一指标；类别不平衡时重点看 Precision、Recall、PR 曲线和混淆矩阵。

### 8.3 对照实验

至少比较：
1. 原始规则/统计基线；
2. 规则 + 聚合 + Evidence Pack；
3. 完整 LangGraph AI 研判。

这样才能判断 AI 是否真正带来增益，而不是把规则引擎的效果归功于模型。

### 8.4 反馈闭环

人工复核可修正 verdict、关联关系和证据质量；反馈进入待审核标注集。经复核后才能更新基准集、规则配置或提示模板。每次版本更新都运行回归集，并比较误报、漏报、成本和时延。不得未经审核直接将模型自己的输出作为真实标签。

## 9. 成本、性能与故障保护

- 源端优先过滤/聚合，避免无必要的全量拉取。
- 对每个数据源设置查询时间跨度、请求频率、返回记录数、单任务/每日查询预算。
- 对每个任务设置 Evidence Pack 样本上限、LLM Token/成本上限和工具调用上限。
- 超预算时明确标记 deferred / stats_only / budget_exceeded，不静默丢弃。
- 无候选时记录扫描结果但不调用 LLM。
- 部分查询失败、截断、分页失败和字段解析失败必须进入数据质量状态。
- Checkpoint 仅在完整成功或按明确定义的部分成功策略后推进；失败不能静默前移。
- Fingerprint、任务幂等键和重叠窗口共同处理重复/迟到数据。
- 保存每任务查询量、候选数、AI 调用次数、Token、成本估算和耗时。

## 10. PoC 技术实现边界

| 能力 | PoC 方案 | 后续评估条件 |
|---|---|---|
| 规则检测 | Python 配置化规则 | 规则数量/运营协作复杂度明显增加 |
| 统计检测 | Python + 简单统计库 | 数据量和在线性能证明需要流式/专用计算 |
| 聚合存储 | PostgreSQL 关系表 + JSONB | 查询/聚合性能经压测无法满足 |
| 聚类 | 多维窗口分组 + 可解释关联规则 | 标注集证明复杂聚类显著改善质量 |
| Agent | LangGraph 固定流程 | 多步骤调查复杂度需要更丰富状态管理 |
| 任务调度 | PostgreSQL Task + 轻量 Worker | 并发、吞吐和可靠性数据证明需队列 |
| 日志存储 | SLS/CLS 源端为权威 | 查询成本/延迟或留存需求证明需复制 |

PoC 不预先引入 Kafka、Redis、OpenSearch、ClickHouse、图数据库或 Kubernetes。

## 11. 关键风险与缓解

| 风险 | 缓解措施 |
|---|---|
| 规则预筛选漏掉未知攻击 | 统计异常、抽样审计和预筛选召回率评估 |
| IP 聚合误合并 | 多维聚合、弱关联不自动合并、人工拆分 |
| 代表样本有偏 | 分层抽样并记录选择方法与覆盖率 |
| LLM 幻觉/误读动作 | 强制 evidence ID、字段语义状态和动作独立判断 |
| Prompt Injection | 原始日志作为不可信数据、隔离指令、工具权限白名单 |
| 数据不完整却输出确定结论 | 明确截断/失败/缺失，必要时 inconclusive |
| 成本失控 | 源端查询预算、无候选跳过模型、Token/工具调用上限 |
| 评估数据泄漏 | 按活动/时间/目标隔离独立测试集 |

## 12. 分阶段交付与验收

### Stage A：数据契约与基准
- 确认统一事件、检测信号、聚合对象和 Evidence Pack Schema。
- 完成字段语义注册和脱敏样本集。
- 建立初始人工标注规范。
- Exit：关键字段均有来源/语义状态；未知字段不会被猜测。

### Stage B：预筛选与聚合
- 实现去重、基础质量过滤、首批确定性规则、统计特征和行为分组。
- 记录规则/聚合版本及成员引用。
- Exit：可复现聚合结果；有错误合并/漏合并评估；预筛选召回可测。

### Stage C：Evidence Pack
- 实现统计、时间线、代表性样本、反证、未知项、来源和截断标记。
- Exit：证据引用可定位，样本与总体严格区分，数据质量状态完整。

### Stage D：LangGraph
- 实现固定节点、条件补充查询、只读工具和结构化输出。
- Exit：结论可追溯；工具受权限/预算控制；证据不足能输出 inconclusive。

### Stage E：评估与优化
- 建立分层评估集和规则基线对照。
- 测量准确性、证据质量、成本和时延。
- Exit：形成可重复的评估报告；目标阈值基于实测数据确定。

## 13. 待验证事项（不得预先固化为事实）

1. 阿里云和腾讯云 WAF 各日志类型的字段覆盖、动作语义和查询能力。
2. 事件延迟分布、时间戳准确性和可接受的重叠窗口。
3. 规则检测在真实业务流量上的误报与漏报。
4. 行为聚合的窗口、Key 和相似条件。
5. Evidence Pack 样本量、抽样策略和 Token 预算。
6. 不同模型在相同测试集上的准确率、稳定性和成本。
7. 是否需要额外历史数据存储或更高吞吐的聚合组件。

任何参数调整应通过配置版本、评估报告和 Decision Log/ADR 记录；功能新增应补充需求、测试和验收标准。
