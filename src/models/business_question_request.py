from dataclasses import dataclass


@dataclass
class BusinessQuestionRequest:
    """Question received by the AI."""

    question: str

    listing_id: str

    marketplace: str

    capability: str