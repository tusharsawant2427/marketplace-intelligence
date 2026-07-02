from dataclasses import dataclass

@dataclass
class Listing:
    """Represents a marketplace listing."""

    listing_id: str
    marketplace_id: str
    platform_unique_id: str | None = None
    title : str | None = None
    description: str | None = None
    status: str | None = None
    platform: str | None = None
    platform_id: str | None = None
    marketplace: str | None = None
    category: str | None = None
    category_id: str | None = None
    inactive_reason: str | None = None
    