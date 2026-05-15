import argparse
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from decimal import Decimal

def parse_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
    with open(file_path, 'r') as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"Error parsing {file_path}: {exc}")
            return None

def map_type(ontology_type: str, format: Optional[str] = None) -> str:
    mapping = {
        'string': 'str',
        'number': 'float',
        'integer': 'int',
        'boolean': 'bool',
        'object': 'Dict[str, Any]',
        'array': 'List[Any]',
    }
    
    if ontology_type == 'string':
        if format == 'date':
            return 'date'
        if format == 'date-time':
            return 'datetime'

    if ontology_type == 'number' and format == 'decimal':
        return 'Decimal'

    if ontology_type in mapping:
        return mapping[ontology_type]

    # Preserve custom ontology value-object names such as Country or Currency.
    if ontology_type and ontology_type[:1].isupper():
        return ontology_type

    return 'Any'

def get_ref_name(ref_path: str) -> str:
    # Extracts entity name from common_ontology or $ref
    # e.g., "../common/FinancialInstrumentBase.yml#/ontology/entities/InterestRate" -> "InterestRate"
    return ref_path.split('/')[-1]

def generate_pydantic_code(all_entities: Dict[str, Any]) -> str:
    lines = [
        "from __future__ import annotations",
        "from typing import List, Optional, Any, Union, Dict",
        "from datetime import date, datetime",
        "from decimal import Decimal",
        "from pydantic import BaseModel, Field, RootModel",
        "from enum import Enum",
        ""
    ]
    
    # Sort entities to handle inheritance
    defined = set(["BaseModel", "Enum", "RootModel", "Any", "str", "float", "int", "bool", "date", "datetime", "List", "Optional", "Union", "Dict", "Decimal"])
    remaining = list(all_entities.keys())
    ordered_entities = []
    
    while remaining:
        progress = False
        for entity_name in list(remaining):
            entity_data = all_entities[entity_name]
            
            # Check bases
            bases = []
            is_a = entity_data.get('is_a')
            if is_a:
                bases.append(is_a)
            
            composition = entity_data.get('composition', {})
            if isinstance(composition, dict):
                all_of = composition.get('all_of', [])
                for base in all_of:
                    if base != entity_name and base not in bases:
                        bases.append(base)
            
            if all(base in defined for base in bases):
                ordered_entities.append(entity_name)
                defined.add(entity_name)
                remaining.remove(entity_name)
                progress = True
        
        if not progress:
            # Circular dependency or missing base, just add the rest and hope forward refs handle it
            # (Inheritance doesn't work with forward refs in Python, but we must proceed)
            ordered_entities.extend(remaining)
            break

    for entity_name in ordered_entities:
        entity_data = all_entities[entity_name]
        if not isinstance(entity_data, dict):
            continue
            
        description = entity_data.get('description', '')
        enum_values = entity_data.get('enum')
        
        if enum_values:
            lines.append(f"class {entity_name}(str, Enum):")
            if description:
                clean_desc = description.replace('"""', "'''")
                lines.append(f'    """\n    {clean_desc}\n    """')
            for val in enum_values:
                # Ensure the enum key is a valid Python identifier
                safe_key = val.replace('-', '_').replace(' ', '_').replace('.', '_').replace('/', '_')
                if safe_key.startswith('_'):
                    # Check if it was only leading slashes/underscores
                    stripped = safe_key.lstrip('_')
                    if stripped:
                        safe_key = stripped
                    else:
                        safe_key = f"VAL_{safe_key}"
                
                if safe_key and safe_key[0].isdigit():
                    safe_key = f"_{safe_key}"
                lines.append(f"    {safe_key} = \"{val}\"")
            lines.append("")
            continue

        # Inheritance
        bases = []
        is_a = entity_data.get('is_a')
        if is_a:
            bases.append(is_a)
        
        composition = entity_data.get('composition', {})
        if isinstance(composition, dict):
            all_of = composition.get('all_of', [])
            for base in all_of:
                if base != entity_name and base not in bases:
                    bases.append(base)
        
        if not bases:
            bases = ["BaseModel"]
        
        base_str = ", ".join(bases)
        
        properties = entity_data.get('properties') or {}
        required = entity_data.get('required', [])
        
        if not properties:
            entity_type = entity_data.get('type')
            if entity_type and entity_type != 'object':
                # Use RootModel for simple types
                python_type = map_type(entity_type, entity_data.get('format'))
                lines.append(f"class {entity_name}(RootModel):")
                if description:
                    clean_desc = description.replace('"""', "'''")
                    lines.append(f'    """\n    {clean_desc}\n    """')
                lines.append(f"    root: {python_type}")
            else:
                lines.append(f"class {entity_name}({base_str}):")
                if description:
                    clean_desc = description.replace('"""', "'''")
                    lines.append(f'    """\n    {clean_desc}\n    """')
                lines.append("    pass")
            lines.append("")
            continue

        lines.append(f"class {entity_name}({base_str}):")
        if description:
            # Escape triple quotes in description
            clean_desc = description.replace('"""', "'''")
            lines.append(f'    """\n    {clean_desc}\n    """')
        
        for prop_name, prop_data in properties.items():
            if not isinstance(prop_data, dict):
                continue
                
            prop_type = "Any"
            prop_desc = prop_data.get('description', '')
            
            if 'common_ontology' in prop_data:
                prop_type = get_ref_name(prop_data['common_ontology'])
            elif 'classification_ref' in prop_data:
                prop_type = get_ref_name(prop_data['classification_ref'])
            elif '$ref' in prop_data:
                prop_type = get_ref_name(prop_data['$ref'])
            elif 'ref' in prop_data:
                prop_type = get_ref_name(prop_data['ref'])
            elif 'oneOf' in prop_data:
                types = []
                for item in prop_data['oneOf']:
                    if isinstance(item, dict) and '$ref' in item:
                        types.append(get_ref_name(item['$ref']))
                    elif isinstance(item, str):
                        types.append(item)
                if types:
                    prop_type = f"Union[{', '.join(types)}]"
            elif 'type' in prop_data:
                if prop_data['type'] == 'array':
                    items = prop_data.get('items', {})
                    if isinstance(items, dict):
                        item_type = map_type(items.get('type', 'Any'))
                        if 'common_ontology' in items:
                            item_type = get_ref_name(items['common_ontology'])
                        elif 'classification_ref' in items:
                            item_type = get_ref_name(items['classification_ref'])
                        elif 'ref' in items:
                             item_type = get_ref_name(items['ref'])
                        elif '$ref' in items:
                             item_type = get_ref_name(items['$ref'])
                        prop_type = f"List[{item_type}]"
                    else:
                        prop_type = "List[Any]"
                else:
                    prop_type = map_type(prop_data['type'], prop_data.get('format'))

            is_required = prop_name in required
            if not is_required:
                prop_type = f"Optional[{prop_type}]"
                default_val = "None"
            else:
                default_val = "..."

            field_args = []
            if prop_desc:
                # Clean up description: replace newlines with spaces and escape quotes
                clean_prop_desc = prop_desc.replace('\n', ' ').replace('"', '\\"')
                field_args.append(f'description="{clean_prop_desc}"')
            
            if field_args:
                lines.append(f"    {prop_name}: {prop_type} = Field({default_val}, {', '.join(field_args)})")
            else:
                if is_required:
                    lines.append(f"    {prop_name}: {prop_type}")
                else:
                    lines.append(f"    {prop_name}: {prop_type} = None")
        
        lines.append("")
        
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Convert ontology YAML files to a single Pydantic model file.')
    parser.add_argument('--input', '-i', default='ontology', help='Input directory containing YAML files (default: ontology)')
    parser.add_argument('--output', '-o', default='output/pydantic/models.py', help='Output file path (default: output/pydantic/models.py)')
    parser.add_argument('--clear', action='store_true', help='Clear the output file before generating new content')
    args = parser.parse_args()

    ontology_dir = Path(args.input)
    output_file = Path(args.output)
    
    if not ontology_dir.exists():
        print(f"Error: Input directory '{ontology_dir}' does not exist.")
        return

    if args.clear and output_file.exists():
        print(f"Deleting previous output file {output_file}...")
        output_file.unlink()
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    all_entities = {}
    
    # First pass: collect all entities
    for yaml_file in ontology_dir.rglob("*.yml"):
        print(f"Reading {yaml_file}...")
        data = parse_yaml(yaml_file)
        if data and 'ontology' in data:
            entities = data['ontology'].get('entities', {})
            if entities:
                # Merge entities, prefer the one with more information (e.g., type or properties)
                for name, entity_data in entities.items():
                    if name in all_entities:
                        print(f"Warning: Entity {name} duplicated in {yaml_file}")
                        # If existing entity has no type/properties but new one has, prefer new one
                        existing = all_entities[name]
                        if not existing.get('type') and not existing.get('properties') and (entity_data.get('type') or entity_data.get('properties')):
                             all_entities[name] = entity_data
                    else:
                        all_entities[name] = entity_data

    if all_entities:
        pydantic_code = generate_pydantic_code(all_entities)
        with open(output_file, 'w') as f:
            f.write(pydantic_code)
        print(f"Generated {output_file}")
    else:
        print("No entities found.")

if __name__ == "__main__":
    main()
