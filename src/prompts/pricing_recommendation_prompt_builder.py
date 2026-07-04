from src.domain.pricing_scenario import PricingScenario
from src.domain.erp_pricing_context import ErpPricingContext
from src.services.amazon_sp_api_service import SpApiPricingData
from src.services.pricing.recommendation_engine import PricingConstraints

class PricingRecommendationPromptBuilder:
    """
    Builds the prompt to generate an explainable recommendation 
    for the pricing agent.
    """

    def build(
        self, 
        current_price: float, 
        scenario: PricingScenario, 
        constraints: PricingConstraints,
        erp_context: ErpPricingContext,
        sp_api_data: SpApiPricingData
    ) -> str:
        
        target_margin = f"{constraints.target_margin_percentage}%" if constraints.target_margin_percentage else "N/A"
        buy_box = f"₹{sp_api_data.buy_box_price}" if sp_api_data.buy_box_price else "N/A"
        
        prompt = f"""
You are the Listing Intelligence Center AI. Your job is to explain the following pricing recommendation to a business user.

### Business Goals:
- Target Margin: {target_margin}
- Beat Buy Box By: ₹{constraints.beat_buy_box_by if constraints.beat_buy_box_by is not None else 'N/A'}

### Current State:
- Current Price: ₹{current_price}
- Current Buy Box Price: {buy_box}
- MRP: ₹{erp_context.mrp}

### Our Recommendation:
- Recommended Selling Price: ₹{scenario.selling_information.selling_price}
- Expected Gross Profit: ₹{scenario.profit_analysis.gross_profit}
- Expected Profit Margin: {scenario.profit_analysis.profit_percentage}%
- Break-even Price: ₹{scenario.profit_analysis.break_even_price}

### Key Costs & Fees at Recommended Price:
- Referral Fee: ₹{scenario.marketplace_fee.commission_fee}
- Weight Handling / Fulfillment: ₹{scenario.marketplace_fee.fulfillment_fee}
- Total Platform Fee (inc. GST): ₹{scenario.marketplace_fee.total_platform_fee}
- Product Cost: ₹{scenario.cost_breakdown.purchase_cost}

Please generate a clear, human-readable explanation for this recommendation. Do not perform any math yourself. Trust the numbers provided. 
Your response should explain *why* this price is recommended based on their goals, how it compares to the Buy Box and Break-even price, and what major fees are driving the costs.
Keep it concise, professional, and actionable.
"""
        return prompt.strip()
