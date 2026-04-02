"""Policy Engine 单元测试。

覆盖范围：
  1. 模型测试（Violation, Warning, PolicyResult, Rule）
  2. 规则引擎核心（PolicyEngine.check/register_rule/get_violations）
  3. 价格规则（PriceMaxChangePctRule, PriceMinCostRule, PriceMaxDailyChangesRule）
  4. 广告规则（AdMaxDailyBudgetRule, AdAcosThresholdRule, AdMaxKeywordBidRule）
  5. 库存规则（InvMaxReplenishUnitsRule, InvSafetyStockWarningRule）
  6. 规则配置化（环境变量控制阈值 / 规则开关）
  7. 集成测试（submit_for_approval 违规阻断）
  8. 自定义规则注册
"""
from __future__ import annotations

import os
from typing import List
from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# 1. 模型测试
# ===========================================================================

class TestViolation:
    def test_violation_creation(self):
        from src.policy.models import Violation
        v = Violation(
            rule_id="price.max_change_pct",
            rule_name="单次调价幅度限制",
            message="幅度超限",
        )
        assert v.rule_id == "price.max_change_pct"
        assert not hasattr(v, "allowed")  # Violation 无 allowed 字段，allowed 属于 PolicyResult

    def test_violation_to_dict(self):
        from src.policy.models import Violation
        v = Violation(
            rule_id="price.max_change_pct",
            rule_name="单次调价幅度限制",
            message="幅度超限",
            field="new_price",
            actual=0.25,
            threshold=0.20,
        )
        d = v.to_dict()
        assert d["rule_id"] == "price.max_change_pct"
        assert d["actual"] == 0.25
        assert d["threshold"] == 0.20
        assert d["field"] == "new_price"


class TestWarning:
    def test_warning_creation(self):
        from src.policy.models import Warning
        w = Warning(
            rule_id="price.max_daily_changes",
            rule_name="每日调价次数限制",
            message="已达上限",
        )
        assert w.rule_id == "price.max_daily_changes"

    def test_warning_to_dict(self):
        from src.policy.models import Warning
        w = Warning(rule_id="r1", rule_name="R1", message="msg", field="f1")
        d = w.to_dict()
        assert d["rule_id"] == "r1"
        assert d["field"] == "f1"


class TestPolicyResult:
    def test_allowed_when_no_violations(self):
        from src.policy.models import PolicyResult
        result = PolicyResult(allowed=True)
        assert result.allowed is True
        assert result.violations == []
        assert result.warnings == []

    def test_not_allowed_when_violations(self):
        from src.policy.models import PolicyResult, Violation
        v = Violation(rule_id="x", rule_name="X", message="m")
        result = PolicyResult(allowed=False, violations=[v])
        assert result.allowed is False
        assert len(result.violations) == 1

    def test_to_dict(self):
        from src.policy.models import PolicyResult, Violation, Warning
        v = Violation(rule_id="x", rule_name="X", message="m")
        w = Warning(rule_id="y", rule_name="Y", message="w")
        result = PolicyResult(allowed=False, violations=[v], warnings=[w], decision_type="price_adjustment")
        d = result.to_dict()
        assert d["allowed"] is False
        assert d["violation_count"] == 1
        assert d["warning_count"] == 1
        assert d["decision_type"] == "price_adjustment"


# ===========================================================================
# 2. 规则引擎核心
# ===========================================================================

