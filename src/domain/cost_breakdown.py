from dataclasses import dataclass


@dataclass
class CostBreakdown:
    """
    Represents the breakdown of costs associated with selling a listing
    on a marketplace.
    """

    purchase_cost: float

    transport_cost: float

    packaging_cost: float

    advertisement_cost: float

    royalty_cost: float
