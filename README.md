# Temporal-Metabolic: Evolutionary Time Validation for Metabolic Models

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![PyPI version](https://badge.fury.io/py/temporal-metabolic.svg)](https://badge.fury.io/py/temporal-metabolic)
[![Documentation Status](https://readthedocs.org/projects/temporal-metabolic/badge/?version=latest)](https://temporal-metabolic.readthedocs.io/en/latest/?badge=latest)

**Remove anachronistic reactions from metabolic models for historically-accurate simulations**

## 🚨 The Problem

**96.2% of oxygen-producing pathways in modern metabolic models are temporally inappropriate for early Earth studies**. This creates fundamental errors when modeling:
- The Great Oxygenation Event (2.4 Ga)
- Early life evolution (>2.5 Ga)
- Biosignature interpretation for exoplanets
- Any historical metabolic reconstruction

## 💡 The Solution

`temporal-metabolic` provides a framework to:
1. **Annotate** metabolic reactions with evolutionary ages
2. **Filter** models for specific geological eras (Archean, Proterozoic, Phanerozoic)
3. **Validate** temporal appropriateness with confidence levels
4. **Generate** historically-accurate metabolic models

## 🚀 Quick Start

### Installation

```bash
pip install temporal-metabolic
```

### Basic Usage

```python
from temporal import annotate_model, filter_model_for_era
import cobra

# Load your model
model = cobra.io.read_sbml_model("e_coli.xml")

# Annotate with evolutionary ages
annotations = annotate_model(model)

# Create an Archean-appropriate model (>2.5 Ga)
archean_model, stats = filter_model_for_era(
    model, 
    annotations,
    era_name="archean"
)

print(f"Removed {len(stats['removed_reactions'])} anachronistic reactions")
```

### Command Line Interface

```bash
# Annotate a model
temporal-annotate --model e_coli.xml --out annotations.yaml

# Filter for Archean era with confidence gating
temporal-filter --model e_coli.xml \
    --annotations annotations.yaml \
    --era archean \
    --min-confidence medium \
    --out e_coli_archean.xml

# Run the demo
temporal-demo
```

## 📊 Key Features

### Confidence-Gated Filtering
Only remove reactions when confidence in age assignment is high:
```bash
temporal-filter --min-confidence high  # Conservative approach
```

### EC Number-Based Categorization
Robust classification using enzyme commission numbers:
- `1.11.1.6` → Catalase (Archean-appropriate)
- `1.11.1.*` → Peroxidases (not net O₂ producers)
- `1.9.3.*` → Alternative oxidases (post-Archean)

### Cross-Model Compatibility
BiGG ID normalization handles model-specific variants:
```yaml
ASPO6: [ASPO6_c, ASPO6_syn, L_ASPARTATE_OXIDASE]
```

## 📈 Validation Results

Applied to 4 phylogenetically diverse organisms:

| Organism | Model | O₂ Pathways | Spurious | Archean-OK |
|----------|-------|-------------|----------|------------|
| *E. coli* | iML1515 | 38 | 97.4% | 1 |
| *S. cerevisiae* | iMM904 | 34 | 97.1% | 1 |
| *Synechocystis* | iJN678 | 14 | 92.9% | 1 |
| *Synechococcus* | iJB785 | 18 | 94.4% | 1 |

**Only catalase consistently predates 2.5 Ga across all models**

## 📚 Documentation

Full documentation available at [temporal-metabolic.readthedocs.io](https://temporal-metabolic.readthedocs.io)

- [Quickstart Guide](https://temporal-metabolic.readthedocs.io/quickstart)
- [API Reference](https://temporal-metabolic.readthedocs.io/api)
- [Database Schema](https://temporal-metabolic.readthedocs.io/database)
- [Examples](https://temporal-metabolic.readthedocs.io/examples)

## 🔬 Scientific Background

This tool addresses "network complexity artifacts" - the accumulation of anachronistic reactions in metabolic models that evolved long after the time period being studied. Our research shows:

- Modern models contain ~26× more oxygen pathways than existed in the Archean
- Standard validation misses these temporal artifacts
- Historical modeling studies may have significant errors

Read the paper: *[Network Complexity Artifacts in Metabolic Models: Implications for Evolutionary Systems Bilogy](https://drive.google.com/file/d/1KbXtDgAPlys0Xz3Y7jq0iUeRJ9zR2xdI/view?usp=sharing)*

## 🛠️ Advanced Usage

### Custom Age Assignments

```yaml
# my_ages.yaml
reactions:
  MY_REACTION:
    estimated_age_ga: 3.0
    confidence: high
    archean_appropriate: true
```

```bash
temporal-annotate --model my_model.xml --db my_ages.yaml
```

### Era Series Generation

```python
from temporal import create_era_series

# Generate models for all geological eras
era_models = create_era_series(model)

for era, (era_model, stats) in era_models.items():
    print(f"{era}: {len(era_model.reactions)} reactions")
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding Reaction Ages

1. Fork the repository
2. Add entries to `temporal/sources/oxygen_pathway_ages.yaml`
3. Include citations and confidence levels
4. Submit a pull request

## 📖 Citation

If you use `temporal-metabolic` in your research, please cite:

```bibtex
@software{temporal_metabolic_2025,
  author = {Tyson Valle},
  title = {Temporal-Metabolic: Evolutionary Time Validation for Metabolic Models},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/yourusername/temporal-metabolic},
  doi = {10.5281/zenodo.XXXXXXX}
}

@article{network_artifacts_2025,
  author = {[Your Name] and [Collaborators]},
  title = {Network Complexity Artifacts in Metabolic Models: Implications for Evolutionary Systems Biology},
  journal = {[Target Journal]},
  year = {2025},
  doi = {10.XXXX/paper}
}
```

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Developed as part of the AI for Social Good initiative
- Supported by [Your Institution/Mentor]
- Models from [BiGG Models Database](http://bigg.ucsd.edu/)

## 📬 Contact

- **Author**: Tyson Valle
- **Email**: valletyson76@gmai.com
- **Website**: https://www.ai4sg.com/
- **Issues**: [GitHub Issues](https://github.com/yourusername/temporal-metabolic/issues)

---

*Ensuring metabolic models respect the arrow of time* 🕐