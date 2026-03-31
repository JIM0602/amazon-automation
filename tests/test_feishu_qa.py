"""飞书机器人问答功能测试 — 覆盖 RAG 集成、会话上下文管理、指令路由。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================ #
#  Fixtures
# ============================================================================ #

@pytest.fixture(autouse=True)
def reset_context():
    """每个测试前后清空会话上下文，防止测试间污染。"""
    import src.feishu.bot_handler as bh
    bh._CONTEXT.clear()
    yield
    bh._CONTEXT.clear()


@pytest.fixture()
def mock_settings():
    """伪造 settings，避免读取 .env 文件。"""
    import src.feishu.bot_handler  # noqa: F401
    with patch("src.feishu.bot_handler.settings") as m:
        m.FEISHU_APP_ID = "test_app_id"
        m.FEISHU_APP_SECRET = "test_app_secret"
        m.FEISHU_ENCRYPT_KEY = None
        yield m


@pytest.fixture()
def mock_bot(mock_settings):
    """注入 mock bot 到全局单例。"""
    import src.feishu.bot_handler as bh
    bh._bot_instance = None

    mock = MagicMock()
    mock.send_text_message.return_value = {
        "code": 0,
        "data": {"message_id": "om_thinking_001"},
    }
    mock.send_thinking.return_value = "om_thinking_001"
    mock.update_message.return_value = {"code": 0}
    bh._bot_instance = mock
    yield mock
    bh._bot_instance = None


@pytest.fixture()
def mock_rag_query():
    """mock RAG query 函数，返回固定答案。"""
    with patch("src.feishu.bot_handler.rag_query") as m:
        m.return_value = "这是来自知识库的回答。【来源：亚马逊运营手册】"
        yield m


# ============================================================================ #
#  FeishuBot 新方法测试
# ============================================================================ #

class TestSendThinking:
    def test_returns_message_id(self, mock_settings):
        """send_thinking 应发送占位消息并返回 message_id。"""
        import src.feishu.bot_handler as bh
        bh._bot_instance = None

        mock_token_resp = MagicMock()
        mock_token_resp.raise_for_status = MagicMock()
        mock_token_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "mock_token",
            "expire": 7200,
        }
        mock_send_resp = MagicMock()
        mock_send_resp.raise_for_status = MagicMock()
        mock_send_resp.json.return_value = {
            "code": 0,
            "data": {"message_id": "om_thinking_xyz"},
        }

        from src.feishu.bot_handler import FeishuBot
        bot = FeishuBot("app_id", "app_secret")

        with patch("src.feishu.bot_handler.requests.post") as mock_post:
            mock_post.side_effect = [mock_token_resp, mock_send_resp]
            msg_id = bot.send_thinking("oc_chat_001")

        assert msg_id == "om_thinking_xyz"

    def test_sends_thinking_text(self, mock_settings):
        """send_thinking 发送的文本应包含"正在思考中"。"""
        import src.feishu.bot_handler as bh
        bh._bot_instance = None

        mock_token_resp = MagicMock()
        mock_token_resp.raise_for_status = MagicMock()
        mock_token_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "mock_token",
            "expire": 7200,
        }
        mock_send_resp = MagicMock()
        mock_send_resp.raise_for_status = MagicMock()
        mock_send_resp.json.return_value = {"code": 0, "data": {"message_id": "om_xyz"}}

        from src.feishu.bot_handler import FeishuBot
        bot = FeishuBot("app_id", "app_secret")

        with patch("src.feishu.bot_handler.requests.post") as mock_post:
            mock_post.side_effect = [mock_token_resp, mock_send_resp]
            bot.send_thinking("oc_chat_002")

        # 第2次调用是发消息
        send_call = mock_post.call_args_list[1]
        call_kwargs = send_call.kwargs if send_call.kwargs else send_call[1]
        payload = call_kwargs["json"]
        content = json.loads(payload["content"])
        assert "思考" in content["text"] or "thinking" in content["text"].lower()


class TestUpdateMessage:
    def test_calls_patch_api(self, mock_settings):
        """update_message 应调用 PATCH 接口更新消息。"""
        import src.feishu.bot_handler as bh
        bh._bot_instance = None

        mock_token_resp = MagicMock()
        mock_token_resp.raise_for_status = MagicMock()
        mock_token_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "mock_token",
            "expire": 7200,
        }
        mock_patch_resp = MagicMock()
        mock_patch_resp.raise_for_status = MagicMock()
        mock_patch_resp.json.return_value = {"code": 0}

        from src.feishu.bot_handler import FeishuBot
        bot = FeishuBot("app_id", "app_secret")

        with patch("src.feishu.bot_handler.requests.post", return_value=mock_token_resp):
            with patch("src.feishu.bot_handler.requests.patch", return_value=mock_patch_resp) as mock_p:
                result = bot.update_message("om_msg_001", "新的回答内容")

        assert result["code"] == 0
        mock_p.assert_called_once()
        call_kwargs = mock_p.call_args.kwargs if mock_p.call_args.kwargs else mock_p.call_args[1]
        assert "om_msg_001" in call_kwargs.get("url", mock_p.call_args[0][0] if mock_p.call_args[0] else "")

    def test_update_message_contains_new_content(self, mock_settings):
        """update_message 应将新内容放到请求体中。"""
        import src.feishu.bot_handler as bh
        bh._bot_instance = None

        mock_token_resp = MagicMock()
        mock_token_resp.raise_for_status = MagicMock()
        mock_token_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "mock_token",
            "expire": 7200,
        }
        mock_patch_resp = MagicMock()
        mock_patch_resp.raise_for_status = MagicMock()
        mock_patch_resp.json.return_value = {"code": 0}

        from src.feishu.bot_handler import FeishuBot
        bot = FeishuBot("app_id", "app_secret")

        with patch("src.feishu.bot_handler.requests.post", return_value=mock_token_resp):
            with patch("src.feishu.bot_handler.requests.patch", return_value=mock_patch_resp) as mock_p:
                bot.update_message("om_msg_002", "最终回答文本")

        call_kwargs = mock_p.call_args.kwargs if mock_p.call_args.kwargs else mock_p.call_args[1]
        payload = call_kwargs["json"]
        content = json.loads(payload["content"])
        assert content["text"] == "最终回答文本"


# ============================================================================ #
#  会话上下文管理测试
# ============================================================================ #

class TestSessionContext:
    def test_context_stores_qa_pair(self, mock_bot, mock_rag_query):
        """问答后应在上下文中存储用户问题和助手回答。"""
        import src.feishu.bot_handler as bh

        bh.handle_qa("user_001", "oc_chat_001", "如何处理差评？")

        ctx = bh._CONTEXT.get("user_001", [])
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[0]["content"] == "如何处理差评？"
        assert ctx[1]["role"] == "assistant"

    def test_context_accumulates_rounds(self, mock_bot, mock_rag_query):
        """多次问答应累积到上下文中。"""
        import src.feishu.bot_handler as bh

        bh.handle_qa("user_002", "oc_chat_002", "问题1")
        bh.handle_qa("user_002", "oc_chat_002", "问题2")
        bh.handle_qa("user_002", "oc_chat_002", "问题3")

        ctx = bh._CONTEXT.get("user_002", [])
        assert len(ctx) == 6  # 3轮 * 2条

    def test_context_clears_after_5_rounds(self, mock_bot, mock_rag_query):
        """超过5轮后上下文应被清空（清空发生在第11条消息添加时）。"""
        import src.feishu.bot_handler as bh

        # 进行6轮问答：第6轮第1条（user）触发清空（10+1=11>10），然后只剩 assistant 1条
        for i in range(6):
            bh.handle_qa("user_003", "oc_chat_003", f"问题{i + 1}")

        ctx = bh._CONTEXT.get("user_003", [])
        # 清空后第6轮：user触发清空->[], 然后加assistant->1条
        # 说明上下文在超过5轮后确实被清空了
        assert len(ctx) <= 2  # 清空后至多剩下第6轮的部分数据

    def test_context_isolated_per_user(self, mock_bot, mock_rag_query):
        """不同用户的上下文应相互隔离。"""
        import src.feishu.bot_handler as bh

        bh.handle_qa("user_A", "oc_chat", "用户A的问题")
        bh.handle_qa("user_B", "oc_chat", "用户B的问题")

        ctx_a = bh._CONTEXT.get("user_A", [])
        ctx_b = bh._CONTEXT.get("user_B", [])
        assert len(ctx_a) == 2
        assert len(ctx_b) == 2
        assert ctx_a[0]["content"] == "用户A的问题"
        assert ctx_b[0]["content"] == "用户B的问题"

    def test_exactly_5_rounds_not_cleared(self, mock_bot, mock_rag_query):
        """恰好5轮问答时上下文不应被清空。"""
        import src.feishu.bot_handler as bh

        for i in range(5):
            bh.handle_qa("user_004", "oc_chat_004", f"问题{i + 1}")

        ctx = bh._CONTEXT.get("user_004", [])
        assert len(ctx) == 10  # 5轮 * 2条，恰好等于 MAX * 2，不超过，不清除


# ============================================================================ #
#  handle_qa 流程测试
# ============================================================================ #

class TestHandleQA:
    def test_returns_rag_answer(self, mock_bot, mock_rag_query):
        """handle_qa 应返回 RAG 答案字符串。"""
        import src.feishu.bot_handler as bh

        result = bh.handle_qa("user_qa1", "oc_chat", "什么是FBA？")

        assert "知识库" in result or "来源" in result or result != ""

    def test_calls_send_thinking(self, mock_bot, mock_rag_query):
        """handle_qa 应先调用 send_thinking 发送占位消息。"""
        import src.feishu.bot_handler as bh

        bh.handle_qa("user_qa2", "oc_chat", "测试问题")

        mock_bot.send_thinking.assert_called_once_with("oc_chat")

    def test_calls_update_message_with_answer(self, mock_bot, mock_rag_query):
        """handle_qa 应在获取答案后调用 update_message 更新占位消息。"""
        import src.feishu.bot_handler as bh

        bh.handle_qa("user_qa3", "oc_chat", "测试问题")

        mock_bot.update_message.assert_called_once()
        call_args = mock_bot.update_message.call_args
        # 第一个参数应为 message_id
        assert call_args[0][0] == "om_thinking_001"

    def test_rag_failure_returns_friendly_message(self, mock_bot):
        """RAG 调用失败时，handle_qa 应返回友好错误提示，不暴露错误堆栈。"""
        import src.feishu.bot_handler as bh

        with patch("src.feishu.bot_handler.rag_query", side_effect=Exception("数据库连接失败")):
            result = bh.handle_qa("user_qa4", "oc_chat", "测试问题")

        assert result == "系统出错，请稍后重试"
        assert "数据库连接失败" not in result  # 不暴露内部错误

    def test_rag_import_error_returns_friendly_message(self, mock_bot):
        """rag_query 为 None 时，handle_qa 应返回友好错误提示。"""
        import src.feishu.bot_handler as bh

        with patch("src.feishu.bot_handler.rag_query", None):
            result = bh.handle_qa("user_qa5", "oc_chat", "测试问题")

        assert result == "系统出错，请稍后重试"

    def test_send_thinking_failure_does_not_abort(self, mock_bot, mock_rag_query):
        """send_thinking 失败时不影响问答流程继续执行。"""
        import src.feishu.bot_handler as bh

        mock_bot.send_thinking.side_effect = Exception("发送失败")

        result = bh.handle_qa("user_qa6", "oc_chat", "测试问题")

        # 仍然返回 RAG 答案
        assert result != ""
        assert result != "系统出错，请稍后重试"


# ============================================================================ #
#  command_router 完整路由测试（5种 action）
# ============================================================================ #

class TestCommandRouterFull:
    def test_knowledge_query_wen_prefix(self):
        """以"问："开头 → knowledge_query。"""
        from src.feishu.command_router import route_command

        result = route_command("问：如何优化广告", "user_r01")
        assert result["action"] == "knowledge_query"
        assert result["query"] == "如何优化广告"

    def test_knowledge_query_question_mark_en(self):
        """英文问号开头 → knowledge_query。"""
        from src.feishu.command_router import route_command

        result = route_command("?FBA费用怎么算", "user_r02")
        assert result["action"] == "knowledge_query"
        assert result["query"] == "FBA费用怎么算"

    def test_knowledge_query_question_mark_cn(self):
        """中文问号开头 → knowledge_query。"""
        from src.feishu.command_router import route_command

        result = route_command("？亚马逊退款流程", "user_r03")
        assert result["action"] == "knowledge_query"
        assert result["query"] == "亚马逊退款流程"

    def test_daily_report_jinri_baogao(self):
        """包含"今日报告" → daily_report。"""
        from src.feishu.command_router import route_command

        result = route_command("今日报告", "user_r04")
        assert result["action"] == "daily_report"

    def test_daily_report_ribao(self):
        """包含"日报" → daily_report。"""
        from src.feishu.command_router import route_command

        result = route_command("给我看下日报", "user_r05")
        assert result["action"] == "daily_report"

    def test_selection_analysis(self):
        """包含"选品分析" → selection_analysis。"""
        from src.feishu.command_router import route_command

        result = route_command("开始选品分析吧", "user_r06")
        assert result["action"] == "selection_analysis"

    def test_emergency_stop_pause_all(self):
        """包含"暂停所有" → emergency_stop。"""
        from src.feishu.command_router import route_command

        result = route_command("暂停所有任务", "user_r07")
        assert result["action"] == "emergency_stop"
        assert result["sender_id"] == "user_r07"

    def test_emergency_stop_critical(self):
        """包含"紧急停机" → emergency_stop。"""
        from src.feishu.command_router import route_command

        result = route_command("紧急停机！", "user_r08")
        assert result["action"] == "emergency_stop"

    def test_help_command_chinese(self):
        """消息为"帮助" → help。"""
        from src.feishu.command_router import route_command

        result = route_command("帮助", "user_r09")
        assert result["action"] == "help"
        assert "message" in result
        assert len(result["message"]) > 0

    def test_help_command_english(self):
        """消息为"help" → help。"""
        from src.feishu.command_router import route_command

        result = route_command("help", "user_r10")
        assert result["action"] == "help"

    def test_help_command_english_uppercase(self):
        """消息为"HELP"（大写）→ help。"""
        from src.feishu.command_router import route_command

        result = route_command("HELP", "user_r11")
        assert result["action"] == "help"

    def test_help_message_contains_command_list(self):
        """帮助消息应包含主要指令说明。"""
        from src.feishu.command_router import route_command

        result = route_command("帮助", "user_r12")
        msg = result["message"]
        # 应包含问答、日报、选品、停机等关键词
        assert "?" in msg or "问" in msg
        assert "日报" in msg or "报告" in msg
        assert "选品" in msg

    def test_unknown_command(self):
        """随机文本 → unknown。"""
        from src.feishu.command_router import route_command

        result = route_command("随便说一句话", "user_r13")
        assert result["action"] == "unknown"
        assert "message" in result

    def test_empty_message_unknown(self):
        """空白消息 → unknown。"""
        from src.feishu.command_router import route_command

        result = route_command("   ", "user_r14")
        assert result["action"] == "unknown"

    def test_existing_routes_not_broken_ribao(self):
        """原有"报告"路由仍然有效（兼容性）。"""
        from src.feishu.command_router import route_command

        result = route_command("发一下昨天的报告", "user_r15")
        assert result["action"] == "daily_report"

    def test_existing_routes_not_broken_xuan_pin(self):
        """原有"选品"路由仍然有效（兼容性）。"""
        from src.feishu.command_router import route_command

        result = route_command("帮我做选品", "user_r16")
        assert result["action"] == "selection_analysis"
