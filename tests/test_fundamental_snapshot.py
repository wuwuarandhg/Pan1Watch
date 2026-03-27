from src.core.fundamentals import build_fundamental_snapshot


def test_build_fundamental_snapshot_from_quote_like_payload() -> None:
    snapshot = build_fundamental_snapshot(
        {
            "symbol": "600519",
            "name": "贵州茅台",
            "market": "CN",
            "pe_ratio": 18.5,
            "turnover_rate": 2.8,
            "total_market_value": 22000,
            "revenue_yoy": 14.2,
            "profit_yoy": 16.8,
            "roe": 28.0,
            "gross_margin": 41.5,
            "operating_cashflow_to_profit": 1.15,
            "peg_ratio": 1.1,
        }
    )
    assert snapshot["available"] is True
    assert snapshot["valuation_band"] == "均衡"
    assert snapshot["size_label"] in {"超大盘", "大盘"}
    assert snapshot["quality_score"] is not None
    assert snapshot["composite_score"] >= 60


def test_build_fundamental_snapshot_marks_missing_metrics() -> None:
    snapshot = build_fundamental_snapshot(
        {
            "symbol": "AAPL",
            "market": "US",
            "pe_ratio": 55.0,
            "turnover_rate": 0.5,
            "total_market_value": 2.5e12,
        }
    )
    assert snapshot["valuation_band"] == "高估"
    assert "revenue_yoy" in snapshot["missing_metrics"]
    assert snapshot["quality_score"] is None
