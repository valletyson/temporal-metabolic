"""
Filter metabolic models to create era-specific versions.
Remove or constrain reactions based on temporal appropriateness.
"""

import cobra
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import warnings
from .schema import ReactionTemporalAnnotation, TemporalDatabase
from .annotate import annotate_model

# Era cutoffs in billions of years ago (Ga)
ERA_CUTOFFS = {
    "archean": 2.5,
    "proterozoic": 0.541,
    "phanerozoic": 0.0,
    "modern": 0.0
}

def filter_model_for_era(
    model: cobra.Model,
    annotations: TemporalDatabase,
    era_name: str = None,
    era_cutoff_ga: float = None,
    removal_strategy: str = "remove",  # "remove", "constrain", or "mark"
    preserve_essential: bool = True,
    min_confidence: str = None  # "high", "medium", "low", "very_low"
) -> Tuple[cobra.Model, Dict]:
    """
    Filter a metabolic model to be appropriate for a specific geological era.
    
    Args:
        model: The metabolic model to filter
        annotations: Temporal annotations database
        era_name: Name of era (archean, proterozoic, phanerozoic)
        era_cutoff_ga: Custom cutoff in Ga (overrides era_name)
        removal_strategy: How to handle inappropriate reactions
            - "remove": Delete reactions from model
            - "constrain": Set flux bounds to 0
            - "mark": Just mark reactions (no modification)
        preserve_essential: Keep reactions essential for growth
        min_confidence: Minimum confidence level for removal (if set, low confidence → constrain/mark)
    
    Returns:
        Filtered model and statistics dictionary
    """
    
    # Determine cutoff
    if era_cutoff_ga is None:
        if era_name is None:
            raise ValueError("Must provide either era_name or era_cutoff_ga")
        era_cutoff_ga = ERA_CUTOFFS.get(era_name.lower())
        if era_cutoff_ga is None:
            raise ValueError(f"Unknown era: {era_name}. Use: {list(ERA_CUTOFFS.keys())}")
    
    # Create a copy of the model (work around COBRApy copy issues)
    try:
        filtered_model = model.copy()
    except TypeError:
        # Fallback for COBRApy version issues
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
            cobra.io.write_sbml_model(model, tmp.name)
            filtered_model = cobra.io.read_sbml_model(tmp.name)
            import os
            os.unlink(tmp.name)
    
    # Track statistics
    stats = {
        "era": era_name or f">{era_cutoff_ga} Ga",
        "cutoff_ga": era_cutoff_ga,
        "total_reactions": len(model.reactions),
        "removed_reactions": [],
        "constrained_reactions": [],
        "preserved_essential": [],
        "inappropriate_count": 0,
        "appropriate_count": 0,
        "unknown_count": 0
    }
    
    # Find essential reactions if preserving
    essential_reactions = set()
    if preserve_essential and removal_strategy != "mark":
        try:
            # Test for growth capability
            solution = filtered_model.optimize()
            if solution.status == "optimal" and solution.objective_value > 0:
                # Find essential reactions via single deletions
                for rxn in filtered_model.reactions:
                    if rxn.id in annotations.reactions:
                        with filtered_model as temp_model:
                            temp_model.reactions.get_by_id(rxn.id).knock_out()
                            temp_solution = temp_model.optimize()
                            if temp_solution.status != "optimal" or temp_solution.objective_value < 0.01:
                                essential_reactions.add(rxn.id)
        except Exception as e:
            warnings.warn(f"Could not determine essential reactions: {e}")
    
    # Define confidence hierarchy for gating
    confidence_levels = {
        "high": 3,
        "medium": 2,
        "low": 1,
        "very_low": 0
    }
    min_conf_level = confidence_levels.get(min_confidence, -1) if min_confidence else -1
    
    # Process each reaction
    reactions_to_remove = []
    reactions_to_constrain = []
    
    for rxn in filtered_model.reactions:
        # Check if reaction has annotation
        if rxn.id not in annotations.reactions:
            stats["unknown_count"] += 1
            continue
        
        annotation = annotations.reactions[rxn.id]
        
        # Check if appropriate for era
        is_appropriate = False
        if era_name == "archean" and annotation.archean_appropriate is not None:
            is_appropriate = annotation.archean_appropriate
        elif era_name == "proterozoic" and annotation.proterozoic_appropriate is not None:
            is_appropriate = annotation.proterozoic_appropriate
        elif era_name == "phanerozoic" and annotation.phanerozoic_appropriate is not None:
            is_appropriate = annotation.phanerozoic_appropriate
        else:
            # Use age cutoff
            is_appropriate = annotation.is_appropriate_for_era(era_cutoff_ga)
        
        if is_appropriate:
            stats["appropriate_count"] += 1
        else:
            stats["inappropriate_count"] += 1
            
            # Check if essential
            if rxn.id in essential_reactions:
                stats["preserved_essential"].append(rxn.id)
                warnings.warn(f"Preserving essential but inappropriate reaction: {rxn.id}")
                continue
            
            # Check confidence level for gating
            reaction_confidence = annotation.evidence.confidence if annotation.evidence else "medium"
            reaction_conf_level = confidence_levels.get(reaction_confidence, 1)
            
            # Determine actual strategy based on confidence
            effective_strategy = removal_strategy
            if min_confidence and reaction_conf_level < min_conf_level:
                # Low confidence: be conservative
                if removal_strategy == "remove":
                    effective_strategy = "constrain"  # Downgrade to constrain
                    stats.setdefault("confidence_downgraded", []).append(rxn.id)
            
            # Apply strategy
            if effective_strategy == "remove":
                reactions_to_remove.append(rxn.id)
                stats["removed_reactions"].append(rxn.id)
            elif effective_strategy == "constrain":
                reactions_to_constrain.append(rxn.id)
                stats["constrained_reactions"].append(rxn.id)
            elif effective_strategy == "mark":
                # Just tracking, no modification
                pass
    
    # Apply modifications
    if removal_strategy == "remove":
        for rxn_id in reactions_to_remove:
            try:
                filtered_model.reactions.get_by_id(rxn_id).remove_from_model()
            except KeyError:
                warnings.warn(f"Could not remove reaction {rxn_id}")
    
    elif removal_strategy == "constrain":
        for rxn_id in reactions_to_constrain:
            try:
                rxn = filtered_model.reactions.get_by_id(rxn_id)
                rxn.lower_bound = 0
                rxn.upper_bound = 0
            except KeyError:
                warnings.warn(f"Could not constrain reaction {rxn_id}")
    
    # Update model metadata
    filtered_model.id = f"{model.id}_{era_name or 'filtered'}" if hasattr(model, 'id') else f"filtered_{era_name}"
    filtered_model.name = f"{model.name if hasattr(model, 'name') else 'Model'} - {era_name or f'>{era_cutoff_ga} Ga'}"
    
    # Add filtering information to model annotation
    if not hasattr(filtered_model, 'notes'):
        filtered_model.notes = {}
    filtered_model.notes['temporal_filter'] = {
        'era': era_name or f">{era_cutoff_ga} Ga",
        'cutoff_ga': era_cutoff_ga,
        'removal_strategy': removal_strategy,
        'statistics': stats
    }
    
    return filtered_model, stats

