#!/usr/bin/env python3
"""
Basic usage example for temporal-metabolic.

This script demonstrates:
1. Loading a metabolic model
2. Annotating with temporal information
3. Filtering for different eras
4. Comparing model capabilities
"""

import cobra
from temporal import annotate_model, filter_model_for_era
import pandas as pd


def main():
    """Run basic temporal validation workflow."""
    
    print("="*60)
    print("TEMPORAL-METABOLIC: Basic Usage Example")
    print("="*60)
    
    # Step 1: Load a model
    print("\n1. Loading E. coli model from BiGG...")
    model = cobra.io.load_model("iML1515")
    print(f"   Model: {model.id}")
    print(f"   Reactions: {len(model.reactions)}")
    print(f"   Metabolites: {len(model.metabolites)}")
    
    # Step 2: Annotate with temporal information
    print("\n2. Annotating oxygen-related reactions...")
    annotations = annotate_model(model, focus_on_o2=True)
    
    # Count annotations by category
    categories = {}
    for ann in annotations.reactions.values():
        cat = ann.category or "unknown"
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"   Total O₂ reactions annotated: {len(annotations.reactions)}")
    print("\n   Categories found:")
    for cat, count in sorted(categories.items()):
        print(f"     - {cat}: {count}")
    
    # Count by era appropriateness
    archean_count = sum(1 for a in annotations.reactions.values() if a.archean_appropriate)
    print(f"\n   Archean-appropriate: {archean_count}")
    print(f"   Post-Archean: {len(annotations.reactions) - archean_count}")
    
    # Step 3: Create era-specific models
    print("\n3. Creating era-specific models...")
    
    results = []
    for era in ["archean", "proterozoic", "phanerozoic"]:
        print(f"\n   Filtering for {era.capitalize()} era...")
        
        era_model, stats = filter_model_for_era(
            model,
            annotations,
            era_name=era,
            removal_strategy="remove"
        )
        
        # Test growth capabilities
        with era_model:
            # Anaerobic growth
            if "EX_o2_e" in era_model.reactions:
                era_model.reactions.EX_o2_e.lower_bound = 0
            anaerobic_growth = era_model.optimize().objective_value
            
            # Aerobic growth (if possible)
            if "EX_o2_e" in era_model.reactions:
                era_model.reactions.EX_o2_e.lower_bound = -20
                aerobic_growth = era_model.optimize().objective_value
            else:
                aerobic_growth = 0
        
        result = {
            "Era": era.capitalize(),
            "Reactions": len(era_model.reactions),
            "Removed": len(stats['removed_reactions']),
            "O₂ Pathways": stats['appropriate_count'],
            "Anaerobic Growth": f"{anaerobic_growth:.4f}",
            "Aerobic Growth": f"{aerobic_growth:.4f}"
        }
        results.append(result)
        
        print(f"     - Reactions: {len(era_model.reactions)}")
        print(f"     - Removed: {len(stats['removed_reactions'])}")
        print(f"     - O₂ pathways remaining: {stats['appropriate_count']}")
    
    # Step 4: Display comparison table
    print("\n4. Era Comparison Summary:")
    print("-"*60)
    
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    
    # Step 5: Conservative filtering example
    print("\n5. Conservative filtering (high confidence only)...")
    
    conservative_model, conservative_stats = filter_model_for_era(
        model,
        annotations,
        era_name="archean",
        removal_strategy="remove",
        min_confidence="high"
    )
    
    print(f"   Standard removal: {len(results[0]['Removed'])} reactions")
    print(f"   Conservative removal: {len(conservative_stats['removed_reactions'])} reactions")
    
    if 'confidence_downgraded' in conservative_stats:
        print(f"   Downgraded to constrain: {len(conservative_stats['confidence_downgraded'])} reactions")
    
    # Step 6: Show what was removed
    print("\n6. Example removed reactions (Archean filtering):")
    
    for rxn_id in list(stats['removed_reactions'])[:5]:
        if rxn_id in annotations.reactions:
            ann = annotations.reactions[rxn_id]
            rxn = model.reactions.get_by_id(rxn_id)
            print(f"\n   {rxn_id}: {rxn.name}")
            print(f"     Category: {ann.category}")
            print(f"     Age: ~{ann.estimated_age_ga} Ga")
            print(f"     Confidence: {ann.evidence.confidence}")
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)
    print("\nKey Findings:")
    print(f"• {len(annotations.reactions)} oxygen pathways identified")
    print(f"• Only {archean_count} appropriate for Archean (>2.5 Ga)")
    print(f"• {(1 - archean_count/len(annotations.reactions))*100:.1f}% are anachronistic")
    print("\nThis demonstrates the prevalence of network complexity artifacts")
    print("in modern metabolic models when applied to early Earth studies.")


if __name__ == "__main__":
    main()