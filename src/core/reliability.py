from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache


EVALUATED_OUTCOME_STATUSES = ("evaluated", "hit_target", "hit_stop")
AGGRESSIVE_ACTIONS = {"buy", "add", "reduce", "sell", "avoid"}
BEARISH_ACTIONS = {"reduce", "sell", "avoid"}
BULLISH_ACTIONS = {"buy", "add"}


def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _direction_bucket(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"buy", "add", "hold"}:
        return "bullish"
    if act in BEARISH_ACTIONS:
        return "bearish"
    return "neutral"


def _is_direction_hit(action: str, outcome_return_pct: float | None) -> bool | None:
    ret = _safe_float(outcome_return_pct)
    if ret is None:
        return None
    bucket = _direction_bucket(action)
    if bucket == "bullish":
        return ret > 0.5
    if bucket == "bearish":
        return ret < -0.5
    return abs(ret) <= 2.0


def _directional_edge(action: str, outcome_return_pct: float | None) -> float | None:
    ret = _safe_float(outcome_return_pct)
    if ret is None:
        return None
    bucket = _direction_bucket(action)
    if bucket == "bullish":
        return ret
    if bucket == "bearish":
        return -ret
    return -abs(ret)


def _get_attr(row, name: str, default=None):
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def summarize_prediction_reliability(rows: list) -> dict:
    sample_size = 0
    hit_count = 0
    edge_sum = 0.0
    edge_count = 0
    action_counts: dict[str, int] = {}

    for row in rows or []:
        status = str(_get_attr(row, "outcome_status", "") or "").strip().lower()
        if status not in EVALUATED_OUTCOME_STATUSES:
            continue
        action = str(_get_attr(row, "action", "watch") or "watch").strip().lower()
        ret = _safe_float(_get_attr(row, "outcome_return_pct"))
        if ret is None:
            continue
        sample_size += 1
        action_counts[action] = action_counts.get(action, 0) + 1
        if _is_direction_hit(action, ret) is True:
            hit_count += 1
        edge = _directional_edge(action, ret)
        if edge is not None:
            edge_sum += edge
            edge_count += 1

    dominant_action = ""
    dominant_action_count = 0
    if action_counts:
        dominant_action, dominant_action_count = max(
            action_counts.items(),
            key=lambda item: (item[1], item[0]),
        )
    hit_rate = (hit_count / sample_size * 100.0) if sample_size > 0 else None
    avg_edge_pct = (edge_sum / edge_count) if edge_count > 0 else None
    dominant_action_ratio = (
        dominant_action_count / sample_size if sample_size > 0 else None
    )

    if sample_size < 5:
        tier = "insufficient"
    elif (hit_rate or 0.0) < 28.0 or (avg_edge_pct or 0.0) < -0.3:
        tier = "very_low"
    elif (hit_rate or 0.0) < 40.0 or (avg_edge_pct or 0.0) < 0.6:
        tier = "low"
    elif (hit_rate or 0.0) < 55.0 or (avg_edge_pct or 0.0) < 1.2:
        tier = "medium"
    else:
        tier = "high"

    return {
        "sample_size": sample_size,
        "hit_count": hit_count,
        "hit_rate": round(hit_rate, 2) if hit_rate is not None else None,
        "avg_edge_pct": round(avg_edge_pct, 3) if avg_edge_pct is not None else None,
        "dominant_action": dominant_action,
        "dominant_action_ratio": round(dominant_action_ratio, 4)
        if dominant_action_ratio is not None
        else None,
        "action_counts": action_counts,
        "tier": tier,
    }


