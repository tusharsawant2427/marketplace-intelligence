from src.database.connection import async_session
from src.database.repository import ErpRepository
from src.services.pricing.recommendation_engine import PricingRecommendationEngine, PricingConstraints
from src.services.amazon_sp_api_service import AmazonSpApiService, SpApiPricingData
from src.agents.pricing_recommendation_agent import PricingRecommendationAgent

async def recommend_optimal_price(
    asin: str,
    osp_id: int,
    marketplace_id: int,
    node_id: int,
    fulfillment_meta_id: int,
    current_price: float,
    target_margin_percentage: float = None,
    beat_buy_box_by: float = None
) -> str:
    """
    Analyzes an existing marketplace listing (OSP) and calculates the optimal 
    selling price to meet a target profit margin or to beat the Buy Box price.
    Uses real-time Amazon SP-API data and Live ERP fee rules.

    Args:
        asin: The Amazon Standard Identification Number.
        osp_id: The internal OnlineSellingProduct ID.
        marketplace_id: The internal marketplace ID (e.g. 1 for Amazon India).
        node_id: The category node ID.
        fulfillment_meta_id: The internal ID representing fulfillment type.
        current_price: The current selling price of the item.
        target_margin_percentage: (Optional) The desired profit margin %.
        beat_buy_box_by: (Optional) Amount in INR to beat the Buy Box.
        
    Returns:
        A human-readable AI-generated explanation of the recommended price.
    """
    
    try:
        async with async_session() as session:
            repository = ErpRepository(session)

            # Fetch ERP Data
            erp_context = await repository.get_erp_pricing_context(osp_id)
            fee_masters = await repository.get_amazon_fee_masters(
                marketplace_id=marketplace_id, 
                node_id=node_id, 
                fulfillment_meta_id=fulfillment_meta_id
            )
            # Live buy-box data is only available for platforms we have an integration for
            # (Amazon via SP-API). For others, run an ERP-only recommendation with no buy box.
            # Live pricing needs both an Amazon integration AND an ASIN to look up. A pre-listing
            # product (no ASIN) is always ERP-only.
            mkt_platform = await repository.get_marketplace_platform(marketplace_id)
            has_live_pricing = bool(mkt_platform and mkt_platform["has_live_pricing"]) and bool(asin)

            if has_live_pricing:
                sp_creds = await repository.get_amazon_sp_credentials()
                amazon_marketplace_id = await repository.get_amazon_marketplace_id(marketplace_id)
                sp_api_service = AmazonSpApiService(credentials=sp_creds)
                sp_api_data = await sp_api_service.get_live_pricing(asin, amazon_marketplace_id)
            else:
                # No live integration: deterministic ERP-only, no competitor/buy-box data.
                sp_api_data = SpApiPricingData(
                    asin=asin, buy_box_price=None, buy_box_currency="INR",
                    is_buy_box_winner=False, competitor_count=0,
                )

            # Run Recommendation Engine
            constraints = PricingConstraints(
                target_margin_percentage=target_margin_percentage,
                beat_buy_box_by=beat_buy_box_by,
                buy_box_price=sp_api_data.buy_box_price,
                max_price=erp_context.mrp
            )

            engine = PricingRecommendationEngine()
            scenario = engine.recommend_price(
                context=erp_context,
                fee_masters=fee_masters,
                constraints=constraints
            )

            if not scenario:
                return "Failed to find a viable pricing scenario within the given constraints."

            # Generate Explanation
            agent = PricingRecommendationAgent()
            recommendation = agent.generate_explanation(
                current_price=current_price,
                scenario=scenario,
                constraints=constraints,
                erp_context=erp_context,
                sp_api_data=sp_api_data
            )
            
            return recommendation.summary + "\n\n" + "\n".join(recommendation.recommended_actions)

    except Exception as e:
        return f"Error executing pricing recommendation: {str(e)}"