def create_era_series(
    model: cobra.Model,
    annotations: TemporalDatabase = None,
    eras: List[str] = None,
    removal_strategy: str = "remove"
) -> Dict[str, Tuple[cobra.Model, Dict]]:
    """
    Create a series of models for different geological eras.
    
    Args:
        model: Base metabolic model
        annotations: Temporal annotations (will be generated if None)
        eras: List of era names (default: ["archean", "proterozoic", "phanerozoic"])
        removal_strategy: How to handle inappropriate reactions
    
    Returns:
        Dictionary mapping era names to (model, stats) tuples
    """
    
    if eras is None:
        eras = ["archean", "proterozoic", "phanerozoic"]
    
    if annotations is None:
        print("Generating temporal annotations...")
        annotations = annotate_model(model)
    
    era_models = {}
    
    for era in eras:
        print(f"Creating {era} model...")
        filtered_model, stats = filter_model_for_era(
            model, 
            annotations, 
            era_name=era,
            removal_strategy=removal_strategy
        )
        era_models[era] = (filtered_model, stats)
        
        print(f"  - Reactions: {len(filtered_model.reactions)}/{len(model.reactions)}")
        print(f"  - Removed: {len(stats['removed_reactions'])}")
        print(f"  - Appropriate: {stats['appropriate_count']}")
        print(f"  - Unknown: {stats['unknown_count']}")
    
    return era_models

