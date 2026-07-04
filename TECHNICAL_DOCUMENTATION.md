# Marketplace Intelligence Agent - Technical Documentation

## Overview
The Marketplace Intelligence Agent is an AI-driven, Python-based application designed to analyze product listings across multiple e-commerce platforms (e.g., Amazon, Flipkart) and provide intelligent recommendations. It uses Large Language Models (LLMs) to answer specific business questions related to pricing, profitability, and marketplace performance.

## Technology Stack
- **Language**: Python 3.x
- **Framework**: FastAPI (for the web framework / API layer)
- **Data Validation & Modeling**: Pydantic
- **AI/LLM Integration**: `google-genai`
- **Observability & Tracing**: OpenTelemetry (`opentelemetry-api`, `opentelemetry-sdk`)
- **Other Key Dependencies**: 
  - `httpx`, `requests` for network calls
  - `aiosqlite` for asynchronous SQLite database access
  - `tenacity` for retries
  - `watchdog` for file system monitoring

## Architecture & Directory Structure
The project follows a Domain-Driven Design (DDD) and Clean Architecture pattern.

- **`src/`**: Contains the core application logic and domain models.
  - `domain/`: Core business entities (e.g., `OnlineSellingProduct`, `PricingScenario`, `MarketplaceListing`, `CostBreakdown`). These are strictly typed models encapsulating state and behavior without tying them to database rows.
  - `models/`: DTOs and API request/response models (e.g., `BusinessQuestionRequest`, `AnalysisResult`).
  - `services/`: Business logic, such as `PricingContextBuilder` which gathers all necessary pricing information to feed into the AI.
  - `prompts/`: Contains builders like `PricingPromptBuilder` responsible for constructing structured context prompts to send to the LLM.
  - `api/`: API routes (FastAPI endpoints).
  - `agents/`: AI agents tailored for specific tasks (e.g., pricing intelligence).
  - `database/`: Database connection and data access layer.
  - `config/`, `utils/`, `tools/`: Helpers, configuration files, and auxiliary tool integration.
- **`docs/`**: Extensive project documentation including Business Requirements, Domain Models, Capability Maps, Data Sources, and PRD.
- **`pricing_agent/`**: Contains specific implementations/scripts for the pricing analysis agent (`agent.py`).
- **`frontend/`**: Directory reserved for the frontend web application (currently empty).
- **`main.py`**: Entry point script for simulating and testing the core capability of building pricing contexts and generating prompts.
- **`sample_domain_graph.py`**: Script to construct and validate the domain model object graph without running business logic. This acts as a structural integrity test for the DDD implementation.

## Core Domain Models
As outlined in `docs/06-domain-model.md` and `sample_domain_graph.py`, the core abstractions include:
1. **Product & Platform Structure**: 
   - `OnlineSellingProduct` -> `Platform` (e.g., Amazon) -> `Marketplace` (e.g., India).
2. **Listing**: Represents the product listing on a specific marketplace (`MarketplaceListing`).
3. **Pricing & Financials**: 
   - `PricingScenario`, `FulfillmentStrategy`, `SellingInformation`, `CostBreakdown`, `ProfitAnalysis`, `MarketplaceFee`.
4. **Agent Communication**: 
   - `AnalysisRequest` (input to the agent) and `AnalysisResult` (structured output from the agent).

## How it Works
1. **Request Intake**: A `BusinessQuestionRequest` is received (e.g., "What is the recommended price for this listing?").
2. **Context Building**: The `PricingContextBuilder` retrieves data for the specific `listing_id` and `marketplace` to build a comprehensive data graph including current pricing, costs, fees, and fulfillment strategies.
3. **Prompt Construction**: The `PricingPromptBuilder` transforms this rich context into a structured text prompt formatted for the LLM.
4. **Agent Evaluation**: The configured AI agent processes the prompt and returns an `AnalysisResult` containing a summary, root cause, confidence score, recommendations, and priority.
