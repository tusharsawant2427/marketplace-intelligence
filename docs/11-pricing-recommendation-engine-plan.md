# Pricing Recommendation Engine & LIC Integration Plan

Based on your vision, the **Listing Intelligence Center (LIC)** will transform the ERP from a deterministic pricing simulator into an AI-powered decision-support system. The flagship feature driving this transformation is the **Pricing Recommendation Engine (Backward Calculator)**.

This document outlines the architectural plan to build this engine on top of your existing Laravel ERP database schema and Amazon SP-API.

---

## 1. The Core Challenge: Forward vs. Backward Calculation

Your existing `LpaCalculation` is a **forward calculator**:
`Selling Price -> Fees -> Taxes -> Costs -> Profit`

The new engine requires a **backward calculator**:
`Target Profit / Business Goal -> Reverse Fees -> Recommended Selling Price`

### Why Backward Calculation is Complex
We cannot use simple algebra to reverse the formula because marketplace fees are **step functions (tiered)** based on the selling price. For example:
- `amazon_referral_fees` change based on price bands (`min_value`, `max_value`).
- `amazon_closing_fees` are tiered by price bands.
- Amazon SP-API fees might dynamically shift based on category exceptions.

### The Solution: Bounded Search Algorithm
Instead of algebraic reversal, the engine will use a **Bounded Search Algorithm** (like Binary Search) over the deterministic forward calculator.

1. **Define Bounds**: 
   - `Min Bound`: Break-even price (Profit = 0).
   - `Max Bound`: MRP (Maximum Retail Price from `saleable_mrps`).
2. **Set Constraints**: Target Profit (e.g., 15%), Competitor Buy Box Price (from SP-API).
3. **Iterate**: The algorithm rapidly tests candidate prices between the Min and Max bounds using the existing `analyse()` logic.
4. **Converge**: It finds the exact selling price that yields the target profit while respecting the constraints (e.g., "Must be below Buy Box").

---

## 2. Architecture & Data Flow

The architecture will orchestrate data from three sources: the **Laravel ERP DB**, **Amazon SP-API**, and the **AI Engine**.

### Phase 1: Data Hydration
The Python Intelligence Service fetches required data:
1. **ERP Data (via read-only DB connection)**:
   - Target OSP details (`online_selling_products`, `dimensions`, `saleable_mrps`, `hsn_codes`).
   - Fee Masters (`amazon_referral_fees`, `amazon_weight_handling_fees`, `amazon_closing_fees`, `amazon_storage_fees`).
   - Fulfillment context (`fulfillment_type_meta_data`, `nodes`).
2. **Live Marketplace Data (via Amazon SP-API)**:
   - `AnyOfferChangedNotification` / `GetPricing` API for live Buy Box price.
   - `GetMyFeesEstimate` API (optional, to validate ERP fee master accuracy).
   - `ListingsItem` API for current active status and suppression alerts.

### Phase 2: The Recommendation Engine (Deterministic)
The Python service runs the Bounded Search Algorithm:
1. Compute the absolute **Break-even price** (minimum floor).
2. Fetch the **Buy Box price** (competitive ceiling).
3. Run the search to find candidate prices that satisfy the user's specific goals:
   - *Goal A*: Maximize volume (Price = Buy Box - ₹1).
   - *Goal B*: Target Margin (Price that yields 15% margin).
4. Output a **Structured Recommendation Object**.

### Phase 3: AI Explanation Layer
AI does **not** calculate the price. It acts as the business interpreter.
We pass the Structured Recommendation Object, ERP context, and SP-API context into the LLM prompt.

**LLM Prompt Context:**
- Current Price: ₹500
- Recommended Price: ₹685
- Target: 15% Margin
- Buy Box: ₹700
- Fee Changes: Referral fee is 17%.

**LLM Output Generation:**
> "To achieve your goal of a 15% profit margin, we recommend increasing the price to ₹685. This price keeps you highly competitive, sitting ₹15 below the current Buy Box owner. The increase offsets the recent high referral fees (17%) in this category while keeping you well under the MRP."

---

## 3. Step-by-Step Implementation Plan

### Step 1: Replicate `LpaCalculation` in Python (The Pricing Engine)
To run the bounded search efficiently without hammering the Laravel API, we need to port the deterministic `LpaCalculation` logic to the Python LIC service.
- **Action**: Create Python domain models mapping to the schema in `10-osp-analyse-pricing-schema.md`.
- **Action**: Implement the forward pricing calculator in Python (handling GST, Referral, Closing, Weight Handling, etc.).

### Step 2: Implement the Bounded Search Algorithm
- **Action**: Build the reverse-search logic (`PricingRecommendationEngine`).
- **Action**: Allow passing constraints (e.g., `TargetMargin`, `BeatBuyBox`, `MaxPrice`).

### Step 3: Amazon SP-API Integration
- **Action**: Integrate Amazon SP-API `Catalog Items` and `Pricing` endpoints to fetch real-time ASIN data.
- **Action**: Create a service to merge ERP expected data with SP-API actual data.

### Step 4: AI Explainability Pipeline
- **Action**: Create the `PricingRecommendationPromptBuilder`.
- **Action**: Wire up `google-genai` to take the deterministic recommendation and generate the human-readable explanation.

### Step 5: API & Frontend Integration
- **Action**: Expose the `/recommend-price` endpoint in FastAPI.
- **Action**: The ADK (Agent Development Kit) acts as the orchestrator between the user, the business services, and the AI.

---

## 4. Why This Approach Wins

1. **Trust**: Because the math is deterministic and relies strictly on the `pulse_erp` database schema, business users will trust the numbers. 
2. **Explainability**: The AI tells the *story* of the numbers, fulfilling your principle: *"Every recommendation must be explainable."*
3. **Extensibility**: Once the core OSP -> Platform -> Marketplace domain is modeled in Python, adding **Inventory Intelligence** or **Advertising Intelligence** uses the exact same foundational graph.
4. **Performance**: Running the bounded search in Python memory over cached master tables allows for millisecond recommendation generation, suitable for bulk operations later.
