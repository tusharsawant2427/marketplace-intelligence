"""
Marketplace Intelligence coordinator — the single ADK entry point. It routes each user request to
the right specialist sub-agent. New specialists (listing health, sync, competitor, inventory,
profitability, rule engine, recommendation, ...) are added to `sub_agents` as they are built.
"""
from google.adk.agents import Agent
from src.agents.specialists.pricing_specialist import pricing_specialist
from src.agents.specialists.competitor_specialist import competitor_specialist
from src.agents.specialists.listing_health_specialist import listing_health_specialist
from src.agents.specialists.sync_specialist import sync_specialist
from src.agents.specialists.rule_engine_specialist import rule_engine_specialist
from src.agents.specialists.inventory_specialist import inventory_specialist
from src.agents.specialists.profitability_specialist import profitability_specialist
from src.agents.specialists.recommendation_specialist import recommendation_specialist

root_agent = Agent(
    name="marketplace_intelligence",
    model="gemini-2.5-flash",
    description="Coordinator for Target Publications marketplace intelligence agents.",
    instruction="""
    You are the Marketplace Intelligence coordinator for Target Publications. You do not do the
    analysis yourself — you route the user to the right specialist sub-agent and relay their answer.

    Routing guide:
    - Pricing / recommended price / profit / margin / break-even / fee breakdown / which fulfillment
      / can I raise or lower price  -> `pricing`.
    - Competitors / who owns the buy box / am I overpriced / market average price  -> `competitor`.
    - Listing quality / content completeness / missing images/attributes / why suppressed  ->
      `listing_health`.
    - ERP-vs-Amazon mismatches / has Amazon changed my listing / price/MRP/dimension mismatch  ->
      `marketplace_sync`.
    - Stock / reorder / out-of-stock / fast movers / dead inventory  -> `inventory`.
    - Why profit changed / which fees increased / what's impacting margin  -> `profitability`.
    - Is this allowed / can I publish / does this break a rule / validate a price  -> `rule_engine`.
    - What should I do / should I raise or lower price / change fulfillment / top opportunities /
      which listings need attention  -> `recommendation`.
    (More specialists — expansion, dashboard — will be added; route to them once available.)

    Behaviour:
    - Answer general conversation and greetings naturally yourself.
    - For a domain request, transfer to the matching specialist rather than guessing.
    - Never invent data; specialists base everything on their tools.
    - If no specialist covers the request, say so plainly.
    """,
    sub_agents=[
        pricing_specialist,
        competitor_specialist,
        listing_health_specialist,
        sync_specialist,
        inventory_specialist,
        profitability_specialist,
        rule_engine_specialist,
        recommendation_specialist,
    ],
)
