from src.clients.erp_api_client import ErpApiClient, ErpApiError
from src.adk_tools.dimensions_tools import get_package_dimensions


async def recommend_optimal_price(
    osp_id: int,
    marketplace_id: int,
    node_id: int,
    fulfillment_meta_id: int,
    target_margin_percentage: float,
    asin: str = None,
    weight: float = None,
    length: float = None,
    width: float = None,
    height: float = None,
    selling_zone: str = "National",
) -> dict:
    """
    Recommend the optimal listing price to hit a target profit margin, computed by the ERP's
    bounded-search engine. Returns the optimal price and the resulting fee/profit (LPA) breakdown.

    Resolve osp_id/marketplace_id/node_id/fulfillment_meta_id via resolve_pricing_context first.
    Package weight (g) and dimensions (cm) are fetched automatically from the Amazon catalog when an
    `asin` is provided and they are not passed — you normally do NOT need to ask the user for them.

    Args:
        osp_id, marketplace_id, node_id, fulfillment_meta_id: resolved identifiers.
        target_margin_percentage: desired profit margin, e.g. 20 for 20%.
        asin: the ASIN (from resolve_pricing_context's platform_unique_id) — used to auto-fetch dims.
        weight, length, width, height: package weight (g)/dims (cm); auto-filled from `asin` if omitted.
        selling_zone: LOCAL / REGIONAL / NATIONAL (defaults to National).

    Returns {"optimal_price": ..., "lpa_breakdown": {...}}. If dimensions are neither supplied nor
    fetchable, returns status="need_input" asking for weight/dimensions.
    """
    try:
        if None in (weight, length, width, height) and asin:
            dims = await get_package_dimensions(asin, marketplace_id)
            if dims.get("status") not in ("error", "not_found"):
                weight = weight or dims.get("weight")
                length = length or dims.get("length")
                width = width or dims.get("width")
                height = height or dims.get("height")

        if None in (weight, length, width, height):
            return {"status": "need_input",
                    "message": "Package weight and dimensions are required and could not be fetched "
                               "from the catalog. Please provide weight (g) and length/width/height (cm)."}

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
