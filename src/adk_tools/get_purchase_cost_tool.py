from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def get_purchase_cost(osp_id: int) -> dict:
    """
    Return the purchase/printing cost of an OSP (OnlineSellingProduct) with its per-saleable
    breakdown, computed by the ERP (3-tier cost logic, summed as cost x quantity x MOQ).

    Use this when the user just wants the purchase/printing cost of a product (no marketplace,
    fee or profit analysis needed).

    Args:
        osp_id: The internal OnlineSellingProduct id.

    Returns:
        {"osp_id": int, "total": float, "moq": float,
         "items": [{"label": "BTB - Feb2023(V HINDI WB)", "unit_cost": 31.17,
                    "quantity": 1, "line_cost": 31.17}, ...]}
    """
    try:
        data = await ErpApiClient().get_purchase_cost_breakdown(osp_id)
        data.setdefault("osp_id", osp_id)
        return data
    except ErpApiError as e:
        return {"status": "error", "message": str(e)}
