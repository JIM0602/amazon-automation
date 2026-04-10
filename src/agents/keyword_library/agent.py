from __future__ import annotations

from typing import override

from src.agents.base_agent import BaseAgent


class KeywordLibraryAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="关键词库Agent")

    @override
    def run(self, **kwargs: object) -> None:
        self.log("关键词库批量构建流程已启动")
        self.last_run: dict[str, object] = {
            "agent_type": "keyword_library",
            "status": "ok",
            "inputs": kwargs,
            "result": None,
        }
