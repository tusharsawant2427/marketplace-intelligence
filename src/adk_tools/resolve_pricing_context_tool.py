from src.database.connection import async_session
from src.services.pricing_input_resolver import resolve_pricing_inputs


async def resolve_pricing_context(
    platform_unique_id: str = None,
    listing_id: int = None,
    osp_id: int = None,
    marketplace_id: int = None,
    node_id: int = None,
    fulfillment_meta_id: int = None,
) -> dict:
    """
    Resolve the identifiers needed for a price recommendation from whatever the user gave.
    ALWAYS call this before recommend_optimal_price, and re-call it as the user supplies more.

    Provide any subset of:
        platform_unique_id: The platform listing id / ASIN / SKU (e.g. "B07Q46XQQC").
        listing_id: Internal listing id.
        osp_id: Internal OnlineSellingProduct id.
        marketplace_id: Internal marketplace id (a choice, or refinement).
        node_id: Internal category node id (used for pre-listing products, or refinement).
        fulfillment_meta_id: Internal fulfillment id (a choice, or refinement).

    If an OSP has no listings yet (pre-listing / ANALYSIS_PENDING), this walks the user through
    picking a marketplace -> category -> fulfillment from `suggestions`; such products are priced
    ERP-only (no ASIN means no live buy-box).

    Returns a dict with:
        status = "ready"      -> `resolved` holds osp_id, marketplace_id, node_id,
                                 fulfillment_meta_id, platform_unique_id and has_live_pricing;
                                 proceed to recommend_optimal_price.
        status = "need_input" -> `missing` names the next field to collect and `suggestions`
                                 lists the exact options to offer the user. Ask, then re-call
                                 this tool with the choice.
        status = "not_found"  -> the identifier matched nothing; ask the user to re-check.

    When resolved.has_live_pricing is False, the platform (e.g. Flipkart, Meesho) has no live
    marketplace integration: tell the user live buy-box data isn't available and that the
    recommendation will be a deterministic ERP-fee-based estimate.
    """

    try:
        async with async_session() as session:
            return await resolve_pricing_inputs(
                session,
                platform_unique_id=platform_unique_id,
                listing_id=listing_id,
                osp_id=osp_id,
                marketplace_id=marketplace_id,
                node_id=node_id,
                fulfillment_meta_id=fulfillment_meta_id,
            )
    except Exception as e:
        return {"status": "error", "message": f"Error resolving pricing context: {e}"}
