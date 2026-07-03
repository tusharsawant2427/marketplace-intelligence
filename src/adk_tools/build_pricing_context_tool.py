from src.services.pricing_context_builder import PricingContextBuilder
from src.models.business_question_request import BusinessQuestionRequest

def build_pricing_context(question: str, listing_id: str, marketplace: str = 'Amazon'):
    """ Builds the pricing context for a given business question request."""
    
    request = BusinessQuestionRequest(
        question=question,
        listing_id=listing_id,
        marketplace=marketplace,
        capability="pricing_analysis"
    )
    
    builder = PricingContextBuilder()
    context = builder.build(request)
    
    return context