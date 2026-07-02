from dataclasses import dataclass

from src.models.listing import Listing
from src.models.pricing import Pricing
from src.models.charges import Charges
from src.models.business_question_request import BusinessQuestionRequest


@dataclass
class PricingAnalysisContext:
    """Everything required for pricing analysis."""

    request: BusinessQuestionRequest

    listing: Listing

    pricing: Pricing

    charges: Charges