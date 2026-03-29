import asyncio
from datetime import datetime
from pathlib import Path
import sys
import types
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

openai_stub = types.ModuleType("openai")


class _AsyncOpenAI:  # pragma: no cover - test stub only
    def __init__(self, *args, **kwargs):
        pass


openai_stub.AsyncOpenAI = _AsyncOpenAI
sys.modules.setdefault("openai", openai_stub)

apprise_stub = types.ModuleType("apprise")


class _Apprise:  # pragma: no cover - test stub only
    def __init__(self, *args, **kwargs):
        pass

    def add(self, *args, **kwargs):
        return True

    async def async_notify(self, *args, **kwargs):
        return True


apprise_stub.Apprise = _Apprise
sys.modules.setdefault("apprise", apprise_stub)

yaml_stub = types.ModuleType("yaml")
yaml_stub.safe_load = lambda *args, **kwargs: {}
sys.modules.setdefault("yaml", yaml_stub)

from src.agents.base import AgentContext, PortfolioInfo
from src.agents.postmarket_chart_monitor import (
    PostmarketChartMonitorAgent,
    is_after_market_close,
)
from src.config import AppConfig, Settings, StockConfig
from src.models.market import MarketCode, StockData


def test_is_after_market_close_cn():
    tz = ZoneInfo("Asia/Shanghai")
    assert not is_after_market_close(
        MarketCode.CN, datetime(2026, 3, 30, 14, 59, tzinfo=tz)
    )
    assert is_after_market_close(
        MarketCode.CN, datetime(2026, 3, 30, 15, 0, tzinfo=tz)
    )


def test_collect_skips_when_not_holding():
    agent = PostmarketChartMonitorAgent(
        bypass_market_hours=True,
        holding_only=True,
    )
    context = AgentContext(
        ai_client=None,  # type: ignore[arg-type]
        notifier=None,  # type: ignore[arg-type]
        config=AppConfig(
            settings=Settings(),
            watchlist=[
                StockConfig(
                    symbol="600519",
                    name="贵州茅台",
                    market=MarketCode.CN,
                )
            ],
        ),
        portfolio=PortfolioInfo(),
    )

    data = asyncio.run(agent.collect(context))
    assert data["stock_data"] is None
    assert "无持仓" in data["skip_reason"]


def test_period_defaults_to_daily_when_invalid():
    agent = PostmarketChartMonitorAgent(period="invalid")
    assert agent.period == "daily"
    assert agent.period_label == "日K"


def test_build_prompt_uses_selected_period():
    agent = PostmarketChartMonitorAgent(period="weekly")
    stock = StockData(
        symbol="600519",
        name="贵州茅台",
        market=MarketCode.CN,
        current_price=1500.0,
        change_pct=1.2,
        change_amount=18.0,
        volume=10000,
        turnover=1500000000,
        open_price=1480.0,
        high_price=1510.0,
        low_price=1475.0,
        prev_close=1482.0,
    )

    _, user_prompt = agent.build_prompt(
        {
            "stock_data": stock,
            "position": {},
            "kline_summary": {},
        },
        None,  # type: ignore[arg-type]
    )

    assert "周K复盘" in user_prompt
    assert "截图周期：周K" in user_prompt
