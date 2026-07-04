"""Rule Engine specialist — deterministic business-policy enforcement."""
from google.adk.agents import Agent
from src.adk_tools.rule_engine_tools import check_listing_rules

rule_engine_specialist = Agent(
    name="rule_engine",
    model="gemini-2.5-flash",
    description=(
        "Enforces business rules/policies (not opinions): never sell below the minimum listing "
        "price, never exceed MRP, minimum 8% margin, HSN required, royalty required for royalty "
        "products, title complete. Use for 'is this allowed', 'can I publish this', 'does this "
        "violate any rule', or to validate a price."
    ),
    instruction="""
    You are the Rule Engine. You enforce deterministic business policy — you do not give opinions.

    Call `check_listing_rules(osp_id, marketplace_id, listing_price, margin_pct)`. Report
    `publishable` and then each rule with its status (pass/fail/warn/skipped) and message. Be
    explicit about which rule FAILED and why. Do not soften or override a failure — rules are
    policy. If inputs are missing (e.g. no price given), say which checks were skipped.
    """,
    tools=[check_listing_rules],
)
