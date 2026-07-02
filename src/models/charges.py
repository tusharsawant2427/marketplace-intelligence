from dataclasses import dataclass

@dataclass
class Charge:
    """ Represents a markeplace charges information. """

    advertisement_charge: float | None = None
    packaging_charge: float | None = None
    transport_charge: float | None = None
    delivery_charge_local: float | None = None
    delivery_charge_regional: float | None = None
    delivery_charge_national: float | None = None
    platform_charge_local: float | None = None
    platform_charge_reginal: float | None = None
    platform_charge_national: float | None = None
    