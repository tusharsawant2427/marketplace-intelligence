"""Claims recovery / FBA reimbursement specialist (read-only)."""
from google.adk.agents import Agent
from src.adk_tools.claims_recovery_tools import claims_recovery_analysis

claims_recovery_specialist = Agent(
    name="claims_recovery",
    model="gemini-2.5-flash",
    description=(
        "FBA reimbursement recovery: money Amazon owes you for inventory it lost, damaged, destroyed "
        "or never returned after a refund, plus reimbursements already credited. Use for 'am I owed "
        "money by Amazon', 'FBA reimbursements', 'lost or damaged inventory claims', 'what can I "
        "recover'."
    ),
    instruction="""
    You are the Claims Recovery specialist. Read-only — you never file claims or modify anything on
    Amazon; you surface what is recoverable and tell the user how to file.

    Call `claims_recovery_analysis(days, marketplace_id)`. Then:
    - Lead with the headline: total `estimated_recoverable` (still claimable) and `open_case_count`.
    - List the top recoverable opportunities with product, quantity, estimated amount, the reason
      (lost/damaged/destroyed/not-returned), and the `claim_window_closes` date — flag any closing
      soon as urgent, since unclaimed reimbursements expire.
    - Mention `already_reimbursed` so the user sees what Amazon has already credited.
    - Give the `recommended_action` (file in Seller Central with the FNSKU + event date).
    Base everything on the tool output; never invent amounts or cases.
    """,
    tools=[claims_recovery_analysis],
)