def summarize_historical_edge(
    sample_size: int,
    win_rate: float | None,
    avg_return_pct: float | None,
) -> dict:
    wins = int(round((float(win_rate or 0.0) / 100.0) * float(sample_size or 0)))
    avg_ret = _safe_float(avg_return_pct) or 0.0
    rate = _safe_float(win_rate) or 0.0

    if sample_size < 5:
        tier = "insufficient"
        penalty_points = 0.0
        bonus_points = 0.0
        weight_multiplier = 1.0
    elif avg_ret <= -3.0 or rate < 22.0:
        tier = "very_low"
        penalty_points = 7.5 if sample_size >= 20 else 6.0
        bonus_points = 0.0
        weight_multiplier = 0.84
    elif avg_ret <= -1.5 or rate < 32.0:
        tier = "low"
        penalty_points = 5.0 if sample_size >= 16 else 4.0
        bonus_points = 0.0
        weight_multiplier = 0.9
    elif avg_ret < 0.0 or rate < 42.0:
        tier = "neutral"
        penalty_points = 2.0
        bonus_points = 0.0
        weight_multiplier = 0.97
    elif avg_ret >= 1.5 and rate >= 58.0:
        tier = "high"
        penalty_points = 0.0
        bonus_points = 2.5 if sample_size >= 12 else 1.5
        weight_multiplier = 1.05
    elif avg_ret >= 0.5 and rate >= 50.0:
        tier = "positive"
        penalty_points = 0.0
        bonus_points = 1.0
        weight_multiplier = 1.02
    else:
        tier = "neutral"
        penalty_points = 0.0
        bonus_points = 0.0
        weight_multiplier = 1.0

    return {
        "sample_size": int(sample_size or 0),
        "wins": wins,
        "win_rate": round(rate, 2) if sample_size > 0 else None,
        "avg_return_pct": round(avg_ret, 3) if sample_size > 0 else None,
        "tier": tier,
        "penalty_points": round(penalty_points, 3),
        "bonus_points": round(bonus_points, 3),
        "weight_multiplier": round(weight_multiplier, 4),
    }


@lru_cache(maxsize=256)
def get_agent_reliability_profile(
    agent_name: str,
    stock_symbol: str,
    stock_market: str,
    *,
    lookback_days: int = 240,
    min_stock_samples: int = 12,
    min_market_samples: int = 24,
) -> dict:
    from src.web.database import SessionLocal
    from src.web.models import AgentPredictionOutcome

    agent = (agent_name or "").strip()
    symbol = (stock_symbol or "").strip()
    market = (stock_market or "CN").strip().upper() or "CN"
    if not agent or not symbol:
        empty = summarize_prediction_reliability([])
        return {"effective": empty, "stock": empty, "market": empty, "scope": "none"}

    cutoff = (date.today() - timedelta(days=max(30, int(lookback_days)))).strftime(
        "%Y-%m-%d"
    )
    db = SessionLocal()
    try:
        stock_rows = (
            db.query(AgentPredictionOutcome)
            .filter(
                AgentPredictionOutcome.agent_name == agent,
                AgentPredictionOutcome.stock_symbol == symbol,
                AgentPredictionOutcome.stock_market == market,
                AgentPredictionOutcome.prediction_date >= cutoff,
                AgentPredictionOutcome.outcome_status.in_(EVALUATED_OUTCOME_STATUSES),
            )
            .all()
        )
        market_rows = (
            db.query(AgentPredictionOutcome)
            .filter(
                AgentPredictionOutcome.agent_name == agent,
                AgentPredictionOutcome.stock_market == market,
                AgentPredictionOutcome.prediction_date >= cutoff,
                AgentPredictionOutcome.outcome_status.in_(EVALUATED_OUTCOME_STATUSES),
            )
            .all()
        )
    finally:
        db.close()

    stock_summary = summarize_prediction_reliability(stock_rows)
    market_summary = summarize_prediction_reliability(market_rows)
    if stock_summary["sample_size"] >= max(5, int(min_stock_samples)):
        effective = dict(stock_summary)
        scope = "stock"
    elif market_summary["sample_size"] >= max(8, int(min_market_samples)):
        effective = dict(market_summary)
        scope = "market"
    elif stock_summary["sample_size"] >= market_summary["sample_size"]:
        effective = dict(stock_summary)
        scope = "stock_partial"
    else:
        effective = dict(market_summary)
        scope = "market_partial"

    return {
        "stock": stock_summary,
        "market": market_summary,
        "effective": effective,
        "scope": scope,
    }


def _action_ratio(summary: dict | None, action: str) -> float:
    data = summary if isinstance(summary, dict) else {}
    sample_size = int(data.get("sample_size") or 0)
    if sample_size <= 0:
        return 0.0
    counts = data.get("action_counts") if isinstance(data.get("action_counts"), dict) else {}
    return float(counts.get((action or "").strip().lower(), 0)) / float(sample_size)


