"""每日数据汇报 Agent — 核心逻辑。

职责：
1. 聚合昨日销售数据（总销售额/订单数/退款数/SKU排行/环比趋势）
2. 汇总各 Agent 最近运行状态（成功/失败/未运行/上次时间/待审批数）
3. 获取市场动态（卖家精灵数据/竞品/异常告警）
4. 生成飞书卡片 JSON 并发送

模块顶部必须导入所有需要 patch 的对象（学自 T7/T10/T11/T14 踩坑经验）。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# ——————————————————————————————————————————————————————
# 可 patch 依赖（模块顶部导入，允许测试覆盖）
# ——————————————————————————————————————————————————————
try:
    from src.db.connection import db_session
    _DB_AVAILABLE = True
except ImportError:  # pragma: no cover
    db_session = None  # type: ignore[assignment]
    _DB_AVAILABLE = False

try:
    from src.db.models import AgentRun, DailyReport, ApprovalRequest
    _MODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    AgentRun = None  # type: ignore[assignment]
    DailyReport = None  # type: ignore[assignment]
    ApprovalRequest = None  # type: ignore[assignment]
    _MODELS_AVAILABLE = False

try:
    from src.amazon_api.mock import get_mock_orders, get_mock_inventory, get_mock_products
    _MOCK_API_AVAILABLE = True
except ImportError:  # pragma: no cover
    get_mock_orders = None  # type: ignore[assignment]
    get_mock_inventory = None  # type: ignore[assignment]
    get_mock_products = None  # type: ignore[assignment]
    _MOCK_API_AVAILABLE = False

try:
    from src.seller_sprite.client import get_client as get_seller_sprite_client
    _SELLER_SPRITE_AVAILABLE = True
except ImportError:  # pragma: no cover
    get_seller_sprite_client = None  # type: ignore[assignment]
    _SELLER_SPRITE_AVAILABLE = False

try:
    from src.feishu.bot_handler import get_bot
    _FEISHU_BOT_AVAILABLE = True
except ImportError:  # pragma: no cover
    get_bot = None  # type: ignore[assignment]
    _FEISHU_BOT_AVAILABLE = False

try:
    from src.config import settings
    _SETTINGS_AVAILABLE = True
except ImportError:  # pragma: no cover
    settings = None  # type: ignore[assignment]
    _SETTINGS_AVAILABLE = False

try:
    from src.agents.base_agent import BaseAgent
    _BASE_AGENT_AVAILABLE = True
except ImportError:  # pragma: no cover
    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, name: str):
            self.name = name
            self.dry_run = True

        def run(self, **kwargs):
            pass

        def log(self, msg: str):
            logging.getLogger(__name__).info("[%s] %s", self.name, msg)

        def warn(self, msg: str):
            logging.getLogger(__name__).warning("[%s] %s", self.name, msg)
    _BASE_AGENT_AVAILABLE = False

try:
    from src.llm.schema_validator import validate_llm_output
    from src.llm.schemas.daily_report import DailyReportSchema
    _SCHEMA_VALIDATOR_AVAILABLE = True
except ImportError:  # pragma: no cover
    validate_llm_output = None  # type: ignore[assignment]
    DailyReportSchema = None  # type: ignore[assignment]
    _SCHEMA_VALIDATOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# ——————————————————————————————————————————————————————
# Mock 数据常量（dry_run=True 时使用）
# ——————————————————————————————————————————————————————
_AGENT_TYPES = [
    "daily_report_agent",
    "selection_agent",
    "llm_cost_report",
    "scheduler:daily_report",
    "scheduler:selection_analysis",
]

_MOCK_AGENT_STATUSES = [
    {"agent_type": "selection_agent", "status": "success", "last_run": "2026-03-30 10:05:22", "run_count": 3},
    {"agent_type": "llm_cost_report", "status": "success", "last_run": "2026-03-30 23:00:11", "run_count": 1},
    {"agent_type": "daily_report_agent", "status": "not_run", "last_run": None, "run_count": 0},
]

_MOCK_MARKET_DATA = {
    "category": "pet supplies",
    "market_size_usd": 12_500_000_000.0,
    "growth_rate": 0.12,
    "top_keywords": ["pet bed", "cat water fountain", "dog leash"],
    "competitor_alert": "KONG Company 本周新品 B09XNEWPRD 排名上升至 BSR #523",
}


# ——————————————————————————————————————————————————————
# 辅助函数
# ——————————————————————————————————————————————————————

def _calc_change(current: float, previous: float) -> Dict[str, Any]:
    """计算环比变化，返回 pct 和方向。"""
    if previous == 0:
        return {"pct": 0.0, "direction": "flat", "emoji": "→", "color": "grey"}
    pct = round((current - previous) / previous * 100, 1)
    if pct > 0:
        return {"pct": pct, "direction": "up", "emoji": "↑", "color": "green"}
    elif pct < 0:
        return {"pct": pct, "direction": "down", "emoji": "↓", "color": "red"}
    else:
        return {"pct": 0.0, "direction": "flat", "emoji": "→", "color": "grey"}


def _format_change_text(change: Dict[str, Any]) -> str:
    """格式化环比文本，带 emoji。"""
    return f"{change['emoji']} {abs(change['pct'])}%"


def _get_yesterday() -> date:
    return date.today() - timedelta(days=1)


def _get_day_before_yesterday() -> date:
    return date.today() - timedelta(days=2)


def _get_last_week_same_day() -> date:
    return date.today() - timedelta(days=8)


# ——————————————————————————————————————————————————————
# 板块1：销售数据
# ——————————————————————————————————————————————————————

def _collect_sales_data(dry_run: bool) -> Dict[str, Any]:
    """收集昨日销售数据，返回结构化 dict。"""
    if dry_run or not _MOCK_API_AVAILABLE:
        # 使用 Mock 数据
        orders = get_mock_orders(days=30) if get_mock_orders else []
    else:
        # Phase 2: 真实 API 调用
        orders = get_mock_orders(days=30)  # pragma: no cover

    yesterday = str(_get_yesterday())
    day_before = str(_get_day_before_yesterday())
    last_week = str(_get_last_week_same_day())

    def _filter_orders(day_str: str) -> List[dict]:
        return [o for o in orders if o.get("order_date") == day_str]

    def _calc_revenue(day_orders: List[dict]) -> float:
        return round(sum(o.get("price", 0) * o.get("quantity", 1) for o in day_orders), 2)

    def _count_refunds(day_orders: List[dict]) -> int:
        # Mock 数据没有退款字段，模拟约 5% 退款
        return max(0, round(len(day_orders) * 0.05))

    yesterday_orders = _filter_orders(yesterday)
    day_before_orders = _filter_orders(day_before)
    last_week_orders = _filter_orders(last_week)

    # 如果 mock 数据没有昨日订单，用最近10天平均模拟
    if not yesterday_orders:
        yesterday_orders = orders[:10]
    if not day_before_orders:
        day_before_orders = orders[10:20]
    if not last_week_orders:
        last_week_orders = orders[5:12]

    revenue_today = _calc_revenue(yesterday_orders)
    revenue_prev = _calc_revenue(day_before_orders)
    revenue_lastweek = _calc_revenue(last_week_orders)
    orders_today = len(yesterday_orders)
    orders_prev = len(day_before_orders)

    # SKU 销量排行
    sku_sales: Dict[str, int] = {}
    for o in yesterday_orders:
        asin = o.get("asin", "UNKNOWN")
        sku_sales[asin] = sku_sales.get(asin, 0) + o.get("quantity", 1)
    sku_ranking = sorted(sku_sales.items(), key=lambda x: x[1], reverse=True)

    # 获取产品名称映射
    product_map: Dict[str, str] = {}
    if get_mock_products:
        for p in get_mock_products():
            product_map[p["asin"]] = p["title"]

    sku_ranking_detail = [
        {
            "rank": i + 1,
            "asin": asin,
            "name": product_map.get(asin, asin),
            "qty": qty,
        }
        for i, (asin, qty) in enumerate(sku_ranking[:5])
    ]

    return {
        "date": yesterday,
        "revenue": revenue_today,
        "orders": orders_today,
        "refunds": _count_refunds(yesterday_orders),
        "revenue_vs_prev_day": _calc_change(revenue_today, revenue_prev),
        "orders_vs_prev_day": _calc_change(orders_today, orders_prev),
        "revenue_vs_last_week": _calc_change(revenue_today, revenue_lastweek),
        "sku_ranking": sku_ranking_detail,
    }


# ——————————————————————————————————————————————————————
# 板块2：Agent 任务进度
# ——————————————————————————————————————————————————————

def _collect_agent_progress(dry_run: bool) -> Dict[str, Any]:
    """收集各 Agent 最近运行状态和待审批数量。"""
    if dry_run or not _DB_AVAILABLE or db_session is None:
        # 使用 Mock 数据
        pending_approvals = 2  # mock
        return {
            "agent_statuses": _MOCK_AGENT_STATUSES,
            "pending_approvals": pending_approvals,
        }

    # Phase 2: 真实 DB 查询
    agent_statuses = []
    try:
        with db_session() as session:
            for agent_type in _AGENT_TYPES:
                run = (
                    session.query(AgentRun)
                    .filter(AgentRun.agent_type == agent_type)
                    .order_by(AgentRun.started_at.desc())
                    .first()
                )
                if run:
                    last_run_str = run.finished_at.isoformat() if run.finished_at else None
                    agent_statuses.append({
                        "agent_type": agent_type,
                        "status": run.status,
                        "last_run": last_run_str,
                        "run_count": 1,
                    })
                else:
                    agent_statuses.append({
                        "agent_type": agent_type,
                        "status": "not_run",
                        "last_run": None,
                        "run_count": 0,
                    })

            # 待审批数
            pending_approvals = (
                session.query(ApprovalRequest)
                .filter(ApprovalRequest.status == "pending")
                .count()
            )
    except Exception as exc:
        logger.warning("查询 agent 进度失败，使用 mock 数据: %s", exc)
        agent_statuses = _MOCK_AGENT_STATUSES
        pending_approvals = 0

    return {
        "agent_statuses": agent_statuses,
        "pending_approvals": pending_approvals,
    }


# ——————————————————————————————————————————————————————
# 板块3：市场动态
# ——————————————————————————————————————————————————————

def _collect_market_data(dry_run: bool) -> Dict[str, Any]:
    """收集市场动态数据：类目趋势/竞品动态/异常告警。"""
    # 异常告警（库存/广告）
    alerts = []

    if get_mock_inventory:
        inventory = get_mock_inventory()
        for item in inventory:
            fulfillable = item.get("fulfillable", 0)
            sku = item.get("sku", "")
            if fulfillable < 20:
                alerts.append(f"🔴 库存告警：{sku} 可售库存仅 {fulfillable} 件")

    if dry_run or not _SELLER_SPRITE_AVAILABLE or get_seller_sprite_client is None:
        category_data = _MOCK_MARKET_DATA
    else:
        try:
            client = get_seller_sprite_client()
            raw = client.get_category_data("pet supplies")
            category_data = {
                "category": raw.get("category", "pet supplies"),
                "market_size_usd": raw.get("market_size_usd", 0),
                "growth_rate": raw.get("growth_rate", 0),
                "top_keywords": [],
                "competitor_alert": _MOCK_MARKET_DATA["competitor_alert"],
            }
        except Exception as exc:
            logger.warning("获取卖家精灵数据失败，使用 mock: %s", exc)
            category_data = _MOCK_MARKET_DATA

    return {
        "category": category_data.get("category"),
        "market_size_usd": category_data.get("market_size_usd"),
        "growth_rate": category_data.get("growth_rate"),
        "top_keywords": category_data.get("top_keywords", []),
        "competitor_alert": category_data.get("competitor_alert"),
        "inventory_alerts": alerts,
    }


# ——————————————————————————————————————————————————————
# 飞书卡片生成
# ——————————————————————————————————————————————————————

def generate_feishu_card(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """生成飞书卡片 JSON（官方 interactive 格式）。

    Args:
        report_data: generate_daily_report 返回的完整报告 dict

    Returns:
        合法的飞书卡片 JSON dict，可直接传给 send_card_message
    """
    report_date = report_data.get("report_date", str(date.today()))
    sales = report_data.get("sales", {})
    progress = report_data.get("agent_progress", {})
    market = report_data.get("market", {})

    # 板块1 内容
    revenue = sales.get("revenue", 0)
    orders = sales.get("orders", 0)
    refunds = sales.get("refunds", 0)
    rev_vs_prev = sales.get("revenue_vs_prev_day", {})
    rev_vs_week = sales.get("revenue_vs_last_week", {})
    ord_vs_prev = sales.get("orders_vs_prev_day", {})

    # 环比颜色 tag
    def _color_tag(change: Dict[str, Any], text: str) -> Dict[str, Any]:
        color = change.get("color", "grey")
        tag_name = f"text_tag_green" if color == "green" else ("text_tag_red" if color == "red" else "text_tag_blue")
        return {
            "tag": tag_name,
            "text": text,
        }

    rev_prev_tag = _color_tag(rev_vs_prev, _format_change_text(rev_vs_prev) if rev_vs_prev else "—")
    rev_week_tag = _color_tag(rev_vs_week, _format_change_text(rev_vs_week) if rev_vs_week else "—")
    ord_prev_tag = _color_tag(ord_vs_prev, _format_change_text(ord_vs_prev) if ord_vs_prev else "—")

    # SKU 排行
    sku_lines = []
    for item in sales.get("sku_ranking", [])[:3]:
        sku_lines.append(
            f"  {item['rank']}. {item['name']} — 销量 {item['qty']} 件"
        )
    sku_text = "\n".join(sku_lines) if sku_lines else "  暂无数据"

    # 板块2 内容
    agent_statuses = progress.get("agent_statuses", [])
    pending = progress.get("pending_approvals", 0)
    status_emoji = {"success": "✅", "failed": "❌", "running": "🔄", "not_run": "⚪"}

    agent_lines = []
    for a in agent_statuses:
        emoji = status_emoji.get(a.get("status", "not_run"), "⚪")
        last = a.get("last_run") or "从未运行"
        agent_lines.append(f"  {emoji} {a['agent_type']}  最后运行：{last}")
    agent_text = "\n".join(agent_lines) if agent_lines else "  暂无运行记录"

    # 板块3 内容
    market_size = market.get("market_size_usd", 0)
    growth_pct = round((market.get("growth_rate", 0) or 0) * 100, 1)
    competitor = market.get("competitor_alert", "无异常")
    inv_alerts = market.get("inventory_alerts", [])
    alerts_text = "\n".join(inv_alerts) if inv_alerts else "  库存正常，无告警"

    elements = [
        # 分割线
        {"tag": "hr"},
        # 标题：板块1
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**📊 销售数据汇总**",
            },
        },
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**昨日总销售额**\n${revenue:.2f}",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**订单数**\n{orders} 单 | 退款 {refunds} 单",
                    },
                },
            ],
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**环比昨天：** {_format_change_text(rev_vs_prev) if rev_vs_prev else '—'}  "
                    f"| **对比上周同期：** {_format_change_text(rev_vs_week) if rev_vs_week else '—'}  "
                    f"| **订单环比：** {_format_change_text(ord_vs_prev) if ord_vs_prev else '—'}"
                ),
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**SKU 销量排行（Top 3）**\n{sku_text}",
            },
        },
        # 分割线
        {"tag": "hr"},
        # 板块2
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**🤖 Agent 任务进度**",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{agent_text}\n\n⏳ **待审批任务：** {pending} 个",
            },
        },
        # 分割线
        {"tag": "hr"},
        # 板块3
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**📈 市场动态简报**",
            },
        },
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**类目规模**\n${market_size / 1e9:.1f}B",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**年增长率**\n{growth_pct}%",
                    },
                },
            ],
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**竞品动态：** {competitor}",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**库存/广告告警**\n{alerts_text}",
            },
        },
        # 分割线
        {"tag": "hr"},
        # 底部操作按钮
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📋 查看详情"},
                    "type": "default",
                    "url": "https://open.feishu.cn",
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔍 触发选品分析"},
                    "type": "primary",
                    "value": {"action": "trigger_selection_analysis"},
                },
            ],
        },
    ]

    card = {
        "config": {
            "wide_screen_mode": True,
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"📅 PUDIWIND 运营日报 — {report_date}",
            },
            "template": "blue",
        },
        "elements": elements,
    }
    return card


# ——————————————————————————————————————————————————————
# 核心函数：生成日报
# ——————————————————————————————————————————————————————

def generate_daily_report(dry_run: bool = True) -> Dict[str, Any]:
    """生成每日运营日报数据（3个板块）。

    Args:
        dry_run: True 时使用 Mock 数据，不调用真实 API

    Returns:
        包含 3 个板块的日报 dict:
        {
            "report_date": "2026-03-30",
            "agent_run_id": "<uuid>",
            "sales": {...},
            "agent_progress": {...},
            "market": {...},
            "status": "completed",
            "generated_at": "<iso datetime>",
        }
    """
    report_date = str(_get_yesterday())
    agent_run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    logger.info("generate_daily_report | dry_run=%s date=%s", dry_run, report_date)

    # 收集 3 个板块数据
    try:
        sales = _collect_sales_data(dry_run=dry_run)
    except Exception as exc:
        logger.error("收集销售数据失败: %s", exc)
        sales = {"error": str(exc)}

    try:
        agent_progress = _collect_agent_progress(dry_run=dry_run)
    except Exception as exc:
        logger.error("收集 agent 进度失败: %s", exc)
        agent_progress = {"error": str(exc)}

    try:
        market = _collect_market_data(dry_run=dry_run)
    except Exception as exc:
        logger.error("收集市场数据失败: %s", exc)
        market = {"error": str(exc)}

    report = {
        "report_date": report_date,
        "agent_run_id": agent_run_id,
        "sales": sales,
        "agent_progress": agent_progress,
        "market": market,
        "status": "completed",
        "generated_at": now.isoformat(),
        "dry_run": dry_run,
    }

    # Schema 校验（非阻塞：失败时降级为原始 report dict）
    if _SCHEMA_VALIDATOR_AVAILABLE and validate_llm_output is not None and DailyReportSchema is not None:
        validation_result = validate_llm_output(
            raw_output=report,
            schema_class=DailyReportSchema,
            context="daily_report_agent.generate_daily_report",
        )
        if validation_result.success:
            logger.info("generate_daily_report | Schema校验通过 date=%s", report_date)
        else:
            logger.warning(
                "generate_daily_report | Schema校验失败（已降级）errors=%s",
                validation_result.errors,
            )
    else:
        logger.debug("generate_daily_report | Schema校验器不可用，跳过校验")

    # 写 audit 日志（函数内导入避免循环依赖）
    try:
        from src.utils.audit import log_action
        log_action(
            action="daily_report_agent.run",
            actor="daily_report_agent",
            pre_state={"dry_run": dry_run, "report_date": report_date},
            post_state={"agent_run_id": agent_run_id, "status": "completed"},
        )
    except Exception as exc:
        logger.warning("写 audit 日志失败（非致命）: %s", exc)

    return report


def _save_to_db(report: Dict[str, Any]) -> None:
    """将日报结果写入 agent_runs 和 daily_reports 表（非 dry_run 时调用）。"""
    if not _DB_AVAILABLE or db_session is None:
        logger.warning("DB 不可用，跳过写入")
        return

    try:
        now = datetime.now(timezone.utc)
        report_date_obj = date.fromisoformat(report.get("report_date", str(date.today())))

        with db_session() as session:
            # 写 agent_runs
            run = AgentRun(
                agent_type="daily_report_agent",
                status=report.get("status", "completed"),
                input_summary=f"daily_report date={report.get('report_date')}",
                output_summary=json.dumps(
                    {"report_date": report.get("report_date"), "status": report.get("status")},
                    ensure_ascii=False,
                ),
                finished_at=now,
            )
            session.add(run)
            session.flush()

            # 写 daily_reports（get-then-set upsert 模式，兼容 SQLite）
            existing = (
                session.query(DailyReport)
                .filter(DailyReport.report_date == report_date_obj)
                .first()
            )
            if existing:
                existing.content_json = report
                existing.sent_at = None  # 重新生成，sent_at 置空
            else:
                daily = DailyReport(
                    report_date=report_date_obj,
                    content_json=report,
                    sent_at=None,
                )
                session.add(daily)

            session.commit()
            logger.info("日报已写入数据库 | report_date=%s", report.get("report_date"))
    except Exception as exc:
        logger.error("写入 DB 失败（非致命）: %s", exc)


def _mark_report_sent(report_date_str: str) -> None:
    """标记日报已发送（更新 sent_at 字段）。"""
    if not _DB_AVAILABLE or db_session is None:
        return
    try:
        now = datetime.now(timezone.utc)
        report_date_obj = date.fromisoformat(report_date_str)
        with db_session() as session:
            rec = (
                session.query(DailyReport)
                .filter(DailyReport.report_date == report_date_obj)
                .first()
            )
            if rec:
                rec.sent_at = now
                session.commit()
    except Exception as exc:
        logger.warning("标记 sent_at 失败: %s", exc)


# ——————————————————————————————————————————————————————
# DailyReportAgent 类
# ——————————————————————————————————————————————————————

class DailyReportAgent(BaseAgent):
    """每日数据汇报 Agent。

    工作流：
    1. 调用 generate_daily_report() 收集 3 个板块数据
    2. 调用 generate_feishu_card() 生成卡片 JSON
    3. 调用 send_card_message() 发送到飞书群
    4. 写 DB（dry_run=False 时）
    5. 写 audit log
    """

    AGENT_TYPE = "daily_report_agent"

    def __init__(self, chat_id: Optional[str] = None, dry_run: Optional[bool] = None):
        super().__init__(name=self.AGENT_TYPE)
        # chat_id 优先参数，其次 settings.FEISHU_CHAT_ID
        if chat_id is not None:
            self.chat_id = chat_id
        elif _SETTINGS_AVAILABLE and settings is not None:
            self.chat_id = getattr(settings, "FEISHU_CHAT_ID", "")
        else:
            self.chat_id = ""

        if dry_run is not None:
            self.dry_run = dry_run

    def run(self, dry_run: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
        """执行日报流程。

        Args:
            dry_run: 覆盖实例级别的 dry_run 标志

        Returns:
            {"status": "ok"/"error", "report": {...}, "card_sent": bool}
        """
        effective_dry_run = dry_run if dry_run is not None else self.dry_run
        self.log(f"run started | dry_run={effective_dry_run}")

        # Step 1: 生成报告数据
        report = generate_daily_report(dry_run=effective_dry_run)

        # Step 2: 生成飞书卡片
        card = generate_feishu_card(report)

        # Step 3: 发送卡片（非 dry_run 时）
        card_sent = False
        if not effective_dry_run and self.chat_id:
            try:
                if _FEISHU_BOT_AVAILABLE and get_bot is not None:
                    bot = get_bot()
                    bot.send_card_message(self.chat_id, card)
                    card_sent = True
                    _mark_report_sent(report["report_date"])
                    self.log("飞书卡片发送成功")
            except Exception as exc:
                self.warn(f"飞书卡片发送失败（非致命）: {exc}")
        elif effective_dry_run:
            self.log("dry_run 模式，跳过飞书发送")

        # Step 4: 写 DB（非 dry_run 时）
        if not effective_dry_run:
            _save_to_db(report)

        result = {
            "status": "ok",
            "report": report,
            "card": card,
            "card_sent": card_sent,
            "dry_run": effective_dry_run,
        }
        self.log(f"run finished | status=ok card_sent={card_sent}")
        return result
