import sys

content = """
# ---------------------------------------------------------------------------
#  Admin / Boss Only Pages
# ---------------------------------------------------------------------------

from src.db import get_db
from sqlalchemy.orm import Session
from src.db.models import SystemConfig
from src.config import settings
from src.api.auth import USERS

try:
    from src.agents.model_config import AGENT_MODEL_MAP as MODEL_CONFIG
except ImportError:
    try:
        from src.agents.model_config import MODEL_CONFIG
    except ImportError:
        MODEL_CONFIG = {}

@router.get("/users")
def get_users(_: dict = Depends(require_role("boss"))) -> list[dict[str, str]]:
    \"\"\"Return list of users with roles.\"\"\"
    result = []
    for username, info in USERS.items():
        result.append({
            "username": username,
            "role": info.get("role", "unknown")
        })
    return result

@router.get("/agent-config")
def get_agent_config(_: dict = Depends(require_role("boss"))) -> dict[str, str]:
    \"\"\"Return agent type to model assignments.\"\"\"
    return MODEL_CONFIG

class AgentConfigRequest(BaseModel):
    model: str

@router.put("/agent-config/{agent_type}")
def update_agent_config(
    agent_type: str,
    payload: AgentConfigRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role("boss"))
) -> dict[str, str]:
    \"\"\"Update model for an agent (write to system_config table).\"\"\"
    model_name = payload.model
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name is required")
        
    config_key = f"agent_model_{agent_type}"
    config = db.query(SystemConfig).filter(SystemConfig.key == config_key).first()
    
    if config:
        config.value = model_name
    else:
        config = SystemConfig(key=config_key, value=model_name)
        db.add(config)
        
    db.commit()
    return {"status": "success", "agent_type": agent_type, "model": model_name}

@router.get("/api-status")
def get_api_status(_: dict = Depends(require_role("boss"))) -> dict[str, bool]:
    \"\"\"Return which API keys are configured.\"\"\"
    return {
        "OpenAI": bool(settings.OPENAI_API_KEY),
        "Anthropic": bool(settings.ANTHROPIC_API_KEY),
        "Amazon Ads": bool(settings.AMAZON_ADS_CLIENT_ID),
        "SP-API": bool(settings.AMAZON_SP_API_CLIENT_ID),
        "Seller Sprite": bool(settings.SELLER_SPRITE_API_KEY),
        "Google Trends": bool(settings.GOOGLE_TRENDS_API_KEY)
    }

@router.get("/config")
def get_system_config(
    db: Session = Depends(get_db),
    _: dict = Depends(require_role("boss"))
) -> dict[str, str]:
    \"\"\"Return all system_config entries.\"\"\"
    configs = db.query(SystemConfig).all()
    return {c.key: c.value for c in configs if c.value is not None}

class SystemConfigRequest(BaseModel):
    value: str

@router.put("/config/{key}")
def update_system_config(
    key: str,
    payload: SystemConfigRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role("boss"))
) -> dict[str, str]:
    \"\"\"Update a system_config entry.\"\"\"
    value = payload.value
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if config:
        config.value = value
    else:
        config = SystemConfig(key=key, value=value)
        db.add(config)
        
    db.commit()
    return {"status": "success", "key": key, "value": value}
"""

with open('src/api/system.py', 'a', encoding='utf-8') as f:
    f.write(content)
