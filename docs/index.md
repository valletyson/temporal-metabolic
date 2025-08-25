# Temporal-Metabolic

**Remove anachronistic reactions from metabolic models for historically-accurate simulations**

## The Network Complexity Artifact Problem

Modern genome-scale metabolic models (GEMs) are powerful tools for understanding cellular metabolism. However, when applied to historical questions—like modeling early life or the Great Oxygenation Event—they contain a critical flaw: **network complexity artifacts**.

!!! danger "96.2% of oxygen pathways shouldn't exist in early Earth models"
    Our analysis of 104 oxygen-producing reactions across 4 organisms reveals that only catalase 
    consistently predates the Archean-Proterozoic boundary (2.5 Ga).

### What are Network Complexity Artifacts?

These are anachronistic reactions in metabolic models that:

- ✅ Exist in modern organisms
- ✅ Pass standard validation tests
- ❌ Did NOT exist during the historical period being modeled

This creates fundamental errors in:

- Early Earth studies (Archean, >2.5 Ga)
- Great Oxygenation Event modeling (2.4 Ga)
- Evolutionary metabolic reconstruction
- Astrobiology and biosignature interpretation

## The Solution: Temporal Validation

`temporal-metabolic` provides a systematic framework to:

1. **Annotate** reactions with evolutionary ages
2. **Filter** models for specific geological eras
3. **Validate** temporal appropriateness
4. **Generate** historically-accurate models

## Quick Example

=== "Python"

    ```python
    from temporal import annotate_model, filter_model_for_era
    import cobra

    # Load a model
    model = cobra.io.read_sbml_model("e_coli.xml")

    # Annotate with evolutionary ages
    annotations = annotate_model(model)

    # Create Archean-appropriate model (>2.5 Ga)
    archean_model, stats = filter_model_for_era(
        model, 
        annotations,
        era_name="archean"
    )

    print(f"Removed {len(stats['removed_reactions'])} anachronistic reactions")
    # Output: Removed 37 anachronistic reactions
    ```

=== "Command Line"

    ```bash
    # Annotate a model
    temporal-annotate --model e_coli.xml --out annotations.yaml

    # Filter for Archean era
    temporal-filter --model e_coli.xml \
        --annotations annotations.yaml \
        --era archean \
        --out e_coli_archean.xml
    ```

## Key Features

### 🎯 Confidence-Gated Filtering
Only remove reactions when we're confident about their age:
```bash
temporal-filter --min-confidence high  # Conservative approach
```

### 🔬 EC Number Classification
Robust categorization using enzyme commission numbers:
- `1.11.1.6` → Catalase (Archean-appropriate ✅)
- `1.11.1.*` → Peroxidases (not net O₂ producers ❌)

### 🔄 Cross-Model Compatibility
Handles model-specific ID variants automatically

### 📊 Comprehensive Database
Curated evolutionary ages with citations and confidence levels

## Impact

Our findings have profound implications for evolutionary systems biology:

!!! info "26× Overestimation"
    Modern models suggest ~26× more oxygen pathways than actually existed in the Archean

This affects conclusions about:

- When oxygen production became possible
- How early life survived oxidative stress
- What biosignatures ancient life could produce
- How metabolism evolved over geological time

## Getting Started

Ready to ensure your models respect the arrow of time?

<div class="grid cards" markdown>

- :material-download: **[Installation](installation.md)**  
  Install via pip or from source

- :material-rocket: **[Quickstart](quickstart.md)**  
  5-minute tutorial to get running

- :material-book: **[User Guide](concepts.md)**  
  Understand the concepts and workflow

- :material-api: **[API Reference](api.md)**  
  Detailed documentation of all functions

</div>

## Citation

If you use `temporal-metabolic` in your research, please cite:

```bibtex
@software{temporal_metabolic_2025,
  author = {[Your Name]},
  title = {Temporal-Metabolic: Evolutionary Time Validation for Metabolic Models},
  year = {2025},
  doi = {10.5281/zenodo.XXXXXXX}
}
```

## Support

- 📧 **Email**: your.email@example.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/temporal-metabolic/issues)
- 📚 **Paper**: [Network Complexity Artifacts in Metabolic Models](https://doi.org/10.XXXX/paper)