class TestPolicyEngineCore:
    def test_engine_initializes_with_builtin_rules(self):
        from src.policy.engine import PolicyEngine
        engine = PolicyEngine(load_builtin=True)
        rules = engine.list_rules()
        assert len(rules) > 0

    def test_check_returns_policy_result(self):
        from src.policy.engine import PolicyEngine
        engine = PolicyEngine(load_builtin=False)
        result = engine.check("price_adjustment", {})
        assert result.allowed is True
        assert result.violations == []

    def test_register_custom_rule(self):
        from src.policy.engine import PolicyEngine
        from src.policy.models import Rule, Violation, Warning

        class AlwaysViolateRule(Rule):
            rule_id = "test.always_violate"
            rule_name = "总是违规测试规则"
            applicable_decision_types = ["test_type"]

            def check(self, payload):
                return [Violation(rule_id=self.rule_id, rule_name=self.rule_name, message="测试违规")], []

        engine = PolicyEngine(load_builtin=False)
        engine.register_rule(AlwaysViolateRule())
        result = engine.check("test_type", {})
        assert result.allowed is False
        assert len(result.violations) == 1

    def test_register_rule_without_id_raises(self):
        from src.policy.engine import PolicyEngine
        from src.policy.models import Rule

        class NoIdRule(Rule):
            rule_id = ""
            rule_name = "无 ID 规则"
            def check(self, payload):
                return [], []

        engine = PolicyEngine(load_builtin=False)
        with pytest.raises(ValueError):
            engine.register_rule(NoIdRule())

    def test_unregister_rule(self):
        from src.policy.engine import PolicyEngine
        from src.policy.models import Rule, Violation

        class TempRule(Rule):
            rule_id = "test.temp"
            rule_name = "临时规则"
            applicable_decision_types = ["x"]
            def check(self, payload):
                return [Violation(rule_id=self.rule_id, rule_name=self.rule_name, message="m")], []

        engine = PolicyEngine(load_builtin=False)
        engine.register_rule(TempRule())
        assert engine.check("x", {}).allowed is False

        engine.unregister_rule("test.temp")
        assert engine.check("x", {}).allowed is True

    def test_disable_and_enable_rule(self):
        from src.policy.engine import PolicyEngine
        from src.policy.models import Rule, Violation

        class DisableTestRule(Rule):
            rule_id = "test.disable"
            rule_name = "可禁用测试规则"
            applicable_decision_types = ["x"]
            def check(self, payload):
                return [Violation(rule_id=self.rule_id, rule_name=self.rule_name, message="m")], []

        engine = PolicyEngine(load_builtin=False)
        engine.register_rule(DisableTestRule())

        # 禁用后不违规
        engine.disable_rule("test.disable")
        assert engine.check("x", {}).allowed is True

        # 重新启用后违规
        engine.enable_rule("test.disable")
        assert engine.check("x", {}).allowed is False

    def test_get_violations_returns_list(self):
        from src.policy.engine import PolicyEngine
        engine = PolicyEngine(load_builtin=False)
        violations = engine.get_violations("price_adjustment", {})
        assert isinstance(violations, list)

    def test_rule_only_applies_to_matching_decision_type(self):
        from src.policy.engine import PolicyEngine
        from src.policy.models import Rule, Violation

        class PriceOnlyRule(Rule):
            rule_id = "test.price_only"
            rule_name = "仅价格规则"
            applicable_decision_types = ["price_adjustment"]
            def check(self, payload):
                return [Violation(rule_id=self.rule_id, rule_name=self.rule_name, message="m")], []

        engine = PolicyEngine(load_builtin=False)
        engine.register_rule(PriceOnlyRule())

        # price_adjustment 时违规
        assert engine.check("price_adjustment", {}).allowed is False
        # ad_budget 时不违规
        assert engine.check("ad_budget", {}).allowed is True

    def test_rule_exception_does_not_crash_engine(self):
        """单条规则抛出异常时引擎应继续执行其他规则。"""
        from src.policy.engine import PolicyEngine
        from src.policy.models import Rule, Violation

        class BuggyRule(Rule):
            rule_id = "test.buggy"
            rule_name = "Bug 规则"
            applicable_decision_types = []
            def check(self, payload):
                raise RuntimeError("故意崩溃")

        class GoodRule(Rule):
            rule_id = "test.good"
            rule_name = "正常规则"
            applicable_decision_types = []
            def check(self, payload):
                return [Violation(rule_id=self.rule_id, rule_name=self.rule_name, message="m")], []

        engine = PolicyEngine(load_builtin=False)
        engine.register_rule(BuggyRule())
        engine.register_rule(GoodRule())

        # 即使 BuggyRule 崩溃，GoodRule 仍应产生违规
        result = engine.check("anything", {})
        assert result.allowed is False
        assert any(v.rule_id == "test.good" for v in result.violations)

    def test_get_policy_engine_singleton(self):
        import src.policy.engine as engine_module
        engine_module._engine_instance = None

        from src.policy.engine import get_policy_engine
        e1 = get_policy_engine()
        e2 = get_policy_engine()
        assert e1 is e2

        engine_module._engine_instance = None  # 清理


