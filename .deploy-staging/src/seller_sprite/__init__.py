"""卖家精灵 (Seller Sprite) 数据采集模块.

对外暴露:
    SellerSpriteBase  — 抽象基类，定义4个数据采集方法
    MockSellerSpriteClient — Mock实现，返回宠物用品类目模拟数据
    get_client        — 工厂函数，通过 SELLER_SPRITE_USE_MOCK 环境变量控制
"""

from src.seller_sprite.client import (
    SellerSpriteBase,
    MockSellerSpriteClient,
    get_client,
)

__all__ = [
    "SellerSpriteBase",
    "MockSellerSpriteClient",
    "get_client",
]
