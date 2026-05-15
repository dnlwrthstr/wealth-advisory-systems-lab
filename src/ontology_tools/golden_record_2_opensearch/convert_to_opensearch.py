"""Generate OpenSearch index mappings for tier-3 (golden) record entities.

Discovers every YAML entity tagged ``kind: golden_record`` under the ontology
directory, builds an OpenSearch index mapping per golden family by recursing
into locally-defined value-object refs and **resolving** ``common_ontology``
references across files so cross-file scalar value-objects (Currency,
CfiCode, LegalEntityIdentifier, LongText…) map to the right scalar OpenSearch
type, and emits:

  * ``<index>.index.json``   — index settings + mappings
  * ``create_indices.sh``    — idempotent bulk-creation script

This utility intentionally does NOT emit documents: the actual golden
documents are produced at runtime by the enrichment pipeline and bulk-indexed
against these mappings. The ontology defines the *shape*, not the data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


INDEX_PREFIX = "pms_golden_"
MAX_REF_DEPTH = 6   # guard against accidental cross-file recursion


# Cache for parsed silver YAML files so we don't re-read on every ref.
_YAML_CACHE: Dict[Path, Optional[Dict[str, Any]]] = {}


def _load_yaml_cached(path: Path) -> Optional[Dict[str, Any]]:
    resolved = path.resolve()
    if resolved in _YAML_CACHE:
        return _YAML_CACHE[resolved]
    parsed = parse_yaml(resolved) if resolved.exists() else None
    _YAML_CACHE[resolved] = parsed
    return parsed


def _entities_of(file_path: Path) -> Dict[str, Any]:
    """Return the ``ontology.entities`` dict of ``file_path``, or {}."""
    parsed = _load_yaml_cached(file_path)
    if not parsed:
        return {}
    entities = (parsed.get("ontology") or {}).get("entities") or {}
    return entities if isinstance(entities, dict) else {}


def resolve_common_ontology(
    ref: str, base_file: Path
) -> Optional[Tuple[Dict[str, Any], Path]]:
    """Resolve ``relative/path.yml#/ontology/entities/EntityName`` to the
    target entity dict, plus the absolute path of the target file (for
    transitive ref resolution).

    Returns ``None`` if the file or pointer can't be resolved.
    """
    if "#" not in ref:
        return None
    file_part, pointer = ref.split("#", 1)
    target_file = (base_file.parent / file_part).resolve()
    parsed = _load_yaml_cached(target_file)
    if parsed is None:
        return None
    parts = [p for p in pointer.strip("/").split("/") if p]
    cursor: Any = parsed
    for part in parts:
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return None
    if not isinstance(cursor, dict):
        return None
    return cursor, target_file


def parse_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"Error parsing {file_path}: {exc}")
            return None


def slugify(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def index_name_for(entity_name: str) -> str:
    slug = slugify(entity_name)
    if slug.endswith("_golden"):
        slug = slug[: -len("_golden")]
    elif slug.endswith("golden"):
        slug = slug[: -len("golden")].rstrip("_")
    return f"{INDEX_PREFIX}{slug}"


def collect_golden_records(
    ontology_dir: Path,
) -> List[Dict[str, Any]]:
    """Walk the ontology directory and return one descriptor per golden entity."""
    records: List[Dict[str, Any]] = []

    for yaml_file in sorted(ontology_dir.rglob("*.yml")):
        data = parse_yaml(yaml_file)
        if not data:
            continue

        ontology = data.get("ontology") or {}
        entities = ontology.get("entities") or {}
        if not isinstance(entities, dict):
            continue

        for entity_name, entity_data in entities.items():
            if not isinstance(entity_data, dict):
                continue
            if entity_data.get("kind") != "golden_record":
                continue

            records.append(
                {
                    "entity_name": entity_name,
                    "entity_data": entity_data,
                    "ontology_name": ontology.get("name"),
                    "ontology_version": ontology.get("version"),
                    "source_entity": ontology.get("source_entity"),
                    "source_file": str(yaml_file.relative_to(ontology_dir)),
                    "source_file_abs": yaml_file.resolve(),
                    "local_entities": entities,
                }
            )

    return records


def map_field_type(
    prop_data: Dict[str, Any],
    local_entities: Dict[str, Any],
    source_file: Path,
    seen: Tuple[str, ...] = (),
    depth: int = 0,
) -> Dict[str, Any]:
    """Map a single property definition to an OpenSearch field mapping.

    Resolution rules (in order):
      1. Local ``ref`` / ``$ref`` → recurse into the local entity.
      2. ``common_ontology`` → resolve the cross-file ref; recurse into the
         target entity if it has properties, otherwise treat the target as
         a scalar value-object and re-map its inline ``type``. Falls back to
         a dynamic object if the ref can't be resolved.
      3. ``type: array`` → recurse into ``items``.
      4. ``type: object`` → build a nested mapping from inline properties.
      5. Custom types (``Country``, ``CfiCode``) → keyword.
      6. Scalars (string/integer/number/boolean, date variants) → conventional.
    """
    if depth >= MAX_REF_DEPTH:
        return {"type": "object", "dynamic": True}

    # 1. Local ref.
    ref_target = prop_data.get("ref") or prop_data.get("$ref")
    if isinstance(ref_target, str) and ref_target in local_entities and ref_target not in seen:
        target = local_entities[ref_target]
        # If the target is a pass-through alias (just `common_ontology` or
        # an inline `type`, no `properties`), delegate to map_field_type
        # so the alias gets resolved instead of producing an empty object.
        if not target.get("properties"):
            return map_field_type(
                target, local_entities, source_file,
                seen=seen + (ref_target,), depth=depth + 1,
            )
        return build_object_mapping(
            target,
            local_entities,
            source_file,
            seen=seen + (ref_target,),
            depth=depth + 1,
        )

    # 2. Cross-file common_ontology reference — try to resolve it so we map
    #    Currency / CfiCode / LegalEntityIdentifier (scalar value-objects) to
    #    the right scalar type, and structured value-objects (Price,
    #    CurrencyAmount, FinancialInstrumentIdentification) to nested objects.
    co_ref = prop_data.get("common_ontology")
    if co_ref:
        resolved = resolve_common_ontology(co_ref, source_file)
        if resolved is None:
            # Ref unresolvable — fall back to dynamic object so docs still index.
            return {"type": "object", "dynamic": True}
        target_entity, target_file = resolved
        # Reference-data entries are full lookup records (Currency table,
        # CFI table, …); the inline field value is the scalar key/code, not
        # the full record. Map to text+keyword if either:
        #   - the entity is explicitly tagged `kind: reference_data`, or
        #   - the resolved file lives under `ontology/reference_data/`
        #     (project convention — pair of canonical entity + reference
        #     data table files under that directory).
        if target_entity.get("kind") == "reference_data" or any(
            p.name == "reference_data" for p in target_file.parents
        ):
            return {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            }
        # Local `ref` / `$ref` references inside the resolved entity point
        # to other entities defined in the *target* file (e.g. FundFeeStructure
        # in Fund.yml refs OngoingFees in the same file). Switch
        # `local_entities` to the target file's entities so those refs
        # resolve correctly.
        target_local_entities = _entities_of(target_file)
        if target_entity.get("properties"):
            return build_object_mapping(
                target_entity,
                target_local_entities,
                target_file,
                seen=seen,
                depth=depth + 1,
            )
        # Scalar value-object — its `type` is what the field actually holds.
        # Recurse so a chained common_ontology alias (e.g., silver Currency ->
        # reference_data CurrencyReferenceEntry) also falls into the
        # reference-data short-circuit on the next hop.
        return map_field_type(
            target_entity, target_local_entities, target_file, seen, depth + 1
        )

    prop_type = prop_data.get("type")
    fmt = prop_data.get("format")

    # 3. Custom convenience types.
    if prop_type == "Country":
        return {"type": "keyword"}
    if prop_type == "CfiCode":
        return {"type": "keyword"}

    # 4. Arrays.
    if prop_type == "array":
        items = prop_data.get("items")
        if isinstance(items, dict):
            item_mapping = map_field_type(items, local_entities, source_file, seen, depth + 1)
            # Arrays of objects → `nested` so each element retains its
            # identity for correlated queries (e.g. `topHoldings WHERE
            # identifier = X AND weight > 0.05`). For object types we
            # promote `object` → `nested`; scalar item types pass through.
            if item_mapping.get("type") == "object":
                item_mapping["type"] = "nested"
            return item_mapping
        return {
            "type": "text",
            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
        }

    # 5. Object with inline properties.
    if prop_type == "object":
        return build_object_mapping(prop_data, local_entities, source_file, seen, depth + 1)

    # 6. Scalar primitives.
    if prop_type == "integer":
        return {"type": "long"}
    if prop_type == "number":
        return {"type": "double"}
    if prop_type == "boolean":
        return {"type": "boolean"}

    # 7. Strings — date variants take precedence; otherwise text+keyword.
    if prop_type == "string":
        if fmt == "date":
            return {"type": "date", "format": "yyyy-MM-dd"}
        if fmt in ("date-time", "datetime"):
            return {"type": "date"}
        if prop_data.get("enum"):
            return {"type": "keyword"}
        return {
            "type": "text",
            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
        }

    # 8. Fallback — opaque scalar / unknown shape.
    return {
        "type": "text",
        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
    }


def build_object_mapping(
    entity_data: Dict[str, Any],
    local_entities: Dict[str, Any],
    source_file: Path,
    seen: Tuple[str, ...] = (),
    depth: int = 0,
) -> Dict[str, Any]:
    """Build a nested object mapping from an entity / inline-object definition."""
    properties = entity_data.get("properties") or {}
    mapped: Dict[str, Any] = {}
    for prop_name, prop_data in properties.items():
        if not isinstance(prop_data, dict):
            continue
        mapped[prop_name] = map_field_type(
            prop_data, local_entities, source_file, seen, depth
        )

    return {
        "type": "object",
        "dynamic": False,
        "properties": mapped,
    }


def build_index_mapping(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build the full index settings + mappings document for a golden record."""
    entity_data = record["entity_data"]
    local_entities = record["local_entities"]
    source_file = record["source_file_abs"]

    properties = entity_data.get("properties") or {}
    mapped_properties: Dict[str, Any] = {}
    for prop_name, prop_data in properties.items():
        if not isinstance(prop_data, dict):
            continue
        mapped_properties[prop_name] = map_field_type(
            prop_data, local_entities, source_file
        )

    return {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
            },
        },
        "mappings": {
            "dynamic": False,
            "_meta": {
                "ontology": record["ontology_name"],
                "ontology_version": record["ontology_version"],
                "source_entity": record["source_entity"],
                "source_file": record["source_file"],
                "tier": "golden",
            },
            "properties": mapped_properties,
        },
    }


