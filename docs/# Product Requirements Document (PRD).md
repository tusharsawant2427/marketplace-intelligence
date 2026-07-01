# Product Requirements Document (PRD)

# Listing Intelligence Center (LIC)

## Version

1.0

## Product Owner

Online Business Team

## Engineering Team

ERP Online Module Team

## Related Modules

* Online Selling Product (OSP)
* Listing
* Marketplace Listing
* Listing Metadata
* Listing Price Analysis
* Reconciliation
* Platform Masters
* Charges Masters

---

# 1. Problem Statement

The current ERP supports:

* OSP Management
* Listing Management
* Marketplace Management
* Pricing Analysis
* Reconciliation

However, there is no centralized system that continuously validates whether listings are:

* Marketplace compliant
* Correctly priced
* Profitable
* Properly configured
* Synchronized with marketplace expectations

This results in:

* Incorrect pricing
* Margin leakage
* Invalid marketplace metadata
* Missing mandatory attributes
* Wrong fee assumptions
* Listing rejection risks
* Operational dependency on manual audits

---

# 2. Product Vision

Create a centralized Listing Intelligence Center that continuously evaluates all marketplace listings and provides:

* Listing Health Monitoring
* Pricing Intelligence
* Amazon Readiness Validation
* Metadata Validation
* Marketplace Synchronization
* Alerting and Rectification
* Executive Reporting

The system shall become the operational control tower for all marketplace listings.

---

# 3. Business Goals

### Goal 1

Reduce pricing errors by 90%.

### Goal 2

Reduce manual listing audits by 80%.

### Goal 3

Identify loss-making listings before sales occur.

### Goal 4

Improve listing readiness and compliance across marketplaces.

### Goal 5

Create a scalable foundation for future Amazon, Flipkart, and Meesho integrations.

---

# 4. Scope

## Included

* Listing validation
* Pricing intelligence
* Profitability analysis
* Alert management
* Marketplace readiness validation
* Amazon integration
* Listing health scoring
* Fee verification
* Metadata verification

## Excluded (Phase 1)

* A+ Content Management
* SEO Content Management
* Automated Listing Publishing
* AI Content Generation
* Competitor Scraping

---

# 5. System Architecture

## Integration Approach

The Listing Intelligence Center will be implemented as a new module inside the existing ERP.

### New Module

TOS

* Listing Intelligence Center

  * Dashboard
  * Validation Center
  * Pricing Intelligence
  * Alerts
  * Marketplace Sync
  * Audit Logs

### Source of Truth

Existing ERP tables remain the source of truth.

No duplication of:

* OSP
* Listings
* Metadata
* Pricing
* Fee Masters

---

# 6. Core Features

## Feature 1: Listing Health Engine

Every active listing receives a health score.

### Health Components

| Component        | Weight |
| ---------------- | ------ |
| Pricing          | 25     |
| Metadata         | 25     |
| Compliance       | 20     |
| Marketplace Sync | 15     |
| State Integrity  | 15     |

### Score

0-100

### Categories

Healthy

80-100

Warning

60-79

Critical

Below 60

---

## Feature 2: Pricing Intelligence

### Existing Inputs

* Listing Price
* Platform Charges
* Delivery Charges
* Royalty
* Packaging
* Advertisement Charges
* Transport Charges

### New Outputs

* Expected Margin
* Profitability
* Revenue Leakage
* Recommended Price

### Validation Rules

#### Negative Margin

Flag listing.

#### Settlement Below Threshold

Flag listing.

#### Price Below Minimum Listing Price

Flag listing.

#### Excessive Platform Price Difference

Flag listing.

---

## Feature 3: Amazon Readiness Validator

Validate whether listing can be published according to Amazon requirements.

### Checks

#### Mandatory Attributes

Validate category specific attributes.

Examples:

Books

* Title
* Author
* ISBN
* Publisher

Toys

* Brand
* Age Range
* Material

#### Weight

Weight available.

#### Dimensions

