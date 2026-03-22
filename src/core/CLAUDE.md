[根目录](../../CLAUDE.md) > [src](../) > **core**

# src/core · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

`src/core` 是后端的核心基础设施层，提供以下能力：
- Agent 调度（APScheduler 封装）
- AI 客户端（OpenAI 兼容接口）
- 通知管理（apprise 封装，支持 Telegram 等）
- 通知策略（静默时段、去重、重试）
- 价格提醒引擎
- 策略引擎与策略目录
- 上下文存储（跨天 AI 记忆）
- 日志上下文（结构化日志）
- 数据采集协调

## 关键子模块

### 调度器

| 文件 | 类 | 说明 |
|------|----|------|
| `scheduler.py` | `AgentScheduler` | APScheduler 封装，按 cron 计划调度 Agent |
| `price_alert_scheduler.py` | `PriceAlertScheduler` | 每 60 秒轮询价格提醒规则 |
| `context_scheduler.py` | `ContextMaintenanceScheduler` | 每 6 小时维护上下文快照和结果评估 |
| `schedule_parser.py` | — | cron 表达式解析与校验 |

### AI 与通知

| 文件 | 类/函数 | 说明 |
|------|--------|------|
| `ai_client.py` | `AIClient` | OpenAI 兼容 HTTP 客户端（支持 base_url + proxy） |
| `notifier.py` | `NotifierManager` | apprise 多渠道通知管理（Telegram, email 等） |
| `notify_policy.py` | `NotifyPolicy` | 静默时段、重试次数、退避时间策略 |
| `notify_dedupe.py` | `check_and_mark_notify` | 通知幂等去重（基于 SQLite TTL 记录） |

### 策略引擎

| 文件 | 说明 |
|------|------|
| `strategy_engine.py` | 策略评分、因子计算、入场候选榜生成 |
| `strategy_catalog.py` | `ensure_strategy_catalog()` 初始化内置策略 |
| `entry_candidates.py` | 入场候选榜管理与更新 |
| `suggestion_pool.py` | 建议池聚合（汇总各 Agent 建议） |
| `prediction_outcome.py` | 建议后验评估（与实际涨跌对比） |

### 上下文与记忆

| 文件 | 说明 |
|------|------|
| `context_builder.py` | 为 Agent 构建跨天上下文摘要 |
| `context_store.py` | 上下文快照 CRUD（`StockContextSnapshot` 表） |
| `analysis_history.py` | 历史分析记录管理（`AnalysisHistory` 表） |
| `kline_context.py` | K 线技术指标上下文提取 |
| `news_ranker.py` | 新闻重要性排序 |

### 信号与结构化输出

| 文件 | 说明 |
|------|------|
| `signals/structured_output.py` | AI 结构化输出解析（JSON 提取、建议动作解析） |
| `signals/signal_pack.py` | 信号包封装 |

### 工具

| 文件 | 说明 |
|------|------|
| `log_context.py` | `log_context()` 上下文管理器，给日志附加 trace_id、agent_name 等字段 |
| `agent_runs.py` | `record_agent_run()` 记录 Agent 运行结果到 DB |
| `agent_catalog.py` | Agent 种子配置、分类（workflow/capability）枚举 |
| `cn_symbol.py` | A 股代码标准化（上交所/深交所前缀处理） |
| `timezone.py` | 时区工具（基于 zoneinfo） |
| `json_store.py` | 本地 JSON 文件存储（用于轻量持久化） |
| `json_safe.py` | JSON 序列化安全处理（NaN/Inf 过滤） |
| `intraday_event_gate.py` | 盘中事件门控（防重复触发） |
| `update_checker.py` | 检查 GitHub Releases 是否有新版本 |
| `data_collector.py` | 多数据源采集协调器 |

## 对外接口

### AIClient

```python
class AIClient:
    def __init__(self, base_url: str, api_key: str, model: str, proxy: str = ""): ...
    async def chat(self, system_prompt: str, user_content: str) -> str: ...
```

### NotifierManager

```python
class NotifierManager:
    def add_channel(self, channel_type: str, config: dict): ...
    async def notify_with_result(self, title: str, content: str, images: list[str]) -> dict: ...
```

### AgentScheduler

```python
class AgentScheduler:
    def set_context_builder(self, builder: Callable): ...
    def register(self, agent: BaseAgent, schedule: str, execution_mode: str): ...
    def start(self): ...
    def shutdown(self): ...
```

### NotifyPolicy

```python
class NotifyPolicy:
    timezone: str
    quiet_hours: str          # 格式 "23:00-07:00"
    retry_attempts: int
    retry_backoff_seconds: float
    dedupe_ttl_overrides: dict[str, int]  # agent_name -> TTL 分钟

    def is_quiet_now(self) -> bool: ...
    def dedupe_ttl_minutes(self, agent_name: str, default: int) -> int: ...
```

## 相关文件清单

| 文件 | 重要性 |
|------|--------|
| `src/core/scheduler.py` | 核心 |
| `src/core/ai_client.py` | 核心 |
| `src/core/notifier.py` | 核心 |
| `src/core/notify_policy.py` | 核心 |
| `src/core/notify_dedupe.py` | 核心 |
| `src/core/agent_catalog.py` | 核心 |
| `src/core/strategy_engine.py` | 重要 |
| `src/core/context_builder.py` | 重要 |
| `src/core/signals/structured_output.py` | 重要 |
| `src/core/log_context.py` | 辅助 |
| `src/core/update_checker.py` | 辅助 |

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
