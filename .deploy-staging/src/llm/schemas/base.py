"""Pydantic Schema 通用基类。

提供：
  - BaseOutputSchema  — 所有 LLM 输出 Schema 的基类
  - SchemaValidationError — Schema 校验异常
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="BaseOutputSchema")


class BaseOutputSchema(BaseModel):
    """LLM 输出 Schema 基类。

    所有结构化 LLM 输出的 Schema 都应继承此类。

    特性：
    - 支持 from_dict / from_json 解析
    - 支持 to_dict / to_json 序列化
    - 允许额外字段（extra="ignore"），容错处理
    """

    model_config = ConfigDict(
        # 忽略 LLM 输出中多余的字段（容错）
        extra="ignore",
        # 允许从任意类型强制转换
        arbitrary_types_allowed=True,
        # 校验赋值
        validate_assignment=True,
    )

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """从字典解析 Schema 对象。

        Args:
            data: LLM 输出的字典数据

        Returns:
            解析后的 Schema 对象

        Raises:
            pydantic.ValidationError: 数据不符合 Schema 定义时抛出
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """从 JSON 字符串解析 Schema 对象。

        Args:
            json_str: LLM 输出的 JSON 字符串

        Returns:
            解析后的 Schema 对象

        Raises:
            pydantic.ValidationError: 数据不符合 Schema 定义时抛出
            json.JSONDecodeError: JSON 格式非法时抛出
        """
        return cls.model_validate_json(json_str)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        return self.model_dump()

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""
        return self.model_dump_json()

    @classmethod
    def get_schema_json(cls) -> str:
        """返回 JSON Schema 字符串（用于 Prompt 注入）。"""
        return cls.model_json_schema().__str__()
