from src.database.connection import async_session
from src.database.repository import ErpRepository


async def get_purchase_cost(osp_id: int) -> dict:
    """
    Return the purchase/printing cost of an OSP (OnlineSellingProduct) with its per-saleable
    breakdown, using the ERP's 3-tier cost logic (recent BTB PO -> older PO -> JUP+cover ->
    previous edition), summed as cost x quantity x MOQ.

    Use this when the user just wants the purchase/printing cost of a product (no marketplace,
    fee or profit analysis needed).

    Args:
        osp_id: The internal OnlineSellingProduct id.

    Returns:
        {"osp_id": int, "total": float, "moq": float,
         "items": [{"label": "BTB - Feb2023(V HINDI WB)", "unit_cost": 31.17,
                    "quantity": 1, "line_cost": 31.17}, ...]}
        `total` is 0.0 with an empty `items` list if the OSP has no current combination.
    """
    try:
        async with async_session() as session:
            breakdown = await ErpRepository(session).get_purchase_cost_breakdown_for_osp(osp_id)
            breakdown["osp_id"] = osp_id
            return breakdown
    except Exception as e:
        return {"status": "error", "message": f"Error fetching purchase cost: {e}"}
