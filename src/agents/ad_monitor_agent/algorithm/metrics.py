from __future__ import annotations

from math import exp

from .models import ConfidenceLevel


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_acos(spend: float, sales: float) -> float:
    return _safe_div(spend, sales) * 100.0


def calculate_roas(sales: float, spend: float) -> float:
    return _safe_div(sales, spend)


def calculate_tacos(spend: float, total_sales: float) -> float:
    return _safe_div(spend, total_sales) * 100.0


def calculate_cpc(spend: float, clicks: int) -> float:
    return _safe_div(spend, clicks)


def calculate_ctr(clicks: int, impressions: int) -> float:
    return _safe_div(clicks, impressions) * 100.0


def calculate_cvr(orders: int | float, clicks: int | float) -> float:
    return _safe_div(orders, clicks) * 100.0


def bayesian_smoothed_cvr(
    orders: int,
    clicks: int,
    prior_cvr: float = 0.05,
    prior_weight: float = 20.0,
) -> float:
    return (orders + prior_weight * prior_cvr) / (clicks + prior_weight) if (clicks + prior_weight) else 0.0


def get_confidence_level(orders: int | float, clicks: int | float, spend: float) -> ConfidenceLevel:
    if orders >= 20 and clicks >= 200 and spend >= 100:
        return ConfidenceLevel.HIGH
    if orders >= 10 and clicks >= 100 and spend >= 50:
        return ConfidenceLevel.MEDIUM_HIGH
    if orders >= 5 and clicks >= 50 and spend >= 25:
        return ConfidenceLevel.MEDIUM
    if orders >= 2 and clicks >= 20:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.VERY_LOW


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def placement_efficiency_score(
    roas_norm: float,
    acos_norm: float,
    cvr_norm: float,
    cpc_norm: float,
) -> float:
    roas_norm = _clamp01(roas_norm)
    acos_norm = _clamp01(acos_norm)
    cvr_norm = _clamp01(cvr_norm)
    cpc_norm = _clamp01(cpc_norm)
    return (roas_norm * 0.35) + ((1 - acos_norm) * 0.25) + (cvr_norm * 0.25) + ((1 - cpc_norm) * 0.15)


def normalize(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return _clamp01((value - minimum) / (maximum - minimum))


def decayed_weight(days_ago: int, half_life: float = 30.0) -> float:
    if days_ago < 0:
        days_ago = 0
    return exp(-(days_ago / half_life))
