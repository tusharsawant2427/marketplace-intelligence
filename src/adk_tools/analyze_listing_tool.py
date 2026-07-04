from src.database.connection import async_session
from src.services.pricing.listing_analysis import ListingAnalysisService


async def analyze_listing(
    osp_id: int,
    marketplace_id: int,
    node_id: int,
    listing_price: float,
    weight: float,
    length: float,
    width: float,
    height: float,
    marketplace_mrp: float = None,
    advertisement_charge_pct: float = None,
    listing_price_discount: float = 0.0,
    local_delivery_charge: float = 0.0,
    regional_delivery_charge: float = 0.0,
    national_delivery_charge: float = 0.0,
    step_level_name: str = "ADVANCED",
) -> dict:
    """
    Run the full ERP Listing Price Analysis (LPA) for a listing at a given price: returns a header
    block plus one fully-costed row per (fulfillment type x selling zone), with commission,
    fulfillment, fixed, collection, storage and pick-pack fees, net platform fee (incl 18% GST),
    all taxes/costs, gross profit, profit % and profit per item.

    Use this (not recommend_optimal_price) when the user wants the detailed fee/profit breakdown for
    a specific listing price. Resolve osp_id/marketplace_id/node_id via resolve_pricing_context first.

    Args:
        osp_id, marketplace_id, node_id: resolved identifiers.
        listing_price: the selling price to analyse.
        weight: package weight in grams; length/width/height in cm (needed for weight-handling,
            pick-pack and storage fees).
        marketplace_mrp: displayed MRP (defaults to the product's saleable MRP).
        advertisement_charge_pct: advert % of MRP (defaults to the platform's configured rate).
        listing_price_discount: % discount (default 0).
        local/regional/national_delivery_charge: per-zone delivery (default 0).
        step_level_name: Amazon step-program level (PREMIUM/ADVANCED/STANDARD/BASIC/NO_LEVEL).

    Returns a dict {"header": {...}, "rows": [...]}. Note: fee values are looked up live from the
    ERP fee masters. If weight/dimensions are unknown, ask the user for them.
    """
    try:
        async with async_session() as session:
            svc = ListingAnalysisService(session)
            return await svc.analyze(
                osp_id=osp_id, marketplace_id=marketplace_id, node_id=node_id,
                listing_price=listing_price, weight=weight, length=length, width=width, height=height,
                marketplace_mrp=marketplace_mrp, advertisement_charge_pct=advertisement_charge_pct,
                listing_price_discount=listing_price_discount,
                local_delivery_charge=local_delivery_charge,
                regional_delivery_charge=regional_delivery_charge,
                national_delivery_charge=national_delivery_charge,
                step_level_name=step_level_name,
            )
    except Exception as e:
        return {"status": "error", "message": f"Error analysing listing: {e}"}
