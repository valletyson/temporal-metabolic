#!/usr/bin/env python3
"""
Demonstration of the temporal modeling framework.
Shows how to annotate models and create era-specific versions.
"""

import sys
from pathlib import Path
import cobra
import yaml
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from temporal.annotate import annotate_model, load_category_defaults
from temporal.filter import filter_model_for_era, create_era_series, validate_filtered_model
from temporal.schema import TemporalDatabase

def demo_basic_annotation():
    """Demonstrate basic model annotation."""
    print("\n" + "="*60)
    print("TEMPORAL ANNOTATION DEMONSTRATION")
    print("="*60)
    
    # Load a model (using the Synechocystis model as example)
    model_path = Path(__file__).parent.parent / "models" / "eSyn6803.xml"
    if not model_path.exists():
        print(f"Model not found at {model_path}")
        return None
    
    print(f"\n1. Loading model from {model_path}")
    model = cobra.io.read_sbml_model(str(model_path))
    print(f"   Model: {model.id if hasattr(model, 'id') else 'Unknown'}")
    print(f"   Reactions: {len(model.reactions)}")
    print(f"   Metabolites: {len(model.metabolites)}")
    
    # Annotate the model
    print("\n2. Annotating model with temporal information...")
    database = annotate_model(model, focus_on_o2=True)
    
    print(f"   Annotated reactions: {len(database.reactions)}")
    print(f"   Model metadata stored: {len(database.models)}")
    
    # Show annotation statistics
    if model.id in database.models:
        meta = database.models[model.id]
        print(f"\n3. Annotation Statistics:")
        print(f"   Total reactions: {meta.total_reactions}")
        print(f"   Annotated: {meta.annotated_reactions}")
        print(f"   Coverage: {meta.annotation_coverage:.1%}")
        print(f"   Archean-appropriate: {meta.archean_appropriate_count}")
        print(f"   High confidence: {meta.high_confidence_fraction:.1%}")
    
    # Show some example annotations
    print("\n4. Example Annotations:")
    for i, (rxn_id, ann) in enumerate(list(database.reactions.items())[:5]):
        print(f"\n   Reaction: {rxn_id}")
        print(f"   Category: {ann.category}")
        print(f"   Estimated age: {ann.estimated_age_ga} Ga")
        print(f"   Archean appropriate: {ann.archean_appropriate}")
        print(f"   Confidence: {ann.evidence.confidence}")
    
    return database

def demo_era_filtering(database: TemporalDatabase = None):
    """Demonstrate filtering models for different eras."""
    print("\n" + "="*60)
    print("ERA-SPECIFIC MODEL FILTERING")
    print("="*60)
    
    # Load model
    model_path = Path(__file__).parent.parent / "models" / "eSyn6803.xml"
    if not model_path.exists():
        print(f"Model not found at {model_path}")
        return
    
    model = cobra.io.read_sbml_model(str(model_path))
    
    if database is None:
        print("\n1. Generating annotations...")
        database = annotate_model(model, focus_on_o2=True)
    
    # Create Archean model
    print("\n2. Creating Archean-appropriate model (>2.5 Ga)...")
    archean_model, archean_stats = filter_model_for_era(
        model,
        database,
        era_name="archean",
        removal_strategy="remove",
        preserve_essential=False  # For demonstration
    )
    
    print(f"   Original reactions: {archean_stats['total_reactions']}")
    print(f"   Appropriate reactions: {archean_stats['appropriate_count']}")
    print(f"   Removed reactions: {len(archean_stats['removed_reactions'])}")
    print(f"   Unknown reactions: {archean_stats['unknown_count']}")
    
    # Show what was removed
    if archean_stats['removed_reactions']:
        print(f"\n   Examples of removed reactions:")
        for rxn_id in archean_stats['removed_reactions'][:5]:
            if rxn_id in database.reactions:
                ann = database.reactions[rxn_id]
                print(f"   - {rxn_id} ({ann.category}, ~{ann.estimated_age_ga} Ga)")
    
    # Validate the filtered model
    print("\n3. Validating filtered model...")
    validation = validate_filtered_model(model, archean_model)
    
    print(f"   Reactions: {validation['filtered_reactions']}/{validation['original_reactions']}")
    print(f"   Metabolites: {validation['filtered_metabolites']}/{validation['original_metabolites']}")
    print(f"   Orphan metabolites: {validation['orphan_metabolites']['new_orphans']} new")
    
    if 'original_growth' in validation['tests']:
        orig_growth = validation['tests']['original_growth']
        print(f"   Original model growth: {orig_growth['status']}")
        if orig_growth['objective_value']:
            print(f"     Objective: {orig_growth['objective_value']:.4f}")
    
    if 'filtered_growth' in validation['tests']:
        filt_growth = validation['tests']['filtered_growth']
        print(f"   Filtered model growth: {filt_growth['status']}")
        if filt_growth['objective_value']:
            print(f"     Objective: {filt_growth['objective_value']:.4f}")
    
    return archean_model, archean_stats

