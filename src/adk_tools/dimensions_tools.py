"""Fetch package weight + dimensions for an ASIN from the Amazon catalog (read-only)."""
from src.services.sp_api_factory import build_sp_api
from src.services.amazon_sp_api_service import SpApiWriteOperationBlocked

_WEIGHT_TO_GRAMS = {"grams": 1.0, "gram": 1.0, "g": 1.0, "kilograms": 1000.0, "kilogram": 1000.0,
                    "kg": 1000.0, "pounds": 453.592, "pound": 453.592, "lb": 453.592,
                    "ounces": 28.3495, "ounce": 28.3495, "oz": 28.3495}
_LENGTH_TO_CM = {"millimeters": 0.1, "millimeter": 0.1, "mm": 0.1, "centimeters": 1.0,
                 "centimeter": 1.0, "cm": 1.0, "meters": 100.0, "meter": 100.0, "m": 100.0,
                 "inches": 2.54, "inch": 2.54, "in": 2.54, "feet": 30.48, "foot": 30.48}


def _to_grams(entry: dict):
    if not entry:
        return None
    return round(float(entry.get("value", 0)) * _WEIGHT_TO_GRAMS.get((entry.get("unit") or "").lower(), 1.0), 2)


def _to_cm(dim: dict):
    if not dim or dim.get("value") is None:
        return None
    return round(float(dim["value"]) * _LENGTH_TO_CM.get((dim.get("unit") or "").lower(), 1.0), 2)


async def get_package_dimensions(asin: str, marketplace_id: int = 1) -> dict:
    """
    Fetch the package weight (grams) and length/width/height (cm) for an Amazon ASIN from the
    catalog, so pricing/recommendation tools don't have to ask the user. Prefers package
    weight/dimensions, falls back to item weight/dimensions. Units are normalized to g / cm.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns {"asin","weight","length","width","height","source"} or a status="error"/"not_found".
    Call this before recommend_optimal_price / analyze_listing when weight/dimensions are unknown.
    """
    try:
        svc, amazon_marketplace_id = await build_sp_api(marketplace_id)
        attrs = (await svc.get_catalog_item(asin, amazon_marketplace_id)).get("attributes", {})

        for wkey, dkey, source in (("item_package_weight", "item_package_dimensions", "package"),
                                   ("item_weight", "item_dimensions", "item")):
            w = (attrs.get(wkey) or [None])[0]
            d = (attrs.get(dkey) or [None])[0]
            weight = _to_grams(w)
            length = _to_cm((d or {}).get("length"))
            width = _to_cm((d or {}).get("width"))
            height = _to_cm((d or {}).get("height"))
            if weight or (length and width and height):
                return {"asin": asin, "weight": weight, "length": length, "width": width,
                        "height": height, "source": f"amazon_catalog_{source}"}

        return {"status": "not_found", "asin": asin,
                "message": "No weight/dimensions on the Amazon catalog; ask the user to provide them."}
    except SpApiWriteOperationBlocked:
        raise
    except Exception as e:
        return {"status": "error", "message": f"Dimension lookup failed for {asin}: {e}"}