# ===========================================================================
# 3. 价格规则
# ===========================================================================

class TestPriceMaxChangePctRule:
    def _get_rule(self):
        from src.policy.rules import PriceMaxChangePctRule
        return PriceMaxChangePctRule()

    def test_violation_when_over_threshold(self):
        rule = self._get_rule()
        # 25% 变化，超过默认 20%
        payload = {"current_price": 10.0, "new_price": 12.5}
        violations, warnings = rule.check(payload)
        assert len(violations) == 1
        assert violations[0].rule_id == "price.max_change_pct"

    def test_no_violation_when_within_threshold(self):
        rule = self._get_rule()
        # 10% 变化，低于默认 20%
        payload = {"current_price": 10.0, "new_price": 11.0}
        violations, warnings = rule.check(payload)
        assert violations == []

    def test_no_violation_when_exactly_at_threshold(self):
        rule = self._get_rule()
        # 恰好 20%
        payload = {"current_price": 10.0, "new_price": 12.0}
        violations, warnings = rule.check(payload)
        assert violations == []

    def test_skip_when_missing_fields(self):
        rule = self._get_rule()
        violations, warnings = rule.check({})
        assert violations == []

    def test_skip_when_price_zero(self):
        rule = self._get_rule()
        violations, warnings = rule.check({"current_price": 0.0, "new_price": 5.0})
        assert violations == []

    def test_price_decrease_also_checked(self):
        rule = self._get_rule()
        # 降价 30%，也超过 20%
        payload = {"current_price": 10.0, "new_price": 7.0}
        violations, warnings = rule.check(payload)
        assert len(violations) == 1

    def test_custom_threshold_via_env(self):
        rule = self._get_rule()
        with patch.dict(os.environ, {"POLICY_PRICE_MAX_CHANGE_PCT": "0.10"}):
            # 15% 变化，超过 10%
            violations, _ = rule.check({"current_price": 10.0, "new_price": 11.5})
            assert len(violations) == 1

    def test_sku_in_message(self):
        rule = self._get_rule()
        payload = {"current_price": 10.0, "new_price": 13.0, "sku": "TEST-SKU"}
        violations, _ = rule.check(payload)
        assert "TEST-SKU" in violations[0].message

    def test_disabled_via_env(self):
        rule = self._get_rule()
        env_key = "POLICY_RULE_PRICE_MAX_CHANGE_PCT_ENABLED"
        with patch.dict(os.environ, {env_key: "false"}):
            violations, _ = rule.check({"current_price": 10.0, "new_price": 20.0})
            assert violations == []


class TestPriceMinCostRule:
    def _get_rule(self):
        from src.policy.rules import PriceMinCostRule
        return PriceMinCostRule()

    def test_violation_below_cost(self):
        rule = self._get_rule()
        violations, _ = rule.check({"new_price": 8.0, "cost_price": 10.0})
        assert len(violations) == 1

    def test_no_violation_at_cost(self):
        rule = self._get_rule()
        violations, _ = rule.check({"new_price": 10.0, "cost_price": 10.0})
        assert violations == []

    def test_no_violation_above_cost(self):
        rule = self._get_rule()
        violations, _ = rule.check({"new_price": 12.0, "cost_price": 10.0})
        assert violations == []

    def test_skip_when_missing_fields(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])

    def test_custom_margin_via_env(self):
        rule = self._get_rule()
        with patch.dict(os.environ, {"POLICY_PRICE_MIN_MARGIN": "0.10"}):
            # 最低价 = 10.0 * 1.1 = 11.0
            violations, _ = rule.check({"new_price": 10.5, "cost_price": 10.0})
            assert len(violations) == 1


