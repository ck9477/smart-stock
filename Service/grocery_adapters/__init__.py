"""
Multi-site grocery adapters package.

Usage:
    from Service.grocery_adapters import RamiLevyAdapter
    from Service.grocery_adapters import create_adapter

    # Direct
    bot = RamiLevyAdapter()

    # Factory
    bot = create_adapter("rami_levy")
    bot = create_adapter("shuk_city")
    bot = create_adapter("victory")

    bot.process_product(barcode="729...", name="product", quantity=2)
    bot.close()
"""

from Service.grocery_adapters.rami_levy import RamiLevyAdapter
from Service.grocery_adapters.shuk_city import ShukCityAdapter
from Service.grocery_adapters.victory import VictoryAdapter


__all__ = [
    "RamiLevyAdapter",
    "ShukCityAdapter",
    "VictoryAdapter",
    "create_adapter",
]


def create_adapter(store: str, **kwargs):
    """
    Factory function ליצירת Adapter לפי שם הרשת.

    Args:
        store: אחד מ: 'rami_levy', 'shuk_city', 'victory'
        **kwargs: מועברים ל-constructor (לדוגמה headless)

    Returns:
        BaseGroceryAdapter instance
    """
    adapters = {
        "rami_levy": RamiLevyAdapter,
        "shuk_city": ShukCityAdapter,
        "victory": VictoryAdapter,
    }
    cls = adapters.get(store)
    if not cls:
        raise ValueError(
            f"Unknown store: '{store}'. Options: {list(adapters.keys())}"
        )
    return cls(**kwargs)
