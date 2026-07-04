"""Pricing what-if — simulate a price change and compare profit/margin (ERP LPA)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError
from src.adk_tools.dimensions_tools import get_package_dimensions


def _best(rows):
    return max(rows, key=lambda r: r.get("gross_profit", 0)) if rows else None


async def price_what_if(osp_id: int, marketplace_id: int, node_id: int, current_price: float,
                        delta: float, asin: str = None, weight: float = None, length: float = None,
                        width: float = None, height: float = None) -> dict:
    """
    Simulate changing the listing price by `delta` and compare profit/margin before vs after. Use
    for 'what if I increase/decrease price by ₹X', 'margin simulation'. Weight/dimensions auto-fetch
    from the catalog when `asin` is given.

    Args:
        osp_id, marketplace_id, node_id: resolved identifiers.
        current_price: the current listing price.
        delta: change to apply (e.g. +20 or -15).
        asin: used to auto-fetch weight/dimensions.

    Returns {"before":{price,best_fulfillment,gross_profit,profit_pct},
             "after":{...},"change":{price_delta,gross_profit_delta,profit_pct_delta}}.
    """
    try:
        if None in (weight, length, width, height) and asin:
            d = await get_package_dimensions(asin, marketplace_id)
            if d.get("status") not in ("error", "not_found"):
                weight, length, width, height = d.get("weight"), d.get("length"), d.get("width"), d.get("height")
        if None in (weight, length, width, height):
            return {"status": "need_input", "message": "Weight/dimensions required and not fetchable."}

        client = ErpApiClient()
        common = dict(marketplace_id=marketplace_id, node_id=node_id, weight=weight, length=length,
                      width=width, height=height, step_level=2, advertisement_charge_pct=10)
        before = _best((await client.get_lpa_analysis(osp_id, listing_price=current_price, **common)).get("rows", []))
        after = _best((await client.get_lpa_analysis(osp_id, listing_price=current_price + delta, **common)).get("rows", []))
        if not before or not after:
            return {"status": "error", "message": "LPA returned no rows for the simulation."}

        def summarize(price, row):
            return {"price": price, "best_fulfillment": row.get("fulfillment_type"),
                    "selling_zone": row.get("selling_zone"), "gross_profit": row.get("gross_profit"),
                    "profit_pct": row.get("profit_pct")}

        b = summarize(current_price, before)
        a = summarize(current_price + delta, after)
        return {
            "before": b, "after": a,
            "change": {
                "price_delta": delta,
                "gross_profit_delta": round(a["gross_profit"] - b["gross_profit"], 2),
                "profit_pct_delta": round(a["profit_pct"] - b["profit_pct"], 2),
            },
        }
    except ErpApiError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Price simulation failed: {e}"}
