from google.adk.agents import Agent
from src.adk_tools.build_pricing_context_tool import  (
    build_pricing_context
)
root_agent = Agent(
    name = "pricing_agent",
    model = "gemini-2.5-flash",
    description = "Pricing ecommerce analysis agent.",
    instruction = """ 
    You are a pricing ecommerce analysis assistant.
    Your responsibility is to help users understand pricing decisions.
    Always explain your reasoning clearly and provide actionable insights.
    """,
    tools = [
        build_pricing_context
    ]
)