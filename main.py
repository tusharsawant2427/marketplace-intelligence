from src.services.listing_intelligence_service import ListingIntelligenceService
from src.models.business_question_request import BusinessQuestionRequest
from src.prompts.pricing_prompt_builder import PricingPromptBuilder

def main():

    # Step 1: Simulate receiving a business question request
    request = BusinessQuestionRequest(
        question="What is the recommended price for this listing?",
        listing_id="2109",
        marketplace="India",
        capability="pricing_analysis"
    )

    # Step 2: Build the pricing context
    builder  = ListingIntelligenceService()

    # Step 3: Build the pricing context
    context = builder.build(request)
    prompt = PricingPromptBuilder().build(context)
    # Step 4: Print the context for demonstration
    print("Business Question Request:")
    print(prompt)

if __name__ == "__main__":
    main()