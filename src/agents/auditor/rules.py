from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"   # auto-block
    WARNING = "warning"     # alert boss
    INFO = "info"           # log only


@dataclass
class AuditRule:
    id: str
    name: str
    description: str
    severity: Severity
    check_fn_name: str  # name of the check function


RULES: list[AuditRule] = [
    AuditRule(id="R001", name="budget_overrun", description="广告预算超支>20%", severity=Severity.CRITICAL, check_fn_name="check_budget_overrun"),
    AuditRule(id="R002", name="unauthorized_write", description="未经审批的SP-API写操作", severity=Severity.CRITICAL, check_fn_name="check_unauthorized_write"),
    AuditRule(id="R003", name="missing_approval", description="缺少HITL审批", severity=Severity.CRITICAL, check_fn_name="check_missing_approval"),
    AuditRule(id="R004", name="data_inconsistency", description="数据不一致", severity=Severity.CRITICAL, check_fn_name="check_data_inconsistency"),
    AuditRule(id="R005", name="unusual_spending", description="异常支出模式", severity=Severity.WARNING, check_fn_name="check_unusual_spending"),
    AuditRule(id="R006", name="keyword_stuffing", description="关键词堆砌", severity=Severity.WARNING, check_fn_name="check_keyword_stuffing"),
    AuditRule(id="R007", name="duplicate_content", description="重复内容", severity=Severity.WARNING, check_fn_name="check_duplicate_content"),
    AuditRule(id="R008", name="brand_deviation", description="偏离品牌指南", severity=Severity.WARNING, check_fn_name="check_brand_deviation"),
    AuditRule(id="R009", name="normal_operation", description="正常操作记录", severity=Severity.INFO, check_fn_name="check_normal_operation"),
    AuditRule(id="R010", name="performance_metrics", description="性能指标记录", severity=Severity.INFO, check_fn_name="check_performance_metrics"),
]


def get_rules_by_severity(severity: Severity) -> list[AuditRule]:
    return [r for r in RULES if r.severity == severity]


def get_rules_summary() -> str:
    lines: list[str] = []
    for sev in Severity:
        rules: list[AuditRule] = get_rules_by_severity(sev)
        lines.append(f"\n### {sev.value.upper()} ({len(rules)} rules)")
        for r in rules:
            lines.append(f"- [{r.id}] {r.name}: {r.description}")
    return "\n".join(lines)
