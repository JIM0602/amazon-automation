"""JSON Schema 输出校验模块单元测试。

覆盖范围：
  1. BaseOutputSchema 基类（from_dict / from_json / to_dict / to_json）
  2. SelectionResultSchema 校验（正常、缺字段、错误类型）
  3. DailyReportSchema 校验
  4. validate_llm_output 核心函数
     - 校验成功（直接 dict 输入）
     - 校验成功（JSON 字符串输入）
     - 校验失败 + 无 retry_fn → 降级
     - 校验失败 + retry_fn 重试成功
     - 校验失败 + retry_fn 重试2次仍失败 → 降级
  5. _extract_json_from_text 工具函数
  6. SchemaValidator 类（统计、reset_stats）
  7. 审计日志写入（失败时触发）
"""
from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call

import pytest
from pydantic import ValidationError


# ============================================================================ #
#  导入被测模块
# ============================================================================ #

from src.llm.schema_validator import (
    SchemaValidationResult,
    SchemaValidator,
    _extract_json_from_text,
    _normalize_llm_output,
    validate_llm_output,
    MAX_RETRIES,
)
from src.llm.schemas.base import BaseOutputSchema
from src.llm.schemas.selection_result import (
    SelectionResultSchema,
    ProductCandidateSchema,
    MarketDataSchema,
)
from src.llm.schemas.daily_report import DailyReportSchema, SalesDataSchema


# ============================================================================ #
#  测试数据 Fixtures
# ============================================================================ #

@pytest.fixture
def valid_product_candidate_dict() -> Dict[str, Any]:
    return {
        "asin": "B0PUDI001",
        "product_name": "PUDIWIND 宠物记忆棉睡垫",
        "reason": "评分4.6，BSR 1523，符合知识库原则3",
        "market_data": {
            "rating": 4.6,
            "review_count": 186,
            "price": 29.99,
            "bsr_rank": 1523,
            "monthly_sales": 320,
        },
        "risks": ["竞争中等，建议监控"],
        "score": 8.5,
        "kb_references": ["原则3：评分4.5+代表市场已验证"],
    }


@pytest.fixture
def valid_selection_result_dict(valid_product_candidate_dict) -> Dict[str, Any]:
    return {
        "category": "pet_supplies",
        "analysis_date": "2026-04-01",
        "candidates": [valid_product_candidate_dict],
        "kb_principles_used": ["原则1：搜索量>10000", "原则3：评分4.5+"],
        "agent_run_id": str(uuid.uuid4()),
    }


@pytest.fixture
def valid_daily_report_dict() -> Dict[str, Any]:
    return {
        "report_date": "2026-04-01",
        "agent_run_id": str(uuid.uuid4()),
        "sales": {
            "date": "2026-04-01",
            "revenue": 1234.56,
            "orders": 42,
            "refunds": 2,
        },
        "agent_progress": {
            "agent_statuses": [
                {
                    "agent_type": "selection_agent",
                    "status": "success",
                    "last_run": "2026-04-01 10:00:00",
                    "run_count": 1,
                }
            ],
            "pending_approvals": 3,
        },
        "market": {
            "category": "pet supplies",
            "market_size_usd": 12500000000.0,
            "growth_rate": 0.12,
            "top_keywords": ["dog leash", "cat tree"],
            "inventory_alerts": [],
        },
        "status": "completed",
        "generated_at": "2026-04-01T00:00:00+00:00",
        "dry_run": True,
    }


# ============================================================================ #
#  1. BaseOutputSchema 基类测试
# ============================================================================ #

class SimpleSchema(BaseOutputSchema):
    """测试用简单 Schema。"""
    name: str
    value: int = 0


