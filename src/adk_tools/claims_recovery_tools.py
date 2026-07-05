"""Claims recovery / FBA reimbursement tools (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def claims_recovery_analysis(days: int = 90, marketplace_id: int = 1) -> dict:
    """
    Find FBA reimbursement money: units Amazon lost/damaged/destroyed that were never reimbursed
    (recoverable — you can still file a claim), plus reimbursements Amazon has already credited. Use
    for 'am I owed money by Amazon', 'FBA reimbursements', 'lost/damaged inventory claims',
    'reimbursement opportunities', 'money to recover'.

    Args:
        days: trailing window to scan (default 90).
        marketplace_id: internal marketplace id (default 1 = Amazon-India).

    Returns {"window_days","since","currency","summary":{already_reimbursed,estimated_recoverable,
             open_case_count,reimbursed_case_count},"recoverable_opportunities":[...],
             "reimbursements_received":[...]}.
    """
    try:
        # Passthrough: Laravel proxies Finances + Reports SP-API and returns the reconciled shape.
        result = await ErpApiClient().claims_recovery(marketplace_id, days)
        if not result:  # 404 = endpoint not deployed yet (ErpApiClient returns None on 404)
            return {"status": "unavailable",
                    "message": "Claims recovery endpoint is not available on the ERP yet "
                               "(GET /marketplaces/{mp}/claims-recovery). See docs/15."}
        return result
    except ErpApiError as e:
        return {"status": "error", "message": f"Claims recovery analysis failed: {e}"}
