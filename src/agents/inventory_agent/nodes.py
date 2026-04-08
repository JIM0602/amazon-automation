"""库存监控 Agent 节点函数。"""
from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import update

logger = logging.getLogger(__name__)

try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    _db_available = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    _db_available = False

try:
    from src.llm.client import chat
    _llm_available = True
except ImportError:
    chat = None  # type: ignore[assignment]
    _llm_available = False

from .schemas import InventoryState

_MOCK_INVENTORY_DATA = [
    {"sku": "PET-LEASH-001", "product_name": "Premium Dog Leash", "current_stock": 45, "daily_sales_avg": 3.2, "days_of_stock": 14.1, "in_transit": 100, "warehouse": "FBA-US"},
    {"sku": "PET-BOWL-002", "product_name": "Stainless Steel Bowl", "current_stock": 230, "daily_sales_avg": 5.1, "days_of_stock": 45.1, "in_transit": 0, "warehouse": "FBA-US"},
    {"sku": "PET-TOY-003", "product_name": "Squeaky Dog Toy", "current_stock": 12, "daily_sales_avg": 8.5, "days_of_stock": 1.4, "in_transit": 0, "warehouse": "FBA-US"},
    {"sku": "PET-BED-004", "product_name": "Orthopedic Dog Bed", "current_stock": 67, "daily_sales_avg": 2.0, "days_of_stock": 33.5, "in_transit": 50, "warehouse": "FBA-US"},
    {"sku": "PET-TREAT-005", "product_name": "Organic Dog Treats", "current_stock": 8, "daily_sales_avg": 12.0, "days_of_stock": 0.7, "in_transit": 0, "warehouse": "FBA-US"},
    {"sku": "PET-COLLAR-006", "product_name": "Adjustable Cat Collar", "current_stock": 156, "daily_sales_avg": 4.3, "days_of_stock": 36.3, "in_transit": 0, "warehouse": "FBA-US"},
]


def _filter_mock_inventory(sku_list: List[str]) -> List[Dict[str, Any]]:
    if not sku_list:
        return list(_MOCK_INVENTORY_DATA)
    wanted = set(sku_list)
    return [item for item in _MOCK_INVENTORY_DATA if item.get("sku") in wanted]


def init_run(state: InventoryState) -> InventoryState:
    if state.get("error"):
        return state

    sku_list = state.get("sku_list", [])
    threshold_days = state.get("threshold_days", 30)
    dry_run = state.get("dry_run", True)

    logger.info("inventory_agent init_run | sku_count=%d threshold_days=%s dry_run=%s", len(sku_list), threshold_days, dry_run)

    if not isinstance(sku_list, list):
        state["error"] = "sku_list 必须是列表"
        state["status"] = "failed"
        return state

    if threshold_days is None:
        threshold_days = 30
    if not isinstance(threshold_days, int) or threshold_days <= 0:
        state["error"] = "threshold_days 必须是正整数"
        state["status"] = "failed"
        return state

    state["threshold_days"] = threshold_days
    run_id = str(uuid.uuid4())

    if not dry_run and _db_available and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="inventory_agent",
                    status="running",
                    input_summary=json.dumps({"sku_count": len(sku_list), "threshold_days": threshold_days}),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run)
                session.commit()
            logger.info("inventory_agent init_run | agent_run_id=%s", run_id)
        except Exception as exc:
            logger.warning("inventory_agent init_run DB写入失败（非阻塞）: %s", exc)
    else:
        logger.info("inventory_agent init_run | dry_run=True, 跳过DB写入 agent_run_id=%s", run_id)

    state["agent_run_id"] = run_id
    state["status"] = "running"
    return state


def fetch_inventory(state: InventoryState) -> InventoryState:
    if state.get("error"):
        return state

    dry_run = state.get("dry_run", True)
    sku_list = state.get("sku_list", [])

    logger.info("inventory_agent fetch_inventory | dry_run=%s", dry_run)

    inventory_data = _filter_mock_inventory(sku_list)

    if not dry_run:
        logger.warning("inventory_agent fetch_inventory | SP-API 尚未配置，回退使用 mock 数据（T6/T18 之后接入）")
        for item in inventory_data:
            item["note"] = "SP-API 未配置，当前为 mock 数据"

    state["inventory_data"] = inventory_data
    return state


