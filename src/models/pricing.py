from dataclasses import dataclass

@dataclass
class Pricing:
    """ Represents a markeplace pricing information. """

    minimum_price: float | None = None
    selling_price: float | None = None
    mrp: float | None = None
    recommended_price: float | None = None
