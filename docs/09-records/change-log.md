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

## 2026-11-26 — Adopt uv project management
- 新增 `pyproject.toml`，统一声明项目元数据、运行依赖、开发依赖和 pytest 配置。
- 配置 pytest 从仓库根目录解析导入路径，便于测试导入 `src` 包。
- 更新 README，采用 `uv sync`、`uv run pytest` 和 `uv run` 执行项目命令。
- 暂时保留 `requirements.txt`，兼容传统 pip 安装方式；后续以 `pyproject.toml` 和 `uv.lock` 为依赖管理基线。
- `uv.lock` 由开发者在本地首次运行 `uv sync` 时生成并提交。
