from src.services.pricing_context_builder import PricingContextBuilder
from src.models.business_question_request import BusinessQuestionRequest


def main():

    # Step 1: Simulate receiving a business question request
    request = BusinessQuestionRequest(
        question="What is the recommended price for this listing?",
        listing_id="2109",
        marketplace="India",
        capability="pricing_analysis"
    )

    # Step 2: Build the pricing context
    builder  = PricingContextBuilder()

    # Step 3: Build the pricing context
    context = builder.build(request)

    # Step 4: Print the context for demonstration
    print("Business Question Request:")
    print(context)

if __name__ == "__main__":
    main()