class TestPriceMaxDailyChangesRule:
    def _get_rule(self):
        from src.policy.rules import PriceMaxDailyChangesRule
        return PriceMaxDailyChangesRule()

    def test_violation_when_over_limit(self):
        rule = self._get_rule()
        violations, warnings = rule.check({"daily_change_count": 4})
        assert len(violations) == 1

    def test_warning_when_at_limit(self):
        rule = self._get_rule()
        violations, warnings = rule.check({"daily_change_count": 3})
        assert violations == []
        assert len(warnings) == 1

    def test_no_violation_when_under_limit(self):
        rule = self._get_rule()
        violations, warnings = rule.check({"daily_change_count": 2})
        assert violations == []
        assert warnings == []

    def test_skip_when_missing_field(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])


# ===========================================================================
# 4. 广告规则
# ===========================================================================

class TestAdMaxDailyBudgetRule:
    def _get_rule(self):
        from src.policy.rules import AdMaxDailyBudgetRule
        return AdMaxDailyBudgetRule()

    def test_violation_over_budget(self):
        rule = self._get_rule()
        violations, _ = rule.check({"daily_budget_usd": 600.0})
        assert len(violations) == 1

    def test_warning_near_budget(self):
        rule = self._get_rule()
        # 80% * 500 = 400
        violations, warnings = rule.check({"daily_budget_usd": 450.0})
        assert violations == []
        assert len(warnings) == 1

    def test_no_issue_under_budget(self):
        rule = self._get_rule()
        violations, warnings = rule.check({"daily_budget_usd": 100.0})
        assert violations == []
        assert warnings == []

    def test_skip_when_missing_field(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])

    def test_custom_limit_via_env(self):
        rule = self._get_rule()
        with patch.dict(os.environ, {"POLICY_AD_MAX_DAILY_BUDGET_USD": "100.0"}):
            violations, _ = rule.check({"daily_budget_usd": 150.0})
            assert len(violations) == 1


class TestAdAcosThresholdRule:
    def _get_rule(self):
        from src.policy.rules import AdAcosThresholdRule
        return AdAcosThresholdRule()

    def test_violation_acos_over_threshold_with_increase(self):
        rule = self._get_rule()
        payload = {"current_acos": 0.60, "budget_change_usd": 50.0}
        violations, _ = rule.check(payload)
        assert len(violations) == 1

    def test_no_violation_acos_over_threshold_but_no_increase(self):
        """ACoS 超标但没有加投，不违规。"""
        rule = self._get_rule()
        payload = {"current_acos": 0.60, "budget_change_usd": -50.0}
        violations, _ = rule.check(payload)
        assert violations == []

    def test_no_violation_acos_under_threshold(self):
        rule = self._get_rule()
        payload = {"current_acos": 0.30, "budget_change_usd": 100.0}
        violations, _ = rule.check(payload)
        assert violations == []

    def test_warning_acos_near_threshold(self):
        rule = self._get_rule()
        # 80% of 0.50 = 0.40
        payload = {"current_acos": 0.45, "budget_change_usd": 0}
        violations, warnings = rule.check(payload)
        assert violations == []
        assert len(warnings) == 1

    def test_violation_via_bid_increase(self):
        """通过提高出价（bid_change_usd > 0）触发违规。"""
        rule = self._get_rule()
        payload = {"current_acos": 0.60, "bid_change_usd": 0.5}
        violations, _ = rule.check(payload)
        assert len(violations) == 1

    def test_skip_when_missing_acos(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])

    def test_custom_threshold_via_env(self):
        rule = self._get_rule()
        with patch.dict(os.environ, {"POLICY_AD_ACOS_THRESHOLD_PCT": "0.30"}):
            payload = {"current_acos": 0.35, "budget_change_usd": 10.0}
            violations, _ = rule.check(payload)
            assert len(violations) == 1


