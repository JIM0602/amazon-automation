"""Product Listing Agent 状态 Schema。"""
from __future__ import annotations

from typing import Any


class ProductListingState(dict[str, Any]):
    """LangGraph workflow state."""

    def __init__(self, **kwargs: Any):
        super().__init__(
            product_data=kwargs.get("product_data", {}),
            sku=kwargs.get("sku", ""),
            marketplace=kwargs.get("marketplace", "ATVPDKIKX0DER"),
            prepared_payload=kwargs.get("prepared_payload", {}),
            validation_errors=kwargs.get("validation_errors", []),
            submission_result=kwargs.get("submission_result", {}),
            dry_run=kwargs.get("dry_run", True),
            agent_run_id=kwargs.get("agent_run_id", ""),
            error=kwargs.get("error"),
            status=kwargs.get("status", "running"),
            requires_approval=kwargs.get("requires_approval", True),
            **{
                k: v
                for k, v in kwargs.items()
                if k
                not in {
                    "product_data",
                    "sku",
                    "marketplace",
                    "prepared_payload",
                    "validation_errors",
                    "submission_result",
                    "dry_run",
                    "agent_run_id",
                    "error",
                    "status",
                    "requires_approval",
                }
            },
        )
