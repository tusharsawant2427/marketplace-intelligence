# Business Knowledge

The AI can only answer business questions when it combines:

- Business Data
- Business Knowledge

This document defines the knowledge required by the Marketplace Intelligence Engine.

---

# Knowledge Layers

## 1. Marketplace Knowledge

The AI should understand marketplace-specific rules.

Examples

Amazon

- Listing lifecycle
- Buy Box
- Pricing rules
- Suppressed listings
- Restricted products
- Hazmat
- FBA
- A10 SEO algorithm

Flipkart

- Catalog rules
- Listing status
- Fulfillment
- Search ranking
- Pricing

Meesho

- Shipping policy
- Commission
- Catalog requirements

Jiomart

- Fees
- Catalog
- Marketplace rules

---

## 2. Company Knowledge

Internal business rules.

Examples

Pricing Policy

- Minimum margin
- Target margin
- Maximum discount
- MAP policy

Promotion Policy

- Promotion eligibility
- Campaign strategy
- Seasonal planning

Inventory Policy

- Safety stock
- Reorder level
- Stock aging

Marketplace Strategy

- Preferred marketplace
- Channel priorities
- Buy Box strategy

Executive KPIs

- Revenue
- Margin
- Growth
- Inventory turnover

---

## 3. Industry Knowledge

General marketplace expertise.

Examples

SEO

- Keyword optimization
- Title optimization
- Bullet optimization
- Search intent

Pricing

- Dynamic pricing
- Psychological pricing
- Competitor matching

Sales

- Conversion optimization
- Promotion strategy
- Customer behavior

Marketplace Operations

- Account Health
- Listing suppression
- Compliance

---

# Knowledge Hierarchy

Business Question

↓

Business Data

+

Marketplace Knowledge

+

Company Knowledge

+

Industry Knowledge

↓

Business Intelligence

↓

Business Recommendation

---

# Future Roadmap

The knowledge base may evolve into:

knowledge/

amazon/

flipkart/

pricing/

seo/

sales/

inventory/

company/

sop/

Eventually this can be replaced with a RAG (Retrieval-Augmented Generation) system backed by a vector database, allowing the AI to retrieve the most relevant documentation and policies dynamically.