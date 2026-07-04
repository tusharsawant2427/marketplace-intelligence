from dataclasses import dataclass, field

from src.domain.marketplace import Marketplace


@dataclass
class Platform:
    """
    Represents one selling platform.

    Example:
        Amazon
        Flipkart
        Meesho

    A Platform does not calculate anything. It only organizes the
    hierarchy of marketplaces that live underneath it.
    """

    name: str

    marketplaces: list[Marketplace] = field(default_factory=list)
