"""Deterministic identifier utilities shared across gold-tier builders."""

from __future__ import annotations

from typing import Optional


def valor_from_isin(isin: Optional[str]) -> Optional[str]:
    """Derive the Swiss VALOREN number from a CH-prefixed ISIN.

    Structure of a CH ISIN:  ``CH`` + 9-digit zero-padded valor + 1 check digit.
    The valor is the digits at positions 3-11, stripped of leading zeros.

      CH1319968579  →  131996857   (Allreal Holding senior bond)
      CH0026985082  →  2698508     (Lehman Brothers Switzerland)

    Non-CH ISINs do not encode a valor; SIX Swiss Exchange assigns one
    proprietarily when a foreign instrument is admitted to Swiss trading,
    and that mapping is not available through any public free endpoint we've
    been able to reach. For those, returns None.
    """
    if not isin or len(isin) != 12 or not isin.startswith("CH"):
        return None
    digits = isin[2:11]
    if not digits.isdigit():
        return None
    stripped = digits.lstrip("0")
    return stripped or "0"
