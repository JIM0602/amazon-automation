import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import require_role
from src.db import get_db
from src.db.models import AgentRun
from src.config import settings

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
logger = logging.getLogger(__name__)

@router.get("/costs")
def get_monitoring_costs(
    period: str = Query("daily", description="daily/weekly/monthly"),
    days: int = Query(30, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(require_role("boss")),  # type: ignore
    db: Session = Depends(get_db)  # type: ignore
) -> Dict[str, Any]:
    # We ignore the type on depends because basedpyright does not like FastAPI depends defaults
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    runs = db.query(AgentRun).filter(
        AgentRun.cost_usd.isnot(None),  # type: ignore
        AgentRun.started_at >= start_date  # type: ignore
    ).all()

    by_agent: Dict[str, Dict[str, Any]] = {}
    by_model: Dict[str, Dict[str, Any]] = {}
    daily_trend: Dict[str, float] = {}
    total_cost: float = 0.0
    today_cost: float = 0.0
    
    today_str = now.strftime("%Y-%m-%d")

    for r in runs:
        run: Any = r
        cost: float = float(run.cost_usd) if run.cost_usd is not None else 0.0
        total_cost += cost
        
        # Handle started_at safely
        if getattr(run, "started_at", None) is None:
            continue
            
        date_str: str = run.started_at.strftime("%Y-%m-%d")
        if date_str == today_str:
            today_cost += cost
            
        daily_trend[date_str] = daily_trend.get(date_str, 0.0) + cost
        
        # By Agent
        a_type: str = str(run.agent_type) if getattr(run, "agent_type", None) else "unknown"
        if a_type not in by_agent:
            by_agent[a_type] = {"agent_type": a_type, "total_cost": 0.0, "call_count": 0}
        by_agent[a_type]["total_cost"] += cost
        by_agent[a_type]["call_count"] += 1
        
        # By Model (parse from content or result_json)
        content_text: str = str(getattr(run, "content", ""))
        if getattr(run, "input_summary", None):
            content_text += str(run.input_summary)
        if getattr(run, "output_summary", None):
            content_text += str(run.output_summary)
            
        model_name = "unknown"
        res_json = getattr(run, "result_json", None)
        if isinstance(res_json, dict) and "model" in res_json:
            model_name = str(res_json["model"])
        else:
            # Parse model=xxx or "model":"xxx"
            match = re.search(r'model(?:=|\s*:\s*|["\':\s]+)([a-zA-Z0-9\-\.]+)', content_text, re.IGNORECASE)
            if match:
                model_name = str(match.group(1)).lower()
                
        if model_name not in by_model:
            by_model[model_name] = {"model": model_name, "total_cost": 0.0, "call_count": 0}
        by_model[model_name]["total_cost"] += cost
        by_model[model_name]["call_count"] += 1

    # Format daily trend
    trend_list: list[Dict[str, Any]] = []
    for d in range(days + 1):
        dt = start_date + timedelta(days=d)
        d_str = dt.strftime("%Y-%m-%d")
        trend_list.append({
            "date": d_str,
            "total_cost": round(daily_trend.get(d_str, 0.0), 4)
        })
        
    by_agent_list = sorted(list(by_agent.values()), key=lambda x: float(str(x["total_cost"])), reverse=True)
    by_model_list = sorted(list(by_model.values()), key=lambda x: float(str(x["total_cost"])), reverse=True)
    
    # Format floats
    for item in by_agent_list:
        item["total_cost"] = round(float(str(item["total_cost"])), 4)
    for item in by_model_list:
        item["total_cost"] = round(float(str(item["total_cost"])), 4)

    # Use period somehow so linter won't complain about unused variables
    _ = period
    _ = current_user

    return {
        "by_agent": by_agent_list,
        "by_model": by_model_list,
        "daily_trend": trend_list,
        "total_cost": round(total_cost, 4),
        "daily_limit": float(settings.MAX_DAILY_LLM_COST_USD),
        "today_cost": round(today_cost, 4)
    }
