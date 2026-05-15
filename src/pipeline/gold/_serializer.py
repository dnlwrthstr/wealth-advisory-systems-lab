"""Pydantic-dump post-processing shared across gold-tier builders.

The ontology defines `Currency` as a value object (code + numericCode +
name + …), but the OpenSearch index mapping and the bundled example
payloads store it as the bare ISO 4217 code string. This helper walks
a `model_dump(mode="json", exclude_none=True)` tree and flattens any
Currency-shaped subdict to its `code` value.

`Country` and `CfiCode` are `RootModel[str]` in the generated pydantic
and already serialise as scalars — no flattening needed.
"""

from __future__ import annotations

from typing import Any, Set

from universe.models import Currency


_CURRENCY_KEYS: Set[str] = set(Currency.model_fields.keys())


def flatten_value_objects(node: Any) -> Any:
    if isinstance(node, dict):
        keys = set(node.keys())
        if "code" in keys and keys.issubset(_CURRENCY_KEYS):
            return node["code"]
        return {k: flatten_value_objects(v) for k, v in node.items()}
    if isinstance(node, list):
        return [flatten_value_objects(item) for item in node]
    return node
