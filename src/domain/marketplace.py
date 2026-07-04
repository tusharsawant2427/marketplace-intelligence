from dataclasses import dataclass, field

from src.domain.pricing_scenario import PricingScenario
from src.domain.marketplace_listing import MarketplaceListing


@dataclass
class Marketplace:
    """
    Represents a marketplace inside a platform.

    Example:
        India
        UAE
        UK

    A Marketplace is an organizational entity, not a pricing entity.
    Pricing lives inside its PricingScenario objects.
    """

    name: str

    pricing_scenarios: list[PricingScenario] = field(default_factory=list)

    listing: MarketplaceListing | None = None