Length, Width, Height available.

#### GST / HSN

Present and valid.

#### Manufacturer Information

Mandatory fields available.

#### Country of Origin

Available.

---

## Feature 4: Metadata Validation

### Validation Rules

#### Weight Validation

Weight exists and is valid.

#### Dimension Validation

All dimensions exist.

#### HSN Validation

HSN available.

#### Duplicate SKU Validation

No duplicate active SKU.

#### Marketplace Mapping Validation

Node, category and marketplace alignment.

---

## Feature 5: State Integrity Validation

Validate consistency between:

* OSP
* Listing
* Marketplace
* Metadata

### Examples

Invalid:

OSP = INACTIVE

Listing = ACTIVE

Invalid:

Listing = HOLD

Metadata = ACTIVE

---

## Feature 6: Alert Center

Centralized alert management.

### Severity

* Critical
* Warning
* Info

### Alert Types

* NEGATIVE_MARGIN
* PRICE_DRIFT
* MISSING_ATTRIBUTE
* WEIGHT_MISMATCH
* DIMENSION_MISMATCH
* CATEGORY_MISMATCH
* FEE_DIFFERENCE
* DUPLICATE_SKU
* STATE_INCONSISTENCY

---

# 7. Amazon Integration

## Purpose

Validation and verification.

Amazon is not the pricing authority.

ERP remains the pricing authority.

---

## APIs

### Product Type Definitions API

Required attribute validation.

### Listings API

Payload validation.

### Catalog Items API

Weight and dimension verification.

### Product Fees API

Fee verification.

### Reports API

Bulk marketplace verification.

---

## Sync Strategy

Use scheduled synchronization.

No real-time API dependency.

### Daily Jobs

* Listing Validation
* Fee Validation
* Content Validation

### 6 Hour Jobs

* Price Verification

---

# 8. New Database Tables

## listing_health_scores

Stores overall health score.

---

## listing_alerts

Stores generated alerts.

Fields:

* listing_id
* platform_id
* severity
* type
* message
* status

---

## listing_validation_results

Stores validation outcomes.

Fields:

* listing_id
* validation_type
* expected_value
* actual_value
* status
* remarks

---

## marketplace_snapshots

Stores marketplace verification snapshots.

Fields:

* listing_id
* platform_id
* snapshot_type
* payload
* captured_at

---

## fee_verification_results

Stores ERP vs marketplace fee comparison.

---

# 9. User Roles

## Category Manager

View alerts.

Rectify issues.

Review pricing.

---

## Online Operations

Manage validation failures.

Monitor listing health.

---

## Management

View dashboards and KPIs.

---

# 10. Dashboard KPIs

### Listing Health

Healthy Listings

Warning Listings

Critical Listings

### Pricing

Loss Making Listings

Margin Distribution

Revenue Leakage

### Validation

Missing Attributes

Metadata Errors

Compliance Failures

### Marketplace

Amazon Ready Listings

Pending Listings

Validation Failures

---

# 11. Success Metrics

### Pricing Accuracy

Greater than 95%

### Listing Readiness

Greater than 90%

### Alert Resolution SLA

Less than 48 hours

### Manual Audit Reduction

Greater than 80%

---

# 12. Phase-wise Roadmap

## Phase 1

Duration: 4 Weeks

Deliverables:

* Health Engine
* Pricing Intelligence
* Alert Framework
* Dashboard

## Phase 2

Duration: 4 Weeks

Deliverables:

* Amazon Readiness Validator
* Metadata Validation
* State Validation

## Phase 3

Duration: 4-6 Weeks

Deliverables:

* Amazon SP-API Integration
* Fee Verification
* Marketplace Snapshots
* Automated Recommendations

---

# Expected Outcome

The Listing Intelligence Center becomes the centralized governance layer for all marketplace listings and ensures that every listing is:

* Correctly configured
* Correctly priced
* Profitable
* Marketplace compliant
* Operationally healthy
  before impacting revenue.
