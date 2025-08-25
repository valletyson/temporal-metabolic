# Quickstart Guide

Get up and running with `temporal-metabolic` in 5 minutes!

## Installation

```bash
pip install temporal-metabolic
```

Or install from source:
```bash
git clone https://github.com/yourusername/temporal-metabolic
cd temporal-metabolic
pip install -e .
```

## Basic Workflow

The typical workflow has three steps:

1. **Annotate** your model with temporal information
2. **Filter** for your era of interest
3. **Analyze** the results

## Example: Creating an Archean E. coli Model

### Step 1: Download a Model

```python
import cobra

# Download E. coli model from BiGG
model = cobra.io.load_model("iML1515")
print(f"Loaded {model.id}: {len(model.reactions)} reactions")
# Output: Loaded iML1515: 2712 reactions
```

### Step 2: Annotate with Temporal Information

```python
from temporal import annotate_model

# Annotate all reactions with evolutionary ages
annotations = annotate_model(model, focus_on_o2=True)

print(f"Annotated {len(annotations.reactions)} reactions")
print(f"Archean-appropriate: {sum(1 for a in annotations.reactions.values() if a.archean_appropriate)}")
# Output: Annotated 38 reactions
# Output: Archean-appropriate: 1
```

### Step 3: Filter for Archean Era

```python
from temporal import filter_model_for_era

# Create Archean-appropriate model (>2.5 Ga)
archean_model, stats = filter_model_for_era(
    model,
    annotations,
    era_name="archean",
    removal_strategy="remove"
)

print(f"Original: {stats['total_reactions']} reactions")
print(f"Removed: {len(stats['removed_reactions'])} anachronistic reactions")
print(f"Archean model: {len(archean_model.reactions)} reactions")
# Output: Original: 2712 reactions
# Output: Removed: 37 anachronistic reactions  
# Output: Archean model: 2675 reactions
```

### Step 4: Compare Models

```python
# Test growth under anaerobic conditions
with model:
    model.reactions.EX_o2_e.lower_bound = 0  # No oxygen
    original_growth = model.optimize().objective_value

with archean_model:
    archean_model.reactions.EX_o2_e.lower_bound = 0
    archean_growth = archean_model.optimize().objective_value

print(f"Original growth: {original_growth:.4f}")
print(f"Archean growth: {archean_growth:.4f}")
print(f"Growth ratio: {archean_growth/original_growth:.2f}x")
```

## Command Line Usage

The same workflow using CLI tools:

```bash
# Step 1: Get a model (using cobrapy in Python first)
python -c "import cobra; cobra.io.save_json_model(cobra.io.load_model('iML1515'), 'iML1515.json')"

# Step 2: Annotate
temporal-annotate --model iML1515.json --out iML1515_annotations.yaml --only-o2

# Step 3: Filter for Archean
temporal-filter \
    --model iML1515.json \
    --annotations iML1515_annotations.yaml \
    --era archean \
    --strategy remove \
    --out iML1515_archean.xml \
    --stats archean_stats.yaml

# View statistics
cat archean_stats.yaml
```

## Conservative Filtering

For publication-ready results, use confidence-gated filtering:

```python
# Only remove high-confidence anachronistic reactions
archean_conservative, stats = filter_model_for_era(
    model,
    annotations,
    era_name="archean",
    removal_strategy="remove",
    min_confidence="high"  # Only remove if we're sure
)

print(f"Conservative removal: {len(stats['removed_reactions'])} reactions")
print(f"Downgraded to constrain: {len(stats.get('confidence_downgraded', []))}")
```

## Creating an Era Series

Generate models for all geological eras:

```python
from temporal import create_era_series

# Create models for Archean, Proterozoic, and Phanerozoic
era_models = create_era_series(model)

for era_name, (era_model, stats) in era_models.items():
    print(f"{era_name.capitalize()}:")
    print(f"  Reactions: {len(era_model.reactions)}")
    print(f"  Removed: {len(stats['removed_reactions'])}")
    print(f"  O₂ pathways: {stats['appropriate_count']}")
    print()
```

## Analyzing Results

### Check What Was Removed

```python
# See which pathways were removed
for rxn_id in stats['removed_reactions'][:5]:
    if rxn_id in annotations.reactions:
        ann = annotations.reactions[rxn_id]
        print(f"{rxn_id}: {ann.category} (~{ann.estimated_age_ga} Ga)")
```

### Validate Model Functionality

```python
from temporal.filter import validate_filtered_model

# Check that the filtered model still works
validation = validate_filtered_model(model, archean_model)

print(f"Original can grow: {validation['tests']['original_growth']['status']}")
print(f"Archean can grow: {validation['tests']['filtered_growth']['status']}")
print(f"New orphan metabolites: {validation['orphan_metabolites']['new_orphans']}")
```

## Next Steps

Now that you've created your first temporally-validated model:

- 📖 Read the [Concepts](concepts.md) guide to understand the methodology
- 🔧 Explore [CLI options](cli.md) for batch processing
- 📊 Learn about the [database schema](database.md) to add your own age assignments
- 🤝 [Contribute](contributing.md) improvements to the temporal database

## Troubleshooting

!!! question "Model won't grow after filtering?"
    Some essential reactions might have been removed. Try:
    
    1. Use `preserve_essential=True` in filtering
    2. Use `min_confidence="high"` for conservative filtering
    3. Check for orphan metabolites in the validation

!!! question "No reactions being annotated?"
    Make sure your model has oxygen-related reactions. Remove `focus_on_o2=True` 
    to annotate all reactions, not just O₂ producers.

!!! question "Different results between models?"
    Model-specific IDs can vary. Check `temporal/sources/mappings/bigg_aliases.yaml` 
    for ID normalization.

## Example Output

Here's what you should see for a typical model:

```
Original model: iML1515
  Total reactions: 2712
  O₂-producing reactions: 38
  
Temporal annotation:
  Archean-appropriate: 1 (catalase only)
  Post-Archean: 37
  
Archean-filtered model:
  Reactions retained: 2675
  Reactions removed: 37
  Growth capability: ✓ Maintained
  O₂ production: ✗ Eliminated
```

Ready to explore more? Check out the [full examples](examples.md) or dive into the [API documentation](api.md)!