def analyze_stock(state: InventoryState) -> InventoryState:
    if state.get("error"):
        return state

    inventory_data = state.get("inventory_data", [])
    dry_run = state.get("dry_run", True)

    logger.info("inventory_agent analyze_stock | item_count=%d dry_run=%s", len(inventory_data), dry_run)

    if dry_run:
        critical = [i["sku"] for i in inventory_data if float(i.get("days_of_stock", 0)) < 7]
        warning = [i["sku"] for i in inventory_data if 7 <= float(i.get("days_of_stock", 0)) < float(state.get("threshold_days", 30))]
        analysis = {
            "overall_stock_health": "需要重点关注，部分 SKU 库存偏低",
            "immediate_attention_skus": critical,
            "recommended_reorder_targets": {i["sku"]: int(max(0, math.ceil(float(i.get("daily_sales_avg", 0)) * 60 - float(i.get("current_stock", 0)) - float(i.get("in_transit", 0))))) for i in inventory_data},
            "warning_skus": warning,
        }
        state["analysis"] = analysis
        return state

    if not _llm_available or chat is None:
        logger.warning("inventory_agent analyze_stock | LLM 不可用，使用 mock 分析")
        state["analysis"] = {
            "overall_stock_health": "LLM 不可用，已回退到静态分析",
            "immediate_attention_skus": [i["sku"] for i in inventory_data if float(i.get("days_of_stock", 0)) < 7],
            "recommended_reorder_targets": {i["sku"]: int(max(0, math.ceil(float(i.get("daily_sales_avg", 0)) * 60 - float(i.get("current_stock", 0)) - float(i.get("in_transit", 0))))) for i in inventory_data},
        }
        return state

    try:
        import json as _json

        system_message = "You are an Amazon FBA inventory analyst. Analyze the following inventory data and provide: 1) Overall stock health assessment, 2) SKUs requiring immediate attention, 3) Recommended reorder quantities based on 60-day runway target. Respond in JSON format."
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": _json.dumps({"inventory_data": inventory_data, "threshold_days": state.get("threshold_days", 30)}, ensure_ascii=False)},
        ]
        response = chat(model="gpt-4o-mini", messages=messages, temperature=0.2, max_tokens=1200)
        content = response.get("content", "")
        try:
            analysis = _json.loads(content)
        except Exception:
            analysis = {
                "overall_stock_health": content.strip(),
                "immediate_attention_skus": [i["sku"] for i in inventory_data if float(i.get("days_of_stock", 0)) < 7],
                "recommended_reorder_targets": {i["sku"]: int(max(0, math.ceil(float(i.get("daily_sales_avg", 0)) * 60 - float(i.get("current_stock", 0)) - float(i.get("in_transit", 0))))) for i in inventory_data},
            }
        state["analysis"] = analysis
    except Exception as exc:
        logger.error("inventory_agent analyze_stock 失败: %s", exc)
        state["error"] = f"库存分析失败: {exc}"
        state["status"] = "failed"

    return state


def generate_alerts(state: InventoryState) -> InventoryState:
    if state.get("error"):
        return state

    inventory_data = state.get("inventory_data", [])
    threshold_days = int(state.get("threshold_days", 30))
    alerts: List[Dict[str, Any]] = []

    logger.info("inventory_agent generate_alerts | item_count=%d threshold_days=%s", len(inventory_data), threshold_days)

    for item in inventory_data:
        sku = item.get("sku", "")
        product_name = item.get("product_name", "")
        current_stock = int(item.get("current_stock", 0))
        daily_sales_avg = float(item.get("daily_sales_avg", 0))
        days_of_stock = float(item.get("days_of_stock", 0))
        in_transit = int(item.get("in_transit", 0))
        recommended_reorder_qty = int(max(0, math.ceil(daily_sales_avg * 60 - current_stock - in_transit)))

        if days_of_stock < 7:
            alert_type = "critical"
            message = f"【紧急补货】{product_name}（{sku}）当前仅剩 {days_of_stock:.1f} 天库存，建议立即安排补货，建议补货 {recommended_reorder_qty} 件。"
        elif days_of_stock < threshold_days:
            alert_type = "warning"
            message = f"【库存预警】{product_name}（{sku}）库存可支撑 {days_of_stock:.1f} 天，低于阈值 {threshold_days} 天，建议尽快补货 {recommended_reorder_qty} 件。"
        elif in_transit > 0:
            alert_type = "info"
            message = f"【在途提醒】{product_name}（{sku}）已有 {in_transit} 件在途库存，当前库存可支撑 {days_of_stock:.1f} 天。"
        else:
            continue

        alerts.append({
            "sku": sku,
            "product_name": product_name,
            "alert_type": alert_type,
            "days_of_stock": days_of_stock,
            "current_stock": current_stock,
            "daily_sales_avg": daily_sales_avg,
            "recommended_reorder_qty": recommended_reorder_qty,
            "message": message,
        })

    state["alerts"] = alerts
    return state


def save_results(state: InventoryState) -> InventoryState:
    if state.get("error"):
        return state

    dry_run = state.get("dry_run", True)
    alerts = state.get("alerts", [])
    agent_run_id = state.get("agent_run_id", "")

    logger.info("inventory_agent save_results | alert_count=%d dry_run=%s", len(alerts), dry_run)

    if dry_run:
        logger.info("inventory_agent save_results | dry_run=True，跳过真实写入")
        return state

    if not _db_available or db_session is None or AgentRun is None or not agent_run_id:
        logger.warning("inventory_agent save_results | DB 不可用或 agent_run_id 缺失，跳过写入")
        return state

    try:
        run_uuid = uuid.UUID(agent_run_id)
        with db_session() as session:
            session.execute(
                update(AgentRun)
                .where(AgentRun.id == run_uuid)
                .values(
                    result_json={
                        "alerts": alerts,
                        "analysis": state.get("analysis", {}),
                        "inventory_data": state.get("inventory_data", []),
                    },
                    output_summary=json.dumps({"alert_count": len(alerts), "status": state.get("status", "running")}),
                )
            )
            session.commit()
        logger.info("inventory_agent save_results | DB已更新 agent_run_id=%s", agent_run_id)
    except Exception as exc:
        logger.warning("inventory_agent save_results 失败（非阻塞）: %s", exc)

    return state


def finalize_run(state: InventoryState) -> InventoryState:
    agent_run_id = state.get("agent_run_id", "")
    error = state.get("error")
    final_status = "failed" if error else "completed"
    state["status"] = final_status

    logger.info("inventory_agent finalize_run | agent_run_id=%s status=%s", agent_run_id, final_status)

    if not state.get("dry_run", True) and _db_available and db_session is not None and AgentRun is not None and agent_run_id:
        try:
            run_uuid = uuid.UUID(agent_run_id)
            with db_session() as session:
                session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == run_uuid)
                    .values(
                        status=final_status,
                        finished_at=datetime.now(timezone.utc),
                        output_summary=json.dumps(
                            {
                                "alert_count": len(state.get("alerts", [])),
                                "status": final_status,
                                "error": error,
                            }
                        )[:200],
                    )
                )
                session.commit()
        except Exception as exc:
            logger.warning("inventory_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    return state
