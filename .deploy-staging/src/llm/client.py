"""统一 LLM 调用封装。

支持模型:
  - gpt-4o-mini
  - gpt-4o
  - claude-3-5-sonnet
  - claude-3-haiku

主要接口:
  chat(model, messages, temperature, max_tokens) -> dict
    返回: {"content": str, "model": str, "input_tokens": int, "output_tokens": int, "cost_usd": float,
           "cache_hit": bool}

异常:
  DailyCostLimitExceeded — 当日费用超过上限时抛出
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, AsyncGenerator

try:
    from loguru import logger  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover
    import logging as _logging
    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

# 模块级懒加载：check_daily_limit / send_feishu_warning（便于测试 patch）
from src.llm.cost_monitor import check_daily_limit, send_feishu_warning

# 限流模块（便于测试 patch）
from src.utils.rate_limiter import get_rate_limiter, RateLimitExceeded
from src.utils.api_priority import ApiPriority

# 缓存模块（便于测试 patch）
try:
    from src.llm.cache import (
        compute_cache_key,
        get_cached_response,
        set_cached_response,
        record_cache_hit,
        is_cacheable,
    )
    _cache_available = True
except Exception:  # pragma: no cover
    _cache_available = False
    compute_cache_key = None  # type: ignore[assignment]
    get_cached_response = None  # type: ignore[assignment]
    set_cached_response = None  # type: ignore[assignment]
    record_cache_hit = None  # type: ignore[assignment]
    is_cacheable = None  # type: ignore[assignment]

# 模块级懒加载：db 相关（便于测试 patch）
try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
except Exception:  # pragma: no cover
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]

# 模块级懒加载：settings（便于测试 patch）
try:
    from src.config import settings
except Exception:  # pragma: no cover
    settings = None  # type: ignore[assignment]


def _resolve_provider(model: str) -> str:
    if model.startswith("openrouter/"):
        return "openrouter"
    if model.startswith("anthropic/") or model.startswith("claude"):
        return "anthropic"
    return "openai"


def _prepare_model_for_provider(model: str, provider: str) -> str:
    if provider == "openrouter":
        if model.startswith("openrouter/"):
            return model
        return f"openrouter/{model}"
    if provider == "anthropic":
        if model.startswith("anthropic/"):
            return model
        if model.startswith("claude"):
            return f"anthropic/{model}"
    return model


def _fallback_openai_model(model: str) -> str:
    if "/" in model:
        return model.split("/")[-1]
    return model


def _get_openrouter_key() -> Optional[str]:
    return getattr(settings, "OPENROUTER_API_KEY", None) if settings is not None else None


def _configure_openrouter_env() -> None:
    openrouter_key = _get_openrouter_key()
    if openrouter_key:
        import os

        os.environ["OPENROUTER_API_KEY"] = openrouter_key


def _call_litellm_completion(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    import litellm  # pyright: ignore[reportMissingImports]

    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    actual_model = response.model or model
    return {
        "content": content,
        "model": actual_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _call_openai_completion(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    import openai  # pyright: ignore[reportMissingImports]

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    actual_model = response.model or model
    return {
        "content": content,
        "model": actual_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

# ---------------------------------------------------------------------------
# 费用价格表 (USD/1K tokens)
# ---------------------------------------------------------------------------
_PRICE_TABLE: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}

# 默认每日上限 (USD)
_DEFAULT_DAILY_LIMIT = 50.0


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------
class DailyCostLimitExceeded(Exception):
    """当日 LLM 调用费用超过上限时抛出。"""

    def __init__(self, daily_cost: float, limit: float):
        self.daily_cost = daily_cost
        self.limit = limit
        super().__init__(
            f"每日 LLM 费用超限：今日已花费 ${daily_cost:.4f}，上限为 ${limit:.2f}"
        )


# ---------------------------------------------------------------------------
# 内部：费用计算
# ---------------------------------------------------------------------------
def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """根据价格表计算 LLM 调用费用（USD）。

    Args:
        model: 模型名称
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数

    Returns:
        费用（USD）
    """
    prices = _PRICE_TABLE.get(model) or _PRICE_TABLE["gpt-4o-mini"]
    input_cost = (input_tokens / 1000.0) * prices["input"]
    output_cost = (output_tokens / 1000.0) * prices["output"]
    return input_cost + output_cost


def _track_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    agent_type: str,
) -> float:
    """记录一次 LLM 调用的用量与费用。"""
    from datetime import datetime, timezone

    cost_usd = _calculate_cost(model, input_tokens, output_tokens)
    started_at = datetime.now(tz=timezone.utc)
    finished_at = started_at

    try:
        _record_agent_run(
            model=model,
            content=f"agent_type={agent_type}; input_tokens={input_tokens}; output_tokens={output_tokens}",
            cost_usd=cost_usd,
            started_at=started_at,
            finished_at=finished_at,
        )
    except Exception as e:
        logger.warning(f"记录 usage 失败（非阻塞）: {e}")

    return cost_usd


# ---------------------------------------------------------------------------
# 内部：将消息列表中的文本进行 PII 过滤
# ---------------------------------------------------------------------------
def _filter_messages_pii(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """对消息列表进行 PII 脱敏（深拷贝，不修改原始列表）。

    Args:
        messages: OpenAI 格式消息列表

    Returns:
        脱敏后的消息列表
    """
    from src.llm.cost_monitor import filter_pii

    filtered = []
    for msg in messages:
        new_msg = dict(msg)
        if isinstance(new_msg.get("content"), str):
            new_msg["content"] = filter_pii(new_msg["content"])
        filtered.append(new_msg)
    return filtered


# ---------------------------------------------------------------------------
# 内部：实际调用 LLM API（便于测试时 mock）
# ---------------------------------------------------------------------------
def _call_llm_api(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """调用实际的 LLM API（优先 litellm，否则 openai）。

    Args:
        model: 模型名称
        messages: 消息列表（已脱敏）
        temperature: 温度参数
        max_tokens: 最大输出 token

    Returns:
        {
            "content": str,
            "model": str,
            "input_tokens": int,
            "output_tokens": int,
        }
    """
    provider = _resolve_provider(model)
    routed_model = _prepare_model_for_provider(model, provider)

    if provider == "openrouter":
        openrouter_key = _get_openrouter_key()
        if openrouter_key:
            _configure_openrouter_env()
            return _call_litellm_completion(routed_model, messages, temperature, max_tokens)
        logger.info("OpenRouter key 为空，降级为 OpenAI 直连: %s", model)
        return _call_openai_completion(_fallback_openai_model(model.replace("openrouter/", "", 1)), messages, temperature, max_tokens)

    try:
        if provider == "anthropic":
            _configure_openrouter_env()
            return _call_litellm_completion(routed_model, messages, temperature, max_tokens)

        return _call_litellm_completion(routed_model, messages, temperature, max_tokens)

    except ImportError:
        logger.debug("litellm 未安装，降级到 openai 直接调用")
        return _call_openai_completion(model, messages, temperature, max_tokens)

# ---------------------------------------------------------------------------
# 内部：非阻塞写入 agent_runs
# ---------------------------------------------------------------------------
def _record_agent_run(
    model: str,
    content: str,
    cost_usd: float,
    started_at,
    finished_at,
) -> None:
    """将 LLM 调用记录写入 agent_runs 表。

    非阻塞：即使数据库写入失败也不影响调用结果。

    Args:
        model: 模型名称
        content: 输出内容
        cost_usd: 本次调用费用
        started_at: 调用开始时间
        finished_at: 调用完成时间
    """
    if AgentRun is None or db_session is None:
        logger.warning("记录 agent_runs 失败：数据库组件不可用")
        return
    try:
        run = AgentRun(
            agent_type="llm_call",
            status="completed",
            input_summary=model,
            output_summary=content[:100],
            cost_usd=cost_usd,
            started_at=started_at,
            finished_at=finished_at,
        )
        with db_session() as session:
            session.add(run)
            session.commit()
        logger.debug(f"已记录 LLM 调用到 agent_runs，费用 ${cost_usd:.6f}")
    except Exception as e:
        logger.warning(f"记录 agent_runs 失败（非阻塞）: {e}")


# ---------------------------------------------------------------------------
# 内部：缓存命中时写入审计日志
# ---------------------------------------------------------------------------
def _record_cache_hit_audit(model: str, cache_key: str) -> None:
    """缓存命中时写入审计日志（agent_runs）。

    非阻塞：即使数据库写入失败也不影响调用结果。

    Args:
        model: 模型名称
        cache_key: 命中的缓存键
    """
    if AgentRun is None or db_session is None:
        logger.warning("写入缓存命中审计日志失败：数据库组件不可用")
        return
    try:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        run = AgentRun(
            agent_type="llm_cache_hit",
            status="completed",
            input_summary=f"{model}:{cache_key[:16]}",
            output_summary="cache_hit",
            cost_usd=0.0,
            started_at=now,
            finished_at=now,
        )
        with db_session() as session:
            session.add(run)
            session.commit()
        logger.debug(f"缓存命中审计日志已写入: model={model!r}")
    except Exception as e:
        logger.warning(f"写入缓存命中审计日志失败（非阻塞）: {e}")


# ---------------------------------------------------------------------------
# 主接口
# ---------------------------------------------------------------------------
def chat(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    priority: ApiPriority = ApiPriority.NORMAL,
    account_id: str = "default",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """统一 LLM 调用接口。

    流程:
      1. 限流检查（令牌桶）
      2. 对 messages 进行 PII 过滤
      3. 检查缓存（若 use_cache=True 且请求可缓存）
      4. 缓存命中时直接返回（记录审计日志）
      5. 检查每日费用上限（超限则抛出 DailyCostLimitExceeded）
      6. 调用 LLM API
      7. 计算本次调用费用
      8. 写入缓存
      9. 非阻塞写入 agent_runs
      10. 返回结果字典

    Args:
        model: 模型名称（gpt-4o-mini / gpt-4o / claude-3-5-sonnet / claude-3-haiku）
        messages: OpenAI 格式消息列表，如 [{"role": "user", "content": "..."}]
        temperature: 温度参数，默认 0.7
        max_tokens: 最大输出 token 数，默认 2000
        priority: 调用优先级，影响限流权重，默认 NORMAL
        account_id: 账号 ID，用于按账号维度限流，默认 "default"
        use_cache: 是否启用缓存，默认 True

    Returns:
        {
            "content": str,
            "model": str,
            "input_tokens": int,
            "output_tokens": int,
            "cost_usd": float,
            "cache_hit": bool,
        }

    Raises:
        DailyCostLimitExceeded: 当日费用已超出上限
        RateLimitExceeded: 请求被限流（status_code=429）
    """
    from datetime import datetime, timezone

    # 1. 限流检查
    limiter = get_rate_limiter()
    limiter.acquire_or_raise(
        api_group="llm",
        account_id=account_id,
        priority=priority,
    )

    # 2. PII 过滤
    filtered_messages = _filter_messages_pii(messages)
    logger.debug(f"PII 过滤完成，准备调用模型 {model!r}")

    # 3. 检查缓存
    if use_cache and _cache_available and is_cacheable is not None and compute_cache_key is not None and get_cached_response is not None and record_cache_hit is not None:
        cache_key = compute_cache_key(
            messages=filtered_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cached = get_cached_response(cache_key)
        if cached is not None:
            # 4. 缓存命中：更新命中计数并记录审计日志
            record_cache_hit(cache_key)
            _record_cache_hit_audit(model=model, cache_key=cache_key)
            logger.info(
                f"LLM 缓存命中 model={model!r} key={cache_key[:16]}..."
            )
            result = dict(cached)
            result["cache_hit"] = True
            return result
    else:
        cache_key = None

    # 5. 检查每日费用上限
    status = check_daily_limit()
    if status["exceeded"]:
        logger.error(
            f"每日 LLM 费用超限：已花费 ${status['daily_cost']:.4f} / "
            f"上限 ${status['limit']:.2f}"
        )
        raise DailyCostLimitExceeded(
            daily_cost=status["daily_cost"],
            limit=status["limit"],
        )

    # 发送 80% 预警（在调用前，不阻塞）
    if status["warning"]:
        try:
            send_feishu_warning(status["percentage"])
        except Exception as e:
            logger.warning(f"预警发送失败（继续执行）: {e}")

    # 6. 调用 LLM API
    started_at = datetime.now(tz=timezone.utc)
    api_result = _call_llm_api(
        model=model,
        messages=filtered_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    finished_at = datetime.now(tz=timezone.utc)

    content = api_result["content"]
    actual_model = api_result["model"]
    input_tokens = api_result["input_tokens"]
    output_tokens = api_result["output_tokens"]

    # 7. 计算费用
    cost_usd = _calculate_cost(model, input_tokens, output_tokens)
    logger.info(
        f"LLM 调用完成 model={actual_model!r} "
        f"in={input_tokens} out={output_tokens} cost=${cost_usd:.6f}"
    )

    # 8. 写入缓存（若 use_cache=True，请求可缓存，且有 cache_key）
    if use_cache and _cache_available and cache_key is not None:
        if is_cacheable is not None and set_cached_response is not None and is_cacheable(filtered_messages, response_content=content):
            response_to_cache = {
                "content": content,
                "model": actual_model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            }
            try:
                set_cached_response(
                    cache_key=cache_key,
                    messages=filtered_messages,
                    model=actual_model,
                    response=response_to_cache,
                )
            except Exception as e:
                logger.warning(f"写入缓存失败（非阻塞）: {e}")

    # 9. 非阻塞写入 agent_runs
    try:
        _record_agent_run(
            model=actual_model,
            content=content,
            cost_usd=cost_usd,
            started_at=started_at,
            finished_at=finished_at,
        )
    except Exception as e:
        logger.warning(f"记录 agent_runs 失败（非阻塞，来自 chat）: {e}")

    # 10. 返回结果
    return {
        "content": content,
        "model": actual_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "cache_hit": False,
    }


async def chat_stream(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    agent_type: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """统一 LLM 流式调用接口。"""
    resolved_model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    resolved_temperature = 0.7 if temperature is None else temperature
    resolved_max_tokens = 2000 if max_tokens is None else max_tokens
    provider = _resolve_provider(resolved_model)
    routed_model = _prepare_model_for_provider(resolved_model, provider)

    try:
        limiter = get_rate_limiter()
        limiter.acquire_or_raise(
            api_group="llm",
            account_id="default",
            priority=ApiPriority.NORMAL,
        )

        filtered_messages = _filter_messages_pii(messages)
        logger.debug(f"PII 过滤完成，准备流式调用模型 {resolved_model!r}")

        status = check_daily_limit()
        if status["exceeded"]:
            logger.error(
                f"每日 LLM 费用超限：已花费 ${status['daily_cost']:.4f} / "
                f"上限 ${status['limit']:.2f}"
            )
            raise DailyCostLimitExceeded(
                daily_cost=status["daily_cost"],
                limit=status["limit"],
            )

        if status["warning"]:
            try:
                send_feishu_warning(status["percentage"])
            except Exception as e:
                logger.warning(f"预警发送失败（继续执行）: {e}")

        input_tokens = 0
        output_tokens = 0
        actual_model = resolved_model
        collected_content = ""

        if provider == "openrouter":
            openrouter_key = _get_openrouter_key()
            if openrouter_key:
                _configure_openrouter_env()
            else:
                logger.info("OpenRouter key 为空，流式调用降级到 OpenAI 直连: %s", resolved_model)
                provider = "openai"
                routed_model = _fallback_openai_model(resolved_model.replace("openrouter/", "", 1))

        if provider == "anthropic":
            _configure_openrouter_env()

        if provider in {"openrouter", "anthropic"}:
            import litellm  # pyright: ignore[reportMissingImports]

            response = await litellm.acompletion(
                model=routed_model,
                messages=filtered_messages,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in response:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if content:
                    collected_content += content
                    output_tokens += 1
                    yield content

            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "completion_tokens", output_tokens) or output_tokens)
            actual_model = getattr(response, "model", resolved_model) or resolved_model
        else:
            import openai  # pyright: ignore[reportMissingImports]

            api_key = getattr(settings, "OPENAI_API_KEY", None)
            client = openai.AsyncOpenAI(api_key=api_key)

            response = await client.chat.completions.create(
                model=resolved_model,
                messages=filtered_messages,
                stream=True,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
            )

            async for chunk in response:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if content:
                    collected_content += content
                    output_tokens += 1
                    yield content

            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "completion_tokens", output_tokens) or output_tokens)
            actual_model = getattr(response, "model", resolved_model) or resolved_model

        _track_usage(
            model=actual_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            agent_type=agent_type or "llm_stream",
        )

    except Exception as e:
        logger.error(f"chat_stream error: {e}")
        yield f"\n\n[Error: {str(e)}]"
