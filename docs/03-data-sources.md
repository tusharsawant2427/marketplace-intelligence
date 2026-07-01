# Data Sources

This document identifies every source of information required by the AI to answer business questions.

The AI never queries the database directly.

All access happens through Tools.

---

# Internal ERP

## Listing

Tables

- listings
- listing_marketplaces
- online_selling_products
- listing_meta_data

Purpose

Provides listing information and metadata.

---

## Pricing

Tables

- products
- saleable_mrps
- production_costs
- online_selling_products

Purpose

Provides pricing information.

---

## Charges

Tables

- marketplace commission fees
- shipping fees
- storage fees
- royalty analysis
- advertisement reports

Purpose

Provides cost breakdown.

---

## Orders

Tables

- amazon_orders
- flipkart_orders
- ecommerce_sale_orders
- order_items

Purpose

Sales history.

---

## Inventory

Tables

- inventories
- warehouses
- stock movements

Purpose

Inventory analysis.

---

## Promotions

Tables

- campaigns
- discounts
- coupons

Purpose

Promotion analysis.

---

## Settlement

Tables

- settlement reports
- payment reconciliation

Purpose

Profitability analysis.

---

# Marketplace APIs

Amazon SP-API

Provides

- Listing Status
- Buy Box
- Catalog
- Inventory
- Performance Notifications
- Pricing
- Competitive Offers

---

Flipkart API

Provides

- Listing Status
- Catalog
- Inventory
- Orders
- Pricing

---

Other Marketplace APIs

- Meesho
- Jiomart
- Myntra

Future integrations.

---

# Knowledge Sources

Internal

- Company SOP
- Pricing Policy
- Promotion Rules
- Margin Policy
- Marketplace SOP

External

- Amazon Documentation
- Flipkart Documentation
- SEO Guidelines
- Marketplace Best Practices

---

# Mapping Business Questions

| Business Question | Data Sources |
|------------------|-------------|
| Why listing inactive? | Listing, Marketplace API |
| Why making loss? | Pricing, Charges, Settlement |
| Suggested price? | Pricing, Charges, Competitor Data |
| Sales decreasing? | Orders, Promotions, Inventory |
| SEO improvement? | Metadata, Marketplace Data |
| Revenue leakage? | Orders, Charges, Promotions |
| Listings requiring promotion? | Sales History, Inventory |
| Executive dashboard | All capabilities |

---

# Design Principle

Tools abstract every data source.

Agents never know where data comes from.