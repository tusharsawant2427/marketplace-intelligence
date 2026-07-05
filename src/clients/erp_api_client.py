"""
HTTP consumer for the Laravel ERP Intelligence API (see docs/12-erp-api-contract.md).

This is the ONLY thing the ADK uses to reach ERP data or Amazon. It holds no DB connection and no
Seller Central credentials — only a base URL and a read-only service token. Every call is a GET to
an allow-listed, ERP-owned endpoint, so the (prompt-injectable) agent can read-to-analyse but can
never reach in and mutate.

Configure with env:
  ERP_API_BASE_URL   e.g. https://erp.internal/api/intelligence
  ERP_API_TOKEN      read-only service bearer token
"""
import os
import httpx

DEFAULT_TIMEOUT = 30.0


class ErpApiError(Exception):
    """Raised when the ERP API returns a non-2xx response or is unreachable."""


def _clean(d: dict) -> dict:
    """Drop None values so optional params are omitted (ERP: omit → default / null)."""
    return {k: v for k, v in d.items() if v is not None}


class ErpApiClient:
    def __init__(self, base_url: str = None, token: str = None, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = (base_url or os.getenv("ERP_API_BASE_URL", "")).rstrip("/")
        self.token = token or os.getenv("ERP_API_TOKEN", "")
        self.timeout = timeout
        if not self.base_url:
            raise ErpApiError("ERP_API_BASE_URL is not configured.")

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _get(self, path: str, params: dict = None):
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._headers(),
                                        params={k: v for k, v in (params or {}).items() if v is not None})
        except httpx.HTTPError as e:
            raise ErpApiError(f"ERP API unreachable ({url}): {e}") from e
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                detail = resp.text[:200]
            raise ErpApiError(f"ERP API {resp.status_code} for {url}: {detail}")
        return resp.json()

    # ---- §1 purchase cost (computed) ----
    async def get_purchase_cost_breakdown(self, osp_id: int) -> dict:
        return await self._get(f"/osp/{osp_id}/purchase-cost") or {"total": 0.0, "moq": 1.0, "items": []}

    # ---- §2 LPA analysis (computed) ----
    async def get_lpa_analysis(self, osp_id: int, **params) -> dict:
        return await self._get(f"/osp/{osp_id}/lpa-analysis", params)

    # ---- §3 live buy-box (computed; Laravel proxies SP-API) ----
    async def get_buy_box(self, marketplace_id: int, asin: str) -> dict:
        return await self._get(f"/marketplaces/{marketplace_id}/buy-box", {"asin": asin})

    # ---- §4 pricing context + fee masters (raw) ----
    async def get_pricing_context(self, osp_id: int, marketplace_id: int, node_id: int,
                                  fulfillment_meta_id: int) -> dict:
        return await self._get(f"/osp/{osp_id}/pricing-context", {
            "marketplace_id": marketplace_id, "node_id": node_id,
            "fulfillment_meta_id": fulfillment_meta_id})

    # ---- §5 listing resolution (raw) ----
    async def find_listings_by_platform_unique_id(self, platform_unique_id: str) -> list[dict]:
        return await self._get("/listings", {"platform_unique_id": platform_unique_id}) or []

    async def get_listing(self, listing_id: int) -> dict | None:
        return await self._get(f"/listings/{listing_id}")

    async def get_listings_for_osp(self, osp_id: int) -> list[dict]:
        return await self._get(f"/osp/{osp_id}/listings") or []

    async def get_listing_marketplaces(self, listing_id: int) -> list[dict]:
        return await self._get(f"/listings/{listing_id}/marketplaces") or []

    # ---- §6 marketplace / fulfillment / category lookups (raw) ----
    async def get_marketplace_platform(self, marketplace_id: int) -> dict | None:
        return await self._get(f"/marketplaces/{marketplace_id}")

    async def get_fulfillment_options(self, marketplace_id: int) -> list[dict]:
        return await self._get(f"/marketplaces/{marketplace_id}/fulfillments") or []

    async def get_category_nodes_for_marketplace(self, marketplace_id: int) -> list[dict]:
        return await self._get(f"/marketplaces/{marketplace_id}/categories") or []

    async def get_supported_marketplaces(self) -> list[dict]:
        return await self._get("/marketplaces/supported") or []

    async def get_marketplace_for_fulfillment(self, fulfillment_meta_id: int) -> int | None:
        data = await self._get(f"/fulfillments/{fulfillment_meta_id}")
        return data.get("marketplace_id") if data else None

    # ---- §8 optional computed recommendation ----
    async def get_price_recommendation(self, osp_id: int, **params) -> dict:
        return await self._get(f"/osp/{osp_id}/recommend-price", params)

    # ================= PHASE 2 (docs/13) =================
    # ---------------- GROUP A: Amazon (Laravel proxies SP-API) ----------------

    async def buy_box_analysis(self, marketplace_id: int, asin: str,
                               our_price: float = None,
                               our_seller_id: str = None) -> dict:
        """A1 → GET /marketplaces/{mp}/buy-box-analysis"""
        return await self._get(
            f"/marketplaces/{marketplace_id}/buy-box-analysis",
            params=_clean({"asin": asin, "our_price": our_price,
                           "our_seller_id": our_seller_id}),
        )

    async def competitors(self, marketplace_id: int, asin: str) -> dict:
        """A2 → GET /marketplaces/{mp}/competitors"""
        return await self._get(f"/marketplaces/{marketplace_id}/competitors",
                               params={"asin": asin})

    async def dimensions(self, marketplace_id: int, asin: str) -> dict:
        """A3 → GET /marketplaces/{mp}/dimensions (grams/cm; {status:not_found} when absent)"""
        return await self._get(f"/marketplaces/{marketplace_id}/dimensions",
                               params={"asin": asin})

    async def catalog_content(self, marketplace_id: int, asin: str) -> dict:
        """A4 → GET /marketplaces/{mp}/catalog-content"""
        return await self._get(f"/marketplaces/{marketplace_id}/catalog-content",
                               params={"asin": asin})

    async def listing_health(self, marketplace_id: int, asin: str) -> dict:
        """A5 → GET /marketplaces/{mp}/listing-health (catalog checks + erp_state)"""
        return await self._get(f"/marketplaces/{marketplace_id}/listing-health",
                               params={"asin": asin})

    async def sync_check(self, marketplace_id: int, asin: str) -> dict:
        """A6 → GET /marketplaces/{mp}/sync-check (404 when no ERP listing for ASIN)"""
        return await self._get(f"/marketplaces/{marketplace_id}/sync-check",
                               params={"asin": asin})

    # ---------------- GROUP B: Analytics / reporting (raw ERP → computed) -----

    async def dashboard(self, days: int = 30) -> dict:
        """B1 → GET /analytics/dashboard"""
        return await self._get("/analytics/dashboard", params={"days": days})

    async def morning_briefing(self, days: int = 7) -> dict:
        """B2 → GET /analytics/morning-briefing"""
        return await self._get("/analytics/morning-briefing", params={"days": days})

    async def growth_opportunities(self) -> dict:
        """B3 → GET /analytics/growth-opportunities"""
        return await self._get("/analytics/growth-opportunities")

    async def reorder_alerts(self, limit: int = 20) -> dict:
        """B4 → GET /inventory/reorder-alerts"""
        return await self._get("/inventory/reorder-alerts", params={"limit": limit})

    async def stock_for_osp(self, osp_id: int) -> dict:
        """B5 → GET /osp/{osp}/stock"""
        return await self._get(f"/osp/{osp_id}/stock")

    async def movers(self, days: int = 30, direction: str = "fast",
                     limit: int = 10) -> dict:
        """B6 → GET /inventory/movers (direction: fast|slow)"""
        return await self._get("/inventory/movers",
                               params={"days": days, "direction": direction, "limit": limit})

    async def sales_trend(self, months: int = 6) -> dict:
        """B7 → GET /analytics/sales-trend"""
        return await self._get("/analytics/sales-trend", params={"months": months})

    async def product_performance(self, direction: str = "top", days: int = 90,
                                  limit: int = 10) -> dict:
        """B8 → GET /analytics/product-performance (direction: top|slow)"""
        return await self._get("/analytics/product-performance",
                               params={"direction": direction, "days": days, "limit": limit})

    async def best_categories(self, days: int = 90, limit: int = 10) -> dict:
        """B9 → GET /analytics/best-categories"""
        return await self._get("/analytics/best-categories",
                               params={"days": days, "limit": limit})

    async def seasonal_pattern(self, category: str = None,
                               title_id: int = None) -> dict:
        """B10 → GET /analytics/seasonal-pattern"""
        return await self._get("/analytics/seasonal-pattern",
                               params=_clean({"category": category, "title_id": title_id}))

    async def profit_drivers(self, osp_id: int, marketplace_id: int,
                             node_id: int = None) -> dict:
        """B11 → GET /osp/{osp}/profit-drivers"""
        return await self._get(f"/osp/{osp_id}/profit-drivers",
                               params=_clean({"marketplace_id": marketplace_id,
                                              "node_id": node_id}))

    async def rule_inputs(self, osp_id: int, marketplace_id: int = None) -> dict:
        """B12 → GET /osp/{osp}/rule-inputs (minimum_listing_price null when mp omitted)"""
        return await self._get(f"/osp/{osp_id}/rule-inputs",
                               params=_clean({"marketplace_id": marketplace_id}))
