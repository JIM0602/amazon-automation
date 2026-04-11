from __future__ import annotations

from typing import override

from src.agents.chat_base_agent import ChatBaseAgent
from .rules import get_rules_summary


class AuditorChatAgent(ChatBaseAgent):
    def __init__(self):
        super().__init__(name="审计Agent")

    @property
    @override
    def agent_type(self) -> str:
        return "auditor"

    @override
    def get_system_prompt(self) -> str:
        return (
            "你是审计AI助手，仅限Boss使用。你的职责是审核所有Agent输出的质量和合规性，发现问题并清晰报告，不自动修复。"
            "审计规则引擎分为三类：Critical（自动阻断）、Warning（告警）、Info（日志）。\n\n"
            "当前审计规则：\n"
            f"{get_rules_summary()}\n\n"
            "你可以查询审计日志、合规趋势、Agent行为分析。"
            "你只报告问题与风险，不执行修复动作，最终行动由Boss决定。"
        )

    @override
    def get_tools(self) -> list[object]:
        return []

    @override
    def get_model(self) -> str:
        return "claude-3-5-sonnet-20241022"
