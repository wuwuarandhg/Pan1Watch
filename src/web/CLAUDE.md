[根目录](../../CLAUDE.md) > [src](../) > **web**

# src/web · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

`src/web` 是后端 Web 层，包含：
- FastAPI 应用实例与路由注册（`app.py`）
- SQLAlchemy ORM 数据模型（`models.py`）
- 数据库初始化与版本迁移（`database.py`、`migrations.py`）
- 所有 REST API 路由模块（`api/` 子目录）
- 响应包装中间件（`response.py`）
- 数据库日志处理器（`log_handler.py`）
- 股票列表缓存（`stock_list.py`）

## 入口与启动

`app.py` 创建 FastAPI 实例，生命周期由 `server.py` 的 `lifespan()` 管理（初始化 DB、启动调度器等）。

## API 路由清单

所有路由挂载在 `/api` 前缀下。带 `[保护]` 标注的需要 JWT 认证。

| 路由前缀 | 文件 | 说明 | 认证 |
|---------|------|------|------|
| `/api/auth` | `api/auth.py` | 登录、注册密码、JWT 签发 | 无 |
| `/api/market` | `api/market.py` | 市场指数行情（上证、深证、纳斯达克等） | 无 |
| `/api/mcp` | `api/mcp.py` | MCP JSON-RPC 工具接口（支持 Bearer/Basic 认证） | Bearer/Basic |
| `/api/stocks` | `api/stocks.py` | 自选股 CRUD、搜索、排序 | 保护 |
| `/api/quotes` | `api/quotes.py` | 实时行情查询 | 保护 |
| `/api/klines` | `api/klines.py` | K 线数据查询 | 保护 |
| `/api/insights` | `api/insights.py` | AI 洞察（按需触发单股分析） | 保护 |
| `/api` (accounts) | `api/accounts.py` | 账户、持仓管理，交易流水 | 保护 |
| `/api/agents` | `api/agents.py` | Agent 配置查询、手动触发 | 保护 |
| `/api/providers` | `api/providers.py` | AI 服务商 + 模型管理 | 保护 |
| `/api/channels` | `api/channels.py` | 通知渠道管理、测试发送 | 保护 |
| `/api/datasources` | `api/datasources.py` | 数据源配置、测试 | 保护 |
| `/api/settings` | `api/settings.py` | 应用设置（代理、静默时段等）、更新检查 | 保护 |
| `/api/logs` | `api/logs.py` | 日志查询（实时 SSE 流） | 保护 |
| `/api` (history) | `api/history.py` | Agent 历史分析记录 | 保护 |
| `/api` (context) | `api/context.py` | 股票上下文快照、预测结果 | 保护 |
| `/api/news` | `api/news.py` | 新闻查询与采集 | 保护 |
| `/api/suggestions` | `api/suggestions.py` | AI 建议池查询 | 保护 |
| `/api/templates` | `api/templates.py` | 提示词模板管理 | 保护 |
| `/api/feedback` | `api/feedback.py` | 建议反馈收集 | 保护 |
| `/api/discovery` | `api/discovery.py` | 市场发现（股票筛选）| 保护 |
| `/api/price-alerts` | `api/price_alerts.py` | 价格提醒规则 CRUD | 保护 |
| `/api/recommendations` | `api/recommendations.py` | 入场候选榜、策略信号 | 保护 |
| `/api/dashboard` | `api/dashboard.py` | 仪表盘总览数据 | 保护 |
| `/api/health` | `app.py` | 健康检查 | 无 |
| `/api/version` | `app.py` | 版本号 | 无 |

## 数据模型（models.py）

数据库使用 SQLite，文件路径：`data/panwatch.db`。

### 核心业务表

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `stocks` | `Stock` | 自选股（symbol, name, market） |
| `accounts` | `Account` | 交易账户（支持多账户：CN/HK/US） |
| `positions` | `Position` | 持仓（account_id + stock_id 唯一键，trading_style: short/swing/long） |
| `position_trades` | `PositionTrade` | 持仓交易流水（add/reduce/overwrite/create） |
| `stock_agents` | `StockAgent` | 自选股与 Agent 多对多关联 |

