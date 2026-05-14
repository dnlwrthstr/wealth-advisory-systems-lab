"""SuitabilityService wraps suitability and appropriateness checks."""

from dataclasses import dataclass

from profiling import ClientProfile
from profiling.signals import combined_risk_profile, liquidity_ratio, risk_capacity

from .products import ProductProfile
from .suitability import suitability_flags


@dataclass
class SuitabilityResult:
    client_id: str
    product_id: str
    liquidity_ratio: float
    risk_capacity: str
    combined_risk_profile: str
    suitable: bool
    flags: list[str]


class SuitabilityService:
    def evaluate(self, profile: ClientProfile, product: ProductProfile) -> SuitabilityResult:
        flags = suitability_flags(profile, product)
        return SuitabilityResult(
            client_id=profile.client_id,
            product_id=product.product_id,
            liquidity_ratio=round(liquidity_ratio(profile), 4),
            risk_capacity=risk_capacity(profile),
            combined_risk_profile=combined_risk_profile(profile),
            suitable=not flags,
            flags=flags,
        )
