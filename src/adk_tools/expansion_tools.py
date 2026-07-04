"""Marketplace Expansion tools — footprint, gaps, and Amazon-India margin projection."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError

AMAZON_INDIA_MARKETPLACE_ID = 1
AMAZON_INDIA_STEP_LEVEL = 2  # ADVANCED on Amazon-India


async def marketplace_expansion(osp_id: int, listing_price: float = None, weight: float = None,
                                length: float = None, width: float = None, height: float = None) -> dict:
    """
    Where a product is (and isn't) listed, and its projected Amazon-India margin. Use for 'best
    marketplace', 'can I sell on X', 'launch readiness', 'expected margin/commission'.

    Args:
        osp_id: internal OnlineSellingProduct id.
        listing_price, weight, length, width, height: needed only for the margin projection (g/cm).

    Returns {"osp_id","current_footprint":[{platform,state,has_live_pricing}],
             "expansion_gaps":[marketplaces with fee data not yet listed],
             "amazon_india_projection": {best_fulfillment, best_zone, gross_profit, profit_pct,
                                         commission} | null, "note"}.
    Non-Amazon (Flipkart/Meesho) margin projection is not yet available from the ERP API.
    """
    try:
        client = ErpApiClient()
        listings = await client.get_listings_for_osp(osp_id)
        footprint = [{"platform": l.get("platform_name"), "state": l.get("state"),
                      "has_live_pricing": l.get("has_live_pricing")} for l in listings]
        listed_platforms = {l.get("platform_name") for l in listings}

        supported = await client.get_supported_marketplaces()
        gaps = [{"marketplace": m.get("marketplace_name"), "platform": m.get("platform_name")}
                for m in supported if m.get("platform_name") not in listed_platforms]

        projection = None
        note = "Non-Amazon (Flipkart/Meesho) margin projection is not yet available from the ERP API."
        if all(v is not None for v in (listing_price, weight, length, width, height)):
            # Project on Amazon-India using the OSP's Amazon listing category (node).
            node_id = None
            for l in listings:
                if l.get("has_live_pricing"):
                    mkts = await client.get_listing_marketplaces(l["listing_id"])
                    am = next((m for m in mkts if m["marketplace_id"] == AMAZON_INDIA_MARKETPLACE_ID), None)
                    if am:
                        node_id = am["node_id"]
                        break
            if node_id is not None:
                lpa = await client.get_lpa_analysis(
                    osp_id, marketplace_id=AMAZON_INDIA_MARKETPLACE_ID, node_id=node_id,
                    listing_price=listing_price, weight=weight, length=length, width=width, height=height,
                    step_level=AMAZON_INDIA_STEP_LEVEL, advertisement_charge_pct=10)
                rows = lpa.get("rows", [])
                if rows:
                    best = max(rows, key=lambda r: r.get("gross_profit", 0))
                    projection = {
                        "marketplace": "Amazon-India",
                        "best_fulfillment": best.get("fulfillment_type"),
                        "best_zone": best.get("selling_zone"),
                        "gross_profit": best.get("gross_profit"),
                        "profit_pct": best.get("profit_pct"),
                        "commission": best.get("commission"),
                    }
            else:
                note = "No Amazon-India category on record for this OSP; " + note

        return {
            "osp_id": osp_id,
            "current_footprint": footprint,
            "expansion_gaps": gaps,
            "amazon_india_projection": projection,
            "note": note,
        }
    except ErpApiError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Expansion analysis failed for OSP {osp_id}: {e}"}
