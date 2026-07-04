from typing import Optional
from dataclasses import dataclass
from src.services.pricing.lpa_calculator import LpaCalculator
from src.domain.erp_pricing_context import ErpPricingContext, AmazonFeeMasters
from src.domain.pricing_scenario import PricingScenario

@dataclass
class PricingConstraints:
    target_margin_percentage: Optional[float] = None
    target_profit_amount: Optional[float] = None
    max_price: Optional[float] = None
    beat_buy_box_by: Optional[float] = None
    buy_box_price: Optional[float] = None

class PricingRecommendationEngine:
    """
    Backward calculator that uses Bounded Search over the deterministic LpaCalculator
    to find the optimal selling price based on business goals.
    """
    
    def __init__(self):
        self.calculator = LpaCalculator()

    def recommend_price(
        self,
        context: ErpPricingContext,
        fee_masters: AmazonFeeMasters,
        constraints: PricingConstraints,
        zone: str = "NATIONAL",
        fulfillment_type: str = "FBA"
    ) -> Optional[PricingScenario]:
        """
        Uses binary search to find the optimal price.
        """
        # Define Bounds
        min_bound = 1.0  # Absolute floor
        max_bound = context.mrp
        
        if constraints.max_price and constraints.max_price < max_bound:
            max_bound = constraints.max_price
            
        if constraints.buy_box_price and constraints.beat_buy_box_by is not None:
            beat_price = constraints.buy_box_price - constraints.beat_buy_box_by
            if beat_price < max_bound:
                max_bound = beat_price

        # First, find the break-even price (margin = 0)
        break_even_scenario = self._search_target(
            target_margin=0.0, 
            min_price=min_bound, 
            max_price=context.mrp, 
            context=context, 
            fee_masters=fee_masters,
            zone=zone,
            fulfillment_type=fulfillment_type
        )
        
        break_even_price = break_even_scenario.selling_information.selling_price if break_even_scenario else min_bound

        # We cannot go below break-even unless explicitly allowed, but let's assume floor = break_even
        search_floor = break_even_price
        
        if constraints.target_margin_percentage is not None:
            optimal_scenario = self._search_target(
                target_margin=constraints.target_margin_percentage,
                min_price=search_floor,
                max_price=max_bound,
                context=context,
                fee_masters=fee_masters,
                zone=zone,
                fulfillment_type=fulfillment_type
            )
            if optimal_scenario:
                optimal_scenario.profit_analysis.break_even_price = round(break_even_price, 2)
                optimal_scenario.selling_information.minimum_price = round(break_even_price, 2)
            return optimal_scenario
            
        # If no margin target, maybe we just want to match the max_bound (e.g. beat buy box)
        return self.calculator.calculate_amazon_scenario(
            candidate_price=max_bound,
            context=context,
            fee_masters=fee_masters,
            zone=zone,
            fulfillment_type=fulfillment_type
        )

    def _search_target(
        self,
        target_margin: float,
        min_price: float,
        max_price: float,
        context: ErpPricingContext,
        fee_masters: AmazonFeeMasters,
        zone: str,
        fulfillment_type: str,
        tolerance: float = 0.5,
        max_iterations: int = 50
    ) -> Optional[PricingScenario]:
        
        low = min_price
        high = max_price
        best_scenario = None
        
        for _ in range(max_iterations):
            mid = (low + high) / 2.0
            scenario = self.calculator.calculate_amazon_scenario(
                candidate_price=mid,
                context=context,
                fee_masters=fee_masters,
                zone=zone,
                fulfillment_type=fulfillment_type
            )
            
            margin = scenario.profit_analysis.profit_percentage
            
            if best_scenario is None or abs(margin - target_margin) < abs(best_scenario.profit_analysis.profit_percentage - target_margin):
                best_scenario = scenario

            # Close enough?
            if abs(margin - target_margin) <= tolerance:
                return scenario
                
            if margin < target_margin:
                # We need more profit, so increase price
                low = mid
            else:
                # We have too much profit, decrease price
                high = mid
                
        return best_scenario
