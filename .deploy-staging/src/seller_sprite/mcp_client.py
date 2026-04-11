"""卖家精灵 MCP (Streamable HTTP) 轻量客户端.

使用 JSON-RPC 2.0 over HTTP + SSE 与 Seller Sprite MCP 服务通信。
零额外依赖 — 仅 httpx（已在项目中）。

协议流程:
    1. POST initialize → 获取 server capabilities + mcp-session-id
    2. POST notifications/initialized (通知, 无响应)
    3. POST tools/list → 枚举可用工具
    4. POST tools/call → 调用具体工具获取数据

参考文档: https://open.sellersprite.com/mcp/16 (接入方式)
"""

from __future__ import annotations

import json
import threading
from typing import Any, Optional

import httpx

try:
    from loguru import logger
except ImportError:
    import logging as _logging

    class logger:  # type: ignore[no-redef]
        @staticmethod
        def info(msg, *a, **kw):
            _logging.info(msg.format(*a) if a else msg)

        @staticmethod
        def warning(msg, *a, **kw):
            _logging.warning(msg.format(*a) if a else msg)

        @staticmethod
        def error(msg, *a, **kw):
            _logging.error(msg.format(*a) if a else msg)

        @staticmethod
        def debug(msg, *a, **kw):
            _logging.debug(msg.format(*a) if a else msg)


class MCPError(Exception):
    """MCP 协议错误。"""


