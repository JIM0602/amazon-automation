from abc import ABC, abstractmethod

from loguru import logger

from src.config import settings


class BaseAgent(ABC):
    """所有Agent的基类"""

    def __init__(self, name: str):
        self.name = name
        self.dry_run = settings.DRY_RUN

    @abstractmethod
    def run(self, **kwargs):
        """执行Agent主逻辑，子类必须实现"""
        pass

    def log(self, msg: str):
        logger.info(f"[{self.name}] {msg}")

    def warn(self, msg: str):
        logger.warning(f"[{self.name}] {msg}")
