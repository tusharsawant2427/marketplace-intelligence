# Marketplace Intelligence Agent - Context Handover

This document summarizes the current state, architecture, and business logic of the Marketplace Intelligence Agent (Listing Intelligence Center) to allow seamless continuation of development.

## 1. Project Vision & Architecture
**Goal:** Build a "Listing Intelligence Center" (LIC) that integrates with the existing Laravel-based `pulse_erp` system. The ERP owns business operations, while the LIC owns business intelligence.
**Core Principle:** Every pricing recommendation must be completely deterministic, explainable, and trace back to exact fees and margins.

**Tech Stack:**
- **Language:** Python 3.12
- **Frameworks:** FastAPI (Web Server), SQLAlchemy/aiomysql (Async Database), Google ADK (Agentic Development Kit)
- **AI Model:** Google Gemini (gemini-2.5-flash)

## 2. Directory Structure
```text
marketplace-intelligence-agent/
├── .env                        # Credentials (DB, GEMINI_API_KEY, AWS_SP_CLIENT_ID/SECRET)
├── server.py                   # FastAPI entrypoint (port 8001)
├── pricing_agent/
│   └── agent.py                # Google ADK agent and tool definitions
└── src/
    ├── api/
    │   └── routes.py           # FastAPI endpoints (e.g. /api/v1/recommend-price)
    ├── database/
    │   └── repository.py       # ErpRepository (Async SQL queries to pulse_erp DB)
    ├── domain/
    │   └── erp_pricing_context.py # Core Data Classes (PricingScenario, AmazonFeeMasters)
    ├── agents/
    │   └── pricing_recommendation_agent.py # Gemini Prompt Builder & LLM Execution
    ├── adk_tools/
    │   └── recommend_price_tool.py # Bridge between ADK Agent and Pricing Engine
    └── services/
        ├── lpa_calculator.py   # Deterministic Math (Fees, Break-Even, Margin)
        ├── amazon_sp_api_service.py # Interacts with live Amazon SP-API
        └── pricing/
            └── recommendation_engine.py # Bounded Search Engine for optimal pricing
```

## 3. Core Business Logic Implemented

### A. The Pricing Engine (Bounded Search)
Instead of guessing prices, we implemented a highly efficient Bounded Search Algorithm (`recommendation_engine.py`) that steps through price tiers. It evaluates exact Referral, Closing, and Weight Handling fees to find the precise optimal selling price required to hit a desired `target_margin_percentage`.

### B. Live SP-API Token Refresh Logic
In `repository.py`, the system fetches live SP-API credentials from the `amazon_sp_settings` table. 
- It checks if `expiry_date` is less than `datetime.now()`.
- If expired, it triggers a live OAuth `POST` request to `https://api.amazon.com/auth/o2/token` using the `refresh_token` and the `AWS_SP_CLIENT_ID` / `AWS_SP_CLIENT_SECRET` from `.env`.
- It dynamically updates the database with the new tokens and expiration time, mirroring the Laravel `AmazonSpApiHelper` logic exactly.

### C. 3-Tier Purchase Cost Calculation
The true "Cost of Goods Sold" is fetched dynamically in `repository.py` using raw SQL, adhering to the ERP's complex manufacturing rules:
1. **Fetch Combo:** Grabs the active/latest combination for the `osp_id` from `online_selling_product_combinations`.
2. **Fetch Saleables:** Loops through all items in that combination via `saleable_online_selling_product_combinations`.
3. **Calculate Unit Price (3-Tier Fallback):**
   - **Tier 1:** Latest Received PO *with Invoice* (`purchase_order_invoice_items` joined to `purchase_order_items` where `is_production_cost=1`).
   - **Tier 2:** Latest PO *without Invoice* directly from `purchase_order_items`.
   - **Tier 3:** Fallback to baseline price in `purchase_prices` table.
4. **Aggregate:** Sums the base unit prices to define the true `purchase_cost`.

## 4. Current API Endpoint
**POST** `http://localhost:8001/api/v1/recommend-price`
**Payload:**
```json
{
  "asin": "B08N5WRWNW",
  "osp_id": 1,
  "marketplace_id": 1,
  "node_id": 1234,
  "fulfillment_meta_id": 5,
  "current_price": 500,
  "target_margin_percentage": 15
}
```
**Flow:** API receives request -> Uses `ErpRepository` to fetch live fee masters and true purchase cost -> Executes Bounded Search Engine to find optimal price -> Passes scenario to `PricingRecommendationAgent` (Gemini) -> Returns a structured, explainable JSON response.

## 5. Next Steps / Known State
- The API is fully functional and successfully executes the complete chain.
- Ensure the `.env` file contains valid `AWS_SP_CLIENT_ID` and `AWS_SP_CLIENT_SECRET`.
- The system is resilient: if a target margin is mathematically impossible, it defaults to returning the closest possible profitable scenario rather than crashing.