def write_index_definitions(
    records: List[Dict[str, Any]], output_dir: Path
) -> Tuple[int, List[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        'OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"',
        "",
    ]
    index_names: List[str] = []

    for record in records:
        index_name = index_name_for(record["entity_name"])
        index_names.append(index_name)
        mapping = build_index_mapping(record)
        mapping_path = output_dir / f"{index_name}.index.json"
        mapping_path.write_text(
            json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        script_lines.append(f'echo "Creating index {index_name}"')
        script_lines.append(
            f'curl -sS -X PUT "$OPENSEARCH_URL/{index_name}" '
            f'-H "Content-Type: application/json" '
            f'--data-binary "@$SCRIPT_DIR/{mapping_path.name}"'
        )
        script_lines.append("echo")
        script_lines.append("")

    script_path = output_dir / "create_indices.sh"
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    return len(records), index_names


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate OpenSearch index mappings for ontology entities tagged "
            "`kind: golden_record`."
        )
    )
    parser.add_argument(
        "--input", "-i", default="ontology", help="Input ontology directory"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="output/opensearch/golden",
        help="Output directory for index definitions and the bulk creation script",
    )
    args = parser.parse_args()

    ontology_dir = Path(args.input)
    output_dir = Path(args.output)

    if not ontology_dir.exists():
        print(f"Error: Input directory '{ontology_dir}' does not exist.")
        return

    records = collect_golden_records(ontology_dir)
    if not records:
        print("No `kind: golden_record` entities found.")
        return

    count, names = write_index_definitions(records, output_dir)
    print(
        f"Generated {output_dir} with {count} golden index mapping(s):\n  - "
        + "\n  - ".join(names)
    )


if __name__ == "__main__":
    main()
