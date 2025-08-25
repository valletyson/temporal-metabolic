# Command Line Interface

`temporal-metabolic` provides three main command-line tools:

## temporal-annotate

Annotate metabolic model reactions with temporal information.

### Usage

```bash
temporal-annotate [OPTIONS]
```

### Options

| Option | Short | Description | Required |
|--------|-------|-------------|----------|
| `--model` | `-m` | Path to SBML model file | ✓ |
| `--out` | `-o` | Output path for annotations (YAML/JSON) | ✓ |
| `--db` | `-d` | Path to temporal database YAML | |
| `--only-o2` | | Only annotate O₂-related reactions | |
| `--curator` | | Curator name for annotations | |

### Examples

#### Basic annotation
```bash
temporal-annotate --model e_coli.xml --out annotations.yaml
```

#### Focus on oxygen pathways
```bash
temporal-annotate --model e_coli.xml --out annotations.yaml --only-o2
```

#### Use custom database
```bash
temporal-annotate \
    --model my_model.xml \
    --db my_ages.yaml \
    --out annotations.json \
    --curator "Jane Doe"
```

### Output Format

The output file (YAML or JSON based on extension) contains:

```yaml
reactions:
  ASPO6:
    reaction_id: ASPO6
    category: alternative_oxidases
    estimated_age_ga: 1.5
    archean_appropriate: false
    evidence:
      confidence: low
      citations: ["DOI:10.1093/molbev/mst012"]
models:
  iML1515:
    total_reactions: 2712
    annotated_reactions: 38
    archean_appropriate_count: 1
```

## temporal-filter

Filter metabolic models for specific geological eras.

### Usage

```bash
temporal-filter [OPTIONS]
```

### Options

| Option | Short | Description | Required |
|--------|-------|-------------|----------|
| `--model` | `-m` | Path to SBML model file | ✓ |
| `--annotations` | `-a` | Path to temporal annotations | ✓ |
| `--era` | `-e` | Geological era (archean/proterozoic/phanerozoic) | ✓ |
| `--out` | `-o` | Output path for filtered model | ✓ |
| `--strategy` | `-s` | Removal strategy (remove/constrain/mark) | |
| `--min-confidence` | | Minimum confidence for removal | |
| `--preserve-essential` | | Keep reactions essential for growth | |
| `--stats` | | Output path for statistics YAML | |

### Geological Eras

| Era | Time Period | Cutoff | Description |
|-----|-------------|--------|-------------|
| `archean` | >2.5 Ga | 2.5 Ga | Pre-GOE, anoxic atmosphere |
| `proterozoic` | 2.5-0.541 Ga | 0.541 Ga | Post-GOE, rising O₂ |
| `phanerozoic` | <0.541 Ga | 0.0 Ga | Modern O₂ levels |

### Removal Strategies

| Strategy | Effect | Use Case |
|----------|--------|----------|
| `remove` | Delete reactions from model | Maximum accuracy |
| `constrain` | Set flux bounds to 0 | Preserve network structure |
| `mark` | Just identify, no changes | Analysis only |

### Confidence Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `high` | Strong evidence for age | Conservative filtering |
| `medium` | Reasonable evidence | Standard filtering |
| `low` | Weak evidence | Aggressive filtering |
| `very_low` | Placeholder/guess | Research only |

### Examples

#### Basic Archean filtering
```bash
temporal-filter \
    --model e_coli.xml \
    --annotations annotations.yaml \
    --era archean \
    --out e_coli_archean.xml
```

#### Conservative filtering with statistics
```bash
temporal-filter \
    --model synechocystis.xml \
    --annotations syn_annotations.yaml \
    --era archean \
    --strategy remove \
    --min-confidence high \
    --preserve-essential \
    --out syn_archean_conservative.xml \
    --stats filtering_stats.yaml
```

