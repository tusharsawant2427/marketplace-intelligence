from dataclasses import dataclass
from typing import List


@dataclass
class BusinessRecommendation:
    """AI response."""

    summary: str
    root_cause: str
    business_impact: str
    confidence: float
    recommended_actions: List[str]
    priority: str
    supporting_evidence: List[str]