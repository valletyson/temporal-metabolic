# Contributing to Temporal-Metabolic

Thank you for your interest in contributing to `temporal-metabolic`! This project aims to improve the accuracy of metabolic modeling for historical and evolutionary studies.

## Ways to Contribute

### 1. 🗓️ Add Temporal Data

The most valuable contributions are new age assignments for metabolic reactions:

1. Fork the repository
2. Edit `temporal/sources/oxygen_pathway_ages.yaml`
3. Add your reaction with:
   - Estimated age (in Ga)
   - Confidence level (high/medium/low/very_low)
   - Citations (DOIs preferred)
   - Brief notes on evidence

Example:
```yaml
reactions:
  NEW_REACTION_ID:
    category: alternative_oxidases
    estimated_age_ga: 1.8
    age_min_ga: 2.0
    age_max_ga: 1.5
    confidence: medium
    archean_appropriate: false
    evidence:
      citations:
        - "DOI:10.1234/example"
      notes: "Phylogenetic analysis suggests emergence in mid-Proterozoic"
```

### 2. 🔬 Add EC Number Mappings

Help improve enzyme classification in `temporal/sources/ec_to_category.yaml`:

```yaml
ec_to_category:
  "1.2.3.4":
    category: your_category
    description: "Enzyme name"
    archean_appropriate: false
    notes: "Evidence for dating"
```

### 3. 🔄 Add ID Crosswalks

Improve model compatibility in `temporal/sources/mappings/bigg_aliases.yaml`:

```yaml
aliases:
  CANONICAL_ID:
    - MODEL_SPECIFIC_ID_1
    - MODEL_SPECIFIC_ID_2
```

### 4. 🐛 Report Issues

Found a bug or incorrect age assignment? [Open an issue](https://github.com/yourusername/temporal-metabolic/issues) with:

- Model name and source
- Reaction ID
- Expected vs actual behavior
- Evidence for corrections

### 5. 📚 Improve Documentation

- Fix typos
- Add examples
- Clarify explanations
- Translate to other languages

## Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/yourusername/temporal-metabolic.git
cd temporal-metabolic
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e .[dev]
```

4. Run tests:
```bash
pytest tests/
```

## Code Style

We use:
- **Black** for formatting
- **isort** for import sorting
- **Type hints** where possible

Before submitting:
```bash
black temporal tests
isort temporal tests
pytest tests/
```

## Pull Request Process

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit:
```bash
git add .
git commit -m "Add: brief description of change"
```

3. Push to your fork:
```bash
git push origin feature/your-feature-name
```

4. Open a Pull Request with:
   - Clear description of changes
   - Link to related issue (if any)
   - Evidence/citations for temporal data
   - Test results

## Commit Message Convention

- `Add:` New features or data
- `Fix:` Bug fixes
- `Update:` Updates to existing data
- `Docs:` Documentation changes
- `Test:` Test additions or changes
- `Refactor:` Code restructuring

Example:
```
Add: Cytochrome c oxidase age assignment (1.8 Ga)

- Added to oxygen_pathway_ages.yaml
- Confidence: medium
- Citation: DOI:10.1234/example
```

## Data Quality Guidelines

### High Confidence
- Multiple independent studies
- Geological and phylogenetic agreement
- Clear fossil or biomarker evidence

### Medium Confidence
- Single well-supported study
- Phylogenetic analysis with calibration
- Indirect geological evidence

### Low Confidence
- Limited evidence
- Conflicting studies
- Inference from related pathways

### Very Low Confidence
- Educated guess
- Placeholder values
- Needs further research

## Review Process

PRs will be reviewed for:

1. **Scientific accuracy**: Citations and evidence quality
2. **Consistency**: Matches existing patterns
3. **Code quality**: Passes tests and style checks
4. **Documentation**: Changes are explained

## Community

- **Discussions**: [GitHub Discussions](https://github.com/yourusername/temporal-metabolic/discussions)
- **Chat**: [Discord/Slack link]
- **Email**: your.email@example.com

## Recognition

Contributors will be:
- Listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Acknowledged in publications using their contributions
- Invited to co-author database papers (major contributors)

## Questions?

Not sure how to contribute? Open a [discussion](https://github.com/yourusername/temporal-metabolic/discussions) or email the maintainers.

Thank you for helping make metabolic modeling more historically accurate! 🕰️