"""JSON Schema 输出校验模块。

职责：
  1. 对 LLM 输出进行 Pydantic Schema 校验
  2. 校验失败时自动重试（最多2次）
  3. 重试2次仍失败时降级（返回原始输出 dict）
  4. 校验失败时记录到审计日志

设计原则：
  - 不强制所有 LLM 调用都用 Schema（仅结构化输出场景）
  - Schema 校验失败不应阻塞整个流程（降级为原始输出）
  - 校验失败事件必须可追溯（写入审计日志）

主要接口：
  validate_llm_output(raw_output, schema_class, ...) -> SchemaValidationResult
  SchemaValidator                                    — 有状态校验器类

用法示例::

    from src.llm.schema_validator import validate_llm_output
    from src.llm.schemas import SelectionResultSchema

    result = validate_llm_output(raw_output, SelectionResultSchema)
    if result.success:
        report = result.data          # SelectionResultSchema 实例
    else:
        raw_dict = result.fallback    # 原始输出 dict（降级）
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import ValidationError

from src.llm.schemas.base import BaseOutputSchema

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseOutputSchema)

# 最大重试次数（含首次尝试之后的2次重试）
MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# 结果容器
# ---------------------------------------------------------------------------

class SchemaValidationResult:
    """Schema 校验结果容器。

    Attributes:
        success (bool):      校验是否成功
        data (Optional[T]):  成功时的 Schema 实例
        fallback (dict):     失败时的原始输出字典（降级）
        errors (list):       错误信息列表（所有尝试的错误）
        attempts (int):      实际尝试次数
    """

    def __init__(
        self,
        success: bool,
        data: Optional[BaseOutputSchema] = None,
        fallback: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        attempts: int = 1,
    ):
        self.success = success
        self.data = data
        self.fallback = fallback or {}
        self.errors = errors or []
        self.attempts = attempts

    def __repr__(self) -> str:
        if self.success:
            return f"<SchemaValidationResult success=True data={type(self.data).__name__}>"
        return (
            f"<SchemaValidationResult success=False "
            f"attempts={self.attempts} errors={self.errors[:1]}>"
        )


# ---------------------------------------------------------------------------
# 工具函数：从 LLM 输出中提取 JSON
# ---------------------------------------------------------------------------

def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """从 LLM 输出文本中提取 JSON。

    支持以下格式：
    1. 纯 JSON 字符串
    2. ```json ... ``` 代码块
    3. 文本中内嵌的 JSON（最大花括号块）

    Args:
        text: LLM 输出文本

    Returns:
        解析出的 dict，若无法提取则返回 None
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # 方式1：直接尝试解析整个文本
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 方式2：提取 ```json ... ``` 代码块
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 方式3：找到最外层花括号块
    start_idx = text.find("{")
    if start_idx != -1:
        # 找到匹配的结束花括号
        depth = 0
        for i, ch in enumerate(text[start_idx:], start=start_idx):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_candidate = text[start_idx : i + 1]
                    try:
                        result = json.loads(json_candidate)
                        if isinstance(result, dict):
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break

    return None


def _normalize_llm_output(raw_output: Any) -> Optional[Dict[str, Any]]:
    """将 LLM 输出规范化为 dict。

    支持：
    - str (JSON 或含 JSON 的文本)
    - dict
    - BaseOutputSchema 实例

    Args:
        raw_output: LLM 原始输出

    Returns:
        规范化后的 dict，失败时返回 None
    """
    if isinstance(raw_output, dict):
        return raw_output

    if isinstance(raw_output, BaseOutputSchema):
        return raw_output.to_dict()

    if isinstance(raw_output, str):
        result = _extract_json_from_text(raw_output)
        if result is not None:
            return result
        # 若无法解析 JSON，尝试包装为 {"content": text}
        return {"_raw_text": raw_output}

    return None


# ---------------------------------------------------------------------------
# 核心校验函数
# ---------------------------------------------------------------------------

