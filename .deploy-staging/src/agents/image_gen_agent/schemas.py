"""Image Generation Agent schema definitions."""
from __future__ import annotations

from typing import Any, Optional


class ImageGenState(dict[str, object]):
    """LangGraph-compatible state container for image generation."""

    def __init__(
        self,
        prompt: str = "",
        product_name: Optional[str] = None,
        style: str = "professional",
        size: str = "1024x1024",
        dry_run: bool = True,
        **kwargs: Any,
    ):
        super().__init__(
            prompt=prompt,
            product_name=product_name,
            style=style,
            size=size,
            dry_run=dry_run,
            enhanced_prompt="",
            image_url="",
            image_data="",
            revised_prompt="",
            agent_run_id="",
            status="running",
            error=None,
            **kwargs,
        )
