"""Competitor Intelligence tools — live Amazon offers/competitive pricing (read-only)."""
from statistics import mean
from src.services.sp_api_factory import build_sp_api
from src.services.amazon_sp_api_service import SpApiWriteOperationBlocked


def _landed(offer: dict) -> float:
    return float(offer.get("ListingPrice", {}).get("Amount", 0.0)) + float(offer.get("Shipping", {}).get("Amount", 0.0))


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
        svc, amazon_marketplace_id = await build_sp_api(marketplace_id)
        payload = (await svc.get_item_offers(asin, amazon_marketplace_id)).get("payload", {})
        offers = payload.get("Offers", [])
        summary = payload.get("Summary", {})

        competitors = [{
            "seller_id": o.get("SellerId"),
            "landed_price": round(_landed(o), 2),
            "is_prime": o.get("PrimeInformation", {}).get("IsPrime", False),
            "is_buy_box": o.get("IsBuyBoxWinner", False),
            "feedback_pct": o.get("SellerFeedbackRating", {}).get("SellerPositiveFeedbackRating"),
        } for o in offers]
        prices = sorted(c["landed_price"] for c in competitors) or [None]
        bb = next((c for c in competitors if c["is_buy_box"]), None)
        ranks = summary.get("SalesRankings", [])

        return {
            "asin": asin,
            "number_of_offers": summary.get("TotalOfferCount", len(offers)),
            "buy_box": {"price": bb["landed_price"], "seller_id": bb["seller_id"], "is_prime": bb["is_prime"]} if bb else None,
            "lowest_price": prices[0],
            "highest_price": prices[-1],
            "market_average": round(mean([c["landed_price"] for c in competitors]), 2) if competitors else None,
            "sales_rank": ranks[0].get("Rank") if ranks else None,
            "competitors": competitors,
        }
    except SpApiWriteOperationBlocked:
        raise
    except Exception as e:
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
