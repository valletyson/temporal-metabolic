"""
Annotate metabolic model reactions with temporal information.
Maps reactions to evolutionary ages based on categories and patterns.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cobra
from datetime import datetime
from .schema import (
    ReactionTemporalAnnotation, 
    Evidence,
    ModelTemporalMetadata,
    TemporalDatabase
)

def load_category_defaults(path: str = None) -> Tuple[Dict, Dict]:
    """Load category defaults and reaction overrides from YAML."""
    if path is None:
        path = Path(__file__).parent / "sources" / "oxygen_pathway_ages.yaml"
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    return data.get("categories", {}), data.get("reactions", {})

def categorize_reaction(rxn: cobra.Reaction, 
                        categories: Dict, 
                        overrides: Dict) -> Optional[str]:
    """Determine the category of a reaction based on ID, name, and patterns."""
    
    # Check for explicit override by ID
    if rxn.id in overrides:
        return overrides[rxn.id].get("category")
    
    # Pattern matching for categories
    rxn_id_lower = rxn.id.lower()
    rxn_name_lower = rxn.name.lower() if rxn.name else ""
    
    # Photosystem II patterns
    if any(pattern in rxn_id_lower for pattern in ['ps2', 'psii', 'photosystem']):
        return 'photosystem_ii'
    if 'photosystem' in rxn_name_lower and 'ii' in rxn_name_lower:
        return 'photosystem_ii'
    
    # Catalase patterns
    if 'cat' in rxn_id_lower and 'cata' not in rxn_id_lower:
        return 'catalases'
    if 'catalase' in rxn_name_lower:
        return 'catalases'
    
    # Peroxidase patterns
    if 'perox' in rxn_id_lower or 'peroxidase' in rxn_name_lower:
        return 'peroxidases'
    
    # Alternative oxidase patterns
    oxidase_patterns = ['oxidase', 'oxidas', 'oxid', 'oxo']
    if any(pattern in rxn_id_lower for pattern in oxidase_patterns):
        # Exclude if it's catalase or peroxidase
        if 'cat' not in rxn_id_lower and 'perox' not in rxn_id_lower:
            return 'alternative_oxidases'
    
    # Default to other if produces O2
    for met, coeff in rxn.metabolites.items():
        if coeff > 0:  # Product
            if any(pattern in met.id.lower() for pattern in ['o2', 'oxygen']) and 'co2' not in met.id.lower():
                return 'other_o2_producers'
    
    return None

def annotate_reaction(rxn: cobra.Reaction,
                      categories: Dict,
                      overrides: Dict,
                      curator: str = "auto") -> Optional[ReactionTemporalAnnotation]:
    """Create temporal annotation for a single reaction."""
    
    # Determine category
    category = categorize_reaction(rxn, categories, overrides)
    if category is None:
        return None
    
    # Get category defaults
    cat_info = categories.get(category, {})
    
    # Check for reaction-specific overrides
    rxn_override = overrides.get(rxn.id, {})
    
    # Build evidence
    evidence = Evidence(
        citations=cat_info.get("evidence", {}).get("citations", []),
        notes=cat_info.get("evidence", {}).get("notes", ""),
        confidence=cat_info.get("confidence", "medium")
    )
    
    # Create annotation
    annotation = ReactionTemporalAnnotation(
        reaction_id=rxn.id,
        category=category,
        estimated_age_ga=rxn_override.get("estimated_age_ga", cat_info.get("estimated_age_ga")),
        age_min_ga=rxn_override.get("age_min_ga", cat_info.get("age_min_ga")),
        age_max_ga=rxn_override.get("age_max_ga", cat_info.get("age_max_ga")),
        archean_appropriate=rxn_override.get("archean_appropriate", cat_info.get("archean_appropriate")),
        proterozoic_appropriate=rxn_override.get("proterozoic_appropriate", cat_info.get("proterozoic_appropriate")),
        phanerozoic_appropriate=rxn_override.get("phanerozoic_appropriate", cat_info.get("phanerozoic_appropriate", True)),
        evidence=evidence,
        last_updated=datetime.now(),
        curator=curator
    )
    
    return annotation

def annotate_model(model: cobra.Model,
                   categories: Dict = None,
                   overrides: Dict = None,
                   focus_on_o2: bool = True) -> TemporalDatabase:
    """Annotate all reactions in a model with temporal information."""
    
    if categories is None or overrides is None:
        categories, overrides = load_category_defaults()
    
    database = TemporalDatabase(
        version="0.1.0",
        last_updated=datetime.now(),
        description=f"Temporal annotations for {model.id if hasattr(model, 'id') else 'model'}"
    )
    
    # Create model metadata
    model_meta = ModelTemporalMetadata(
        model_id=model.id if hasattr(model, 'id') else "unknown",
        model_name=model.name if hasattr(model, 'name') else None,
        total_reactions=len(model.reactions)
    )
    
    # Annotate reactions
    annotations = []
    for rxn in model.reactions:
        # Skip if focusing on O2 and reaction doesn't involve O2
        if focus_on_o2:
            has_o2 = False
            for met in rxn.metabolites:
                if any(pattern in met.id.lower() for pattern in ['o2', 'oxygen']) and 'co2' not in met.id.lower():
                    has_o2 = True
                    break
            if not has_o2:
                continue
        
        annotation = annotate_reaction(rxn, categories, overrides)
        if annotation:
            database.add_reaction(annotation)
            annotations.append(annotation)
    
    # Calculate coverage metrics
    model_meta.calculate_coverage(annotations)
    database.models[model_meta.model_id] = model_meta
    
    return database

def compare_annotations(db1: TemporalDatabase, db2: TemporalDatabase) -> Dict:
    """Compare two temporal annotation databases."""
    
    results = {
        "total_reactions_db1": len(db1.reactions),
        "total_reactions_db2": len(db2.reactions),
        "common_reactions": 0,
        "agreement_on_archean": 0,
        "disagreement_on_archean": 0,
        "unique_to_db1": [],
        "unique_to_db2": [],
        "disagreements": []
    }
    
    common_ids = set(db1.reactions.keys()) & set(db2.reactions.keys())
    results["common_reactions"] = len(common_ids)
    
    for rxn_id in common_ids:
        ann1 = db1.reactions[rxn_id]
        ann2 = db2.reactions[rxn_id]
        
        if ann1.archean_appropriate == ann2.archean_appropriate:
            results["agreement_on_archean"] += 1
        else:
            results["disagreement_on_archean"] += 1
            results["disagreements"].append({
                "reaction_id": rxn_id,
                "db1_archean": ann1.archean_appropriate,
                "db2_archean": ann2.archean_appropriate,
                "db1_age": ann1.estimated_age_ga,
                "db2_age": ann2.estimated_age_ga
            })
    
    results["unique_to_db1"] = list(set(db1.reactions.keys()) - common_ids)
    results["unique_to_db2"] = list(set(db2.reactions.keys()) - common_ids)
    
    return results


def main():
    """Main entry point for temporal-annotate command."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Annotate metabolic model reactions with temporal information"
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        help="Path to SBML model file"
    )
    parser.add_argument(
        "--db", "-d",
        default=None,
        help="Path to temporal database YAML (default: built-in oxygen_pathway_ages.yaml)"
    )
    parser.add_argument(
        "--out", "-o",
        required=True,
        help="Output path for annotations (YAML or JSON based on extension)"
    )
    parser.add_argument(
        "--only-o2",
        action="store_true",
        help="Only annotate O2-related reactions"
    )
    parser.add_argument(
        "--curator",
        default="CLI",
        help="Curator name for annotations"
    )
    
    args = parser.parse_args()
    
    # Load model
    print(f"Loading model from {args.model}...")
    model = cobra.io.read_sbml_model(args.model)
    print(f"  Model: {model.id if hasattr(model, 'id') else 'Unknown'}")
    print(f"  Reactions: {len(model.reactions)}")
    
    # Load or use default categories
    if args.db:
        print(f"Loading temporal database from {args.db}...")
        categories, overrides = load_category_defaults(args.db)
    else:
        print("Using built-in temporal database...")
        categories, overrides = load_category_defaults()
    
    # Annotate model
    print(f"Annotating model reactions...")
    database = annotate_model(
        model,
        categories=categories,
        overrides=overrides,
        focus_on_o2=args.only_o2
    )
    
    print(f"  Annotated reactions: {len(database.reactions)}")
    
    # Count by appropriateness
    archean_count = sum(1 for ann in database.reactions.values() if ann.archean_appropriate)
    print(f"  Archean-appropriate: {archean_count}")
    print(f"  Post-Archean: {len(database.reactions) - archean_count}")
    
    # Save output
    out_path = Path(args.out)
    if out_path.suffix.lower() == '.json':
        database.export_to_json(str(out_path))
        print(f"Saved annotations to {out_path} (JSON)")
    else:
        database.export_to_yaml(str(out_path))
        print(f"Saved annotations to {out_path} (YAML)")


if __name__ == "__main__":
    main()