def demo_era_series():
    """Create models for multiple geological eras."""
    print("\n" + "="*60)
    print("CREATING ERA SERIES")
    print("="*60)
    
    # Load model
    model_path = Path(__file__).parent.parent / "models" / "eSyn6803.xml"
    if not model_path.exists():
        print(f"Model not found at {model_path}")
        return
    
    model = cobra.io.read_sbml_model(str(model_path))
    
    print(f"\n1. Creating models for geological eras...")
    era_models = create_era_series(
        model,
        eras=["archean", "proterozoic", "phanerozoic"],
        removal_strategy="remove"
    )
    
    print(f"\n2. Era Model Summary:")
    print(f"   {'Era':<15} {'Reactions':<12} {'Removed':<12} {'Appropriate':<12}")
    print(f"   {'-'*51}")
    
    for era, (era_model, stats) in era_models.items():
        removed = len(stats['removed_reactions'])
        appropriate = stats['appropriate_count']
        total = len(era_model.reactions)
        print(f"   {era.capitalize():<15} {total:<12} {removed:<12} {appropriate:<12}")
    
    # Save one model as example
    print(f"\n3. Saving Archean model to SBML...")
    archean_model, _ = era_models["archean"]
    output_path = Path(__file__).parent.parent / "models" / "archean_synechocystis.xml"
    cobra.io.write_sbml_model(archean_model, str(output_path))
    print(f"   Saved to: {output_path}")
    
    return era_models

def demo_export_database():
    """Export the temporal database to various formats."""
    print("\n" + "="*60)
    print("EXPORTING TEMPORAL DATABASE")
    print("="*60)
    
    # Load model and create annotations
    model_path = Path(__file__).parent.parent / "models" / "eSyn6803.xml"
    if not model_path.exists():
        print(f"Model not found at {model_path}")
        return
    
    model = cobra.io.read_sbml_model(str(model_path))
    database = annotate_model(model, focus_on_o2=True)
    
    # Export to YAML
    print("\n1. Exporting to YAML...")
    yaml_path = Path(__file__).parent.parent / "data" / "temporal_annotations.yaml"
    database.export_to_yaml(str(yaml_path))
    print(f"   Saved to: {yaml_path}")
    
    # Export to JSON
    print("\n2. Exporting to JSON...")
    json_path = Path(__file__).parent.parent / "data" / "temporal_annotations.json"
    database.export_to_json(str(json_path))
    print(f"   Saved to: {json_path}")
    
    # Create summary CSV
    print("\n3. Creating summary CSV...")
    import pandas as pd
    
    summary_data = []
    for rxn_id, ann in database.reactions.items():
        summary_data.append({
            "reaction_id": rxn_id,
            "category": ann.category,
            "estimated_age_ga": ann.estimated_age_ga,
            "archean_appropriate": ann.archean_appropriate,
            "confidence": ann.evidence.confidence
        })
    
    df = pd.DataFrame(summary_data)
    csv_path = Path(__file__).parent.parent / "data" / "temporal_annotations_summary.csv"
    df.to_csv(csv_path, index=False)
    print(f"   Saved to: {csv_path}")
    print(f"   Total reactions: {len(df)}")
    
    # Show category breakdown
    print("\n4. Category Breakdown:")
    category_counts = df['category'].value_counts()
    for category, count in category_counts.items():
        archean_count = len(df[(df['category'] == category) & (df['archean_appropriate'] == True)])
        print(f"   {category}: {count} reactions ({archean_count} Archean-appropriate)")
    
    return database

def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("TEMPORAL MODELING FRAMEWORK DEMONSTRATION")
    print("="*60)
    print("\nThis demo shows how to:")
    print("1. Annotate metabolic models with temporal information")
    print("2. Filter models for specific geological eras")
    print("3. Create era-specific model series")
    print("4. Export temporal databases")
    
    # Run demonstrations
    database = demo_basic_annotation()
    
    if database:
        demo_era_filtering(database)
        demo_era_series()
        demo_export_database()
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nThe temporal modeling framework provides:")
    print("- Systematic annotation of reaction evolutionary ages")
    print("- Era-specific model filtering capabilities")
    print("- Validation tools for filtered models")
    print("- Export functionality for sharing annotations")
    print("\nUse this framework to create historically-accurate metabolic models!")

if __name__ == "__main__":
    main()