class TestBaseOutputSchema:
    def test_from_dict_valid(self):
        data = {"name": "test", "value": 42}
        obj = SimpleSchema.from_dict(data)
        assert obj.name == "test"
        assert obj.value == 42

    def test_from_dict_extra_fields_ignored(self):
        """多余字段应被忽略（extra="ignore"）。"""
        data = {"name": "test", "value": 10, "extra_field": "should_be_ignored"}
        obj = SimpleSchema.from_dict(data)
        assert obj.name == "test"
        assert not hasattr(obj, "extra_field")

    def test_from_dict_invalid_raises(self):
        """必需字段缺失时应抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            SimpleSchema.from_dict({"value": 42})  # 缺少 name

    def test_from_json_valid(self):
        json_str = '{"name": "json_test", "value": 99}'
        obj = SimpleSchema.from_json(json_str)
        assert obj.name == "json_test"
        assert obj.value == 99

    def test_from_json_invalid_raises(self):
        with pytest.raises((ValidationError, Exception)):
            SimpleSchema.from_json("not valid json")

    def test_to_dict(self):
        obj = SimpleSchema(name="dict_test", value=7)
        result = obj.to_dict()
        assert result == {"name": "dict_test", "value": 7}

    def test_to_json(self):
        obj = SimpleSchema(name="json_test", value=3)
        json_str = obj.to_json()
        parsed = json.loads(json_str)
        assert parsed["name"] == "json_test"
        assert parsed["value"] == 3

    def test_get_schema_json(self):
        schema_json = SimpleSchema.get_schema_json()
        assert "SimpleSchema" in schema_json or "name" in schema_json


# ============================================================================ #
#  2. SelectionResultSchema 测试
# ============================================================================ #

class TestSelectionResultSchema:
    def test_valid_dict(self, valid_selection_result_dict):
        obj = SelectionResultSchema.from_dict(valid_selection_result_dict)
        assert obj.category == "pet_supplies"
        assert len(obj.candidates) == 1
        assert obj.candidates[0].asin == "B0PUDI001"

    def test_missing_required_field_raises(self, valid_selection_result_dict):
        """缺少 category 字段时应报错。"""
        data = dict(valid_selection_result_dict)
        del data["category"]
        with pytest.raises(ValidationError):
            SelectionResultSchema.from_dict(data)

    def test_empty_candidates_raises(self, valid_selection_result_dict):
        """空候选列表应触发 validator。"""
        data = dict(valid_selection_result_dict)
        data["candidates"] = []
        with pytest.raises(ValidationError) as exc_info:
            SelectionResultSchema.from_dict(data)
        assert "候选产品列表不能为空" in str(exc_info.value)

    def test_invalid_analysis_date_raises(self, valid_selection_result_dict):
        data = dict(valid_selection_result_dict)
        data["analysis_date"] = "not-a-date"
        with pytest.raises(ValidationError):
            SelectionResultSchema.from_dict(data)

    def test_score_precision(self, valid_product_candidate_dict):
        """score 应精确到小数点后1位。"""
        data = dict(valid_product_candidate_dict)
        data["score"] = 8.5555
        obj = ProductCandidateSchema.from_dict(data)
        assert obj.score == round(8.5555, 1)

    def test_asin_uppercase_normalization(self, valid_product_candidate_dict):
        """ASIN 应转为大写。"""
        data = dict(valid_product_candidate_dict)
        data["asin"] = "b0pudi001"
        obj = ProductCandidateSchema.from_dict(data)
        assert obj.asin == "B0PUDI001"

    def test_nested_market_data_validation(self, valid_product_candidate_dict):
        """market_data.rating 超出0-5范围应报错。"""
        data = dict(valid_product_candidate_dict)
        data["market_data"] = dict(valid_product_candidate_dict["market_data"])
        data["market_data"]["rating"] = 6.0  # 超出5.0限制
        with pytest.raises(ValidationError):
            ProductCandidateSchema.from_dict(data)

    def test_extra_fields_in_market_data_ignored(self, valid_product_candidate_dict):
        """market_data 中多余字段应被忽略。"""
        data = dict(valid_product_candidate_dict)
        data["market_data"] = dict(valid_product_candidate_dict["market_data"])
        data["market_data"]["unknown_field"] = "ignored"
        obj = ProductCandidateSchema.from_dict(data)
        assert obj.market_data.rating == 4.6


# ============================================================================ #
#  3. DailyReportSchema 测试
# ============================================================================ #

class TestDailyReportSchema:
    def test_valid_dict(self, valid_daily_report_dict):
        obj = DailyReportSchema.from_dict(valid_daily_report_dict)
        assert obj.report_date == "2026-04-01"
        assert obj.status == "completed"

    def test_invalid_status_raises(self, valid_daily_report_dict):
        data = dict(valid_daily_report_dict)
        data["status"] = "unknown_status"
        with pytest.raises(ValidationError):
            DailyReportSchema.from_dict(data)

    def test_invalid_report_date_raises(self, valid_daily_report_dict):
        data = dict(valid_daily_report_dict)
        data["report_date"] = "2026/04/01"  # 错误格式
        with pytest.raises(ValidationError):
            DailyReportSchema.from_dict(data)

    def test_nested_agent_status(self, valid_daily_report_dict):
        obj = DailyReportSchema.from_dict(valid_daily_report_dict)
        assert len(obj.agent_progress.agent_statuses) == 1
        assert obj.agent_progress.pending_approvals == 3

    def test_negative_revenue_raises(self, valid_daily_report_dict):
        """负销售额应报错。"""
        data = dict(valid_daily_report_dict)
        data["sales"] = dict(valid_daily_report_dict["sales"])
        data["sales"]["revenue"] = -100.0
        with pytest.raises(ValidationError):
            DailyReportSchema.from_dict(data)


# ============================================================================ #
#  4. _extract_json_from_text 工具函数测试
# ============================================================================ #

class TestExtractJsonFromText:
    def test_pure_json_string(self):
        text = '{"key": "value", "num": 42}'
        result = _extract_json_from_text(text)
        assert result == {"key": "value", "num": 42}

    def test_json_in_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_embedded_in_text(self):
        text = '这是分析结果：\n{"category": "pets", "score": 8.5}\n希望有帮助。'
        result = _extract_json_from_text(text)
        assert result is not None
        assert result["category"] == "pets"

    def test_no_json_returns_none(self):
        text = "这是纯文本，没有 JSON 内容"
        result = _extract_json_from_text(text)
        assert result is None

    def test_empty_string_returns_none(self):
        result = _extract_json_from_text("")
        assert result is None

    def test_none_input_returns_none(self):
        result = _extract_json_from_text(None)  # type: ignore[arg-type]
        assert result is None

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = _extract_json_from_text(text)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_code_block_without_json_label(self):
        text = '```\n{"key": "value"}\n```'
        result = _extract_json_from_text(text)
        assert result == {"key": "value"}


# ============================================================================ #
#  5. validate_llm_output 核心函数测试
# ============================================================================ #

class TestValidateLlmOutput:
    def test_success_with_valid_dict(self, valid_selection_result_dict):
        """有效 dict 输入应校验成功。"""
        result = validate_llm_output(
            raw_output=valid_selection_result_dict,
            schema_class=SelectionResultSchema,
        )
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, SelectionResultSchema)
        assert result.data.category == "pet_supplies"
        assert result.attempts == 1

    def test_success_with_json_string(self, valid_selection_result_dict):
        """有效 JSON 字符串应校验成功。"""
        json_str = json.dumps(valid_selection_result_dict, ensure_ascii=False)
        result = validate_llm_output(
            raw_output=json_str,
            schema_class=SelectionResultSchema,
        )
        assert result.success is True
        assert result.data.category == "pet_supplies"

    def test_success_with_json_in_text(self, valid_selection_result_dict):
        """包含 JSON 的文本应能成功提取并校验。"""
        text = f"分析完成，结果如下：\n{json.dumps(valid_selection_result_dict)}\n请查收。"
        result = validate_llm_output(
            raw_output=text,
            schema_class=SelectionResultSchema,
        )
        assert result.success is True

    def test_failure_no_retry_fn_returns_fallback(self):
        """校验失败且无 retry_fn 时应降级。"""
        invalid_data = {"category": "pets", "analysis_date": "2026-04-01"}  # 缺少 candidates
        result = validate_llm_output(
            raw_output=invalid_data,
            schema_class=SelectionResultSchema,
        )
        assert result.success is False
        assert result.fallback is not None
        assert len(result.errors) > 0
        assert result.attempts == 1  # 无 retry_fn，只尝试一次

    def test_failure_with_retry_fn_success_on_second_try(self, valid_selection_result_dict):
        """首次失败，retry_fn 返回有效数据时应在第二次成功。"""
        invalid_data = {"bad": "data"}
        retry_counter = {"count": 0}

        def retry_fn():
            retry_counter["count"] += 1
            return valid_selection_result_dict

        result = validate_llm_output(
            raw_output=invalid_data,
            schema_class=SelectionResultSchema,
            retry_fn=retry_fn,
        )
        assert result.success is True
        assert retry_counter["count"] == 1
        assert result.attempts == 2

    def test_failure_retry_fn_always_fails_degrades(self):
        """retry_fn 每次都返回无效数据，最终应降级。"""
        invalid_data = {"still_bad": "data"}
        retry_counter = {"count": 0}

        def retry_fn():
            retry_counter["count"] += 1
            return {"also_bad": "data"}

        result = validate_llm_output(
            raw_output=invalid_data,
            schema_class=SelectionResultSchema,
            retry_fn=retry_fn,
        )
        assert result.success is False
        assert retry_counter["count"] == MAX_RETRIES  # 重试了 MAX_RETRIES 次
        assert result.attempts == MAX_RETRIES + 1
        assert len(result.errors) > 0

    def test_retry_fn_raises_exception_degrades(self):
        """retry_fn 抛出异常时应优雅降级。"""
        invalid_data = {"bad": "data"}

        def failing_retry_fn():
            raise RuntimeError("LLM API error")

        result = validate_llm_output(
            raw_output=invalid_data,
            schema_class=SelectionResultSchema,
            retry_fn=failing_retry_fn,
        )
        assert result.success is False
        assert any("重试函数执行失败" in e for e in result.errors)

    def test_unparseable_input_degrades(self):
        """完全无法解析的输入应降级。"""
        result = validate_llm_output(
            raw_output=12345,  # 非 str/dict
            schema_class=SelectionResultSchema,
        )
        assert result.success is False

    def test_context_passed_to_audit_log(self, valid_selection_result_dict):
        """context 参数应传递给审计日志（校验失败时）。"""
        with patch("src.llm.schema_validator._log_validation_failure") as mock_log:
            validate_llm_output(
                raw_output={"bad": "data"},
                schema_class=SelectionResultSchema,
                context="test_context",
            )
            mock_log.assert_called_once()
            _, kwargs = mock_log.call_args
            # 检查 context 参数
            call_args = mock_log.call_args
            assert "test_context" in str(call_args)

    def test_audit_log_written_on_failure(self):
        """Schema 校验失败时，audit log 应被写入。"""
        with patch("src.llm.schema_validator._log_validation_failure") as mock_log_fn:
            validate_llm_output(
                raw_output={"invalid": "no_candidates"},
                schema_class=SelectionResultSchema,
                context="audit_test",
            )
            mock_log_fn.assert_called_once()

    def test_audit_log_not_written_on_success(self, valid_selection_result_dict):
        """Schema 校验成功时，audit log 不应被写入。"""
        with patch("src.llm.schema_validator._log_validation_failure") as mock_log_fn:
            validate_llm_output(
                raw_output=valid_selection_result_dict,
                schema_class=SelectionResultSchema,
            )
            mock_log_fn.assert_not_called()

    def test_fallback_contains_original_data_on_failure(self):
        """失败时 fallback 应包含原始（规范化后）数据。"""
        original = {"category": "pets", "analysis_date": "2026-04-01"}
        result = validate_llm_output(
            raw_output=original,
            schema_class=SelectionResultSchema,
        )
        assert result.success is False
        assert result.fallback.get("category") == "pets"

    def test_daily_report_schema_validation(self, valid_daily_report_dict):
        """DailyReportSchema 校验测试。"""
        result = validate_llm_output(
            raw_output=valid_daily_report_dict,
            schema_class=DailyReportSchema,
        )
        assert result.success is True
        assert result.data.report_date == "2026-04-01"


# ============================================================================ #
#  6. SchemaValidator 类测试
# ============================================================================ #

class TestSchemaValidator:
    def test_stats_initial(self):
        validator = SchemaValidator(context="test")
        assert validator.stats == {"total": 0, "success": 0, "failed": 0}

    def test_stats_after_success(self, valid_selection_result_dict):
        validator = SchemaValidator(context="test")
        validator.validate(valid_selection_result_dict, SelectionResultSchema)
        assert validator.stats["total"] == 1
        assert validator.stats["success"] == 1
        assert validator.stats["failed"] == 0

    def test_stats_after_failure(self):
        validator = SchemaValidator(context="test")
        validator.validate({"bad": "data"}, SelectionResultSchema)
        assert validator.stats["total"] == 1
        assert validator.stats["success"] == 0
        assert validator.stats["failed"] == 1

    def test_stats_accumulate(self, valid_selection_result_dict):
        validator = SchemaValidator(context="test")
        validator.validate(valid_selection_result_dict, SelectionResultSchema)  # success
        validator.validate({"bad": "data"}, SelectionResultSchema)  # failure
        assert validator.stats["total"] == 2
        assert validator.stats["success"] == 1
        assert validator.stats["failed"] == 1

    def test_reset_stats(self, valid_selection_result_dict):
        validator = SchemaValidator()
        validator.validate(valid_selection_result_dict, SelectionResultSchema)
        validator.reset_stats()
        assert validator.stats == {"total": 0, "success": 0, "failed": 0}

    def test_validate_with_retry_fn(self, valid_selection_result_dict):
        """SchemaValidator.validate 支持 retry_fn 参数。"""
        validator = SchemaValidator(context="test_retry")
        result = validator.validate(
            raw_output={"bad": "data"},
            schema_class=SelectionResultSchema,
            retry_fn=lambda: valid_selection_result_dict,
        )
        assert result.success is True
        assert validator.stats["success"] == 1

    def test_context_passed_through(self, valid_selection_result_dict):
        """context 应透传给 validate_llm_output。"""
        validator = SchemaValidator(context="my_context")
        with patch("src.llm.schema_validator.validate_llm_output") as mock_validate:
            mock_validate.return_value = SchemaValidationResult(
                success=True,
                data=MagicMock(spec=SelectionResultSchema),
                attempts=1,
            )
            validator.validate(valid_selection_result_dict, SelectionResultSchema)
            mock_validate.assert_called_once()
            call_kwargs = mock_validate.call_args[1]
            assert call_kwargs.get("context") == "my_context"


# ============================================================================ #
#  7. 审计日志集成测试
# ============================================================================ #

class TestAuditLogIntegration:
    def test_audit_log_called_with_correct_schema_name(self):
        """失败时审计日志应包含正确的 schema 名称。"""
        with patch("src.llm.schema_validator._log_validation_failure") as mock_fn:
            validate_llm_output(
                raw_output={"bad": "no_required_fields"},
                schema_class=SelectionResultSchema,
                context="audit_integration_test",
            )
            args, kwargs = mock_fn.call_args
            assert kwargs.get("schema_name") == "SelectionResultSchema"

    def test_audit_log_contains_errors(self):
        """审计日志的 errors 参数应包含错误信息。"""
        with patch("src.llm.schema_validator._log_validation_failure") as mock_fn:
            validate_llm_output(
                raw_output={"invalid": "data"},
                schema_class=SelectionResultSchema,
            )
            args, kwargs = mock_fn.call_args
            assert len(kwargs.get("errors", [])) > 0


# ============================================================================ #
#  8. SchemaValidationResult 容器测试
# ============================================================================ #

class TestSchemaValidationResult:
    def test_repr_success(self):
        data = MagicMock(spec=BaseOutputSchema)
        data.__class__.__name__ = "TestSchema"
        result = SchemaValidationResult(success=True, data=data)
        assert "success=True" in repr(result)

    def test_repr_failure(self):
        result = SchemaValidationResult(
            success=False,
            errors=["field required"],
            attempts=3,
        )
        assert "success=False" in repr(result)
        assert "attempts=3" in repr(result)

    def test_fallback_defaults_to_empty_dict(self):
        result = SchemaValidationResult(success=False)
        assert result.fallback == {}

    def test_errors_defaults_to_empty_list(self):
        result = SchemaValidationResult(success=True)
        assert result.errors == []
