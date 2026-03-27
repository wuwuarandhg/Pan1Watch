from types import SimpleNamespace

from src.core.prediction_metrics import summarize_prediction_outcomes


def test_summarize_prediction_outcomes_computes_hit_rate() -> None:
    rows = [
        SimpleNamespace(
            agent_name="premarket_outlook",
            action="buy",
            outcome_return_pct=3.2,
            outcome_status="evaluated",
        ),
        SimpleNamespace(
            agent_name="daily_report",
            action="reduce",
            outcome_return_pct=-2.4,
            outcome_status="hit_stop",
        ),
        SimpleNamespace(
            agent_name="intraday_monitor",
            action="watch",
            outcome_return_pct=1.1,
            outcome_status="evaluated",
        ),
    ]

    summary = summarize_prediction_outcomes(rows)
    assert summary["evaluated"] == 3
    assert summary["hit_count"] == 3
    assert summary["hit_rate"] == 100.0
    assert len(summary["by_agent"]) == 3


def test_summarize_prediction_outcomes_skips_pending_rows() -> None:
    rows = [
        SimpleNamespace(
            agent_name="premarket_outlook",
            action="buy",
            outcome_return_pct=None,
            outcome_status="pending",
        ),
    ]

    summary = summarize_prediction_outcomes(rows)
    assert summary["evaluated"] == 0
    assert summary["hit_rate"] is None
