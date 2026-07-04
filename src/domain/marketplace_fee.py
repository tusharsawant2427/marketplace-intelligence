from dataclasses import dataclass


@dataclass
class MarketplaceFee:
    """
    Represents the fees charged by a marketplace for selling a listing.
    """

    commission_fee: float

    fulfillment_fee: float

    collection_fee: float

    storage_fee: float

    pick_pack_fee: float

    total_platform_fee: float
