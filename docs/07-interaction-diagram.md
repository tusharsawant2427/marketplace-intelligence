# Interaction Diagram

This document defines the execution flow and communication pathways within the system. It clarifies exactly "who talks to whom," ensuring that we have a predictable, structured workflow rather than a chaotic web of direct agent-to-database or agent-to-agent calls.

## Core Execution Philosophy

1. **The User never talks to an Agent directly.** All requests go through the `WorkflowService`.
2. **Agents do not talk to the database directly.** Agents must use specific `Tools` to fetch data.
3. **Tools return strictly typed Domain Models.** Tools do not return raw arrays, generic database rows, or raw JSON.
4. **Agents act as the reasoning engines (using LLMs) to process Domain Models and output a `BusinessRecommendation`.**

---

## General Execution Flow

```text
User
  ↓
WorkflowService (Receives Request, Routes to correct Agent)
  ↓
Agent (LLM performs reasoning based on Domain Models)
  ↓
Tools (Fetch data and return Domain Models)
  ↓
BusinessRecommendation (Domain Model)
  ↓
WorkflowService
  ↓
User / UI
```

---

## Example 1: Marketplace Intelligence

**Business Question:** *"Why is Amazon inactive?"*

```text
User
  ↓
WorkflowService 
  ↓
Marketplace Agent
 ├── FetchListingTool() -> Returns Listing Model
 ├── FetchMarketplaceSnapshotTool() -> Returns MarketplaceSnapshot Model
 └── LLM (Gemini) evaluates the models against Decision Criteria
  ↓
BusinessRecommendation (Summary, Root Cause, Business Impact, Confidence, Recommended Actions, Priority, Supporting Evidence)
  ↓
WorkflowService
  ↓
User / UI
```

---

## Example 2: Pricing Intelligence

**Business Question:** *"Why is this listing making a loss?"*

```text
User
  ↓
WorkflowService
  ↓
Pricing Agent
 ├── FetchListingTool() -> Returns Listing Model
 ├── FetchPricingTool() -> Returns Pricing Model
 ├── FetchChargesTool() -> Returns Charges Model
 └── LLM (Gemini) evaluates the models against Decision Criteria
  ↓
BusinessRecommendation (Summary, Root Cause, Business Impact, Confidence, Recommended Actions, Priority, Supporting Evidence)
  ↓
WorkflowService
  ↓
User / UI
```

---

## Standard Component Roles

- **User / Cron Job:** The initiator of the question or the scheduled trigger.
- **WorkflowService:** The orchestrator. It receives the prompt, creates the `AnalysisRequest`, identifies the correct Agent based on the **Capability Map**, and delegates the task.
- **Agent (e.g., SEO Agent, Sales Agent):** The intelligence for a specific domain. It orchestrates the tools, uses the LLM to perform reasoning on the returned models, and generates the final output.
- **Tools (e.g., FetchListingTool):** The connectors. They interact with external APIs or internal databases and return standardized Domain Models.
- **Domain Models:** The structured data containers (`Listing`, `Pricing`, `Charges`) that ensure data consistency.
- **BusinessRecommendation:** The standardized output format returned back up the chain to the WorkflowService. It is focused on actionable business advice backed by data.
