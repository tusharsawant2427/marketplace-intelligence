from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ReferralFeeBand:
    min_value: float
    max_value: float
    fee_percentage: float

@dataclass
class ClosingFeeBand:
    min_value: float
    max_value: float
    fee: float

@dataclass
class WeightHandlingSlab:
    zone: str  # LOCAL, REGIONAL, NATIONAL
    min_weight_slab: int
    max_weight_slab: int
    weight_slab_step: int
    fee: float
    # Note: real model also has price bands, item_type_id, etc.

@dataclass
class AmazonFeeMasters:
    referral_fees: List[ReferralFeeBand]
    closing_fees: List[ClosingFeeBand]
    weight_handling_fees: List[WeightHandlingSlab]

@dataclass
class ErpPricingContext:
    mrp: float
    weight_grams: float
    sale_gst_percentage: float  # e.g., 18.0
    purchase_cost: float
    packaging_cost: float
    transport_per_kg_rate: float
    advertisement_percentage: float # e.g., 5.0
    royalty_percentage: float # e.g., 0.0
    # simplified category identifier
    is_exception_category: bool = False