def validate_llm_output(
    raw_output: Any,
    schema_class: Type[T],
    retry_fn: Optional[Callable[[], Any]] = None,
    context: Optional[str] = None,
) -> SchemaValidationResult:
    """对 LLM 输出进行 Schema 校验，失败时自动重试最多2次。

    流程：
      1. 尝试将 raw_output 规范化为 dict
      2. 用 schema_class 进行 Pydantic 校验
      3. 校验失败时，若提供 retry_fn 则重新调用 LLM 获取新输出并重试
      4. 超过 MAX_RETRIES 次仍失败 → 降级（返回原始 dict，success=False）
      5. 校验失败时写入审计日志

    Args:
        raw_output:   LLM 原始输出（str 或 dict）
        schema_class: 目标 Pydantic Schema 类（继承 BaseOutputSchema）
        retry_fn:     可选，重试时调用的函数，无参数，返回新的 LLM 输出
        context:      可选，上下文说明（写入审计日志，便于追溯）

    Returns:
        SchemaValidationResult

    Example::

        result = validate_llm_output(
            raw_output=llm_response,
            schema_class=SelectionResultSchema,
            retry_fn=lambda: call_llm_again(),
            context="selection_agent.generate_report",
        )
        if result.success:
            data: SelectionResultSchema = result.data
        else:
            fallback_dict = result.fallback  # 降级数据
    """
    schema_name = schema_class.__name__
    all_errors: List[str] = []
    fallback_dict: Dict[str, Any] = {}

    # 首次尝试 + 最多 MAX_RETRIES 次重试
    current_output = raw_output
    for attempt in range(MAX_RETRIES + 1):
        # 规范化输出
        normalized = _normalize_llm_output(current_output)

        if normalized is None:
            error_msg = f"无法解析 LLM 输出为 dict，类型={type(current_output).__name__}"
            logger.warning(
                "schema_validator | attempt=%d schema=%s error=%s",
                attempt + 1,
                schema_name,
                error_msg,
            )
            all_errors.append(f"[attempt {attempt + 1}] {error_msg}")
            fallback_dict = {"_unparseable": str(current_output)[:500]}
        else:
            # 保存 fallback 数据（最后一次规范化结果）
            fallback_dict = normalized

            try:
                validated = schema_class.from_dict(normalized)
                logger.info(
                    "schema_validator | 校验成功 schema=%s attempt=%d context=%s",
                    schema_name,
                    attempt + 1,
                    context or "N/A",
                )
                return SchemaValidationResult(
                    success=True,
                    data=validated,
                    fallback=normalized,
                    errors=all_errors,
                    attempts=attempt + 1,
                )
            except ValidationError as exc:
                error_summary = _summarize_validation_error(exc)
                logger.warning(
                    "schema_validator | 校验失败 schema=%s attempt=%d/%d errors=%s context=%s",
                    schema_name,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    error_summary,
                    context or "N/A",
                )
                all_errors.append(f"[attempt {attempt + 1}] {error_summary}")

        # 若还有重试机会
        if attempt < MAX_RETRIES:
            if retry_fn is not None:
                logger.info(
                    "schema_validator | 触发重试 schema=%s attempt=%d/%d",
                    schema_name,
                    attempt + 1,
                    MAX_RETRIES + 1,
                )
                try:
                    current_output = retry_fn()
                except Exception as retry_exc:
                    error_msg = f"重试函数执行失败: {retry_exc}"
                    logger.error("schema_validator | %s", error_msg)
                    all_errors.append(f"[retry {attempt + 1}] {error_msg}")
                    break  # 重试函数失败，直接降级
            else:
                # 没有 retry_fn，无法重试，直接降级
                logger.debug(
                    "schema_validator | 无 retry_fn，跳过重试 schema=%s", schema_name
                )
                break

    # 所有尝试均失败 → 降级处理
    logger.warning(
        "schema_validator | 降级处理 schema=%s total_attempts=%d context=%s",
        schema_name,
        min(attempt + 1, MAX_RETRIES + 1),
        context or "N/A",
    )

    # 写审计日志
    _log_validation_failure(
        schema_name=schema_name,
        errors=all_errors,
        fallback=fallback_dict,
        context=context,
    )

    return SchemaValidationResult(
        success=False,
        data=None,
        fallback=fallback_dict,
        errors=all_errors,
        attempts=min(attempt + 1, MAX_RETRIES + 1),
    )


def _summarize_validation_error(exc: ValidationError) -> str:
    """从 Pydantic ValidationError 提取简洁的错误摘要。"""
    errors = exc.errors()
    if not errors:
        return str(exc)

    summaries = []
    for err in errors[:3]:  # 最多显示3个错误
        loc = ".".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "")
        summaries.append(f"{loc}: {msg}" if loc else msg)

    total = len(errors)
    suffix = f" (+{total - 3} more)" if total > 3 else ""
    return "; ".join(summaries) + suffix


def _log_validation_failure(
    schema_name: str,
    errors: List[str],
    fallback: Dict[str, Any],
    context: Optional[str] = None,
) -> None:
    """将 Schema 校验失败事件写入审计日志（非阻塞）。

    Args:
        schema_name: Schema 类名
        errors:      错误信息列表
        fallback:    降级数据摘要
        context:     上下文说明
    """
    try:
        from src.utils.audit import log_action

        # 摘要化 fallback（避免审计日志过大）
        fallback_summary = {
            k: str(v)[:200] for k, v in list(fallback.items())[:10]
        }

        log_action(
            action="schema_validation.failed",
            actor="schema_validator",
            pre_state={
                "schema": schema_name,
                "context": context or "N/A",
            },
            post_state={
                "errors": errors[:5],  # 最多5条错误
                "fallback_keys": list(fallback.keys())[:20],
                "fallback_preview": fallback_summary,
            },
        )
    except Exception as exc:
        logger.warning("schema_validator | 审计日志写入失败（非阻塞）: %s", exc)


# ---------------------------------------------------------------------------
# 有状态校验器类（便于注入到 Agent）
# ---------------------------------------------------------------------------

class SchemaValidator:
    """有状态的 Schema 校验器。

    封装校验逻辑，提供统计计数和上下文追踪。

    Usage::

        validator = SchemaValidator(context="selection_agent")
        result = validator.validate(raw_output, SelectionResultSchema)
        print(validator.stats)  # {"total": 1, "success": 1, "failed": 0}
    """

    def __init__(self, context: Optional[str] = None):
        self.context = context
        self._total = 0
        self._success = 0
        self._failed = 0

    @property
    def stats(self) -> Dict[str, int]:
        """返回校验统计。"""
        return {
            "total": self._total,
            "success": self._success,
            "failed": self._failed,
        }

    def validate(
        self,
        raw_output: Any,
        schema_class: Type[T],
        retry_fn: Optional[Callable[[], Any]] = None,
    ) -> SchemaValidationResult:
        """执行 Schema 校验。

        Args:
            raw_output:   LLM 原始输出
            schema_class: 目标 Schema 类
            retry_fn:     可选重试函数

        Returns:
            SchemaValidationResult
        """
        self._total += 1
        result = validate_llm_output(
            raw_output=raw_output,
            schema_class=schema_class,
            retry_fn=retry_fn,
            context=self.context,
        )
        if result.success:
            self._success += 1
        else:
            self._failed += 1
        return result

    def reset_stats(self) -> None:
        """重置统计计数。"""
        self._total = 0
        self._success = 0
        self._failed = 0