def compute_action_conviction(
    *,
    action: str,
    kline_summary: dict | None = None,
    quote_change_pct: float | None = None,
    quality_score: float | None = None,
) -> dict:
    action_norm = (action or "").strip().lower()
    kline = kline_summary if isinstance(kline_summary, dict) else {}
    bullish_score = 0.0
    bearish_score = 0.0

    trend = str(kline.get("trend") or "").strip()
    if "多头" in trend:
        bullish_score += 2.5
    elif "空头" in trend:
        bearish_score += 2.5

    macd = str(kline.get("macd_cross") or kline.get("macd_status") or "").strip()
    if "金叉" in macd or "多头" in macd:
        bullish_score += 1.5
    elif "死叉" in macd or "空头" in macd:
        bearish_score += 1.5

    rsi_status = str(kline.get("rsi_status") or "").strip()
    if "超卖" in rsi_status or "低位" in rsi_status:
        bullish_score += 1.0
    elif "超买" in rsi_status or "高位" in rsi_status:
        bearish_score += 1.0

    kdj_status = str(kline.get("kdj_status") or "").strip()
    if "金叉" in kdj_status:
        bullish_score += 1.0
    elif "死叉" in kdj_status:
        bearish_score += 1.0

    change_pct = _safe_float(quote_change_pct)
    if change_pct is not None:
        if change_pct >= 4.0:
            bullish_score += 0.6
        elif change_pct <= -4.0:
            bearish_score += 0.6

    volume_ratio = _safe_float(kline.get("volume_ratio"))
    if volume_ratio is not None and volume_ratio >= 1.8:
        if bullish_score >= bearish_score:
            bullish_score += 0.5
        else:
            bearish_score += 0.5

    score_quality = _safe_float(quality_score)
    if score_quality is not None and score_quality >= 85:
        if bullish_score > bearish_score:
            bullish_score += 0.3
        elif bearish_score > bullish_score:
            bearish_score += 0.3

    if action_norm in BEARISH_ACTIONS:
        supportive_score = bearish_score
        opposing_score = bullish_score
    elif action_norm in BULLISH_ACTIONS:
        supportive_score = bullish_score
        opposing_score = bearish_score
    else:
        supportive_score = min(bullish_score, bearish_score)
        opposing_score = max(bullish_score, bearish_score)

    return {
        "bullish_score": round(bullish_score, 3),
        "bearish_score": round(bearish_score, 3),
        "supportive_score": round(supportive_score, 3),
        "opposing_score": round(opposing_score, 3),
    }


def calibrate_agent_suggestion(
    *,
    suggestion: dict,
    agent_name: str,
    stock_symbol: str,
    stock_market: str,
    is_holding: bool,
    kline_summary: dict | None = None,
    quote_change_pct: float | None = None,
    quality_score: float | None = None,
) -> tuple[dict, dict]:
    base = dict(suggestion or {})
    action = str(base.get("action") or "watch").strip().lower()
    profile = get_agent_reliability_profile(
        agent_name=agent_name,
        stock_symbol=stock_symbol,
        stock_market=stock_market,
    )
    stock_profile = profile.get("stock") if isinstance(profile.get("stock"), dict) else {}
    effective = profile.get("effective") if isinstance(profile.get("effective"), dict) else {}
    conviction = compute_action_conviction(
        action=action,
        kline_summary=kline_summary,
        quote_change_pct=quote_change_pct,
        quality_score=quality_score,
    )

    if not is_holding or action not in AGGRESSIVE_ACTIONS:
        return base, {
            "applied": False,
            "profile_scope": profile.get("scope"),
            "effective": effective,
            "stock": stock_profile,
            "conviction": conviction,
        }

    stock_action_ratio = _action_ratio(stock_profile, action)
    effective_tier = str(effective.get("tier") or "insufficient")
    effective_samples = int(effective.get("sample_size") or 0)
    supportive_score = float(conviction.get("supportive_score") or 0.0)
    opposing_score = float(conviction.get("opposing_score") or 0.0)

    reason = ""
    if (
        action in BEARISH_ACTIONS
        and int(stock_profile.get("sample_size") or 0) >= 20
        and stock_action_ratio >= 0.75
        and float(stock_profile.get("hit_rate") or 0.0) < 45.0
        and float(stock_profile.get("avg_edge_pct") or 0.0) < 1.2
        and supportive_score < 4.5
    ):
        reason = "该股票历史上同类减仓建议过于集中，但命中率偏低，当前技术面不足以支撑继续激进处理"
    elif (
        effective_tier in {"very_low", "low"}
        and effective_samples >= 10
        and supportive_score < 4.0
        and opposing_score >= supportive_score - 0.3
    ):
        reason = "该 Agent 在相近样本上的后验表现偏弱，当前信号强度不够"

    if not reason:
        return base, {
            "applied": False,
            "profile_scope": profile.get("scope"),
            "effective": effective,
            "stock": stock_profile,
            "conviction": conviction,
        }

    new_action = action
    new_label = str(base.get("action_label") or "").strip()
    should_alert = bool(base.get("should_alert"))
    if action == "sell":
        if supportive_score >= 3.5:
            new_action = "reduce"
            new_label = "谨慎减仓"
            should_alert = True
        else:
            new_action = "hold"
            new_label = "继续持有"
            should_alert = False
    elif action == "reduce":
        new_action = "hold"
        new_label = "继续持有"
        should_alert = False
    elif action in {"buy", "add"}:
        new_action = "hold"
        new_label = "继续持有"
        should_alert = False
    elif action == "avoid":
        new_action = "watch"
        new_label = "继续观察"
        should_alert = False

    note = f"历史后验校准：{reason}。"
    original_reason = str(base.get("reason") or "").strip()
    base["action"] = new_action
    base["action_label"] = new_label or base.get("action_label") or "继续持有"
    base["should_alert"] = should_alert
    base["reason"] = (
        f"{original_reason}；{note}" if original_reason else note
    )[:220]

    return base, {
        "applied": True,
        "original_action": action,
        "adjusted_action": new_action,
        "reason": reason,
        "profile_scope": profile.get("scope"),
        "effective": effective,
        "stock": stock_profile,
        "conviction": conviction,
    }


