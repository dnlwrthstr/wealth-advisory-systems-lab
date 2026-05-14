"""Suitability, recommendation, and advisory workflow logic."""

from .products import ProductProfile
from .service import SuitabilityResult, SuitabilityService
from .suitability import is_suitable, suitability_flags

__all__ = [
    "ProductProfile",
    "SuitabilityResult",
    "SuitabilityService",
    "is_suitable",
    "suitability_flags",
]

