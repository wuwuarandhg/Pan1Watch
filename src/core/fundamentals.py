from __future__ import annotations

from dataclasses import asdict, is_dataclass


_DEFAULT_MISSING_METRICS = [
    "revenue_yoy",
    "profit_yoy",
    "roe",
    "gross_margin",
    "operating_cashflow_to_profit",
    "peg_ratio",
]


def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _get_value(data, key: str):
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get(key)
    return getattr(data, key, None)


def _to_mapping(data) -> dict:
    if data is None:
        return {}
    if isinstance(data, dict):
        return dict(data)
    if is_dataclass(data):
        return asdict(data)
    out = {}
    for key in (
        "symbol",
        "name",
        "market",
        "exchange",
        "current_price",
        "change_pct",
        "volume",
        "turnover",
        "turnover_rate",
        "pe_ratio",
        "total_market_value",
        "circulating_market_value",
        "revenue_yoy",
        "profit_yoy",
        "roe",
        "gross_margin",
        "operating_cashflow_to_profit",
        "peg_ratio",
    ):
        value = getattr(data, key, None)
        if value is not None:
            out[key] = value
    return out


def _market_code(value) -> str:
    text = str(value or "CN").strip().upper()
    return text or "CN"


def _market_cap_bucket(value: float | None, market: str) -> tuple[str, float | None]:
    if value is None or value <= 0:
        return "未知", None

    if market == "CN" and value < 100000:
        amount_yi = value
    else:
        amount_yi = value / 1e8

    if amount_yi >= 5000:
        return "超大盘", amount_yi
    if amount_yi >= 1500:
        return "大盘", amount_yi
    if amount_yi >= 400:
        return "中盘", amount_yi
    return "小盘", amount_yi


def _score_pe(pe_ratio: float | None) -> tuple[int | None, str, str]:
    if pe_ratio is None or pe_ratio <= 0:
        return None, "未知", "市盈率缺失，暂无法判断估值区间"
    if pe_ratio <= 15:
        return 86, "偏低", f"PE {pe_ratio:.2f}，估值偏低"
    if pe_ratio <= 28:
        return 68, "均衡", f"PE {pe_ratio:.2f}，估值处于均衡区间"
    if pe_ratio <= 45:
        return 44, "偏贵", f"PE {pe_ratio:.2f}，估值开始偏高"
    return 24, "高估", f"PE {pe_ratio:.2f}，估值显著偏高"


def _score_turnover_rate(turnover_rate: float | None) -> tuple[int | None, str, str]:
    if turnover_rate is None or turnover_rate < 0:
        return None, "未知", "换手率缺失，流动性活跃度未知"
    if turnover_rate >= 5:
        return 86, "活跃", f"换手率 {turnover_rate:.2f}%，资金活跃"
    if turnover_rate >= 2:
        return 70, "温和活跃", f"换手率 {turnover_rate:.2f}%，流动性尚可"
    if turnover_rate >= 0.8:
        return 58, "一般", f"换手率 {turnover_rate:.2f}%，流动性一般"
    return 42, "偏低", f"换手率 {turnover_rate:.2f}%，活跃度偏弱"


def _score_growth_metric(
    value: float | None,
    *,
    high: float,
    base: float,
    label: str,
    suffix: str = "%",
) -> tuple[int | None, str]:
    if value is None:
        return None, f"{label}缺失"
    if value >= high:
        return 82, f"{label} {value:.2f}{suffix}，表现较强"
    if value >= base:
        return 65, f"{label} {value:.2f}{suffix}，表现稳健"
    if value >= 0:
        return 50, f"{label} {value:.2f}{suffix}，增速一般"
    return 28, f"{label} {value:.2f}{suffix}，表现偏弱"