class MCPToolClient:
    """Seller Sprite MCP Streamable HTTP 客户端。

    线程安全: 内部使用 Lock 保护 session 状态。
    自动重连: 调用工具时如果 session 失效会自动重新 initialize。
    """

    def __init__(
        self,
        endpoint: str = "https://mcp.sellersprite.com/mcp",
        secret_key: str = "",
        timeout: float = 120.0,
    ) -> None:
        self.endpoint = endpoint
        self.secret_key = secret_key
        self.timeout = timeout

        self._session_id: Optional[str] = None
        self._initialized: bool = False
        self._request_counter: int = 0
        self._lock = threading.Lock()
        self._tools_cache: Optional[list[dict]] = None

    # ------------------------------------------------------------------
    # 内部: JSON-RPC transport
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._request_counter += 1
        return self._request_counter

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "secret-key": self.secret_key,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _send_jsonrpc(
        self,
        method: str,
        params: dict[str, Any],
        *,
        expect_response: bool = True,
    ) -> Optional[dict[str, Any]]:
        """发送 JSON-RPC 2.0 请求并返回 result。

        如果 expect_response=False（通知），不等待响应。
        """
        request_id: Optional[int] = self._next_id() if expect_response else None

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        if request_id is not None:
            payload["id"] = request_id

        headers = self._build_headers()

        logger.debug("MCP request | method={} id={}", method, request_id)

        with httpx.Client(timeout=self.timeout) as client:
            # 使用 streaming 读取 — 应对 SSE 响应
            with client.stream("POST", self.endpoint, headers=headers, json=payload) as response:
                # 捕获 session id
                session_header = response.headers.get("mcp-session-id")
                if session_header:
                    self._session_id = session_header

                if not expect_response:
                    # 通知: 读取并丢弃响应体
                    response.read()
                    return None

                content_type = response.headers.get("content-type", "")

                if "text/event-stream" in content_type:
                    return self._parse_sse(response, request_id)
                else:
                    body = response.read()
                    return self._parse_json(body, request_id)

    def _parse_json(self, body: bytes, request_id: Optional[int]) -> dict[str, Any]:
        """解析普通 JSON 响应。"""
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise MCPError(f"Invalid JSON from MCP server: {exc}\nBody: {body[:500]}") from exc

        if isinstance(data, dict):
            if "error" in data:
                raise MCPError(f"MCP JSON-RPC error: {data['error']}")
            return data.get("result", {})

        raise MCPError(f"Unexpected MCP response type: {type(data)}")

    def _parse_sse(self, response: httpx.Response, request_id: Optional[int]) -> dict[str, Any]:
        """从 SSE 流中提取 JSON-RPC 响应。"""
        result: Optional[dict[str, Any]] = None

        for line in response.iter_lines():
            stripped = line.strip()
            if not stripped or stripped.startswith(":"):
                # 空行或注释行
                continue
            if stripped.startswith("data:"):
                data_str = stripped[5:].strip()
                if not data_str:
                    continue
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    logger.debug("MCP SSE non-JSON data line: {}", data_str[:200])
                    continue

                if not isinstance(data, dict):
                    continue

                # 检查是否是我们期望的响应 (匹配 request id)
                if request_id is not None and data.get("id") == request_id:
                    if "error" in data:
                        raise MCPError(f"MCP JSON-RPC error: {data['error']}")
                    result = data.get("result", {})
                    break  # 找到目标响应，退出

        if result is None:
            raise MCPError("MCP: no matching response received from SSE stream")

        return result

    # ------------------------------------------------------------------
    # 公开: 协议操作
    # ------------------------------------------------------------------

    def initialize(self) -> dict[str, Any]:
        """执行 MCP initialize 握手。"""
        with self._lock:
            if self._initialized:
                return {}

            logger.info("MCP initialize | endpoint={}", self.endpoint)

            result = self._send_jsonrpc("initialize", {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "pudiwind-ai-backend",
                    "version": "1.0.0",
                },
            })

            # 发送 initialized 通知 (MCP 规范要求)
            self._send_jsonrpc(
                "notifications/initialized",
                {},
                expect_response=False,
            )

            self._initialized = True
            logger.info("MCP initialized | session_id={}", self._session_id)
            return result or {}

    def _ensure_initialized(self) -> None:
        """确保已初始化，否则自动初始化。"""
        if not self._initialized:
            self.initialize()

    def list_tools(self) -> list[dict[str, Any]]:
        """枚举 MCP 服务器上所有可用工具。"""
        self._ensure_initialized()

        result = self._send_jsonrpc("tools/list", {})
        tools = (result or {}).get("tools", [])
        self._tools_cache = tools

        logger.info("MCP tools/list | count={}", len(tools))
        for t in tools:
            logger.debug("  tool: {} — {}", t.get("name", "?"), (t.get("description") or "")[:80])

        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """调用 MCP 工具并返回结果。

        Returns:
            工具返回的数据。如果内容是 JSON 文本会自动解析。
        """
        self._ensure_initialized()

        logger.info("MCP tools/call | name={} args={}", name, list(arguments.keys()))

        result = self._send_jsonrpc("tools/call", {
            "name": name,
            "arguments": arguments,
        })

        # MCP 工具调用返回 content 数组
        content_list = (result or {}).get("content", [])

        # 提取文本内容, 尝试 JSON 解析
        texts: list[Any] = []
        for item in content_list:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = item.get("text", "")
                try:
                    texts.append(json.loads(text))
                except (json.JSONDecodeError, TypeError):
                    texts.append(text)
            elif item.get("type") == "resource":
                texts.append(item)

        if len(texts) == 1:
            return texts[0]
        if len(texts) > 1:
            return texts
        # 没有 text 内容，返回原始 result
        return result

    def reset(self) -> None:
        """重置 session 状态，下次调用时重新 initialize。"""
        with self._lock:
            self._session_id = None
            self._initialized = False
            self._tools_cache = None
            self._request_counter = 0
            logger.info("MCP session reset")

    def call_tool_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        """带自动重连的 call_tool — session 失效时自动 reset + retry。"""
        try:
            return self.call_tool(name, arguments)
        except (MCPError, httpx.HTTPError) as exc:
            logger.warning("MCP call_tool failed, resetting session and retrying | error={}", exc)
            self.reset()
            return self.call_tool(name, arguments)