class TestAdMaxKeywordBidRule:
    def _get_rule(self):
        from src.policy.rules import AdMaxKeywordBidRule
        return AdMaxKeywordBidRule()

    def test_violation_over_bid_limit(self):
        rule = self._get_rule()
        violations, _ = rule.check({"keyword_bid_usd": 7.0})
        assert len(violations) == 1

    def test_no_violation_under_bid_limit(self):
        rule = self._get_rule()
        violations, _ = rule.check({"keyword_bid_usd": 3.0})
        assert violations == []

    def test_no_violation_at_bid_limit(self):
        rule = self._get_rule()
        violations, _ = rule.check({"keyword_bid_usd": 5.0})
        assert violations == []

    def test_skip_when_missing_field(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])

    def test_keyword_in_message(self):
        rule = self._get_rule()
        violations, _ = rule.check({"keyword_bid_usd": 10.0, "keyword": "bluetooth speaker"})
        assert "bluetooth speaker" in violations[0].message


# ===========================================================================
# 5. 库存规则
# ===========================================================================

class TestInvMaxReplenishUnitsRule:
    def _get_rule(self):
        from src.policy.rules import InvMaxReplenishUnitsRule
        return InvMaxReplenishUnitsRule()

    def test_violation_over_limit(self):
        rule = self._get_rule()
        violations, _ = rule.check({"replenish_units": 15000})
        assert len(violations) == 1

    def test_no_violation_under_limit(self):
        rule = self._get_rule()
        violations, _ = rule.check({"replenish_units": 5000})
        assert violations == []

    def test_violation_when_zero_units(self):
        rule = self._get_rule()
        violations, _ = rule.check({"replenish_units": 0})
        assert len(violations) == 1

    def test_violation_when_negative_units(self):
        rule = self._get_rule()
        violations, _ = rule.check({"replenish_units": -100})
        assert len(violations) == 1

    def test_skip_when_missing_field(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])

    def test_custom_limit_via_env(self):
        rule = self._get_rule()
        with patch.dict(os.environ, {"POLICY_INV_MAX_REPLENISH_UNITS": "1000"}):
            violations, _ = rule.check({"replenish_units": 1500})
            assert len(violations) == 1


class TestInvSafetyStockWarningRule:
    def _get_rule(self):
        from src.policy.rules import InvSafetyStockWarningRule
        return InvSafetyStockWarningRule()

    def test_warning_when_below_safety_stock(self):
        rule = self._get_rule()
        # 100 件 / 10件/天 = 10天，< 14天阈值
        violations, warnings = rule.check({"current_stock_units": 100, "daily_sales_units": 10})
        assert violations == []
        assert len(warnings) == 1

    def test_no_warning_when_above_safety_stock(self):
        rule = self._get_rule()
        # 300 件 / 10件/天 = 30天，> 14天阈值
        violations, warnings = rule.check({"current_stock_units": 300, "daily_sales_units": 10})
        assert violations == []
        assert warnings == []

    def test_skip_when_daily_sales_zero(self):
        rule = self._get_rule()
        violations, warnings = rule.check({"current_stock_units": 100, "daily_sales_units": 0})
        assert violations == []
        assert warnings == []

    def test_skip_when_missing_fields(self):
        rule = self._get_rule()
        assert rule.check({}) == ([], [])

    def test_custom_threshold_via_env(self):
        rule = self._get_rule()
        with patch.dict(os.environ, {"POLICY_INV_SAFETY_STOCK_DAYS": "30"}):
            # 200/10 = 20天，< 30天阈值
            violations, warnings = rule.check({"current_stock_units": 200, "daily_sales_units": 10})
            assert len(warnings) == 1


