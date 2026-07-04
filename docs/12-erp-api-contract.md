# ERP Intelligence API Contract (Laravel ⇢ ADK)

**Purpose.** The ADK agent must be a *pure consumer*. It holds **no** MySQL connection and **no**
Amazon Seller Central credentials. The Laravel ERP exposes the endpoints below; the ADK calls them
over HTTP only. This isolates all secrets and business logic on the ERP side and keeps the
(prompt-injectable) LLM in a read-only, allow-listed trust boundary.

## Conventions

- **Base URL:** `ERP_API_BASE_URL` (e.g. `https://staging.targeterp.in/api/intelligence`).
- **Auth:** `Authorization: Bearer <ERP_API_TOKEN>` — a service token scoped to read-only
  intelligence endpoints. The ADK never receives DB or SP-API credentials.
- **Method:** all endpoints are `GET` (read-only). No endpoint here may mutate a listing, price,
  or any ERP record. The one legitimate write in the old design (SP-API token refresh) stays
  **inside** Laravel and is never exposed.
- **Money/quantities:** JSON numbers (INR). **Dates/now:** server-side `now` on the ERP.
- **Errors:** non-2xx returns `{"error": {"code": "...", "message": "..."}}`. `404` = not found.
- **Compute location:** _computed_ = Laravel runs its existing logic (`LpaCalculation`,
  `initialPurchasePrice`, SP-API). _raw_ = Laravel returns stored data the ADK reasons over.

---

## 1. Purchase cost — *computed*  → consumed by `get_purchase_cost`

`GET /osp/{osp_id}/purchase-cost`

```json
{
  "osp_id": 5,
  "total": 80.37,
  "moq": 1,
  "items": [
    {"label": "BTB - Feb2023(V HINDI WB)",   "unit_cost": 31.17, "quantity": 1, "line_cost": 31.17},
    {"label": "BTB - Feb2025(V HINDI NOTES)","unit_cost": 49.20, "quantity": 1, "line_cost": 49.20}
  ]
}
```
Laravel uses `EditionProductType::initialPurchasePrice()` × quantity × MOQ. `total: 0` with empty
`items` if the OSP has no current combination.

## 2. Listing Price Analysis (LPA) — *computed*  → consumed by `analyze_listing`

`GET /osp/{osp_id}/lpa-analysis`

Query: `marketplace_id`, `node_id`, `listing_price`, `weight`, `length`, `width`, `height`
(cm/g), optional `marketplace_mrp`, `advertisement_charge_pct`, `listing_price_discount`,
`local_delivery_charge`, `regional_delivery_charge`, `national_delivery_charge`, `step_level`.

```json
{
  "header": {
    "listing_name": "Std. 5th ... Combo (MH Board)", "osp_id": 5, "platform": "Amazon",
    "marketplace_id": 1, "node_id": 8, "node_name": "Educational book", "step_level": "ADVANCED",
    "saleable_mrp": 250, "marketplace_mrp": 280, "listing_price": 280,
    "weight": 485, "length": 28, "width": 20.4, "height": 1.3,
    "purchase_cost": 80.37, "no_of_item": 2, "advertisement_charge_pct": 10
  },
  "rows": [
    {"fulfillment_type": "FBA", "selling_zone": "Local", "commission": 0, "fulfillment_fees": 0,
     "fixed_fee": 0, "collection_fee": 13, "storage_fee": 0.87, "pick_pack": 17,
     "net_platform_fee": 36.43, "sales_gst": 0, "purchase_cost": 80.37, "purchase_gst": 9.64,
     "transport_cost": 5.09, "packaging_cost": 10, "advertisement_cost": 29.5, "royalty_amount": 0,
     "discount_amount": 0, "gross_profit": 108.97, "profit_pct": 43.59, "profit_per_item": 54.49}
  ]
}
```
This is Laravel's native `LpaCalculation` fanned out over fulfillment × zone — the authoritative
numbers (removes the ADK's ported copy).

## 3. Live buy-box — *computed* (Laravel proxies SP-API)  → consumed by `recommend_optimal_price`

`GET /marketplaces/{marketplace_id}/buy-box?asin={asin}`

```json
{"asin": "B07Q46XQQC", "buy_box_price": 699.0, "currency": "INR", "competitor_count": 4,
 "has_live_integration": true}
```
Laravel owns the SP-API credentials and enforces the read-only call. `has_live_integration: false`
for non-Amazon marketplaces (then `buy_box_price: null`).

## 4. Pricing context (fees + costs) — *raw*  → consumed by `recommend_optimal_price` engine

`GET /osp/{osp_id}/pricing-context?marketplace_id=&node_id=&fulfillment_meta_id=`

```json
{
  "mrp": 250, "saleable_mrp": 250, "weight_grams": 485, "sale_gst_percentage": 0,
  "purchase_cost": 80.37, "packaging_cost": 10, "transport_per_kg_rate": 10.5,
  "advertisement_percentage": 10, "royalty_percentage": 0,
  "fee_masters": {
    "referral_fees":   [{"min_value": 251, "max_value": 500, "fee_percentage": 4.0}],
    "closing_fees":    [{"min_value": 251, "max_value": 500, "fee": 20.0}],
    "weight_handling_fees": [{"zone": "LOCAL", "min_weight_slab": 1, "max_weight_slab": 500,
                              "weight_slab_step": 500, "fee": 22.0}]
  }
}
```
Feeds the ADK's bounded-search recommendation engine. (If Laravel prefers, it can instead expose a
computed `/recommend-price` and the ADK drops its search — see §8.)