@lru_cache(maxsize=128)
def load_strategy_edge_map(
    stock_market: str,
    *,
    lookback_days: int = 240,
    horizons: tuple[int, ...] = (3, 5, 10),
    min_samples: int = 8,
) -> dict[str, dict]:
    from sqlalchemy import case, func

    from src.web.database import SessionLocal
    from src.web.models import StrategyOutcome

    market = (stock_market or "CN").strip().upper() or "CN"
    safe_horizons = tuple(sorted({int(x) for x in horizons if int(x) > 0}))
    if not safe_horizons:
        safe_horizons = (3, 5, 10)
    cutoff = (date.today() - timedelta(days=max(30, int(lookback_days)))).strftime(
        "%Y-%m-%d"
    )

    db = SessionLocal()
    try:
        rows = (
            db.query(
                StrategyOutcome.strategy_code,
                StrategyOutcome.stock_market,
                func.count(StrategyOutcome.id).label("sample_size"),
                func.avg(StrategyOutcome.outcome_return_pct).label("avg_ret"),
                (
                    100.0
                    * func.avg(
                        case((StrategyOutcome.outcome_return_pct > 0, 1.0), else_=0.0)
                    )
                ).label("win_rate"),
            )
            .filter(
                StrategyOutcome.outcome_status.in_(EVALUATED_OUTCOME_STATUSES),
                StrategyOutcome.target_date >= cutoff,
                StrategyOutcome.horizon_days.in_(safe_horizons),
            )
            .group_by(StrategyOutcome.strategy_code, StrategyOutcome.stock_market)
            .all()
        )
    finally:
        db.close()

    by_market: dict[tuple[str, str], dict] = {}
    by_all: dict[str, dict] = {}
    for code, row_market, sample_size, avg_ret, win_rate in rows:
        key_code = str(code or "").strip()
        key_market = (row_market or "ALL").strip().upper() or "ALL"
        summary = summarize_historical_edge(
            int(sample_size or 0),
            _safe_float(win_rate),
            _safe_float(avg_ret),
        )
        by_market[(key_code, key_market)] = summary
        all_row = by_all.setdefault(
            key_code,
            {
                "sample_size": 0,
                "ret_weighted_sum": 0.0,
                "win_weighted_sum": 0.0,
            },
        )
        all_row["sample_size"] += int(sample_size or 0)
        all_row["ret_weighted_sum"] += float(_safe_float(avg_ret) or 0.0) * int(
            sample_size or 0
        )
        all_row["win_weighted_sum"] += float(_safe_float(win_rate) or 0.0) * int(
            sample_size or 0
        )

    result: dict[str, dict] = {}
    codes = {code for code, _ in by_market.keys()} | set(by_all.keys())
    for code in codes:
        market_summary = by_market.get((code, market))
        all_metrics = by_all.get(code)
        all_summary = None
        if all_metrics and int(all_metrics.get("sample_size") or 0) > 0:
            sample_size = int(all_metrics.get("sample_size") or 0)
            all_summary = summarize_historical_edge(
                sample_size,
                float(all_metrics.get("win_weighted_sum") or 0.0) / sample_size,
                float(all_metrics.get("ret_weighted_sum") or 0.0) / sample_size,
            )

        chosen = market_summary
        scope = "market"
        if market_summary is None or int(market_summary.get("sample_size") or 0) < max(
            4, int(min_samples)
        ):
            if all_summary is not None and int(all_summary.get("sample_size") or 0) >= max(
                4, int(min_samples)
            ):
                chosen = all_summary
                scope = "all"
        if chosen is None:
            chosen = market_summary or all_summary or summarize_historical_edge(0, None, None)
            scope = "fallback"
        result[code] = {
            **chosen,
            "scope": scope,
            "market": market,
        }
    return result


