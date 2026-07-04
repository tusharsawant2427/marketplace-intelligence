from src.clients.erp_api_client import ErpApiClient, ErpApiError
from src.adk_tools.dimensions_tools import get_package_dimensions


async def analyze_listing(
    osp_id: int,
    marketplace_id: int,
    node_id: int,
    listing_price: float,
    asin: str = None,
    weight: float = None,
    length: float = None,
    width: float = None,
    height: float = None,
    marketplace_mrp: float = None,
    advertisement_charge_pct: float = None,
    listing_price_discount: float = 0.0,
    local_delivery_charge: float = 0.0,
    regional_delivery_charge: float = 0.0,
    national_delivery_charge: float = 0.0,
    step_level_name: str = "ADVANCED",
) -> dict:
    """
    Run the ERP's Listing Price Analysis (LPA) for a listing at a given price: returns a header
    block plus one fully-costed row per (fulfillment type x selling zone), with commission,
    fulfillment, fixed, collection, storage and pick-pack fees, net platform fee (incl 18% GST),
    all taxes/costs, gross profit, profit % and profit per item.

    Use this (not recommend_optimal_price) when the user wants the detailed fee/profit breakdown at
    a specific listing price. Resolve osp_id/marketplace_id/node_id via resolve_pricing_context first.

    Args:
        osp_id, marketplace_id, node_id: resolved identifiers.
        listing_price: the selling price to analyse.
        weight: package weight in grams; length/width/height in cm (needed for weight-handling,
            pick-pack and storage fees).
        marketplace_mrp: displayed MRP (defaults to the product's saleable MRP on the ERP).
        advertisement_charge_pct: advert % of MRP (defaults to the platform's configured rate).
        listing_price_discount: % discount (default 0).
        local/regional/national_delivery_charge: per-zone delivery (default 0).
        step_level_name: Amazon step-program level (PREMIUM/ADVANCED/STANDARD/BASIC/NO_LEVEL).

    Package weight/dimensions are fetched automatically from the Amazon catalog when an `asin` is
    provided and they are not passed — you normally do NOT need to ask the user for them.

    Returns {"header": {...}, "rows": [...]}, or status="need_input" if dims are neither given nor
    fetchable.
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
                    "message": "Package weight and dimensions are required and could not be fetched; "
                               "please provide weight (g) and length/width/height (cm)."}

        return await ErpApiClient().get_lpa_analysis(
            osp_id,
            marketplace_id=marketplace_id,
            node_id=node_id,
            listing_price=listing_price,
            weight=weight,
            length=length,
            width=width,
            height=height,
            marketplace_mrp=marketplace_mrp,
            advertisement_charge_pct=advertisement_charge_pct,
            listing_price_discount=listing_price_discount,
            local_delivery_charge=local_delivery_charge,
            regional_delivery_charge=regional_delivery_charge,
            national_delivery_charge=national_delivery_charge,
            step_level=step_level_name,
        )
    except ErpApiError as e:
        return {"status": "error", "message": str(e)}