#### Constrain instead of remove
```bash
temporal-filter \
    --model yeast.xml \
    --annotations yeast_ann.yaml \
    --era proterozoic \
    --strategy constrain \
    --out yeast_proterozoic.xml
```

### Output Statistics

When using `--stats`, you get detailed filtering information:

```yaml
era: archean
cutoff_ga: 2.5
total_reactions: 863
removed_reactions: [ASPO6, GLYCTO1, PDX5POi, ...]
constrained_reactions: []
preserved_essential: []
inappropriate_count: 13
appropriate_count: 1
unknown_count: 849
confidence_downgraded: [PYDXNO, PYDXO]  # If using min-confidence
```

## temporal-demo

Run the interactive demonstration.

### Usage

```bash
temporal-demo
```

### What It Does

The demo walks through:

1. Loading a sample model
2. Annotating with temporal information
3. Filtering for different eras
4. Comparing model performance
5. Exporting results

### Example Output

```
============================================================
TEMPORAL MODELING FRAMEWORK DEMONSTRATION
============================================================

This demo shows how to:
1. Annotate metabolic models with temporal information
2. Filter models for specific geological eras
3. Create era-specific model series
4. Export temporal databases

Loading model from models/eSyn6803.xml
   Model: iJN678
   Reactions: 863
   Metabolites: 795

Annotating model with temporal information...
   Annotated reactions: 14
   Archean-appropriate: 1
   Coverage: 1.6%
   
Creating Archean-appropriate model (>2.5 Ga)...
   Original reactions: 863
   Removed reactions: 13
   Final reactions: 850
```

## Pipeline Example

Here's a complete workflow using all three tools:

```bash
#!/bin/bash
# Temporal validation pipeline

# 1. Annotate multiple models
for model in *.xml; do
    base=$(basename $model .xml)
    temporal-annotate \
        --model $model \
        --out ${base}_annotations.yaml \
        --only-o2
done

# 2. Create Archean versions with different confidence levels
for conf in high medium low; do
    temporal-filter \
        --model e_coli.xml \
        --annotations e_coli_annotations.yaml \
        --era archean \
        --min-confidence $conf \
        --out e_coli_archean_${conf}.xml \
        --stats stats_${conf}.yaml
done

# 3. Create era series for comparison
for era in archean proterozoic phanerozoic; do
    temporal-filter \
        --model synechocystis.xml \
        --annotations syn_annotations.yaml \
        --era $era \
        --out syn_${era}.xml
done

# 4. Run demo for validation
temporal-demo
```

## Tips and Tricks

### Batch Processing

Process multiple models in parallel:

```bash
find models/ -name "*.xml" | parallel -j 4 \
    temporal-annotate --model {} --out {.}_ann.yaml --only-o2
```

### JSON vs YAML

- **YAML**: Human-readable, good for manual editing
- **JSON**: Faster parsing, better for large datasets

### Validation

Always check the statistics to ensure filtering worked as expected:

```bash
# Quick check of what was removed
grep "removed_reactions" stats.yaml | wc -w
```

### Custom Age Assignments

Override specific reactions in your database:

```yaml
# my_custom_ages.yaml
reactions:
  MY_SPECIAL_RXN:
    estimated_age_ga: 3.5
    confidence: high
    archean_appropriate: true
```

Then use:
```bash
temporal-annotate --model my_model.xml --db my_custom_ages.yaml --out custom_ann.yaml
```

## Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Model not found` | Invalid path | Check file exists and path is correct |
| `Unknown era` | Invalid era name | Use archean, proterozoic, or phanerozoic |
| `No annotations found` | Empty annotation file | Re-run temporal-annotate |
| `Essential reaction would be removed` | Critical reaction is anachronistic | Use `--preserve-essential` |

## Environment Variables

You can set defaults via environment variables:

```bash
export TEMPORAL_DB_PATH=/path/to/custom/database.yaml
export TEMPORAL_CONFIDENCE=high
export TEMPORAL_CURATOR="Your Name"
```