[根目录](../../CLAUDE.md) > [src](../) > **agents**

# src/agents · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

本目录包含所有 AI 分析 Agent 的实现，以及 Agent 公共基类。每个 Agent 负责：数据采集（`collect`）→ Prompt 构建（`build_prompt`）→ AI 调用（`analyze`）→ 通知发送。

Agent 分为两类（由 `src/core/agent_catalog.py` 定义）：
- **workflow**：可被调度器自动调度的工作流 Agent
- **capability**：内部能力 Agent，仅供按需手动触发，不参与自动调度

## 入口与启动

Agent 不直接启动，由 `server.py` 中的 `AgentScheduler`（APScheduler）按 cron 计划调度，或由 `trigger_agent()` / `trigger_agent_for_stock()` 手动触发。

Agent 实例通过 `AGENT_REGISTRY` 字典在 `server.py` 中注册：
```python
AGENT_REGISTRY = {
    "daily_report": DailyReportAgent,
    "premarket_outlook": PremarketOutlookAgent,
    "news_digest": NewsDigestAgent,
    "chart_analyst": ChartAnalystAgent,
    "intraday_monitor": IntradayMonitorAgent,
    "fund_holding_analyst": FundHoldingAnalystAgent,
}
```

## Agent 清单

| Agent | 文件 | 类型 | 默认调度 | 执行模式 | 说明 |
|-------|------|------|---------|---------|------|
| `premarket_outlook` | `premarket_outlook.py` | workflow | `0 9 * * 1-5`（9:00 工作日） | batch | 盘前分析：汇总昨日复盘+隔夜信息，展望今日走势 |
| `intraday_monitor` | `intraday_monitor.py` | workflow | `*/5 9-15 * * 1-5`（盘中每 5 分钟） | single | 盘中监测：逐只股票实时监控，事件驱动推送 |
| `daily_report` | `daily_report.py` | workflow | `30 15 * * 1-5`（15:30 工作日） | batch | 收盘复盘：生成日报，含市场回顾、个股分析、次日展望 |
| `fund_holding_analyst` | `fund_holding_analyst.py` | workflow | `0 20 * * 5`（每周五 20:00） | batch | 基金分析：基金重仓股、持仓重叠度、业绩表现 |
| `news_digest` | `news_digest.py` | capability（已废弃） | — | batch | 新闻能力：由 premarket/daily/intraday 内联调用 |
| `chart_analyst` | `chart_analyst.py` | capability（已废弃） | — | single | 图表技术分析能力：由其他 Agent 按需调用 |

## 对外接口（BaseAgent 基类）

文件：`base.py`

```python
class BaseAgent(ABC):
    name: str
    display_name: str
    description: str

    async def collect(self, context: AgentContext) -> dict: ...
    def build_prompt(self, data: dict, context: AgentContext) -> tuple[str, str]: ...
    async def analyze(self, context: AgentContext, data: dict) -> AnalysisResult: ...
    async def should_notify(self, result: AnalysisResult) -> bool: ...
    async def run(self, context: AgentContext) -> AnalysisResult: ...
    # single 模式专用（intraday_monitor 支持）
    async def run_single(self, context: AgentContext, symbol: str) -> AnalysisResult: ...
```

关键数据类：
```python
@dataclass
class AgentContext:
    ai_client: AIClient
    notifier: NotifierManager
    config: AppConfig          # 包含 watchlist
    portfolio: PortfolioInfo   # 持仓信息
    model_label: str           # 例如 "智谱/glm-4-flash"
    notify_policy: NotifyPolicy | None
    suppress_notify: bool

@dataclass
class AnalysisResult:
    agent_name: str
    title: str
    content: str
    raw_data: dict
    images: list[str]
    timestamp: datetime
```

## 通知去重机制

`BaseAgent.run()` 内置通知去重（`src/core/notify_dedupe`），按 Agent 类型设置不同 TTL：
- `daily_report` / `premarket_outlook`：720 分钟（12 小时）
- `chart_analyst`：360 分钟
- `news_digest`：60 分钟
- `intraday_monitor`：30 分钟（另有每股节流）

## intraday_monitor 特殊配置

支持通过 `config` 字段配置触发阈值：
```json
{
  "event_only": true,
  "price_alert_threshold": 3.0,
  "volume_alert_ratio": 2.0,
  "stop_loss_warning": -5.0,
  "take_profit_warning": 10.0,
  "throttle_minutes": 30
}
```

## 数据模型

持仓相关数据类（`base.py`）：
- `PositionInfo`：单账户单股票持仓（cost_price, quantity, trading_style）
- `AccountInfo`：账户信息 + 持仓列表
- `PortfolioInfo`：多账户持仓聚合，提供 `get_aggregated_position(symbol)` 等方法

## 相关文件清单

| 文件 | 说明 |
|------|------|
| `src/agents/base.py` | 抽象基类、上下文与结果数据类 |
| `src/agents/daily_report.py` | 收盘复盘 Agent |
| `src/agents/premarket_outlook.py` | 盘前分析 Agent |
| `src/agents/intraday_monitor.py` | 盘中监测 Agent（支持 run_single） |
| `src/agents/chart_analyst.py` | 技术分析能力 Agent |
| `src/agents/news_digest.py` | 新闻速递能力 Agent |
| `src/agents/fund_holding_analyst.py` | 基金分析 Agent |
| `src/core/agent_catalog.py` | Agent 种子配置与分类定义 |
| `server.py` | AGENT_REGISTRY 注册表，trigger_agent() 触发函数 |

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
