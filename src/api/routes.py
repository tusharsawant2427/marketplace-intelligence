from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import get_db
from src.database.repository import ErpRepository
from src.services.pricing.recommendation_engine import PricingRecommendationEngine, PricingConstraints
from src.services.amazon_sp_api_service import AmazonSpApiService
from src.agents.pricing_recommendation_agent import PricingRecommendationAgent

router = APIRouter()

class PricingRecommendationRequest(BaseModel):
    asin: str
    osp_id: int
    marketplace_id: int
    node_id: int
    fulfillment_meta_id: int
    current_price: float
    target_margin_percentage: Optional[float] = None
    beat_buy_box_by: Optional[float] = None

@router.post("/recommend-price")
async def recommend_price(
    request: PricingRecommendationRequest,
    session: AsyncSession = Depends(get_db)
):
    repository = ErpRepository(session)
    
    # 1. Hydrate ERP Context from pulse_erp Database
    try:
        erp_context = await repository.get_erp_pricing_context(request.osp_id)
        fee_masters = await repository.get_amazon_fee_masters(
            marketplace_id=request.marketplace_id, 
            node_id=request.node_id, 
            fulfillment_meta_id=request.fulfillment_meta_id
        )
        sp_creds = await repository.get_amazon_sp_credentials()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

    # 2. Hydrate SP-API Data (resolve internal marketplace id -> Amazon SP-API marketplace id)
    amazon_marketplace_id = await repository.get_amazon_marketplace_id(request.marketplace_id)
    sp_api_service = AmazonSpApiService(credentials=sp_creds)
    sp_api_data = await sp_api_service.get_live_pricing(request.asin, amazon_marketplace_id)

    # 3. Setup Constraints
    constraints = PricingConstraints(
        target_margin_percentage=request.target_margin_percentage,
        beat_buy_box_by=request.beat_buy_box_by,
        buy_box_price=sp_api_data.buy_box_price,
        max_price=erp_context.mrp
    )

    # 4. Run Deterministic Bounded Search
    engine = PricingRecommendationEngine()
    scenario = engine.recommend_price(
        context=erp_context,
        fee_masters=fee_masters,
        constraints=constraints
    )

    if not scenario:
        raise HTTPException(status_code=400, detail="Could not find a valid pricing scenario.")

    # 5. Generate AI Explanation
    agent = PricingRecommendationAgent()
    recommendation = agent.generate_explanation(
        current_price=request.current_price,
        scenario=scenario,
        constraints=constraints,
        erp_context=erp_context,
        sp_api_data=sp_api_data
    )

    return recommendation
