"""集成测试专用 Fixtures。

提供：
- mock_all_external: 自动 patch 所有外部依赖（OpenAI / 飞书 / 卖家精灵 / DB）
- mock_feishu_bot: Mock 飞书 Bot 实例
- mock_rag_engine: Mock RAG 引擎（返回固定检索结果）
- mock_db_session: SQLite in-memory 数据库会话
- mock_llm_client: Mock LLM 调用（返回固定响应）
- mock_seller_sprite: Mock 卖家精灵 API

Scope 隔离：
- 所有 fixtures 使用 function scope（不影响单元测试）
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================ #
#  内部 Helpers
# ============================================================================ #

def _make_mock_db_session():
    """创建 mock db_session 上下文管理器（与单元测试相同模式）。"""
    mock_session = MagicMock()

    @contextmanager
    def _mock_cm():
        yield mock_session

    return _mock_cm, mock_session


def _make_rag_search_result(chunk_text: str = "测试文档内容", title: str = "测试文档") -> List[Dict]:
    """生成 Mock RAG 检索结果。"""
    return [
        {
            "chunk_text": chunk_text,
            "chunk_index": 0,
            "metadata": {
                "title": title,
                "category": "运营",
                "source": "test_doc.md",
            },
            "similarity_score": 0.92,
        }
    ]


# ============================================================================ #
#  核心 Fixtures
# ============================================================================ #

@pytest.fixture(scope="function")
def mock_db():
    """返回 (mock_cm, mock_session) 元组，用于 db_session 替换。"""
    return _make_mock_db_session()


@pytest.fixture(scope="function")
def mock_feishu_bot():
    """返回 Mock 飞书 Bot 实例，预设常用方法返回值。"""
    bot = MagicMock()
    bot.send_thinking.return_value = "msg_thinking_001"
    bot.send_text_message.return_value = {"code": 0, "data": {"message_id": "msg_text_001"}}
    bot.send_card_message.return_value = {"code": 0, "data": {"message_id": "msg_card_001"}}
    bot.update_message.return_value = {"code": 0}
    bot.get_tenant_access_token.return_value = "mock_tenant_token_xyz"
    return bot


@pytest.fixture(scope="function")
def mock_rag_results():
    """返回 Mock RAG 检索结果列表。"""
    return _make_rag_search_result(
        chunk_text="选品原则：评分≥4.5，BSR≤5000，竞争适中，定价在市场中位数",
        title="亚马逊选品指南"
    )


@pytest.fixture(scope="function")
def mock_llm_response():
    """返回 Mock LLM 响应字典。"""
    return {
        "content": "根据知识库内容，建议选择评分高、竞争适中的产品。【来源：亚马逊选品指南】",
        "model": "gpt-4o-mini",
        "input_tokens": 150,
        "output_tokens": 80,
        "cost_usd": 0.0001,
    }


@pytest.fixture(scope="function")
def mock_cost_status_ok():
    """返回 Mock 费用检查结果（未超限）。"""
    return {
        "daily_cost": 1.5,
        "limit": 50.0,
        "percentage": 3.0,
        "exceeded": False,
        "warning": False,
    }


@pytest.fixture(scope="function")
def mock_cost_status_exceeded():
    """返回 Mock 费用检查结果（已超限）。"""
    return {
        "daily_cost": 55.0,
        "limit": 50.0,
        "percentage": 110.0,
        "exceeded": True,
        "warning": True,
    }


@pytest.fixture(scope="function")
def mock_all_external(mock_feishu_bot, mock_rag_results, mock_llm_response, mock_cost_status_ok):
    """
    自动 patch 所有外部依赖的综合 Fixture。

    覆盖：
    - 飞书 Bot（发送消息）
    - RAG 引擎（检索 + 回答）
    - LLM 调用（chat）
    - 费用检查（check_daily_limit）
    - DB session（多个模块）
    - 卖家精灵（不可用降级）
    - Kill Switch（正常状态）

    Returns:
        dict with keys: bot, rag_search_results, llm_response, mock_sessions
    """
    mock_cm, mock_session = _make_mock_db_session()
    audit_mock_cm, audit_mock_session = _make_mock_db_session()

    with patch("src.feishu.bot_handler.get_bot", return_value=mock_feishu_bot), \
         patch("src.agents.core_agent.daily_report.get_bot", return_value=mock_feishu_bot), \
         patch("src.llm.cost_monitor.get_bot", return_value=mock_feishu_bot), \
         patch("src.knowledge_base.rag_engine.RAGEngine.search", return_value=mock_rag_results), \
         patch("src.knowledge_base.rag_engine.RAGEngine._call_llm", return_value=("LLM回答内容【来源：测试文档】", 100)), \
         patch("src.llm.client.check_daily_limit", return_value=mock_cost_status_ok), \
         patch("src.llm.client._call_llm_api", return_value={
             "content": mock_llm_response["content"],
             "model": mock_llm_response["model"],
             "input_tokens": mock_llm_response["input_tokens"],
             "output_tokens": mock_llm_response["output_tokens"],
         }), \
         patch("src.llm.client.db_session", mock_cm), \
         patch("src.utils.audit.db_session", audit_mock_cm), \
         patch("src.utils.killswitch.db_session", mock_cm), \
         patch("src.agents.selection_agent.nodes.db_session", mock_cm), \
         patch("src.agents.core_agent.daily_report.db_session", mock_cm), \
         patch("src.knowledge_base.rag_engine.db_session", mock_cm):
        yield {
            "bot": mock_feishu_bot,
            "rag_results": mock_rag_results,
            "llm_response": mock_llm_response,
            "db_session": mock_cm,
            "db_session_obj": mock_session,
            "audit_session": audit_mock_session,
        }
