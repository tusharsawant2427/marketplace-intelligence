"""
Deterministic business Rule Engine — policy enforcement, NOT AI judgement.

Every rule is a pure function over the inputs; results are stable and explainable. Other agents
(esp. Recommendation) call this to gate actions so the LLM never decides policy.
"""
from dataclasses import dataclass

MIN_MARGIN_PCT = 8.0          # don't publish below this margin
MIN_TITLE_LENGTH = 10


@dataclass
class RuleResult:
    rule: str
    status: str   # "pass" | "fail" | "warn" | "skipped"
    message: str


def evaluate_rules(inputs: dict, listing_price: float = None, margin_pct: float = None) -> dict:
    """
    Apply business rules to a proposed listing.

    inputs: from ErpApiClient.rule_inputs (mrp, minimum_listing_price, has_hsn, is_royalty,
            has_royalty_detail, name). listing_price / margin_pct: the proposed scenario (optional).
    Returns {"publishable": bool, "results": [RuleResult...as dicts]}. `publishable` is False if any
    rule fails.
    """
    results: list[RuleResult] = []
    mrp = inputs.get("mrp")
    min_price = inputs.get("minimum_listing_price")
    name = inputs.get("name") or ""

    # 1. Never sell below the minimum listing price (floor).
    if listing_price is None or min_price is None:
        results.append(RuleResult("min_listing_price", "skipped", "No listing price or floor to check."))
    elif listing_price < min_price:
        results.append(RuleResult("min_listing_price", "fail",
                                  f"Price {listing_price} is below the minimum listing price {min_price}."))
    else:
        results.append(RuleResult("min_listing_price", "pass", f"Price {listing_price} >= floor {min_price}."))

    # 2. Never exceed MRP.
    if listing_price is None or mrp is None:
        results.append(RuleResult("mrp_cap", "skipped", "No listing price or MRP to check."))
    elif listing_price > mrp:
        results.append(RuleResult("mrp_cap", "fail", f"Price {listing_price} exceeds MRP {mrp}."))
    else:
        results.append(RuleResult("mrp_cap", "pass", f"Price {listing_price} <= MRP {mrp}."))

    # 3. Minimum margin.
    if margin_pct is None:
        results.append(RuleResult("min_margin", "skipped", "No margin provided."))
    elif margin_pct < MIN_MARGIN_PCT:
        results.append(RuleResult("min_margin", "fail",
                                  f"Margin {margin_pct}% is below the {MIN_MARGIN_PCT}% minimum."))
    else:
        results.append(RuleResult("min_margin", "pass", f"Margin {margin_pct}% >= {MIN_MARGIN_PCT}%."))

    # 4. HSN present.
    results.append(RuleResult("hsn_present", "pass" if inputs.get("has_hsn") else "fail",
                              "HSN present." if inputs.get("has_hsn") else "HSN (tax code) is missing."))

    # 5. Royalty present when the product is royalty-bearing.
    if not inputs.get("is_royalty"):
        results.append(RuleResult("royalty_present", "skipped", "Product is not royalty-bearing."))
    else:
        ok = inputs.get("has_royalty_detail")
        results.append(RuleResult("royalty_present", "pass" if ok else "fail",
                                  "Royalty detail present." if ok else "Royalty product missing royalty detail."))

    # 6. Title completeness.
    if len(name.strip()) >= MIN_TITLE_LENGTH:
        results.append(RuleResult("title_complete", "pass", "Title present."))
    else:
        results.append(RuleResult("title_complete", "fail", "Title missing or too short."))

    publishable = all(r.status != "fail" for r in results)
    return {"publishable": publishable, "results": [r.__dict__ for r in results]}
