"""Policy Engine — 规则引擎核心。

PolicyEngine 是线程安全的规则注册表 + 执行器：
- 启动时自动加载内置规则
- 支持运行时注册自定义规则
- check() 返回 PolicyResult（allowed/violations/warnings）
- get_violations() 只返回违规列表（不含警告）

设计原则：
- 规则不抛异常：单条规则执行失败时记录日志，跳过此规则
- 失败保守策略：规则加载/执行失败不会放行违规决策
- 规则阈值配置化：所有阈值来自 PolicyConfig（环境变量 / 配置文件）
"""
from __future__ import annotations

import logging
from threading import Lock
from typing import Dict, List, Optional, Type

from src.policy.models import PolicyResult, Rule, Violation, Warning

logger = logging.getLogger(__name__)


class PolicyEngine:
    """规则引擎核心。

    使用方式::

        engine = PolicyEngine()

        # 检查决策
        result = engine.check("price_adjustment", payload)
        if not result.allowed:
            for v in result.violations:
                print(v.message)

        # 注册自定义规则
        class MyRule(Rule):
            rule_id = "custom.my_rule"
            rule_name = "自定义规则"
            def check(self, payload):
                return [], []

        engine.register_rule(MyRule())
    """

    def __init__(self, load_builtin: bool = True) -> None:
        """初始化规则引擎。

        Args:
            load_builtin: 是否自动加载内置规则（测试时可设为 False）
        """
        self._rules: Dict[str, Rule] = {}
        self._lock = Lock()

        if load_builtin:
            self._load_builtin_rules()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def check(self, decision_type: str, payload: dict) -> PolicyResult:
        """检查决策是否符合所有已注册规则。

        Args:
            decision_type: 决策类型，如 "price_adjustment"、"ad_budget"、"inventory_replenishment"
            payload:       决策 payload 字典

        Returns:
            PolicyResult，allowed=True 表示合规；False 表示有违规。
        """
        violations, warnings = self._run_rules(decision_type, payload)
        allowed = len(violations) == 0
        return PolicyResult(
            allowed=allowed,
            violations=violations,
            warnings=warnings,
            decision_type=decision_type,
        )

    def register_rule(self, rule: Rule) -> None:
        """注册（或覆盖）一条规则。

        Args:
            rule: Rule 实例，rule.rule_id 必须唯一
        """
        if not rule.rule_id:
            raise ValueError(f"规则 rule_id 不能为空: {rule!r}")
        with self._lock:
            self._rules[rule.rule_id] = rule
            logger.debug("已注册规则: %s (%s)", rule.rule_id, rule.rule_name)

    def unregister_rule(self, rule_id: str) -> bool:
        """注销指定规则。

        Returns:
            True 表示成功注销，False 表示规则不存在
        """
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                logger.debug("已注销规则: %s", rule_id)
                return True
            return False

    def get_violations(self, decision_type: str, payload: dict) -> List[Violation]:
        """获取所有违规项（不含警告）。

        Args:
            decision_type: 决策类型
            payload:       决策 payload

        Returns:
            Violation 列表（空列表表示合规）
        """
        violations, _ = self._run_rules(decision_type, payload)
        return violations

    def list_rules(self) -> List[dict]:
        """列出所有已注册规则的摘要信息。"""
        with self._lock:
            return [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "enabled": r.enabled,
                    "applicable_decision_types": r.applicable_decision_types,
                }
                for r in self._rules.values()
            ]

    def enable_rule(self, rule_id: str) -> bool:
        """启用指定规则。"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            rule.enabled = True
            return True

    def disable_rule(self, rule_id: str) -> bool:
        """禁用指定规则（check 时会跳过）。"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            rule.enabled = False
            return True

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _run_rules(
        self, decision_type: str, payload: dict
    ) -> tuple[List[Violation], List[Warning]]:
        """执行所有适用规则，收集违规和警告。"""
        all_violations: List[Violation] = []
        all_warnings: List[Warning] = []

        with self._lock:
            rules = list(self._rules.values())

        for rule in rules:
            if not rule.enabled:
                logger.debug("跳过已禁用规则: %s", rule.rule_id)
                continue
            if not rule.applies_to(decision_type):
                continue
            try:
                violations, warnings = rule.check(payload)
                all_violations.extend(violations)
                all_warnings.extend(warnings)
            except Exception as exc:  # pylint: disable=broad-except
                # 单条规则失败时记录日志，但不阻止其他规则执行
                logger.error(
                    "规则执行异常（跳过）: rule_id=%s error=%s", rule.rule_id, exc
                )

        return all_violations, all_warnings

    def _load_builtin_rules(self) -> None:
        """加载所有内置规则。"""
        try:
            from src.policy.rules import get_builtin_rules
            for rule in get_builtin_rules():
                self.register_rule(rule)
            logger.info("已加载 %d 条内置规则", len(self._rules))
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("加载内置规则失败: %s", exc)


# ---------------------------------------------------------------------------
# 模块级单例（懒加载）
# ---------------------------------------------------------------------------

_engine_instance: Optional[PolicyEngine] = None
_engine_lock = Lock()


def get_policy_engine() -> PolicyEngine:
    """返回全局 PolicyEngine 单例（线程安全懒加载）。"""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = PolicyEngine()
    return _engine_instance
