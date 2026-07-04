import httpx
from typing import Optional
from dataclasses import dataclass


@dataclass
class SpApiPricingData:
    asin: str
    buy_box_price: Optional[float]
    buy_box_currency: str
    is_buy_box_winner: bool
    competitor_count: int


@dataclass
class SpApiListingStatus:
    asin: str
    status: str
    is_suppressed: bool
    suppression_reasons: list[str]


class SpApiWriteOperationBlocked(PermissionError):
    """
    Raised when code attempts a mutating (write) call against Amazon SP-API.

    This service is intentionally read-only: the Listing Intelligence Center analyses
    listings but must never modify them on Amazon. Any attempt to issue a non-GET
    request (create/update/delete a listing, patch a price, submit a feed, etc.) is
    blocked here and surfaced loudly instead of being silently swallowed.
    """


class AmazonSpApiService:
    """
    Read-only client for Amazon SP-API.

    GUARDRAIL: this service can only READ from Amazon (analysis). It can never modify a
    listing. Enforcement lives in `_request`, the single choke point every HTTP call must
    pass through:
      - Only the GET method is permitted. Every SP-API operation that changes a listing
        (PUT/PATCH/POST/DELETE on listings, pricing, feeds, ...) is therefore blocked.
      - The target path must match a read-only allowlist as defense-in-depth.
    A violation raises `SpApiWriteOperationBlocked` and is NOT caught by the analysis
    fallbacks below, so it can never be masked as a "normal" failure.
    """

    # The only HTTP method this service is ever allowed to use.
    ALLOWED_HTTP_METHODS = frozenset({"GET"})

    # Read-only endpoints this service is permitted to reach (defense-in-depth on top of
    # the GET-only rule). Add new *read* endpoints here as analysis needs grow.
    READ_ONLY_PATH_PREFIXES = (
        "/products/pricing/",            # competitive pricing / offers (read)
        "/products/fees/",               # fees estimate (read)
        "/catalog/",                     # catalog items (read)
        "/catalogitems/",                # catalog items (legacy path, read)
        "/listings/2021-08-01/items/",   # getListingsItem (read); writes blocked by method guard
    )

    def __init__(self, credentials: dict):
        self.access_token = credentials.get("access_token")
        self.base_url = "https://sellingpartnerapi-eu.amazon.com"

    def _get_headers(self) -> dict:
        return {
            "x-amz-access-token": self.access_token,
            "Content-Type": "application/json",
        }

    def _assert_read_only(self, method: str, path: str) -> None:
        """Hard guardrail: allow only read (GET) calls to allowlisted analysis endpoints."""
        normalized = method.upper()
        if normalized not in self.ALLOWED_HTTP_METHODS:
            raise SpApiWriteOperationBlocked(
                f"Blocked {normalized} {path}: this service is read-only and may not modify "
                f"Amazon listings. Only {sorted(self.ALLOWED_HTTP_METHODS)} is permitted."
            )
        if not any(path.startswith(prefix) for prefix in self.READ_ONLY_PATH_PREFIXES):
            raise SpApiWriteOperationBlocked(
                f"Blocked GET {path}: path is not on the read-only allowlist "
                f"{list(self.READ_ONLY_PATH_PREFIXES)}."
            )

    async def _request(self, method: str, path: str, params: Optional[dict] = None) -> httpx.Response:
        """Single choke point for all SP-API traffic. Enforces the read-only guardrail."""
        self._assert_read_only(method, path)  # raises SpApiWriteOperationBlocked on violation
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method.upper(), url, headers=self._get_headers(), params=params
            )
            response.raise_for_status()
            return response

    async def get_live_pricing(self, asin: str, marketplace_id: str) -> SpApiPricingData:
        """
        Calls the Catalog Items / Pricing API to fetch live Buy Box data.
        """
        if not self.access_token:
            # Fallback mock if token is invalid or missing
            return SpApiPricingData(asin, 700.0, "INR", False, 3)

        path = f"/products/pricing/v0/items/{asin}/offers"
        params = {"MarketplaceId": marketplace_id, "ItemCondition": "New"}

        try:
            response = await self._request("GET", path, params=params)
            data = response.json()

            # Parse Buy Box (Simplified for production readiness example)
            offers = data.get("payload", {}).get("Offers", [])
            buy_box = next((o for o in offers if o.get("IsBuyBoxWinner")), None)

            buy_box_price = buy_box["ListingPrice"]["Amount"] if buy_box else None
            currency = buy_box["ListingPrice"]["CurrencyCode"] if buy_box else "INR"

            return SpApiPricingData(
                asin=asin,
                buy_box_price=buy_box_price,
                buy_box_currency=currency,
                is_buy_box_winner=False,  # Would be checked against seller_id
                competitor_count=len(offers),
            )
        except SpApiWriteOperationBlocked:
            # Never mask a guardrail violation as a normal analysis failure.
            raise
        except Exception as e:
            # Fallback on failure to prevent entire analysis from failing
            print(f"SP-API Pricing Error for {asin}: {e}")
            return SpApiPricingData(asin, 700.0, "INR", False, 3)

    # ---- Read-only detail endpoints (Catalog, Listings issues, Competitive Pricing) ----

    async def get_catalog_item(self, asin: str, marketplace_id: str,
                               included_data: str = "attributes,images,summaries,identifiers,productTypes,salesRanks") -> dict:
        """Catalog Items API: attributes, images, summaries, identifiers for an ASIN (read)."""
        path = f"/catalog/2022-04-01/items/{asin}"
        params = {"marketplaceIds": marketplace_id, "includedData": included_data}
        resp = await self._request("GET", path, params=params)
        return resp.json()

    async def get_item_offers(self, asin: str, marketplace_id: str, condition: str = "New") -> dict:
        """Pricing API: all current offers for an ASIN (read) — buy-box, competitor prices/sellers."""
        path = f"/products/pricing/v0/items/{asin}/offers"
        params = {"MarketplaceId": marketplace_id, "ItemCondition": condition}
        resp = await self._request("GET", path, params=params)
        return resp.json()

    async def get_competitive_pricing(self, asin: str, marketplace_id: str) -> dict:
        """Pricing API: competitive price summary (buy-box + lowest prices) for an ASIN (read)."""
        path = "/products/pricing/v0/competitivePrice"
        params = {"MarketplaceId": marketplace_id, "Asins": asin, "ItemType": "Asin"}
        resp = await self._request("GET", path, params=params)
        return resp.json()

    async def get_listings_item(self, seller_id: str, sku: str, marketplace_id: str,
                                included_data: str = "issues,summaries,attributes") -> dict:
        """Listings Items API: a seller's own listing incl. issues[] (suppression/errors) (read)."""
        path = f"/listings/2021-08-01/items/{seller_id}/{sku}"
        params = {"marketplaceIds": marketplace_id, "includedData": included_data}
        resp = await self._request("GET", path, params=params)
        return resp.json()

    async def get_listing_status(self, asin: str, seller_id: str, marketplace_id: str) -> SpApiListingStatus:
        """
        Calls the ListingsItem API to fetch current status.
        """
        if not self.access_token:
            return SpApiListingStatus(asin, "ACTIVE", False, [])

        path = f"/listings/2021-08-01/items/{seller_id}/{asin}"
        params = {"marketplaceIds": marketplace_id}

        try:
            response = await self._request("GET", path, params=params)
            data = response.json()

            issues = data.get("issues", [])
            suppressions = [iss for iss in issues if iss.get("severity") == "ERROR"]

            return SpApiListingStatus(
                asin=asin,
                status="ACTIVE" if not suppressions else "SUPPRESSED",
                is_suppressed=len(suppressions) > 0,
                suppression_reasons=[iss.get("message") for iss in suppressions],
            )
        except SpApiWriteOperationBlocked:
            raise
        except Exception as e:
            print(f"SP-API Listing Status Error for {asin}: {e}")
            return SpApiListingStatus(asin, "ACTIVE", False, [])
