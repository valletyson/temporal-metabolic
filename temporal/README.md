# Temporal Modeling Framework for Metabolic Models

## Overview

This framework provides tools for annotating metabolic models with evolutionary timing information and generating era-specific models appropriate for different geological periods. It addresses the critical issue of **network complexity artifacts** - where modern metabolic models contain anachronistic reactions that didn't exist during earlier geological eras.

## Key Features

- **Temporal Annotation**: Systematically annotate reactions with evolutionary ages
- **Era-Specific Filtering**: Generate Archean, Proterozoic, and Phanerozoic models
- **Biochemical Evolution Database**: Curated database of reaction evolutionary ages
- **Validation Tools**: Ensure filtered models maintain biological validity
- **Export Capabilities**: YAML, JSON, and CSV export formats

## Installation

The framework uses standard Python packages already in your environment:
```bash
# Required packages (already installed)
- cobra
- pydantic
- pyyaml
- pandas
```

## Quick Start

### 1. Basic Usage

```python
from temporal.annotate import annotate_model
from temporal.filter import filter_model_for_era
import cobra

# Load your model
model = cobra.io.read_sbml_model("models/your_model.xml")

# Annotate with temporal information
database = annotate_model(model, focus_on_o2=True)

# Create an Archean-appropriate model
archean_model, stats = filter_model_for_era(
    model,
    database,
    era_name="archean",
    removal_strategy="remove"
)

print(f"Removed {len(stats['removed_reactions'])} post-Archean reactions")
```

### 2. Run the Demo

```bash
python temporal/demo.py
```

This demonstrates:
- Model annotation
- Era-specific filtering
- Validation
- Export functionality

## Components

### Schema (`schema.py`)

Defines the data structures for temporal annotations:

- **ReactionTemporalAnnotation**: Individual reaction annotations
- **Evidence**: Supporting evidence with citations
- **ModelTemporalMetadata**: Model-level statistics
- **TemporalDatabase**: Complete annotation database

### Annotator (`annotate.py`)

Maps reactions to evolutionary ages:

- Pattern-based categorization
- Category defaults from curated database
- Reaction-specific overrides
- Confidence levels

### Filter (`filter.py`)

Creates era-specific models:

- **Archean** (>2.5 Ga): Pre-GOE, anoxic conditions
- **Proterozoic** (2.5-0.541 Ga): Post-GOE, rising O₂
- **Phanerozoic** (<0.541 Ga): Modern O₂ levels

Removal strategies:
- `"remove"`: Delete inappropriate reactions
- `"constrain"`: Set flux bounds to 0
- `"mark"`: Identify without modification

### Database (`sources/oxygen_pathway_ages.yaml`)

Curated evolutionary ages for oxygen pathways:

| Category | Age (Ga) | Archean? | Evidence |
|----------|----------|----------|----------|
| Photosystem II | 2.4 | ❌ | GOE timing |
| Catalases | 2.8 | ✅ | Ancient ROS defense |
| Peroxidases | N/A | ❌ | Not net O₂ producers |
| Alternative oxidases | 1.5 | ❌ | Complex respiration |
| Other O₂ producers | 1.0 | ❌ | Recent innovations |

## Scientific Basis

### The Problem: Network Complexity Artifacts

Modern metabolic models contain reactions that evolved over billions of years. When used for early Earth simulations, these models incorrectly include pathways that didn't exist, leading to:

- **96.2% spurious oxygen pathways** in Archean simulations
- **26× overestimation** of oxygen production capabilities
- **Invalid predictions** for Great Oxygenation Event timing

### The Solution: Temporal Filtering

By annotating reactions with evolutionary ages and filtering based on geological era:

1. **Remove anachronistic reactions** (e.g., PS II from Archean models)
2. **Preserve era-appropriate pathways** (e.g., catalase in all eras)
3. **Maintain model validity** through careful validation

## API Reference

### annotate_model()

```python
def annotate_model(
    model: cobra.Model,
    categories: Dict = None,
    overrides: Dict = None,
    focus_on_o2: bool = True
) -> TemporalDatabase
```

Annotate all reactions in a model with temporal information.

### filter_model_for_era()

```python
def filter_model_for_era(
    model: cobra.Model,
    annotations: TemporalDatabase,
    era_name: str = None,
    era_cutoff_ga: float = None,
    removal_strategy: str = "remove",
    preserve_essential: bool = True
) -> Tuple[cobra.Model, Dict]
```

Filter a model to be appropriate for a specific geological era.

### create_era_series()

```python
def create_era_series(
    model: cobra.Model,
    annotations: TemporalDatabase = None,
    eras: List[str] = None,
    removal_strategy: str = "remove"
) -> Dict[str, Tuple[cobra.Model, Dict]]
```

Create models for multiple geological eras.

## Extending the Database

### Adding New Reactions

Edit `sources/oxygen_pathway_ages.yaml`:

```yaml
reactions:
  YOUR_REACTION_ID:
    category: catalases  # or create new category
    common_names: ["Your reaction name"]
    estimated_age_ga: 2.8
    age_min_ga: 3.0  # Oldest possible
    age_max_ga: 2.5  # Youngest possible
    archean_appropriate: true
    evidence:
      citations:
        - "DOI:10.xxxx/yyyy"
      notes: "Supporting evidence"
```

### Adding New Categories

```yaml
categories:
  your_new_category:
    estimated_age_ga: 2.0
    confidence: medium
    archean_appropriate: false
    evidence:
      citations: ["DOI:..."]
      notes: "Category description"
```

## Validation

The framework includes validation to ensure:

1. **Growth capability**: Filtered models can still grow
2. **No orphan metabolites**: Metabolites remain connected
3. **Essential reactions**: Preserved when necessary
4. **Age consistency**: Ranges are geologically valid

## Export Formats

### YAML Export
```python
database.export_to_yaml("annotations.yaml")
```

### JSON Export
```python
database.export_to_json("annotations.json")
```

### CSV Summary
```python
# See demo.py for pandas DataFrame export
```

## Citations

If you use this framework, please cite:

> "Network Complexity Artifacts in Metabolic Models: Implications for Evolutionary Systems Biology"
> [Your publication details]

## Future Development

Planned enhancements:

1. **Expanded reaction coverage** beyond oxygen pathways
2. **Automated age inference** from phylogenetic data
3. **Integration with BiGG Models** database
4. **Web interface** for community curation
5. **Uncertainty quantification** for age estimates

## Contributing

We welcome contributions! Please:

1. Add new reaction ages with citations
2. Improve categorization patterns
3. Validate filtered models
4. Report issues with anachronistic reactions

## License

[Your license]

## Contact

[Your contact information]