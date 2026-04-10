from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from typing import Any

from .engine import SimulationResult


class SimulationReporter:
    """Generate human-readable simulation reports."""

    def to_markdown(self, result: SimulationResult) -> str:
        lines = [
            "# Ad Simulation Report",
            "",
            "## Executive Summary",
            f"- Mode: {result.mode.value}",
            f"- Confidence: {result.confidence_level}",
            f"- Risk: {result.risk_assessment}",
            "",
            "## Actual vs Simulated",
            "| Metric | Actual | Simulated | Change % |",
            "|---|---:|---:|---:|",
            f"| ACOS | {result.actual_acos:.2f}% | {result.simulated_acos:.2f}% | {result.acos_improvement_pct:.2f}% |",
            f"| ROAS | {result.actual_roas:.2f} | {result.simulated_roas:.2f} | {result.roas_improvement_pct:.2f}% |",
            f"| Spend | {result.actual_spend:.2f} | {result.simulated_spend:.2f} | {result.spend_change_pct:.2f}% |",
            f"| Sales | {result.actual_sales:.2f} | {result.simulated_sales:.2f} | {result.sales_change_pct:.2f}% |",
            "",
            "## Key Metrics Improvement",
            f"- ACOS improvement: {result.acos_improvement_pct:.2f}%",
            f"- ROAS improvement: {result.roas_improvement_pct:.2f}%",
            "",
            "## Risk Assessment",
            f"- {result.risk_assessment}",
            "",
            "## Recommendation Details",
        ]
        for rec in result.recommendation_details:
            lines.append(
                f"- {rec['keyword_id']}: {rec['direction']} {rec['current_bid']:.2f} -> {rec['suggested_bid']:.2f}"
            )
        lines.extend(["", "## Disclaimer", result.disclaimer])
        return "\n".join(lines)

    def to_chart_data(self, result: SimulationResult) -> dict[str, Any]:
        kpi_cards = [
            {
                "label": "ACOS",
                "actual": result.actual_acos,
                "simulated": result.simulated_acos,
                "change_pct": result.acos_improvement_pct,
            },
            {
                "label": "ROAS",
                "actual": result.actual_roas,
                "simulated": result.simulated_roas,
                "change_pct": result.roas_improvement_pct,
            },
            {
                "label": "Spend",
                "actual": result.actual_spend,
                "simulated": result.simulated_spend,
                "change_pct": result.spend_change_pct,
            },
            {
                "label": "Sales",
                "actual": result.actual_sales,
                "simulated": result.simulated_sales,
                "change_pct": result.sales_change_pct,
            },
        ]
        recommendation_summary = {"total": len(result.recommendation_details), "increases": 0, "decreases": 0, "holds": 0}
        for rec in result.recommendation_details:
            direction = str(rec.get("direction", "")).upper()
            if direction == "INCREASE":
                recommendation_summary["increases"] += 1
            elif direction == "DECREASE":
                recommendation_summary["decreases"] += 1
            else:
                recommendation_summary["holds"] += 1
        return {
            "kpi_cards": kpi_cards,
            "daily_trend": [
                {
                    "date": row.get("date"),
                    "actual_acos": row.get("actual_acos", 0.0),
                    "simulated_acos": row.get("simulated_acos", 0.0),
                }
                for row in result.daily_comparison
            ],
            "recommendation_summary": recommendation_summary,
        }

    def to_dict(self, result: SimulationResult) -> dict[str, Any]:
        return self._serialize(asdict(result))

    def _serialize(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {str(key): self._serialize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._serialize(item) for item in value]
        if isinstance(value, tuple):
            return [self._serialize(item) for item in value]
        return value
