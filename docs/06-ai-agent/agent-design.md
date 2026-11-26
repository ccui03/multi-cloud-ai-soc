# AI Agent 设计草案

## 1. 设计原则

- 先检索和聚合，再将有限上下文交给 LLM。
- Agent 输出结论、证据、置信度和待确认问题。
- 工具采用 allowlist，参数进行 Schema 校验。
- 日志内容是数据，不是指令。
- 高风险动作必须由独立策略层和人工审批控制。

## 2. 初步 Agent 职责

| Agent / Node | 职责 | 默认权限 |
|---|---|---|
| Alert Triage | 分类、摘要、优先级建议、去重建议 | 只读 |
| Investigation | 查询相关 WAF/安全日志，整理时间线 | 只读 |
| Threat Intel | 查询 IP/域名/URL 情报 | 只读 |
| Response Planner | 生成处置建议和风险说明 | 只生成建议 |
| Report Writer | 生成结构化调查报告 | 只读 |

这些职责可以先作为一个 LangGraph 工作流中的节点，不必一开始就部署成多个独立 Agent 服务。

## 3. 建议输出结构

```json
{
  "summary": "事件摘要",
  "severity": "low|medium|high|critical",
  "confidence": 0.0,
  "evidence": [
    {
      "event_id": "event-id",
      "reason": "该证据支持的判断"
    }
  ],
  "attack_hypotheses": [],
  "recommended_actions": [],
  "needs_human_review": true
}
```

实际实现时应定义 JSON Schema，并校验模型输出。

## 4. 后续设计事项

- LangGraph 状态结构和 checkpoint。
- 工具清单、输入输出 Schema 和权限。
- Prompt Injection 防护和日志脱敏。
- 模型选择、成本和数据合规。
- 评估集：正常流量、误报、扫描、漏洞利用尝试和真实攻击样例。
