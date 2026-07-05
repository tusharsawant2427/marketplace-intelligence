"""Buy Box Intelligence tools — who owns it, what wins it, why we're losing it (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


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
        # Passthrough: Laravel proxies SP-API and computes reasons_not_winning / price_to_win.
        return await ErpApiClient().buy_box_analysis(marketplace_id, asin, our_price, our_seller_id)
    except ErpApiError as e:
        return {"status": "error", "message": f"Buy Box analysis failed for {asin}: {e}"}
