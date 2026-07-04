from dataclasses import dataclass, field

from src.domain.platform import Platform


@dataclass
class OnlineSellingProduct:
    """
    Root Aggregate.

    Represents an internal product that can be sold
    across multiple platforms.
    """

    product_id: str

    sku: str

    title: str

    description: str

    brand: str

    category: str

    platforms: list[Platform] = field(default_factory=list)
