from dataclasses import dataclass

@dataclass
class FulfillmentStrategy:
    """
    Represents how and where a listing is fulfilled.

    Example:
        fulfillment_type: FBA
        selling_zone: Local
    """
    fulfillment_type: str
    selling_zone: str