@lru_cache(maxsize=128)
def get_candidate_source_edge(
    candidate_source: str,
    stock_market: str,
    *,
    lookback_days: int = 240,
    horizons: tuple[int, ...] = (3, 5, 10),
    min_samples: int = 12,
) -> dict:
    from sqlalchemy import case, func

    from src.web.database import SessionLocal
    from src.web.models import EntryCandidateOutcome

    source = (candidate_source or "").strip().lower()
    market = (stock_market or "CN").strip().upper() or "CN"
    if not source:
        return summarize_historical_edge(0, None, None)

    safe_horizons = tuple(sorted({int(x) for x in horizons if int(x) > 0}))
    if not safe_horizons:
        safe_horizons = (3, 5, 10)
    cutoff = (date.today() - timedelta(days=max(30, int(lookback_days)))).strftime(
        "%Y-%m-%d"
    )

    db = SessionLocal()
    try:
        row = (
            db.query(
                func.count(EntryCandidateOutcome.id).label("sample_size"),
                func.avg(EntryCandidateOutcome.outcome_return_pct).label("avg_ret"),
                (
                    100.0
                    * func.avg(
                        case((EntryCandidateOutcome.outcome_return_pct > 0, 1.0), else_=0.0)
                    )
                ).label("win_rate"),
            )
            .filter(
                EntryCandidateOutcome.candidate_source == source,
                EntryCandidateOutcome.stock_market == market,
                EntryCandidateOutcome.snapshot_date >= cutoff,
                EntryCandidateOutcome.horizon_days.in_(safe_horizons),
                EntryCandidateOutcome.outcome_status.in_(EVALUATED_OUTCOME_STATUSES),
            )
            .first()
        )
        fallback = (
            db.query(
                func.count(EntryCandidateOutcome.id).label("sample_size"),
                func.avg(EntryCandidateOutcome.outcome_return_pct).label("avg_ret"),
                (
                    100.0
                    * func.avg(
                        case((EntryCandidateOutcome.outcome_return_pct > 0, 1.0), else_=0.0)
                    )
                ).label("win_rate"),
            )
            .filter(
                EntryCandidateOutcome.candidate_source == source,
                EntryCandidateOutcome.snapshot_date >= cutoff,
                EntryCandidateOutcome.horizon_days.in_(safe_horizons),
                EntryCandidateOutcome.outcome_status.in_(EVALUATED_OUTCOME_STATUSES),
            )
            .first()
        )
    finally:
        db.close()

    summary = summarize_historical_edge(
        int((row.sample_size if row else 0) or 0),
        _safe_float(row.win_rate if row else None),
        _safe_float(row.avg_ret if row else None),
    )
    if int(summary.get("sample_size") or 0) >= max(4, int(min_samples)):
        return {**summary, "scope": "market", "candidate_source": source, "market": market}

    fallback_summary = summarize_historical_edge(
        int((fallback.sample_size if fallback else 0) or 0),
        _safe_float(fallback.win_rate if fallback else None),
        _safe_float(fallback.avg_ret if fallback else None),
    )
    if int(fallback_summary.get("sample_size") or 0) > 0:
        return {
            **fallback_summary,
            "scope": "all",
            "candidate_source": source,
            "market": market,
        }

    return {**summary, "scope": "fallback", "candidate_source": source, "market": market}
