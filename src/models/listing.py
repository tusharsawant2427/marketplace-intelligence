from dataclasses import dataclass

@dataclass
class Listing:
    """Represents a marketplace listing."""

    listing_id: str
    marketplace_id: str
    asin: str | None = None
    platform_unique_id: str | None = None
    title : stre | None = None
    description: str | None = None
    status: str | None = None
    platform: str | None = None
    marketplace: str | None = None
    category: str | None = None
    category_id: str | None = None
    inactive_reason: str | None = None
    