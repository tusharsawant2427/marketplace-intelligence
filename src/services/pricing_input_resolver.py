"""
Resolves the identifiers a price recommendation needs from whatever the user supplied.

Two modes:
  * Listing-based: a platform_unique_id (ASIN/SKU) or listing_id pins an existing listing,
    from which osp, platform, marketplace and category are derived.
  * Pre-listing: an osp_id with NO listings yet (e.g. an ANALYSIS_PENDING product). There is
    nothing to derive marketplace/category from, so the user picks marketplace -> category ->
    fulfillment from suggestions. There is no ASIN, so there is no live buy-box (ERP-only).

The resolver never guesses when a choice is ambiguous (>1 option): it returns
status="need_input" with the exact `missing` field and `suggestions` to show the user.
When everything is pinned it returns status="ready".
"""
from src.clients.erp_api_client import ErpApiClient


async def resolve_pricing_inputs(
    client: ErpApiClient,
    platform_unique_id: str = None,
    listing_id: int = None,
    osp_id: int = None,
    marketplace_id: int = None,
    node_id: int = None,
    fulfillment_meta_id: int = None,
) -> dict:
    repo = client
    resolved: dict = {}

    def need(missing: str, message: str, suggestions: dict = None) -> dict:
        return {
            "status": "need_input",
            "missing": missing,
            "message": message,
            "suggestions": suggestions or {},
            "resolved": resolved,
        }

    # A fulfillment id alone lets us back-track to its marketplace (and platform).
    if marketplace_id is None and fulfillment_meta_id is not None:
        marketplace_id = await repo.get_marketplace_for_fulfillment(fulfillment_meta_id)

    # ---- Step 1: pin a listing, or fall into pre-listing mode ----
    listing = None
    pre_listing = False
    if listing_id is not None:
        listing = await repo.get_listing(listing_id)
        if not listing:
            return {"status": "not_found", "message": f"No listing found with id {listing_id}.", "resolved": resolved}
    elif platform_unique_id:
        matches = await repo.find_listings_by_platform_unique_id(platform_unique_id)
        if not matches:
            return {"status": "not_found",
                    "message": f"No listing found for platform id '{platform_unique_id}'.",
                    "resolved": resolved}
        if len(matches) > 1:
            return need("listing_id",
                        f"'{platform_unique_id}' matches {len(matches)} listings across platforms. "
                        f"Which one should I analyse?",
                        {"listings": matches})
        listing = matches[0]
    elif osp_id is not None:
        listings = await repo.get_listings_for_osp(osp_id)
        resolved["osp_id"] = osp_id
        if listings:
            return need("listing_id",
                        f"OSP {osp_id} is listed on several platforms. Which platform's listing should I price?",
                        {"listings": listings})
        pre_listing = True  # exists but not listed anywhere yet -> price it pre-listing
    else:
        return need("identifier",
                    "To start, give me one of: a platform id (ASIN/SKU), a listing id, or an OSP id.")

    # ---- Step 2: osp + platform + marketplace + category node ----
    if listing:
        osp_id = listing["osp_id"]
        resolved.update({
            "listing_id": listing["listing_id"],
            "osp_id": osp_id,
            "platform_name": listing["platform_name"],
            "platform_unique_id": listing["platform_unique_id"],
        })
        marketplaces = await repo.get_listing_marketplaces(listing["listing_id"])
        chosen_mkt = None
        if marketplace_id is not None:
            chosen_mkt = next((m for m in marketplaces if m["marketplace_id"] == marketplace_id), None)
        if chosen_mkt is None:
            if not marketplaces:
                return need("marketplace_id",
                            f"Listing {listing['listing_id']} has no marketplace/category on record; "
                            f"I can't look up fees without one.")
            if len(marketplaces) == 1:
                chosen_mkt = marketplaces[0]
            else:
                return need("marketplace_id",
                            "This listing spans multiple marketplaces. Which marketplace should I price for?",
                            {"marketplaces": marketplaces})
        resolved.update({
            "marketplace_id": chosen_mkt["marketplace_id"],
            "marketplace_name": chosen_mkt["marketplace_name"],
            "node_id": chosen_mkt["node_id"],
            "node_name": chosen_mkt["node_name"],
        })
        mkt_platform = await repo.get_marketplace_platform(chosen_mkt["marketplace_id"])
        has_live = bool(mkt_platform and mkt_platform["has_live_pricing"])
        marketplace_id = chosen_mkt["marketplace_id"]
    else:
        # Pre-listing: user chooses marketplace then category from suggestions.
        resolved.update({"osp_id": osp_id, "pre_listing": True, "platform_unique_id": None})
        if marketplace_id is None:
            return need("marketplace_id",
                        f"OSP {osp_id} isn't listed on any marketplace yet. Which marketplace do you want "
                        f"to price it for?",
                        {"marketplaces": await repo.get_supported_marketplaces()})
        mkt_platform = await repo.get_marketplace_platform(marketplace_id)
        if not mkt_platform:
            return {"status": "not_found", "message": f"Marketplace {marketplace_id} not found.", "resolved": resolved}
        resolved.update({
            "marketplace_id": marketplace_id,
            "marketplace_name": mkt_platform["marketplace_name"],
            "platform_name": mkt_platform["platform_name"],
        })
        nodes = await repo.get_category_nodes_for_marketplace(marketplace_id)
        chosen_node = None
        if node_id is not None:
            chosen_node = next((n for n in nodes if n["node_id"] == node_id), None)
        if chosen_node is None:
            if not nodes:
                return need("node_id", f"No category fee data is configured for {mkt_platform['marketplace_name']}.")
            return need("node_id",
                        f"Which product category on {mkt_platform['marketplace_name']}?",
                        {"categories": nodes})
        resolved.update({"node_id": chosen_node["node_id"], "node_name": chosen_node["node_name"]})
        # No ASIN when pre-listing -> no live buy-box even on Amazon.
        has_live = False

    resolved["has_live_pricing"] = has_live

    # ---- Step 3: fulfillment type ----
    fulfillments = await repo.get_fulfillment_options(marketplace_id)
    chosen_ff = None
    if fulfillment_meta_id is not None:
        chosen_ff = next((f for f in fulfillments if f["fulfillment_meta_id"] == fulfillment_meta_id), None)
    if chosen_ff is None:
        if not fulfillments:
            return need("fulfillment_meta_id",
                        f"No fulfillment options are configured for {resolved.get('marketplace_name')}.")
        if len(fulfillments) == 1:
            chosen_ff = fulfillments[0]
        else:
            return need("fulfillment_meta_id",
                        f"How is this fulfilled on {resolved.get('marketplace_name')}?",
                        {"fulfillments": fulfillments})
    resolved.update({
        "fulfillment_meta_id": chosen_ff["fulfillment_meta_id"],
        "fulfillment_type": chosen_ff["fulfillment_type"],
    })

    # ---- Everything pinned ----
    if pre_listing:
        message = (f"OSP {osp_id} isn't listed yet, so I'll compute a deterministic ERP-fee-based "
                   f"pre-listing recommendation for {resolved['marketplace_name']} "
                   f"({resolved['node_name']}) — no live competitor/buy-box data.")
    elif not has_live:
        message = (f"Note: {resolved['platform_name']} has no live buy-box integration, so I'll compute a "
                   f"deterministic ERP-fee-based recommendation without live competitor data.")
    else:
        message = "All inputs resolved. Ready to recommend a price."
    return {"status": "ready", "resolved": resolved, "has_live_pricing": has_live, "message": message}
