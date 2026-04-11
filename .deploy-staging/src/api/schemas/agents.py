"""Agent API Pydantic schemas — T4/T5 REST API models."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AgentType(str, Enum):
    """Supported agent types."""

    selection = "selection"
    listing = "listing"
    competitor = "competitor"
    persona = "persona"
    ad_monitor = "ad_monitor"
    brand_planning = "brand_planning"
    whitepaper = "whitepaper"
    image_generation = "image_generation"
    product_listing = "product_listing"
    inventory = "inventory"
    core_management = "core_management"


AGENT_PARAM_SCHEMAS: dict[str, dict] = {
    "selection": {
        "name": "选品 Agent",
        "description": "分析市场机会，推荐潜力产品候选",
        "params": {
            "category": {"type": "string", "required": False, "default": "pet_supplies", "description": "产品类目"},
            "subcategory": {"type": "string", "required": False, "description": "子类目"},
        },
    },
    "listing": {
        "name": "Listing 优化 Agent",
        "description": "生成和优化亚马逊产品详情页文案",
        "params": {
            "asin": {"type": "string", "required": False, "description": "目标 ASIN"},
            "product_name": {"type": "string", "required": False, "description": "产品名称"},
            "category": {"type": "string", "required": False, "description": "产品类目"},
        },
    },
    "competitor": {
        "name": "竞品调研 Agent",
        "description": "深度分析竞争对手产品数据和市场定位",
        "params": {
            "target_asin": {"type": "string", "required": False, "description": "目标竞品 ASIN"},
            "competitor_asins": {"type": "array", "required": False, "description": "竞品 ASIN 列表"},
        },
    },
    "persona": {
        "name": "用户画像 Agent",
        "description": "基于评论数据构建目标用户画像",
        "params": {
            "category": {"type": "string", "required": False, "description": "产品类目"},
            "asin": {"type": "string", "required": False, "description": "产品 ASIN"},
        },
    },
    "ad_monitor": {
        "name": "广告监控 Agent",
        "description": "监控广告活动表现，发送异常预警",
        "params": {
            "campaigns": {"type": "array", "required": False, "description": "广告活动 ID 列表"},
            "thresholds": {"type": "object", "required": False, "description": "预警阈值配置"},
        },
    },
    "brand_planning": {
        "name": "品牌路径规划 Agent",
        "description": "制定品牌发展战略和路径规划",
        "params": {
            "brand_name": {"type": "string", "required": False, "description": "品牌名称"},
            "target_market": {"type": "string", "required": False, "description": "目标市场"},
        },
    },
    "whitepaper": {
        "name": "产品白皮书 Agent",
        "description": "生成专业的产品白皮书文档",
        "params": {
            "product_name": {"type": "string", "required": True, "description": "产品名称"},
            "asin": {"type": "string", "required": False, "description": "关联 ASIN"},
        },
    },
    "image_generation": {
        "name": "图片生成 Agent",
        "description": "使用 DALL-E 3 生成产品营销图片",
        "params": {
            "prompt": {"type": "string", "required": True, "description": "图片生成提示词"},
            "product_name": {"type": "string", "required": False, "description": "产品名称"},
            "style": {"type": "string", "required": False, "default": "professional", "description": "图片风格"},
        },
    },
    "product_listing": {
        "name": "产品上架 Agent",
        "description": "通过 SP-API 将产品信息上架到亚马逊",
        "params": {
            "product_data": {"type": "object", "required": True, "description": "产品详情数据"},
            "marketplace": {"type": "string", "required": False, "default": "ATVPDKIKX0DER", "description": "目标市场 ID"},
        },
    },
    "inventory": {
        "name": "库存监控 Agent",
        "description": "监控库存水位，发送补货预警",
        "params": {
            "sku_list": {"type": "array", "required": False, "description": "需要监控的 SKU 列表"},
            "threshold_days": {"type": "integer", "required": False, "default": 30, "description": "库存预警天数"},
        },
    },
    "core_management": {
        "name": "核心管理 Agent",
        "description": "系统核心管理功能，协调其他 Agent 运作",
        "params": {
            "action": {"type": "string", "required": False, "description": "管理操作类型"},
            "target_agents": {"type": "array", "required": False, "description": "目标 Agent 类型列表"},
        },
    },
}


class AgentRunRequest(BaseModel):
    """Request body for triggering an agent run."""

    dry_run: bool = True
    params: Optional[dict] = None  # agent-specific params e.g. category, asin


class AgentRunResponse(BaseModel):
    """Immediate response returned when an agent run is accepted (HTTP 202)."""

    run_id: str
    agent_type: str
    status: str = "running"
    message: str


class AgentRunStatus(BaseModel):
    """Detailed status of a single agent run."""

    run_id: str
    agent_type: str
    status: str  # running / success / failed
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    cost_usd: Optional[float] = None
    started_at: str  # ISO-8601
    finished_at: Optional[str] = None
    result: Optional[dict] = None


class AgentRunList(BaseModel):
    """Paginated list of agent runs."""

    runs: list[AgentRunStatus]
    total: int