### AI 与通知

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `ai_services` | `AIService` | AI 服务商（base_url + api_key） |
| `ai_models` | `AIModel` | AI 模型（属于服务商，is_default 标记） |
| `notify_channels` | `NotifyChannel` | 通知渠道（type: telegram 等） |
| `agent_configs` | `AgentConfig` | Agent 配置（schedule, execution_mode, config JSON） |
| `agent_runs` | `AgentRun` | Agent 执行记录（status, trace_id, duration_ms） |
| `log_entries` | `LogEntry` | 结构化日志持久化 |
| `app_settings` | `AppSettings` | 键值对应用设置 |
| `data_sources` | `DataSource` | 数据源配置（type: news/chart/quote/kline/capital_flow） |

### 分析与上下文

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `analysis_history` | `AnalysisHistory` | 历史分析报告（agent_name + stock_symbol + date 唯一） |
| `stock_context_snapshots` | `StockContextSnapshot` | 每日每股上下文快照 |
| `news_topic_snapshots` | `NewsTopicSnapshot` | 新闻主题聚合快照 |
| `agent_context_runs` | `AgentContextRun` | Agent 执行时的上下文摘要 |
| `news_cache` | `NewsCache` | 新闻缓存（去重） |

### 建议与策略

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `stock_suggestions` | `StockSuggestion` | AI 建议池（action: buy/add/reduce/sell/hold/watch/alert/avoid） |
| `entry_candidates` | `EntryCandidate` | 入场候选榜（score, confidence, entry_low/high, stop_loss） |
| `market_scan_snapshots` | `MarketScanSnapshot` | 市场扫描快照 |
| `entry_candidate_feedback` | `EntryCandidateFeedback` | 入场候选反馈 |
| `entry_candidate_outcomes` | `EntryCandidateOutcome` | 入场候选后验结果 |
| `suggestion_feedback` | `SuggestionFeedback` | 建议反馈（useful 布尔值） |
| `agent_prediction_outcomes` | `AgentPredictionOutcome` | Agent 预测后验评估 |

### 策略引擎

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `strategy_catalog` | `StrategyCatalog` | 策略目录（code, risk_level, default_weight） |
| `strategy_signal_runs` | `StrategySignalRun` | 策略信号执行快照 |
| `strategy_outcomes` | `StrategyOutcome` | 策略后验结果 |
| `strategy_weights` | `StrategyWeight` | 策略权重（当前有效值） |
| `strategy_weight_history` | `StrategyWeightHistory` | 策略调权历史 |
| `strategy_factor_snapshots` | `StrategyFactorSnapshot` | 因子分解快照（alpha/catalyst/quality/risk_penalty） |
| `market_regime_snapshots` | `MarketRegimeSnapshot` | 市场状态快照（bullish/neutral/bearish） |
| `portfolio_risk_snapshots` | `PortfolioRiskSnapshot` | 组合风险画像快照 |

### 价格提醒

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `price_alert_rules` | `PriceAlertRule` | 价格提醒规则（条件组、冷却时间、每日上限） |
| `price_alert_hits` | `PriceAlertHit` | 价格提醒命中记录 |
| `notify_throttle` | `NotifyThrottle` | 通知节流记录（防同一股票短时间重复推送） |

## 数据库迁移

- 启动时自动执行，无需手动迁移
- `database.py` 中的 `_migrate()` 处理增量 ALTER TABLE
- `migrations.py` 中的 `run_versioned_migrations()` 处理版本化迁移
- 有 pending 迁移时会自动备份 SQLite 文件（`panwatch.db.bak.YYYYMMDD_HHMMSS`）

## MCP 接口

`api/mcp.py` 实现 JSON-RPC 2.0 协议（`tools/list`、`tools/call`），支持：
- Bearer Token 认证（复用 JWT）
- HTTP Basic 认证（用户名/密码）
- 工具覆盖：股票、行情、K线、持仓、账户、新闻、历史分析、建议池、价格提醒、基金、市场指数、仪表盘等

## 相关文件清单

| 文件 | 说明 |
|------|------|
| `src/web/app.py` | FastAPI 实例，所有路由注册 |
| `src/web/models.py` | 全部 ORM 模型（25+ 张表） |
| `src/web/database.py` | SQLite 引擎、会话工厂、迁移逻辑 |
| `src/web/migrations.py` | 版本化迁移脚本 |
| `src/web/response.py` | 响应体统一包装中间件 |
| `src/web/log_handler.py` | 数据库日志处理器（写入 log_entries 表） |
| `src/web/stock_list.py` | 全量股票列表缓存（用于搜索） |
| `src/web/api/mcp.py` | MCP JSON-RPC 实现 |
| `src/web/api/auth.py` | JWT 认证逻辑 |

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