def validate_filtered_model(
    original_model: cobra.Model,
    filtered_model: cobra.Model,
    test_conditions: Dict = None
) -> Dict:
    """
    Validate that a filtered model maintains basic functionality.
    
    Args:
        original_model: Original unfiltered model
        filtered_model: Filtered model to validate
        test_conditions: Dictionary of exchange reaction bounds to set
    
    Returns:
        Validation results dictionary
    """
    
    results = {
        "original_reactions": len(original_model.reactions),
        "filtered_reactions": len(filtered_model.reactions),
        "reactions_removed": len(original_model.reactions) - len(filtered_model.reactions),
        "original_metabolites": len(original_model.metabolites),
        "filtered_metabolites": len(filtered_model.metabolites),
        "tests": {}
    }
    
    # Test basic FBA
    try:
        original_solution = original_model.optimize()
        results["tests"]["original_growth"] = {
            "status": original_solution.status,
            "objective_value": original_solution.objective_value if original_solution.status == "optimal" else None
        }
    except Exception as e:
        results["tests"]["original_growth"] = {"status": "error", "error": str(e)}
    
    try:
        filtered_solution = filtered_model.optimize()
        results["tests"]["filtered_growth"] = {
            "status": filtered_solution.status,
            "objective_value": filtered_solution.objective_value if filtered_solution.status == "optimal" else None
        }
    except Exception as e:
        results["tests"]["filtered_growth"] = {"status": "error", "error": str(e)}
    
    # Test with specific conditions if provided
    if test_conditions:
        with original_model as orig_test, filtered_model as filt_test:
            # Apply test conditions
            for rxn_id, bounds in test_conditions.items():
                if rxn_id in orig_test.reactions:
                    rxn = orig_test.reactions.get_by_id(rxn_id)
                    if "lower" in bounds:
                        rxn.lower_bound = bounds["lower"]
                    if "upper" in bounds:
                        rxn.upper_bound = bounds["upper"]
                
                if rxn_id in filt_test.reactions:
                    rxn = filt_test.reactions.get_by_id(rxn_id)
                    if "lower" in bounds:
                        rxn.lower_bound = bounds["lower"]
                    if "upper" in bounds:
                        rxn.upper_bound = bounds["upper"]
            
            # Test under conditions
            try:
                orig_cond_solution = orig_test.optimize()
                results["tests"]["original_conditional"] = {
                    "status": orig_cond_solution.status,
                    "objective_value": orig_cond_solution.objective_value if orig_cond_solution.status == "optimal" else None
                }
            except Exception as e:
                results["tests"]["original_conditional"] = {"status": "error", "error": str(e)}
            
            try:
                filt_cond_solution = filt_test.optimize()
                results["tests"]["filtered_conditional"] = {
                    "status": filt_cond_solution.status,
                    "objective_value": filt_cond_solution.objective_value if filt_cond_solution.status == "optimal" else None
                }
            except Exception as e:
                results["tests"]["filtered_conditional"] = {"status": "error", "error": str(e)}
    
    # Check for orphan metabolites
    original_orphans = set()
    filtered_orphans = set()
    
    for met in original_model.metabolites:
        if len(met.reactions) == 0:
            original_orphans.add(met.id)
    
    for met in filtered_model.metabolites:
        if len(met.reactions) == 0:
            filtered_orphans.add(met.id)
    
    results["orphan_metabolites"] = {
        "original": len(original_orphans),
        "filtered": len(filtered_orphans),
        "new_orphans": len(filtered_orphans - original_orphans)
    }
    
    return results


