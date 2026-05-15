### ontology_2_pydantic — Generate Pydantic models from the ontology YAML

#### Overview
`ontology_2_pydantic` converts the modular ontology YAML files (under `ontology/`) into a single Python module containing Pydantic models. It scans all `*.yml` files, collects `ontology.entities`, and emits one `models.py` with:
- Pydantic `BaseModel` classes for each entity
- Typed fields based on YAML property definitions
- Descriptions mapped into Pydantic `Field` metadata

Key mappings:
- `is_a` → class inheritance
- `composition/all_of` → additional base classes
- `common_ontology`, `classification_ref`, `$ref`, `ref` → referenced entity types
- `oneOf` → `Union[...]`
- Arrays → `List[...]`

#### Prerequisites
- Python 3.9+
- PyYAML and Pydantic (installed via project dependencies)

#### Installation (developer mode)
From the project root:

```bash
pip install -e .
```

#### Basic usage
From the project root (recommended):

```bash
python -m ontology_2_pydantic.convert_to_pydantic \
  --input ontology \
  --output output/pydantic/models.py
```

Arguments:
- `--input/-i`: Ontology root directory (default: `ontology`).
- `--output/-o`: Output Python file path (default: `output/pydantic/models.py`).
- `--clear`: Truncate the output file before writing.

The tool emits a single module with all models, ordered by inheritance when possible.

#### Type mapping
Scalar types:
- `string` → `str` (with `format: date` → `date`, `format: date-time` → `datetime`)
- `number` → `float` (with `format: decimal` → `Decimal`)
- `integer` → `int`
- `boolean` → `bool`
- `object` → `Dict[str, Any]`
- `array` → `List[...]`

Reference types:
- `common_ontology`, `classification_ref`, `$ref`, `ref` resolve to the referenced entity name.
- `oneOf` resolves to `Union[...]` of referenced types.

#### Output model
The generated `models.py` contains:
- Imports for Pydantic and standard typing helpers.
- One class per entity, with docstrings from entity `description`.
- Field-level `description` propagated to `Field(..., description=...)`.

Optional properties are generated as `Optional[...] = None`, and required properties omit `Optional` and default to `...` or are left required depending on the source schema.

#### Examples
- Generate models for the entire ontology:
  ```bash
  python -m ontology_2_pydantic.convert_to_pydantic
  ```

- Generate models for a subtree:
  ```bash
  python -m ontology_2_pydantic.convert_to_pydantic \
    --input ontology/bank_data/securities_domain \
    --output output/pydantic/securities_domain_models.py
  ```

#### Notes
- Class ordering attempts to satisfy inheritance; if a base class is missing or circular, models are still emitted to allow forward references where possible.
- Keep ontology files modular and ensure every entity/property includes a `description` field, per project guidelines.

#### Validation
After modifying the ontology, run all converter scripts to ensure generated outputs remain valid, per the project guidelines.