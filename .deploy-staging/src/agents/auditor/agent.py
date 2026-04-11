from __future__ import annotations

from typing import override

from src.agents.base_agent import BaseAgent


class AuditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="审计Agent")

    @override
    def run(self, **kwargs: object) -> None:
        self.log("审计扫描执行")
        self.last_scan: dict[str, object] = {
            "agent_type": "auditor",
            "status": "ok",
            "findings": [],
            "auto_action": None,
            "details": kwargs,
        }
