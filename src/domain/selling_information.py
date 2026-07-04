from dataclasses import dataclass


@dataclass
class SellingInformation:
    """
    Selling information represents how a listing is priced on a
    marketplace: what the customer pays and the price floor.
    """

    mrp: float

    selling_price: float

    customer_pays: float

    delivery_charge: float

    minimum_price: float
