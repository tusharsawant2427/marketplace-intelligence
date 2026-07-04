"""
Maps pulse_erp's internal marketplace to Amazon's SP-API global marketplace id.

The ERP `marketplaces` table stores only a human name (e.g. "Amazon-India") and a
`country_id`; it does NOT store Amazon's marketplace id string (e.g. "A21TJRUUN4KGV").
Amazon SP-API requires that global id, which is a fixed constant per Amazon storefront,
so the mapping lives here keyed by the country name as stored in `countries.name`.

Reference: https://developer-docs.amazon.com/sp-api/docs/marketplace-ids
"""

# Amazon SP-API global marketplace ids, keyed by pulse_erp `countries.name`.
AMAZON_MARKETPLACE_ID_BY_COUNTRY = {
    "India": "A21TJRUUN4KGV",
    "United States": "ATVPDKIKX0DER",
    "Canada": "A2EUQ1WTGCTBG2",
    "United Kingdom": "A1F83G8C2ARO7P",
    "United Arab Emirates": "A2VIGQ35RCS4UG",
}


def resolve_amazon_marketplace_id(country_name: str) -> str:
    """Return Amazon's SP-API marketplace id for the given ERP country name."""
    marketplace_id = AMAZON_MARKETPLACE_ID_BY_COUNTRY.get(country_name)
    if not marketplace_id:
        raise ValueError(
            f"No Amazon SP-API marketplace id mapping for country '{country_name}'. "
            f"Add it to AMAZON_MARKETPLACE_ID_BY_COUNTRY."
        )
    return marketplace_id


def platform_has_live_pricing(platform_name: str) -> bool:
    """
    Whether we have a live-marketplace (buy-box) integration for a platform.

    Only Amazon is wired to SP-API today, so any Amazon storefront supports live pricing;
    every other platform (Flipkart, Meesho, Jiomart, ...) can still be analysed with the
    deterministic ERP fee engine but has no live competitor/buy-box data.
    """
    return (platform_name or "").strip().lower().startswith("amazon")
