"""Policy Engine — Pydantic 数据模型。

定义规则引擎使用的所有数据结构：
- Violation: 违规项（阻断级，allowed=False）
- Warning: 警告项（提示级，允许继续）
- PolicyResult: 规则检查结果
- Rule: 规则接口（ABC）
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Violation:
    """规则违规项（严重，会阻止决策执行）。

    Attributes:
        rule_id:     规则唯一标识，如 "price.max_change_pct"
        rule_name:   规则可读名称
        message:     违规描述
        field:       违规的具体字段（可选）
        actual:      实际值（可选）
        threshold:   阈值（可选）
    """
    rule_id: str
    rule_name: str
    message: str
    field: Optional[str] = None
    actual: Optional[Any] = None
    threshold: Optional[Any] = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "message": self.message,
            "field": self.field,
            "actual": self.actual,
            "threshold": self.threshold,
        }


@dataclass
class Warning:
    """规则警告项（提示级，不阻止执行，仅记录）。

    Attributes:
        rule_id:  规则唯一标识
        rule_name: 规则可读名称
        message:   警告描述
        field:     涉及字段（可选）
    """
    rule_id: str
    rule_name: str
    message: str
    field: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "message": self.message,
            "field": self.field,
        }


@dataclass
class PolicyResult:
    """规则引擎检查结果。

    Attributes:
        allowed:     True 表示决策合规，可以继续；False 表示有违规，应阻止
        violations:  所有违规项列表（非空时 allowed=False）
        warnings:    所有警告项列表（不影响 allowed）
        decision_type: 被检查的决策类型
    """
    allowed: bool
    violations: List[Violation] = field(default_factory=list)
    warnings: List[Warning] = field(default_factory=list)
    decision_type: str = ""

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "decision_type": self.decision_type,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
        }


class Rule(ABC):
    """规则基类。

    所有内置规则和自定义规则都应继承此类。
    `check()` 方法在 payload 不适用本规则时应直接返回空列表。
    """

    #: 规则唯一 ID，例如 "price.max_change_pct"
    rule_id: str = ""

    #: 规则可读名称
    rule_name: str = ""

    #: 适用的决策类型列表（空列表表示适用所有类型）
    applicable_decision_types: List[str] = []

    #: 是否启用
    enabled: bool = True

    @abstractmethod
    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        """检查 payload 是否符合规则。

        Args:
            payload: 决策 payload 字典

        Returns:
            (violations, warnings) 两个列表
        """
        ...

    def applies_to(self, decision_type: str) -> bool:
        """判断本规则是否适用于指定决策类型。"""
        if not self.applicable_decision_types:
            return True
        return decision_type in self.applicable_decision_types
