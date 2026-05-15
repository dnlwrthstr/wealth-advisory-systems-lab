"""Generators that produce pipeline metadata from the ontology YAML.

- `ontology_2_pydantic` — silver-tier validated Python models
- `golden_record_2_opensearch` — gold-tier OpenSearch index mappings

The ontology itself lives at the repo root in `ontology/`. These tools read
that YAML and emit code/configuration consumed by the rest of the lab.
"""
