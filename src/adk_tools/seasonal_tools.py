"""Seasonal Intelligence tools — calendar-month demand patterns from multi-year sales history (via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def seasonal_pattern(category: str = None, title_id: int = None) -> dict:
    """
    Demand seasonality by calendar month across the sales history — which months peak (festival,
    exam, back-to-school). Use for 'when should inventory increase', 'exam/festival/holiday demand',
    'seasonal trend', 'back-to-school'.

    Args:
        category: optional course/sales-group filter (e.g. 'XII', 'MHT-CET').
        title_id: optional specific title to analyse.

    Returns {"scope","by_month":[{month,units,avg_per_year}],"peak_months":[...]}.
    """
    try:
        return await ErpApiClient().seasonal_pattern(category, title_id)  # Laravel returns finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Seasonal analysis failed: {e}"}