# ===========================================================================
# 6. 规则配置化测试
# ===========================================================================

class TestPolicyConfig:
    def test_default_values(self):
        from src.policy.config import PolicyConfig
        cfg = PolicyConfig()
        assert cfg.price_max_change_pct == 0.20
        assert cfg.price_min_margin == 0.0
        assert cfg.price_max_daily_changes == 3
        assert cfg.ad_max_daily_budget_usd == 500.0
        assert cfg.ad_acos_threshold_pct == 0.50
        assert cfg.ad_max_keyword_bid_usd == 5.0
        assert cfg.inv_max_replenish_units == 10000
        assert cfg.inv_safety_stock_days == 14

    def test_override_via_env(self):
        from src.policy.config import PolicyConfig
        with patch.dict(os.environ, {
            "POLICY_PRICE_MAX_CHANGE_PCT": "0.15",
            "POLICY_AD_MAX_DAILY_BUDGET_USD": "200.0",
        }):
            cfg = PolicyConfig()
            assert cfg.price_max_change_pct == 0.15
            assert cfg.ad_max_daily_budget_usd == 200.0

    def test_invalid_env_uses_default(self):
        from src.policy.config import PolicyConfig
        with patch.dict(os.environ, {"POLICY_PRICE_MAX_CHANGE_PCT": "not_a_number"}):
            cfg = PolicyConfig()
            assert cfg.price_max_change_pct == 0.20

    def test_rule_enabled_check(self):
        from src.policy.config import PolicyConfig
        cfg = PolicyConfig()
        with patch.dict(os.environ, {"POLICY_RULE_PRICE_MAX_CHANGE_PCT_ENABLED": "false"}):
            assert cfg.is_rule_enabled("price.max_change_pct") is False

    def test_rule_enabled_by_default(self):
        from src.policy.config import PolicyConfig
        cfg = PolicyConfig()
        assert cfg.is_rule_enabled("price.max_change_pct") is True


# ===========================================================================
# 7. 集成测试 —— submit_for_approval 违规阻断
# ===========================================================================

class TestSubmitForApproval:
    def test_violation_blocks_submission(self):
        from src.policy.integration import submit_for_approval
        from src.policy.engine import PolicyEngine

        # 创建带固定规则的引擎
        from src.policy.models import Rule, Violation as V

        class BlockRule(Rule):
            rule_id = "test.block"
            rule_name = "总是阻断"
            applicable_decision_types = []
            def check(self, payload):
                return [V(rule_id=self.rule_id, rule_name=self.rule_name, message="阻断")], []

        engine = PolicyEngine(load_builtin=False)
        engine.register_rule(BlockRule())

        with patch("src.policy.integration.get_policy_engine", return_value=engine):
            result = submit_for_approval(
                decision_type="price_adjustment",
                action_type="price_adjustment",
                description="test",
                impact="test",
                reason="test",
                risks="test",
                payload={"current_price": 10.0, "new_price": 20.0},
            )

        assert result["allowed"] is False
        assert result["approval_id"] is None
        assert len(result["violations"]) == 1

    def test_compliant_decision_proceeds(self):
        from src.policy.integration import submit_for_approval
        from src.policy.engine import PolicyEngine

        engine = PolicyEngine(load_builtin=False)  # 无规则，全部通过

        mock_create = MagicMock(return_value="mock-approval-id-1234")

        with patch("src.policy.integration.get_policy_engine", return_value=engine), \
             patch("src.feishu.approval.create_approval_request", mock_create):
            result = submit_for_approval(
                decision_type="price_adjustment",
                action_type="price_adjustment",
                description="test",
                impact="test",
                reason="test",
                risks="test",
                payload={},
            )

        assert result["allowed"] is True
        assert result["approval_id"] == "mock-approval-id-1234"

    def test_skip_policy_check_proceeds(self):
        """skip_policy_check=True 时跳过规则检查直接提交。"""
        from src.policy.integration import submit_for_approval

        mock_create = MagicMock(return_value="skip-approval-id")

        with patch("src.policy.integration.create_approval_request", mock_create, create=True):
            result = submit_for_approval(
                decision_type="price_adjustment",
                action_type="price_adjustment",
                description="test",
                impact="test",
                reason="test",
                risks="test",
                payload={"current_price": 1.0, "new_price": 100.0},  # 明显违规
                skip_policy_check=True,
            )

        assert result["allowed"] is True