def build_fundamental_snapshot(data) -> dict:
    raw = _to_mapping(data)
    market = _market_code(raw.get("market"))

    pe_ratio = _safe_float(raw.get("pe_ratio"))
    turnover_rate = _safe_float(raw.get("turnover_rate"))
    total_market_value = _safe_float(raw.get("total_market_value"))
    circulating_market_value = _safe_float(raw.get("circulating_market_value"))
    revenue_yoy = _safe_float(raw.get("revenue_yoy"))
    profit_yoy = _safe_float(raw.get("profit_yoy"))
    roe = _safe_float(raw.get("roe"))
    gross_margin = _safe_float(raw.get("gross_margin"))
    operating_cashflow_to_profit = _safe_float(raw.get("operating_cashflow_to_profit"))
    peg_ratio = _safe_float(raw.get("peg_ratio"))

    valuation_score, valuation_band, pe_note = _score_pe(pe_ratio)
    liquidity_score, turnover_band, turnover_note = _score_turnover_rate(turnover_rate)
    size_label, market_cap_yi = _market_cap_bucket(total_market_value, market)

    factors: list[dict] = [
        {
            "key": "pe_ratio",
            "label": "市盈率",
            "value": pe_ratio,
            "score": valuation_score,
            "band": valuation_band,
            "note": pe_note,
        },
        {
            "key": "turnover_rate",
            "label": "换手率",
            "value": turnover_rate,
            "score": liquidity_score,
            "band": turnover_band,
            "note": turnover_note,
        },
        {
            "key": "market_cap",
            "label": "总市值",
            "value": total_market_value,
            "value_yi": market_cap_yi,
            "band": size_label,
            "note": f"总市值分层: {size_label}",
        },
    ]

    quality_scores: list[int] = []
    quality_notes: list[str] = []
    for key, label, high, base in (
        ("revenue_yoy", "营收同比", 15.0, 5.0),
        ("profit_yoy", "净利润同比", 15.0, 5.0),
        ("roe", "ROE", 15.0, 8.0),
        ("gross_margin", "毛利率", 35.0, 20.0),
    ):
        score, note = _score_growth_metric(
            _safe_float(raw.get(key)),
            high=high,
            base=base,
            label=label,
        )
        factors.append(
            {
                "key": key,
                "label": label,
                "value": _safe_float(raw.get(key)),
                "score": score,
                "note": note,
            }
        )
        if score is not None:
            quality_scores.append(score)
            quality_notes.append(note)

    if operating_cashflow_to_profit is not None:
        if operating_cashflow_to_profit >= 1.0:
            cash_score = 80
            cash_note = f"经营现金/利润 {operating_cashflow_to_profit:.2f}，现金质量较好"
        elif operating_cashflow_to_profit >= 0.7:
            cash_score = 62
            cash_note = f"经营现金/利润 {operating_cashflow_to_profit:.2f}，现金质量尚可"
        else:
            cash_score = 35
            cash_note = f"经营现金/利润 {operating_cashflow_to_profit:.2f}，现金质量偏弱"
    else:
        cash_score = None
        cash_note = "经营现金/利润缺失"
    factors.append(
        {
            "key": "operating_cashflow_to_profit",
            "label": "经营现金/利润",
            "value": operating_cashflow_to_profit,
            "score": cash_score,
            "note": cash_note,
        }
    )
    if cash_score is not None:
        quality_scores.append(cash_score)
        quality_notes.append(cash_note)

    if peg_ratio is not None and peg_ratio > 0:
        if peg_ratio <= 1:
            peg_score = 82
            peg_note = f"PEG {peg_ratio:.2f}，成长与估值匹配较优"
        elif peg_ratio <= 2:
            peg_score = 60
            peg_note = f"PEG {peg_ratio:.2f}，成长估值匹配一般"
        else:
            peg_score = 34
            peg_note = f"PEG {peg_ratio:.2f}，成长性未能覆盖估值"
    else:
        peg_score = None
        peg_note = "PEG 缺失"
    factors.append(
        {
            "key": "peg_ratio",
            "label": "PEG",
            "value": peg_ratio,
            "score": peg_score,
            "note": peg_note,
        }
    )
    if peg_score is not None:
        quality_scores.append(peg_score)
        quality_notes.append(peg_note)

    valuation_component = valuation_score if valuation_score is not None else 55
    liquidity_component = liquidity_score if liquidity_score is not None else 50
    quality_score = (
        round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None
    )
    composite_inputs = [valuation_component * 0.45, liquidity_component * 0.15]
    if quality_score is not None:
        composite_inputs.append(float(quality_score) * 0.40)
    else:
        composite_inputs.append(52.0 * 0.40)
    composite_score = round(sum(composite_inputs), 2)

    missing_metrics = [
        key for key in _DEFAULT_MISSING_METRICS if _safe_float(raw.get(key)) is None
    ]
    available = any(
        x is not None
        for x in (
            pe_ratio,
            turnover_rate,
            total_market_value,
            revenue_yoy,
            profit_yoy,
            roe,
            gross_margin,
            operating_cashflow_to_profit,
            peg_ratio,
        )
    )

    summary_parts = []
    if valuation_band != "未知":
        summary_parts.append(f"估值{valuation_band}")
    if size_label != "未知":
        summary_parts.append(size_label)
    if turnover_band != "未知":
        summary_parts.append(f"流动性{turnover_band}")
    if quality_score is not None:
        if quality_score >= 72:
            summary_parts.append("财务质量较强")
        elif quality_score >= 55:
            summary_parts.append("财务质量中性")
        else:
            summary_parts.append("财务质量偏弱")
    summary = "，".join(summary_parts) if summary_parts else "基本面因子暂缺，当前以估值与流动性因子为主"

    return {
        "symbol": str(raw.get("symbol") or ""),
        "name": str(raw.get("name") or ""),
        "market": market,
        "available": available,
        "composite_score": composite_score,
        "valuation_score": valuation_score,
        "quality_score": quality_score,
        "liquidity_score": liquidity_score,
        "valuation_band": valuation_band,
        "size_label": size_label,
        "turnover_band": turnover_band,
        "pe_ratio": pe_ratio,
        "turnover_rate": turnover_rate,
        "total_market_value": total_market_value,
        "circulating_market_value": circulating_market_value,
        "market_cap_yi": market_cap_yi,
        "summary": summary,
        "factors": factors,
        "quality_notes": quality_notes[:6],
        "missing_metrics": missing_metrics,
    }
