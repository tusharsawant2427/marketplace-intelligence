from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def recommend_optimal_price(
    osp_id: int,
    marketplace_id: int,
    node_id: int,
    fulfillment_meta_id: int,
    target_margin_percentage: float,
    weight: float,
    length: float,
    width: float,
    height: float,
    selling_zone: str = "National",
) -> dict:
    """
    Recommend the optimal listing price to hit a target profit margin, computed by the ERP's
    bounded-search engine. Returns the optimal price and the resulting fee/profit (LPA) breakdown.

    Resolve osp_id/marketplace_id/node_id/fulfillment_meta_id via resolve_pricing_context first, and
    collect the package weight (g) and length/width/height (cm) from the user (needed for fees).

    Args:
        osp_id, marketplace_id, node_id, fulfillment_meta_id: resolved identifiers.
        target_margin_percentage: desired profit margin, e.g. 20 for 20%.
        weight, length, width, height: package weight (g) and dimensions (cm).
        selling_zone: LOCAL / REGIONAL / NATIONAL (defaults to National).

    Returns:
        {"optimal_price": 299.0, "lpa_breakdown": {"commission": ..., "net_platform_fee": ...,
          "gross_profit": ..., "profit_pct": 20.0, ...}}
    """
    try:
        return await ErpApiClient().get_price_recommendation(
            osp_id,
            marketplace_id=marketplace_id,
            node_id=node_id,
            fulfillment_meta_id=fulfillment_meta_id,
            target_margin_percentage=target_margin_percentage,
            weight=weight,
            length=length,
            width=width,
            height=height,
            selling_zone=selling_zone,
        )
    except ErpApiError as e:
        return {"status": "error", "message": str(e)}