def main():
    """Main entry point for temporal-filter command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Filter metabolic models for specific geological eras"
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        help="Path to SBML model file"
    )
    parser.add_argument(
        "--annotations", "-a",
        required=True,
        help="Path to temporal annotations (YAML or JSON)"
    )
    parser.add_argument(
        "--era", "-e",
        choices=["archean", "proterozoic", "phanerozoic"],
        required=True,
        help="Geological era to filter for"
    )
    parser.add_argument(
        "--strategy", "-s",
        choices=["remove", "constrain", "mark"],
        default="remove",
        help="How to handle inappropriate reactions (default: remove)"
    )
    parser.add_argument(
        "--out", "-o",
        required=True,
        help="Output path for filtered model (SBML)"
    )
    parser.add_argument(
        "--preserve-essential",
        action="store_true",
        help="Preserve reactions essential for growth"
    )
    parser.add_argument(
        "--min-confidence",
        choices=["high", "medium", "low", "very_low"],
        help="Minimum confidence for removal (lower confidence → constrain/mark)"
    )
    parser.add_argument(
        "--stats",
        help="Output path for filtering statistics (YAML)"
    )
    
    args = parser.parse_args()
    
    # Load model
    print(f"Loading model from {args.model}...")
    model = cobra.io.read_sbml_model(args.model)
    print(f"  Model: {model.id if hasattr(model, 'id') else 'Unknown'}")
    print(f"  Reactions: {len(model.reactions)}")
    
    # Load annotations
    print(f"Loading annotations from {args.annotations}...")
    import yaml
    import json
    from pathlib import Path
    
    ann_path = Path(args.annotations)
    if ann_path.suffix.lower() == '.json':
        with open(ann_path) as f:
            data = json.load(f)
    else:
        with open(ann_path) as f:
            data = yaml.safe_load(f)
    
    # Convert to TemporalDatabase
    from .schema import TemporalDatabase
    database = TemporalDatabase(**data)
    print(f"  Loaded {len(database.reactions)} reaction annotations")
    
    # Filter model
    print(f"Filtering for {args.era} era using {args.strategy} strategy...")
    if args.min_confidence:
        print(f"  Minimum confidence: {args.min_confidence}")
    filtered_model, stats = filter_model_for_era(
        model,
        database,
        era_name=args.era,
        removal_strategy=args.strategy,
        preserve_essential=args.preserve_essential,
        min_confidence=args.min_confidence
    )
    
    # Print statistics
    print(f"\nFiltering Results:")
    print(f"  Original reactions: {stats['total_reactions']}")
    print(f"  Appropriate reactions: {stats['appropriate_count']}")
    print(f"  Inappropriate reactions: {stats['inappropriate_count']}")
    
    if args.strategy == "remove":
        print(f"  Removed reactions: {len(stats['removed_reactions'])}")
    elif args.strategy == "constrain":
        print(f"  Constrained reactions: {len(stats['constrained_reactions'])}")
    
    if stats['preserved_essential']:
        print(f"  Preserved essential: {len(stats['preserved_essential'])}")
    
    print(f"  Final model reactions: {len(filtered_model.reactions)}")
    
    # Save filtered model
    cobra.io.write_sbml_model(filtered_model, args.out)
    print(f"\nSaved filtered model to {args.out}")
    
    # Save statistics if requested
    if args.stats:
        with open(args.stats, 'w') as f:
            yaml.dump(stats, f, default_flow_style=False)
        print(f"Saved statistics to {args.stats}")


if __name__ == "__main__":
    main()