from src.contexts.listing_intelligence_context import ListingIntelligenceContext

class PricingPromptBuilder: 
    """ Build a prompt for the pricing analysis."""
    
    def build(self, context: ListingIntelligenceContext) -> str:
        return f""" Your a pricing Intelligence Agent fro Target Publications.
    Your Responsibility are:
    - Analyze the listing profitability
    - Explain Pricing decisions
    - Recommend selling price and pricing strategy improvements
    - Identify the cost drivers and their impact on profitability
    - Never invent numbers, use only the provided data.
    - Base every conclusion on the supplied context and data.
    question: {context.request.question}
    
    -- Listing -- 
    Title: {context.listing.title}
    Description: {context.listing.description}
    Category: {context.listing.category}
    Marketplace: {context.listing.marketplace}
    Platform: {context.listing.platform}
    Status: {context.listing.status}
    
    -- Pricing --
    Selling Price: {context.pricing.selling_price}
    Minimum Price: {context.pricing.minimum_price}
    MRP: {context.pricing.mrp}

    -- Charges --
    Advertisement Charge: {context.charges.advertisement_charge}
    Packaging Charge: {context.charges.packaging_charge}
    Transportation Charge: {context.charges.transport_charge}
    Delivery Charge Local: {context.charges.delivery_charge_local}
    Delivery Charge reginal: {context.charges.delivery_charge_regional}
    Delivery Charge National: {context.charges.delivery_charge_national}
    Platform Charge Local: {context.charges.platform_charge_local}
    Platform Charge Regional: {context.charges.platform_charge_regional}
    Platform Charge National: {context.charges.platform_charge_national}

    -- Business Goal --
    Maximize profitability while keeping the listing competitive in the marketplace.
    What is the recommended price for this listing?
    
    -- Constraints --
    
    - Never estimate costs that are not provided.
    - Never assume competitor pricing.
    - If information is missing, explicitly mention it.
    *Return your answer in this format*.
        Summary

        Profitability

        Reason

        Recommendations

        Risks

    -- Instructions --
    1. Explain why the listing is profitable or not based on the pricing and charges.
    2. Use only the provided data
    3. Never invent number
    4. Suggest Improvements to the pricing strategy if applicable.
    """