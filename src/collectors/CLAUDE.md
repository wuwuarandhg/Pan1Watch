[根目录](../../CLAUDE.md) > [src](../) > **collectors**

# src/collectors · CLAUDE.md

> 生成时间：2026-03-22 19:55:32

## 模块职责

`src/collectors` 负责从各外部数据源采集原始数据，供 Agent 使用。每类数据源（新闻、K 线、行情、资金流、基金、截图）有对应的 Collector，通过 `src/core/data_collector.py` 协调调用。

## 采集器清单

| 文件 | 数据类型 | 支持的数据源 Provider | 说明 |
|------|---------|----------------------|------|
| `news_collector.py` | `news` | xueqiu, eastmoney, eastmoney_news | 新闻与公告采集、去重 |
| `kline_collector.py` | `kline` | tencent | 日K/周K/月K 历史数据 |
| `capital_flow_collector.py` | `capital_flow` | eastmoney | 资金流向（主力净流入） |
| `screenshot_collector.py` | `chart` | xueqiu, eastmoney | Playwright 截图 K 线图 |
| `fund_collector.py` | `quote`（基金） | eastmoney_fund | 基金实时估值、重仓股、业绩 |
| `akshare_collector.py` | `quote` | tencent, eastmoney_fund | 实时行情（腾讯源），批量行情 |
| `events_collector.py` | `events` | eastmoney | 事件日历（基于公告结构化） |
| `discovery_collector.py` | — | akshare | 市场发现（股票筛选、涨跌幅排行） |

## 数据源优先级

通过 `DataSource` 表中的 `priority` 字段管理（0 为最高优先级），`data_collector.py` 按优先级尝试，失败则切换到下一个。

## 内置数据源配置

初次启动时由 `server.py` 的 `seed_data_sources()` 自动初始化：

| 数据源名称 | 类型 | Provider | 默认启用 |
|----------|------|----------|---------|
| 东方财富资讯 | news | eastmoney_news | 是 |
| 东方财富公告 | news | eastmoney | 是 |
| 雪球资讯 | news | xueqiu | 否（需配置 cookie） |
| 腾讯K线 | kline | tencent | 是 |
| 东方财富资金流 | capital_flow | eastmoney | 是 |
| 腾讯行情 | quote | tencent | 是 |
| 天天基金 | quote | eastmoney_fund | 否（用于基金） |
| 东方财富事件日历 | events | eastmoney | 是 |
| 雪球K线截图 | chart | xueqiu | 是 |
| 东方财富K线截图 | chart | eastmoney | 否 |

## Playwright 截图功能

`screenshot_collector.py` 使用 Playwright（Chromium）对 K 线图页面截图：
- 本地开发：使用系统安装的 Playwright
- Docker 环境：首次启动时自动安装到 `data/playwright` 目录
- 设置 `PLAYWRIGHT_SKIP_BROWSER_INSTALL=1` 可跳过（不需要截图时）

## 基金采集

`fund_collector.py` 提供：
- `fetch_fund_top_holdings(fund_code)` - 获取基金重仓股
- `fetch_fund_performance(fund_code)` - 获取基金业绩表现

`akshare_collector.py` 中的 `_fetch_fund_quotes()` 提供基金实时估值。

## 市场支持

所有 Collector 通过 `src/models/market.py` 的 `MarketCode` 枚举标识市场：
- `CN`：A 股（上交所 / 深交所）
- `HK`：港股
- `US`：美股
- `FUND`：基金（特殊标识，非交易所）

`src/core/cn_symbol.py` 提供 A 股代码标准化（自动添加 sh/sz 前缀）。

## 相关文件清单

| 文件 | 说明 |
|------|------|
| `src/collectors/akshare_collector.py` | 腾讯行情采集，使用 efinance/akshare |
| `src/collectors/news_collector.py` | 多源新闻采集与去重 |
| `src/collectors/kline_collector.py` | K 线历史数据 |
| `src/collectors/capital_flow_collector.py` | 资金流向 |
| `src/collectors/screenshot_collector.py` | Playwright K 线图截图 |
| `src/collectors/fund_collector.py` | 基金数据采集 |
| `src/collectors/events_collector.py` | 事件日历 |
| `src/collectors/discovery_collector.py` | 市场发现筛选 |
| `src/core/data_collector.py` | 多数据源协调调用入口 |

## 变更记录 (Changelog)

| 时间 | 变更内容 |
|------|----------|
| 2026-03-22 19:55:32 | 初次生成模块文档 |
