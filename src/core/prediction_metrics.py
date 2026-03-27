from __future__ import annotations


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
    if act in {"reduce", "sell", "avoid"}:
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


def summarize_prediction_outcomes(rows: list) -> dict:
    evaluated = []
    by_agent: dict[str, dict] = {}

    for row in rows or []:
        status = str(getattr(row, "outcome_status", "") or "")
        if status not in {"evaluated", "hit_target", "hit_stop"}:
            continue

        ret = _safe_float(getattr(row, "outcome_return_pct", None))
        hit = _is_direction_hit(getattr(row, "action", ""), ret)
        bucket = _direction_bucket(getattr(row, "action", ""))
        evaluated.append((ret, hit, bucket))

        agent = str(getattr(row, "agent_name", "") or "unknown")
        item = by_agent.setdefault(
            agent,
            {
                "agent_name": agent,
                "evaluated": 0,
                "hit_count": 0,
                "avg_return_pct": None,
                "return_sum": 0.0,
            },
        )
        item["evaluated"] += 1
        if hit is True:
            item["hit_count"] += 1
        if ret is not None:
            item["return_sum"] += ret

    total = len(evaluated)
    hit_count = sum(1 for _, hit, _ in evaluated if hit is True)
    returns = [ret for ret, _, _ in evaluated if ret is not None]
    bullish = [hit for _, hit, bucket in evaluated if bucket == "bullish" and hit is not None]
    bearish = [hit for _, hit, bucket in evaluated if bucket == "bearish" and hit is not None]
    neutral = [hit for _, hit, bucket in evaluated if bucket == "neutral" and hit is not None]

    agent_rows = []
    for _, item in sorted(by_agent.items(), key=lambda kv: (-kv[1]["evaluated"], kv[0])):
        avg_return_pct = (
            round(item["return_sum"] / item["evaluated"], 2) if item["evaluated"] > 0 else None
        )
        agent_rows.append(
            {
                "agent_name": item["agent_name"],
                "evaluated": item["evaluated"],
                "hit_count": item["hit_count"],
                "hit_rate": round(item["hit_count"] / item["evaluated"] * 100.0, 2)
                if item["evaluated"] > 0
                else None,
                "avg_return_pct": avg_return_pct,
            }
        )

    return {
        "evaluated": total,
        "hit_count": hit_count,
        "hit_rate": round(hit_count / total * 100.0, 2) if total > 0 else None,
        "avg_return_pct": round(sum(returns) / len(returns), 2) if returns else None,
        "bullish_hit_rate": round(sum(1 for x in bullish if x) / len(bullish) * 100.0, 2)
        if bullish
        else None,
        "bearish_hit_rate": round(sum(1 for x in bearish if x) / len(bearish) * 100.0, 2)
        if bearish
        else None,
        "neutral_hit_rate": round(sum(1 for x in neutral if x) / len(neutral) * 100.0, 2)
        if neutral
        else None,
        "hit_rule": {
            "bullish": "buy/add/hold 在 horizon 内收益率 > 0.5%",
            "bearish": "reduce/sell/avoid 在 horizon 内收益率 < -0.5%",
            "neutral": "watch/alert 在 horizon 内波动幅度 <= 2%",
        },
        "by_agent": agent_rows,
    }