## 5. Listing resolution — *raw*  → consumed by `resolve_pricing_context`

- `GET /listings?platform_unique_id={asin}` → list (may span platforms)
  ```json
  [{"listing_id": 3337, "osp_id": 5, "platform_id": 1, "platform_name": "Amazon",
    "platform_unique_id": "B07Q46XQQC", "state": "UPLOADED"}]
  ```
- `GET /listings/{listing_id}` → single object (same shape) or `404`.
- `GET /osp/{osp_id}/listings` → all listings for an OSP (each with `has_live_pricing`).
- `GET /listings/{listing_id}/marketplaces` →
  ```json
  [{"marketplace_id": 1, "marketplace_name": "Amazon-India", "platform_id": 1,
    "node_id": 8, "node_name": "Educational book", "state": "ACTIVE"}]
  ```
  (One row per marketplace, ACTIVE preferred.)

## 6. Marketplace / fulfillment / category lookups — *raw*  → `resolve_pricing_context`

- `GET /marketplaces/{marketplace_id}` →
  `{"marketplace_id":1,"marketplace_name":"Amazon-India","platform_id":1,"platform_name":"Amazon","has_live_pricing":true}`
- `GET /marketplaces/{marketplace_id}/fulfillments` →
  `[{"fulfillment_meta_id":1,"fulfillment_type":"FBA"}, ...]`
- `GET /marketplaces/{marketplace_id}/categories` →
  `[{"node_id":8,"node_name":"Educational book"}, ...]` (pre-listing category picker)
- `GET /marketplaces/supported` → marketplaces the ERP can price (have fee masters), each with
  `has_live_pricing`.
- `GET /fulfillments/{fulfillment_meta_id}` → `{"fulfillment_meta_id":1,"marketplace_id":1}`
  (back-track fulfillment → marketplace).

## 7. Amazon marketplace id mapping — *raw* (optional)

If Laravel owns the SP-API call (§3), the ADK never needs Amazon's `A21TJRUUN4KGV` string, so this
can be omitted. Kept here only if the ADK must pass it: `GET /marketplaces/{id}/amazon-id →
{"amazon_marketplace_id":"A21TJRUUN4KGV"}`.

## 8. (Optional) computed recommendation — *computed*

If Laravel exposes `GET /osp/{osp_id}/recommend-price?...&target_margin_percentage=` returning the
optimal price + the LPA breakdown, the ADK deletes its bounded-search engine entirely and just
consumes the result. Otherwise the ADK keeps the search using §3 + §4.

---

## ADK tool → endpoint map

| ADK tool | Endpoints | Type |
|---|---|---|
| `get_purchase_cost` | §1 | computed |
| `analyze_listing` | §2 | computed |
| `recommend_optimal_price` | §3 + §4 (or §8) | computed + raw |
| `resolve_pricing_context` | §5, §6 | raw |

## What the ADK deletes once these are live
`src/database/*` (MySQL), `src/services/amazon_sp_api_service.py`,
`src/services/amazon_marketplace.py`, and — if §2/§8 are provided — the ported
`src/services/pricing/*` and `listing_analysis.py`. Replaced by a single `ErpApiClient`.