# ===========================================================================
# 8. 端到端规则引擎测试（完整内置规则集）
# ===========================================================================

class TestBuiltinRulesEndToEnd:
    def setup_method(self):
        from src.policy.engine import PolicyEngine
        self.engine = PolicyEngine(load_builtin=True)

    def test_price_adjustment_compliant(self):
        payload = {
            "current_price": 10.0,
            "new_price": 11.0,     # 10% 变化
            "cost_price": 8.0,
            "daily_change_count": 1,
            "sku": "TEST-001",
        }
        result = self.engine.check("price_adjustment", payload)
        assert result.allowed is True

    def test_price_adjustment_violates_change_pct(self):
        payload = {
            "current_price": 10.0,
            "new_price": 15.0,     # 50% 变化，超过 20%
            "cost_price": 8.0,
            "daily_change_count": 1,
        }
        result = self.engine.check("price_adjustment", payload)
        assert result.allowed is False
        violation_ids = [v.rule_id for v in result.violations]
        assert "price.max_change_pct" in violation_ids

    def test_price_adjustment_violates_cost(self):
        payload = {
            "current_price": 10.0,
            "new_price": 10.0,     # 0% 变化，合规
            "cost_price": 12.0,    # 但低于成本价
            "daily_change_count": 1,
        }
        result = self.engine.check("price_adjustment", payload)
        assert result.allowed is False
        violation_ids = [v.rule_id for v in result.violations]
        assert "price.min_cost" in violation_ids

    def test_ad_budget_compliant(self):
        payload = {
            "daily_budget_usd": 100.0,
            "current_acos": 0.30,
            "budget_change_usd": 20.0,
        }
        result = self.engine.check("ad_budget", payload)
        assert result.allowed is True

    def test_ad_budget_violates_acos(self):
        payload = {
            "daily_budget_usd": 200.0,
            "current_acos": 0.70,   # 超过 50% 阈值
            "budget_change_usd": 50.0,  # 正在加投
        }
        result = self.engine.check("ad_budget", payload)
        assert result.allowed is False

    def test_inventory_replenishment_compliant(self):
        payload = {
            "replenish_units": 500,
            "current_stock_units": 1000,
            "daily_sales_units": 20,   # 50天库存，>14天
        }
        result = self.engine.check("inventory_replenishment", payload)
        assert result.allowed is True

    def test_inventory_replenishment_violates_max_units(self):
        payload = {
            "replenish_units": 20000,   # 超过 10000 上限
            "current_stock_units": 100,
            "daily_sales_units": 10,
        }
        result = self.engine.check("inventory_replenishment", payload)
        assert result.allowed is False

    def test_inventory_safety_stock_warning(self):
        payload = {
            "replenish_units": 100,
            "current_stock_units": 50,    # 5天库存，<14天
            "daily_sales_units": 10,
        }
        result = self.engine.check("inventory_replenishment", payload)
        assert result.allowed is True  # 仅警告，不阻断
        assert len(result.warnings) > 0

    def test_unknown_decision_type_all_pass(self):
        """未知决策类型，所有规则均跳过（无 applicable_decision_types 匹配）。"""
        payload = {"anything": 999}
        result = self.engine.check("unknown_type", payload)
        # 内置规则都有 applicable_decision_types，unknown_type 不匹配任何规则
        # 所以结果应该是 allowed=True
        assert result.allowed is True
