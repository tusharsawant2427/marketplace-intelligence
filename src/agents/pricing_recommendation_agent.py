import os
from google import genai
from src.prompts.pricing_recommendation_prompt_builder import PricingRecommendationPromptBuilder
from src.models.business_recommendation import BusinessRecommendation
from src.domain.pricing_scenario import PricingScenario
from src.domain.erp_pricing_context import ErpPricingContext
from src.services.amazon_sp_api_service import SpApiPricingData
from src.services.pricing.recommendation_engine import PricingConstraints

class PricingRecommendationAgent:
    """
    AI Agent that takes the deterministic pricing recommendation and 
    provides a human-readable business explanation.
    """
    def __init__(self):
        # Initialize Google GenAI client
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash"
        self.prompt_builder = PricingRecommendationPromptBuilder()

    def generate_explanation(
        self,
        current_price: float,
        scenario: PricingScenario,
        constraints: PricingConstraints,
        erp_context: ErpPricingContext,
        sp_api_data: SpApiPricingData
    ) -> BusinessRecommendation:
        
        prompt = self.prompt_builder.build(
            current_price=current_price,
            scenario=scenario,
            constraints=constraints,
            erp_context=erp_context,
            sp_api_data=sp_api_data
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        
        explanation = response.text
        
        # Creating the structured recommendation object
        return BusinessRecommendation(
            summary=f"Recommend setting price to ₹{scenario.selling_information.selling_price}",
            root_cause="Pricing optimization to meet margin goals.",
            business_impact=f"Achieves target margin while staying competitive.",
            confidence=0.95,
            recommended_actions=[explanation],
            priority="Medium",
            supporting_evidence=[
                f"Gross profit: ₹{scenario.profit_analysis.gross_profit}",
                f"Break-even: ₹{scenario.profit_analysis.break_even_price}"
            ]
        )
