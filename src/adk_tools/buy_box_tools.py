"""Buy Box Intelligence tools — who owns it, what wins it, why we're losing it (read-only SP-API)."""
from src.services.sp_api_factory import build_sp_api
from src.services.amazon_sp_api_service import SpApiWriteOperationBlocked


def _landed(o: dict) -> float:
    return round(float(o.get("ListingPrice", {}).get("Amount", 0.0)) + float(o.get("Shipping", {}).get("Amount", 0.0)), 2)


async def buy_box_analysis(asin: str, our_price: float = None, our_seller_id: str = None,
                           marketplace_id: int = 1) -> dict:
    """
    Live Buy Box analysis for an Amazon ASIN: who owns it, the winning price, our position, the price
    that would win it, and likely reasons we're not winning. Use for 'why did I lose the buy box',
    'buy box price', 'what price wins the buy box'.

    Args:
        asin: The Amazon ASIN.
        our_price: our current landed price (optional — helps explain why we're losing).
        our_seller_id: our Amazon seller id (optional — to locate our offer among the offers).
        marketplace_id: internal marketplace id (default 1 = Amazon-India).

    Returns {"asin","has_buy_box","buy_box":{price,seller_id,is_prime,feedback_pct},
             "our_offer":{...}|None,"price_to_win","reasons_not_winning":[...]}.
    """
    try:
        svc, amazon_marketplace_id = await build_sp_api(marketplace_id)
        payload = (await svc.get_item_offers(asin, amazon_marketplace_id)).get("payload", {})
        offers = payload.get("Offers", [])
        bb = next((o for o in offers if o.get("IsBuyBoxWinner")), None)
        ours = next((o for o in offers if our_seller_id and o.get("SellerId") == our_seller_id), None)

        result = {"asin": asin, "has_buy_box": bool(bb)}
        if bb:
            bb_price = _landed(bb)
            result["buy_box"] = {
                "price": bb_price, "seller_id": bb.get("SellerId"),
                "is_prime": bb.get("PrimeInformation", {}).get("IsPrime", False),
                "feedback_pct": bb.get("SellerFeedbackRating", {}).get("SellerPositiveFeedbackRating"),
            }
            # Price is the main lever: to compete, match (or just beat) the buy-box landed price.
            result["price_to_win"] = bb_price
            reasons = []
            ref_price = our_price if our_price is not None else (_landed(ours) if ours else None)
            if ref_price is not None and ref_price > bb_price:
                reasons.append(f"Your price {ref_price} is above the buy-box price {bb_price}.")
            if ours is not None:
                if not ours.get("PrimeInformation", {}).get("IsPrime") and result["buy_box"]["is_prime"]:
                    reasons.append("The buy-box winner offers Prime; your offer does not.")
                if ours.get("IsBuyBoxWinner"):
                    reasons = ["You currently own the buy box."]
            result["reasons_not_winning"] = reasons or [
                "Your price is competitive; remaining factors (fulfillment, seller feedback, stock) decide it."]
        if ours is not None:
            result["our_offer"] = {"price": _landed(ours), "is_buy_box": ours.get("IsBuyBoxWinner", False),
                                   "is_prime": ours.get("PrimeInformation", {}).get("IsPrime", False)}
        return result
    except SpApiWriteOperationBlocked:
        raise
    except Exception as e:
        return {"status": "error", "message": f"Buy Box analysis failed for {asin}: {e}"}
