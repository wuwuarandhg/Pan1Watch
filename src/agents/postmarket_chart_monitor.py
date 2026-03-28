"""盘后 K 线截图监控 Agent - 收盘后基于日 K 截图做多模态分析"""

import logging
from datetime import datetime
from pathlib import Path

from src.agents.base import AgentContext, AnalysisResult
from src.agents.intraday_monitor import IntradayMonitorAgent
from src.collectors.screenshot_collector import ScreenshotCollector, ChartScreenshot
from src.core.context_store import save_agent_context_run, save_agent_prediction_outcome
from src.core.signals import SignalPackBuilder
from src.core.suggestion_pool import save_suggestion
from src.models.market import MarketCode, MARKETS, StockData

logger = logging.getLogger(__name__)

PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "postmarket_chart_monitor.md"
)


def is_after_market_close(market: MarketCode, dt: datetime | None = None) -> bool:
    market_def = MARKETS.get(market)
    if not market_def:
        return False

    if dt is None:
        dt = datetime.now(market_def.get_tz())
    else:
        dt = dt.astimezone(market_def.get_tz())

    if dt.weekday() >= 5:
        return False

    last_session = market_def.sessions[-1] if market_def.sessions else None
    if not last_session:
        return False
    return dt.time() >= last_session.end


class PostmarketChartMonitorAgent(IntradayMonitorAgent):
    """收盘后截取持仓股票日 K，并用多模态 AI 给出持仓建议。"""

    name = "postmarket_chart_monitor"
    display_name = "盘后K线监控"
    description = "A股收盘后截取持仓日K图，AI分析趋势、支撑压力和持仓建议"

    def __init__(
        self,
        throttle_minutes: int = 12 * 60,
        bypass_throttle: bool = False,
        bypass_market_hours: bool = False,
        provider: str = "xueqiu",
        period: str = "daily",
        holding_only: bool = True,
        notify_on_hold: bool = True,
        notify_on_watch: bool = False,
    ):
        super().__init__(
            throttle_minutes=throttle_minutes,
            bypass_throttle=bypass_throttle,
            bypass_market_hours=bypass_market_hours,
            event_only=False,
        )
        self.provider = (provider or "xueqiu").strip().lower() or "xueqiu"
        self.period = (period or "daily").strip().lower() or "daily"
        self.holding_only = bool(holding_only)
        self.notify_on_hold = bool(notify_on_hold)
        self.notify_on_watch = bool(notify_on_watch)
        self._collector: ScreenshotCollector | None = None

    def schedule_skip_reason(self, stock) -> str | None:
        if getattr(stock, "market", None) != MarketCode.CN:
            return "仅支持A股盘后监控"

        market_def = MARKETS.get(MarketCode.CN)
        if not market_def:
            return "A股市场定义缺失"

        now = datetime.now(market_def.get_tz())
        if now.weekday() >= 5:
            return "非交易日"
        if market_def.is_trading_time(now):
            return "仍在交易时段"
        if not is_after_market_close(MarketCode.CN, now):
            return "尚未收盘"
        return None

    async def collect(self, context: AgentContext) -> dict:
        if not context.watchlist:
            msg = "未绑定股票，已跳过盘后K线监控"
            logger.warning(msg)
            return {"stock_data": None, "screenshots": [], "skip_reason": msg}

        stock_config = context.watchlist[0]
        symbol = stock_config.symbol
        market = stock_config.market

        if market != MarketCode.CN:
            msg = "当前仅支持A股盘后K线监控"
            logger.info(f"{msg}: {symbol}")
            return {"stock_data": None, "screenshots": [], "skip_reason": msg}

        if not self.bypass_market_hours:
            skip_reason = self.schedule_skip_reason(stock_config)
            if skip_reason:
                logger.info(f"{skip_reason}: {symbol}")
                return {
                    "stock_data": None,
                    "screenshots": [],
                    "skip_reason": skip_reason,
                }

        positions = context.portfolio.get_positions_for_stock(symbol)
        if self.holding_only and not positions:
            msg = "当前无持仓，已跳过盘后K线监控"
            logger.info(f"{msg}: {symbol}")
            return {"stock_data": None, "screenshots": [], "skip_reason": msg}

        builder = SignalPackBuilder()
        packs = await builder.build_for_symbols(
            symbols=[(symbol, market, stock_config.name)],
            include_news=False,
            news_hours=24,
            portfolio=context.portfolio,
            include_technical=True,
            include_capital_flow=False,
            include_events=True,
            events_days=3,
        )
        pack = packs.get(symbol)
        stock_data = pack.quote if pack and pack.quote else None
        if not stock_data:
            msg = "未获取到收盘行情数据"
            logger.warning(f"{msg}: {symbol}")
            return {"stock_data": None, "screenshots": [], "skip_reason": msg}

        self._collector = ScreenshotCollector()
        screenshots: list[ChartScreenshot] = []
        try:
            screenshot = await self._collector.capture(
                symbol=symbol,
                name=stock_config.name,
                market=market.value,
                period=self.period,
                provider=self.provider,
            )
            if screenshot:
                screenshots.append(screenshot)
            self._collector.cleanup_old_screenshots(max_age_hours=24)
        finally:
            await self._collector.close()
            self._collector = None

        return {
            "stock_data": stock_data,
            "stocks": [stock_data],
            "screenshots": screenshots,
            "signal_pack": pack,
            "kline_summary": pack.technical if pack else None,
            "position": context.portfolio.get_aggregated_position(symbol),
            "timestamp": datetime.now().isoformat(),
        }

    def build_prompt(self, data: dict, context: AgentContext) -> tuple[str, str]:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        stock: StockData | None = data.get("stock_data")
        if not stock:
            return system_prompt, "无股票数据"

        position = data.get("position") or {}
        kline = data.get("kline_summary") or {}

        def safe_num(value, precision=2):
            if value is None:
                return "N/A"
            return f"{float(value):.{precision}f}"

        lines: list[str] = []
        lines.append(f"## 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("## 任务")
        lines.append("- 这是A股收盘后的持仓日K复盘，请优先结合提供的K线截图判断趋势和形态。")
        lines.append("- 结构化指标仅作辅助校验，不要忽略截图中的形态、趋势线、放量缩量和关键位置。")

        lines.append("\n## 股票信息")
        lines.append(f"- 股票：{stock.name}（{stock.symbol}）")
        lines.append(f"- 收盘价：{safe_num(stock.current_price)}")
        lines.append(f"- 涨跌幅：{safe_num(stock.change_pct)}%")
        lines.append(
            f"- 开盘/最高/最低：{safe_num(stock.open_price)}/{safe_num(stock.high_price)}/{safe_num(stock.low_price)}"
        )
        if stock.volume:
            lines.append(f"- 成交量：{stock.volume:.0f} 手")
        if stock.turnover:
            lines.append(f"- 成交额：{stock.turnover / 1e8:.2f} 亿")

        if position:
            avg_cost = position.get("avg_cost")
            pnl_pct = None
            if avg_cost and stock.current_price:
                pnl_pct = (stock.current_price - avg_cost) / avg_cost * 100
            lines.append("\n## 持仓信息")
            lines.append(f"- 持仓数量：{position.get('total_quantity') or 0} 股")
            lines.append(f"- 持仓成本：{safe_num(avg_cost)}")
            if pnl_pct is not None:
                lines.append(f"- 浮动盈亏：{pnl_pct:+.2f}%")
            lines.append(f"- 交易风格：{position.get('trading_style') or 'swing'}")

        if kline and not kline.get("error"):
            lines.append("\n## 结构化技术摘要（辅助）")
            if kline.get("trend"):
                lines.append(f"- 趋势：{kline.get('trend')}")
            if kline.get("macd_status"):
                lines.append(f"- MACD：{kline.get('macd_status')}")
            if kline.get("rsi6") is not None and kline.get("rsi_status"):
                lines.append(
                    f"- RSI6：{safe_num(kline.get('rsi6'), 1)}（{kline.get('rsi_status')}）"
                )
            if kline.get("kline_pattern"):
                lines.append(f"- K线形态：{kline.get('kline_pattern')}")
            if kline.get("volume_trend"):
                vol = kline.get("volume_ratio")
                vol_text = f"{kline.get('volume_trend')}"
                if vol is not None:
                    vol_text += f"（量比 {float(vol):.2f}）"
                lines.append(f"- 量能：{vol_text}")
            support = kline.get("support_m") or kline.get("support")
            resistance = kline.get("resistance_m") or kline.get("resistance")
            if support is not None and resistance is not None:
                lines.append(f"- 支撑/压力：{safe_num(support)} / {safe_num(resistance)}")
            lines.append(
                f"- 均线：MA5 {safe_num(kline.get('ma5'))} / MA10 {safe_num(kline.get('ma10'))} / MA20 {safe_num(kline.get('ma20'))} / MA60 {safe_num(kline.get('ma60'))}"
            )

        lines.append("\n请基于截图和上述信息，给出盘后持仓建议。")
        return system_prompt, "\n".join(lines)

    async def analyze(self, context: AgentContext, data: dict) -> AnalysisResult:
        if data.get("skip_reason"):
            return AnalysisResult(
                agent_name=self.name,
                title=f"【{self.display_name}】跳过",
                content=data.get("skip_reason", "跳过执行"),
                raw_data={"skipped": True, **data},
            )

        stock: StockData | None = data.get("stock_data")
        screenshots: list[ChartScreenshot] = data.get("screenshots", [])
        image_paths = [shot.filepath for shot in screenshots if shot.exists]
        if not stock:
            return AnalysisResult(
                agent_name=self.name,
                title=f"【{self.display_name}】无数据",
                content="未获取到收盘行情数据",
                raw_data={**data, "should_alert": False},
            )

        if not image_paths:
            return AnalysisResult(
                agent_name=self.name,
                title=f"【{self.display_name}】{stock.name}",
                content="未能获取到日K截图，请检查截图链路或稍后重试。",
                raw_data={**data, "should_alert": False},
            )

        system_prompt, user_content = self.build_prompt(data, context)
        raw_content = await context.ai_client.chat(
            system_prompt,
            user_content,
            images=image_paths,
        )

        suggestion = self._parse_suggestion(raw_content)
        notify_actions = {"reduce", "sell", "alert", "avoid"}
        if self.notify_on_hold:
            notify_actions.add("hold")
        if self.notify_on_watch:
            notify_actions.add("watch")
        suggestion["should_alert"] = suggestion.get("action") in notify_actions

        content = raw_content
        if self._try_parse_loose_json(raw_content):
            content = self._format_human_readable_content(stock, suggestion, raw_content)

        analysis_date = (data.get("timestamp") or "")[:10] or datetime.now().strftime(
            "%Y-%m-%d"
        )
        kline_summary = data.get("kline_summary") or {}
        position = data.get("position") or {}
        save_suggestion(
            stock_symbol=stock.symbol,
            stock_name=stock.name,
            action=suggestion.get("action", "watch"),
            action_label=suggestion.get("action_label", "观望"),
            signal=suggestion.get("signal", ""),
            reason=suggestion.get("reason", ""),
            agent_name=self.name,
            agent_label=self.display_name,
            expires_hours=18,
            prompt_context=user_content,
            ai_response=raw_content,
            stock_market=stock.market.value,
            meta={
                "source": self.name,
                "analysis_date": analysis_date,
                "period": self.period,
                "provider": self.provider,
                "quote": {
                    "current_price": stock.current_price,
                    "change_pct": stock.change_pct,
                },
                "position": {
                    "total_quantity": position.get("total_quantity"),
                    "avg_cost": position.get("avg_cost"),
                    "trading_style": position.get("trading_style"),
                },
                "kline_meta": {
                    "computed_at": kline_summary.get("computed_at"),
                    "asof": kline_summary.get("asof"),
                },
                "plan": {
                    "triggers": suggestion.get("triggers")
                    if isinstance(suggestion.get("triggers"), list)
                    else [],
                    "invalidations": suggestion.get("invalidations")
                    if isinstance(suggestion.get("invalidations"), list)
                    else [],
                    "risks": suggestion.get("risks")
                    if isinstance(suggestion.get("risks"), list)
                    else [],
                },
            },
        )
        for horizon in (1, 5):
            save_agent_prediction_outcome(
                agent_name=self.name,
                stock_symbol=stock.symbol,
                stock_market=stock.market.value,
                prediction_date=analysis_date,
                horizon_days=horizon,
                action=suggestion.get("action") or "watch",
                action_label=suggestion.get("action_label") or "观望",
                confidence=None,
                trigger_price=getattr(stock, "current_price", None),
                meta={
                    "source": self.name,
                    "reason": suggestion.get("reason", ""),
                    "signal": suggestion.get("signal", ""),
                },
            )
        save_agent_context_run(
            agent_name=self.name,
            stock_symbol=stock.symbol,
            analysis_date=analysis_date,
            context_payload={
                "position": position,
                "kline_summary": kline_summary,
                "screenshot_count": len(image_paths),
                "provider": self.provider,
                "period": self.period,
            },
            quality={"score": 100 if image_paths else 0},
        )

        title = f"【{self.display_name}】{stock.name} 日K复盘"
        if context.model_label:
            content = content.rstrip() + f"\n\n---\nAI: {context.model_label}"

        return AnalysisResult(
            agent_name=self.name,
            title=title,
            content=content,
            raw_data={
                "stock": {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "current_price": stock.current_price,
                    "change_pct": stock.change_pct,
                },
                "suggestion": suggestion,
                "should_alert": bool(suggestion.get("should_alert")),
                **data,
            },
            images=image_paths,
        )

    async def should_notify(self, result: AnalysisResult) -> bool:
        if result.raw_data.get("skipped"):
            return False
        if not result.raw_data.get("should_alert", False):
            return False

        stock = result.raw_data.get("stock") or {}
        symbol = stock.get("symbol")
        if not symbol:
            return False

        if not self.bypass_throttle and not self._check_throttle(symbol):
            logger.info(
                f"通知节流: {symbol} 在 {self.throttle_minutes} 分钟内已通知"
            )
            return False
        return True

    async def run(self, context: AgentContext) -> AnalysisResult:
        result = await super().run(context)
        stock = (result.raw_data or {}).get("stock") or {}
        symbol = stock.get("symbol")
        if symbol and result.raw_data.get("notified") and not self.bypass_throttle:
            self._update_throttle(symbol)
        return result
