from __future__ import annotations

import json
import pathlib

import pytest

from src.agents.ad_monitor_agent.simulation import (
    HistoricalDataLoader,
    SimulationConfig,
    SimulationEngine,
    SimulationMode,
    SimulationReporter,
)
from src.agents.ad_monitor_agent.simulation.data_loader import SimulationInput


class TestDataLoader:
    def test_generate_sample_data_produces_valid_objects(self):
        loader = HistoricalDataLoader()
        sample = loader.generate_sample_data(num_campaigns=2, num_keywords_per=3, days=30)
        assert isinstance(sample, SimulationInput)
        assert len(sample.campaigns) == 2
        assert len(sample.ad_groups) == 2
        assert len(sample.keywords) == 6
        assert len(sample.search_terms) == 6
        assert len(sample.hourly_data) == 24
        assert len(sample.placement_data) == 6
        assert sample.keywords[0].bid_history

    def test_load_from_dict_converts_correctly(self):
        loader = HistoricalDataLoader()
        loaded = loader.load_from_dict(
            {
                "campaigns": [{"campaign_id": "c1", "name": "Camp 1", "budget": 100, "clicks": 20, "orders": 4, "spend": 50, "sales": 150}],
                "ad_groups": [{"ad_group_id": "g1", "campaign_id": "c1", "current_bid": 1.2, "avg_cpc": 0.9}],
                "keywords": [{"keyword_id": "k1", "campaign_id": "c1", "ad_group_id": "g1", "keyword_text": "shoe", "match_type": "phrase", "clicks": 10, "orders": 2, "spend": 15, "sales": 40, "current_bid": 0.8}],
                "search_terms": [{"campaign_id": "c1", "ad_group_id": "g1", "search_term": "shoe", "match_type": "broad", "clicks": 5, "orders": 1, "spend": 8, "sales": 20}],
                "hourly_performance": [{"hour": 9, "clicks": 3, "orders": 1, "spend": 2, "sales": 6, "impressions": 50}],
                "placement_performance": [{"campaign_id": "c1", "placement": "top_of_search", "clicks": 7, "orders": 2, "spend": 9, "sales": 25, "impressions": 80}],
                "business_context": {"asp_change_pct": -5, "inventory_days": 12, "organic_rank": 9},
            }
        )
        assert loaded.campaigns[0].campaign_id == "c1"
        assert loaded.ad_groups[0].current_bid == 1.2
        assert loaded.keywords[0].match_type.value == "PHRASE"
        assert loaded.search_terms[0].match_type.value == "BROAD"
        assert loaded.hourly_data[0].hour == 9
        assert loaded.placement_data[0].placement == "top_of_search"
        assert loaded.business_context is not None


class TestSimulationEngine:
    @pytest.fixture()
    def sample_input(self) -> SimulationInput:
        return HistoricalDataLoader().generate_sample_data(num_campaigns=2, num_keywords_per=4, days=30)

    def test_backtest_computes_actual_and_simulated_metrics(self, sample_input):
        engine = SimulationEngine()
        result = engine.run(sample_input, SimulationConfig(mode=SimulationMode.BACKTEST, days=7, target_acos=30.0))
        assert result.actual_spend > 0
        assert result.actual_sales > 0
        assert result.simulated_acos >= 0
        assert result.recommendations_count == len(sample_input.keywords)
        assert result.daily_comparison

    def test_what_if_budget_multiplier_decreases_spend(self, sample_input):
        engine = SimulationEngine()
        result = engine.run(
            sample_input,
            SimulationConfig(mode=SimulationMode.WHAT_IF, days=7, budget_multiplier=0.5, cpc_multiplier=1.0, conversion_multiplier=1.0),
        )
        assert result.simulated_spend < result.actual_spend

    def test_stress_test_budget_cut_50(self, sample_input):
        engine = SimulationEngine()
        result = engine.run(
            sample_input,
            SimulationConfig(mode=SimulationMode.STRESS_TEST, days=7, stress_scenario="budget_cut_50"),
        )
        assert result.simulated_spend < result.actual_spend
        assert result.risk_assessment in {"LOW", "MEDIUM", "HIGH"}


class TestReporter:
    def test_markdown_and_chart_data_shape(self):
        engine = SimulationEngine()
        sample = HistoricalDataLoader().generate_sample_data(num_campaigns=1, num_keywords_per=3, days=30)
        result = engine.run(sample, SimulationConfig(mode=SimulationMode.BACKTEST, days=5))
        reporter = SimulationReporter()
        markdown = reporter.to_markdown(result)
        chart_data = reporter.to_chart_data(result)
        payload = reporter.to_dict(result)

        assert "Executive Summary" in markdown
        assert "Actual vs Simulated" in markdown
        assert "Disclaimer" in markdown
        assert len(chart_data["kpi_cards"]) == 4
        assert "daily_trend" in chart_data
        assert "recommendation_summary" in chart_data
        assert payload["disclaimer"]
        json.dumps(payload)


class TestSafety:
    def test_no_api_imports_in_simulation_modules(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "src" / "agents" / "ad_monitor_agent" / "simulation"
        for path in root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "amazon ads" not in text.lower()
            assert "sqlalchemy" not in text.lower()


class TestIntegration:
    def test_full_pipeline_from_sample_data_to_report(self):
        loader = HistoricalDataLoader()
        sample = loader.generate_sample_data(num_campaigns=2, num_keywords_per=5, days=30)
        engine = SimulationEngine()
        result = engine.run(sample, SimulationConfig(mode=SimulationMode.BACKTEST, days=10, target_acos=30.0))
        reporter = SimulationReporter()

        assert result.confidence_level in {"HIGH", "MEDIUM", "LOW", "VERY_LOW"}
        assert result.disclaimer
        assert reporter.to_markdown(result).startswith("# Ad Simulation Report")
        assert reporter.to_dict(result)["mode"] == SimulationMode.BACKTEST
