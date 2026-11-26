# Change Log

## 2026-11-26 — Project Baseline v1.0
- 建立项目章程、需求、架构、候选技术栈和路线图初稿。
- 明确初期以单一 WAF 数据源 PoC 起步。
- 明确 Agent 默认只读，响应动作需策略校验和人工审批。

## 2026-11-26 — SLS / CLS Adapter 首版

- 新增统一 QueryRequest、FetchPage、RawWAFRecord 数据契约。
- 新增 AliyunSLSAdapter（SLS GetLogs / offset 分页）。
- 新增 TencentCLSAdapter（CLS SearchLog / Context 分页）。
- 新增独立 env 文件加载器、SDK 依赖、基础契约测试和云端 smoke test 脚本。
- 更新 README 与日志接入设计，记录 SDK、Endpoint、分页机制和未完成的真实云端验证。
- 注意：当前 WAF 字段映射仍是初始值，需用脱敏日志样本校准。
