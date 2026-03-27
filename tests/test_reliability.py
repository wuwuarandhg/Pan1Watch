from types import SimpleNamespace

from src.core.reliability import (
    calibrate_agent_suggestion,
    summarize_historical_edge,
    summarize_prediction_reliability,
)


def test_summarize_prediction_reliability_tracks_action_bias() -> None:
    rows = [
        SimpleNamespace(
            action="reduce",
            outcome_return_pct=-0.3,
            outcome_status="evaluated",
        ),
        SimpleNamespace(
            action="reduce",
            outcome_return_pct=-0.2,
            outcome_status="evaluated",
        ),
        SimpleNamespace(
            action="reduce",
            outcome_return_pct=0.6,
            outcome_status="evaluated",
        ),
        SimpleNamespace(
            action="hold",
            outcome_return_pct=0.1,
            outcome_status="evaluated",
        ),
        SimpleNamespace(
            action="reduce",
            outcome_return_pct=0.2,
            outcome_status="evaluated",
        ),
    ]

    summary = summarize_prediction_reliability(rows)
    assert summary["sample_size"] == 5
    assert summary["dominant_action"] == "reduce"
    assert summary["dominant_action_ratio"] == 0.8
    assert summary["tier"] in {"low", "very_low", "medium"}


def test_calibrate_agent_suggestion_downgrades_repeated_reduce_bias(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.core.reliability.get_agent_reliability_profile",
        lambda **_: {
            "scope": "stock",
            "stock": {
                "sample_size": 120,
                "hit_rate": 34.0,
                "avg_edge_pct": 0.7,
                "action_counts": {"reduce": 110},
                "tier": "low",
            },
            "effective": {
                "sample_size": 120,
                "hit_rate": 34.0,
                "avg_edge_pct": 0.7,
                "action_counts": {"reduce": 110},
                "tier": "low",
            },
            "market": {},
        },
    )

    suggestion, calibration = calibrate_agent_suggestion(
        suggestion={
            "action": "reduce",
            "action_label": "减仓",
            "reason": "跌破分时支撑",
            "should_alert": True,
        },
        agent_name="intraday_monitor",
        stock_symbol="002410",
        stock_market="CN",
        is_holding=True,
        kline_summary={
            "trend": "震荡",
            "macd_cross": "无",
            "rsi_status": "中性",
            "kdj_status": "中性",
            "volume_ratio": 1.1,
        },
        quote_change_pct=-1.2,
        quality_score=72,
    )

    assert calibration["applied"] is True
    assert suggestion["action"] == "hold"
    assert suggestion["action_label"] == "继续持有"
    assert suggestion["should_alert"] is False
    assert "历史后验校准" in suggestion["reason"]


def test_summarize_historical_edge_penalizes_weak_strategy() -> None:
    summary = summarize_historical_edge(
        sample_size=80,
        win_rate=18.0,
        avg_return_pct=-4.2,
    )

    assert summary["tier"] == "very_low"
    assert summary["penalty_points"] > 0
    assert summary["weight_multiplier"] < 1.0
