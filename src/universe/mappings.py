"""Source-format mappings used during universe ingestion.

These are code-level translations between the FINFOX CSV taxonomy and the
OpenWealth `FinancialInstrumentType` enum — not part of the ontology, so they
live next to the universe code rather than under `ontology/`.
"""

from __future__ import annotations

OPENWEALTH_TYPES = {
    "equity", "simpleBond", "floater", "convertibleBond",
    "fund", "moneyMarket", "commodity", "certificate",
    "highlyStructuredProduct", "future", "option", "other",
}

FINFOX_TO_OW = {
    "equity":                  "equity",
    "simpleBond":              "simpleBond",
    "floater":                 "floater",
    "convertibleBond":         "convertibleBond",
    "fund":                    "fund",
    "moneyMarket":             "moneyMarket",
    "commodity":               "commodity",
    "certificate":             "certificate",
    "highlyStructuredProduct": "highlyStructuredProduct",
    "callOption":              "option",
    "putOption":               "option",
    "future":                  "future",
    "other":                   "other",
    # "currency" and "CHF" are excluded — no valid ISIN
}
