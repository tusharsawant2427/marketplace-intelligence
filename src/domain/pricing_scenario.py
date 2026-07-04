from dataclasses import dataclass

from src.domain.fulfillment_strategy import FulfillmentStrategy
from src.domain.selling_information import SellingInformation
from src.domain.marketplace_fee import MarketplaceFee
from src.domain.cost_breakdown import CostBreakdown
from src.domain.profit_analysis import ProfitAnalysis


@dataclass
class PricingScenario:
    """
    A pricing scenario represents one possible way to sell on a
    marketplace, including the price, fees, costs and resulting profit.

    It carries no Platform, Marketplace or Listing reference, because
    the hierarchy that owns the scenario already knows those.
    """

    fulfillment_strategy: FulfillmentStrategy

    selling_information: SellingInformation

    marketplace_fee: MarketplaceFee

    cost_breakdown: CostBreakdown

    profit_analysis: ProfitAnalysis
