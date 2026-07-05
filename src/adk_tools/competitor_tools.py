"""Competitor Intelligence tools — live Amazon offers/competitive pricing (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def competitor_analysis(asin: str, marketplace_id: int = 1) -> dict:
    """
    Live competitor snapshot for an Amazon ASIN: who owns the Buy Box, how many sellers, the price
    spread (lowest / average / highest landed price) and each competitor's price + Prime + feedback.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns:
        {"asin", "number_of_offers", "buy_box": {"price","seller_id","is_prime"} | None,
         "lowest_price", "highest_price", "market_average", "sales_rank",
         "competitors": [{"seller_id","landed_price","is_prime","is_buy_box","feedback_pct"}, ...]}
        Note: ratings/reviews are not available via SP-API and are omitted.
    """
    try:
        # Passthrough: Laravel proxies SP-API and returns the computed snapshot.
        return await ErpApiClient().competitors(marketplace_id, asin)
    except ErpApiError as e:
        return {"status": "error", "message": f"Competitor analysis failed for {asin}: {e}"}


async def am_i_overpriced(asin: str, our_price: float, marketplace_id: int = 1) -> dict:
    """
    Compare our selling price to the live Buy Box and market average for an ASIN.

    Args:
        asin: The Amazon ASIN.
        our_price: Our current/proposed landed selling price.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns a dict with our_price, buy_box_price, market_average, and a verdict
    ("above_buy_box" / "at_buy_box" / "below_buy_box" / "no_buy_box").
    """
    snap = await competitor_analysis(asin, marketplace_id)
    if snap.get("status") == "error":
        return snap
    # Verdict is derived locally from the same competitor snapshot — no separate endpoint.
    bb = snap.get("buy_box")
    verdict = "no_buy_box"
    if bb:
        if our_price > bb["price"]:
            verdict = "above_buy_box"
        elif abs(our_price - bb["price"]) < 0.01:
            verdict = "at_buy_box"
        else:
            verdict = "below_buy_box"
    return {
        "asin": asin,
        "our_price": our_price,
        "buy_box_price": bb["price"] if bb else None,
        "market_average": snap.get("market_average"),
        "lowest_price": snap.get("lowest_price"),
        "number_of_offers": snap.get("number_of_offers"),
        "verdict": verdict,
    }
