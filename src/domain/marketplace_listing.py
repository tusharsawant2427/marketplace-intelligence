from dataclasses import dataclass


@dataclass
class MarketplaceListing:
    """
    Represents an already published listing.

    Later this will be extended with Buy Box, Inventory, Images,
    Reviews and Health information.
    """

    listing_id: str

    platform_listing_id: str

    status: str
