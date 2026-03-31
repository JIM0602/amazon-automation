"""统一 LLM 调用封装。

支持模型:
  - gpt-4o-mini
  - gpt-4o
  - claude-3-5-sonnet
  - claude-3-haiku

主要接口:
  chat(model, messages, temperature, max_tokens) -> dict
    返回: {"content": str, "model": str, "input_tokens": int, "output_tokens": int, "cost_usd": float}

异常:
  DailyCostLimitExceeded — 当日费用超过上限时抛出
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging as _logging
    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

# 模块级懒加载：check_daily_limit / send_feishu_warning（便于测试 patch）
from src.llm.cost_monitor import check_daily_limit, send_feishu_warning

# 模块级懒加载：db 相关（便于测试 patch）
try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
except Exception:  # pragma: no cover
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]

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
    prices = _PRICE_TABLE.get(model, _PRICE_TABLE.get("gpt-4o-mini"))
    input_cost = (input_tokens / 1000.0) * prices["input"]
    output_cost = (output_tokens / 1000.0) * prices["output"]
    return input_cost + output_cost


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
    try:
        import litellm

        # litellm 使用统一接口
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

    except ImportError:
        # 降级：直接使用 openai
        logger.debug("litellm 未安装，降级到 openai 直接调用")
        import openai
        from src.config import settings

        api_key = getattr(settings, 'OPENAI_API_KEY', None)
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
# 主接口
# ---------------------------------------------------------------------------
def chat(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """统一 LLM 调用接口。

    流程:
      1. 对 messages 进行 PII 过滤
      2. 检查每日费用上限（超限则抛出 DailyCostLimitExceeded）
      3. 调用 LLM API
      4. 计算本次调用费用
      5. 非阻塞写入 agent_runs
      6. 返回结果字典

    Args:
        model: 模型名称（gpt-4o-mini / gpt-4o / claude-3-5-sonnet / claude-3-haiku）
        messages: OpenAI 格式消息列表，如 [{"role": "user", "content": "..."}]
        temperature: 温度参数，默认 0.7
        max_tokens: 最大输出 token 数，默认 2000

    Returns:
        {
            "content": str,
            "model": str,
            "input_tokens": int,
            "output_tokens": int,
            "cost_usd": float,
        }

    Raises:
        DailyCostLimitExceeded: 当日费用已超出上限
    """
    from datetime import datetime, timezone

    # 1. PII 过滤
    filtered_messages = _filter_messages_pii(messages)
    logger.debug(f"PII 过滤完成，准备调用模型 {model!r}")

    # 2. 检查每日费用上限
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

    # 3. 调用 LLM API
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

    # 4. 计算费用
    cost_usd = _calculate_cost(model, input_tokens, output_tokens)
    logger.info(
        f"LLM 调用完成 model={actual_model!r} "
        f"in={input_tokens} out={output_tokens} cost=${cost_usd:.6f}"
    )

    # 5. 非阻塞写入 agent_runs
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

    # 6. 返回结果
    return {
        "content": content,
        "model": actual_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
    }
