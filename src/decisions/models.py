"""决策系统 Pydantic 模型定义。

定义决策状态枚举和数据传输对象 (DTO)。

状态流转图:
    DRAFT → PENDING_APPROVAL → APPROVED → EXECUTING → SUCCEEDED
                                                    ↘ FAILED → ROLLED_BACK
                            ↘ REJECTED
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class DecisionStatus(str, Enum):
    """决策状态枚举。

    合法的状态转换：
    - DRAFT            → PENDING_APPROVAL (submit_for_approval)
    - PENDING_APPROVAL → APPROVED         (approve)
    - PENDING_APPROVAL → REJECTED         (reject)
    - APPROVED         → EXECUTING        (execute — 开始执行)
    - EXECUTING        → SUCCEEDED        (execute — 执行成功)
    - EXECUTING        → FAILED           (execute — 执行失败)
    - FAILED           → ROLLED_BACK      (rollback)
    """

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# 合法状态转换映射：{当前状态: [允许转入的状态]}
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: Dict[DecisionStatus, list[DecisionStatus]] = {
    DecisionStatus.DRAFT: [DecisionStatus.PENDING_APPROVAL],
    DecisionStatus.PENDING_APPROVAL: [DecisionStatus.APPROVED, DecisionStatus.REJECTED],
    DecisionStatus.APPROVED: [DecisionStatus.EXECUTING],
    DecisionStatus.EXECUTING: [DecisionStatus.SUCCEEDED, DecisionStatus.FAILED],
    DecisionStatus.FAILED: [DecisionStatus.ROLLED_BACK],
    # 终态：不允许再转换
    DecisionStatus.SUCCEEDED: [],
    DecisionStatus.REJECTED: [],
    DecisionStatus.ROLLED_BACK: [],
}


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class DecisionCreate(BaseModel):
    """创建决策的请求模型。"""

    decision_type: str = Field(..., description="决策类型（pricing, advertising, listing 等）")
    agent_id: str = Field(..., description="发起决策的 Agent ID")
    payload: Dict[str, Any] = Field(..., description="决策内容（JSON 格式）")
    rollback_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="回滚数据（可选，用于执行失败后恢复原状态）",
    )


class DecisionRead(BaseModel):
    """决策读取响应模型（对应数据库行）。"""

    id: uuid.UUID
    decision_type: str
    agent_id: str
    payload: Dict[str, Any]
    status: DecisionStatus
    created_at: datetime
    updated_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    rollback_payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)  # Pydantic v2 兼容 ORM 对象


class DecisionStatusTransitionError(Exception):
    """状态转换非法时抛出。"""

    def __init__(self, from_status: DecisionStatus, to_status: DecisionStatus):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"非法状态转换: {from_status.value} → {to_status.value}"
        )


class DecisionNotFoundError(Exception):
    """决策记录不存在时抛出。"""

    def __init__(self, decision_id: uuid.UUID):
        self.decision_id = decision_id
        super().__init__(f"决策不存在: id={decision_id}")
