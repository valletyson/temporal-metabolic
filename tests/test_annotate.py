"""Unit tests for temporal annotation functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import cobra
from temporal.annotate import (
    load_category_defaults,
    categorize_reaction,
    annotate_reaction,
    annotate_model
)
from temporal.schema import ReactionTemporalAnnotation


class TestCategorization:
    """Test reaction categorization."""
    
    def test_load_category_defaults(self):
        """Test loading default categories."""
        categories, overrides = load_category_defaults()
        
        assert "photosystem_ii" in categories
        assert "catalases" in categories
        assert categories["catalases"]["estimated_age_ga"] == 2.8
        assert "ASPO6" in overrides
    
    def test_categorize_photosystem_ii(self):
        """Test PS II categorization."""
        categories, overrides = load_category_defaults()
        
        # Test by ID
        rxn = Mock()
        rxn.id = "PSII_RXN"
        rxn.name = "Some reaction"
        rxn.metabolites = {}
        assert categorize_reaction(rxn, categories, overrides) == "photosystem_ii"
        
        # Test by name
        rxn.id = "RXN123"
        rxn.name = "Photosystem II complex"
        assert categorize_reaction(rxn, categories, overrides) == "photosystem_ii"
    
    def test_categorize_catalase(self):
        """Test catalase categorization."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "CAT"
        rxn.name = "Catalase"
        rxn.metabolites = {}
        assert categorize_reaction(rxn, categories, overrides) == "catalases"
    
    def test_categorize_peroxidase(self):
        """Test peroxidase categorization."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "PEROX1"
        rxn.name = "Some peroxidase"
        rxn.metabolites = {}
        assert categorize_reaction(rxn, categories, overrides) == "peroxidases"
    
    def test_categorize_alternative_oxidase(self):
        """Test alternative oxidase categorization."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "OXIDASE_1"
        rxn.name = "Some oxidase"
        rxn.metabolites = {}
        assert categorize_reaction(rxn, categories, overrides) == "alternative_oxidases"
    
    def test_categorize_by_override(self):
        """Test categorization by explicit override."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "ASPO6"  # In overrides
        rxn.name = "Whatever"
        rxn.metabolites = {}
        assert categorize_reaction(rxn, categories, overrides) == "alternative_oxidases"
    
    def test_categorize_other_o2_producer(self):
        """Test categorization of other O2 producers."""
        categories, overrides = load_category_defaults()
        
        # Mock O2-producing reaction
        o2_met = Mock()
        o2_met.id = "o2_c"
        
        rxn = Mock()
        rxn.id = "UNKNOWN_RXN"
        rxn.name = "Unknown reaction"
        rxn.metabolites = {o2_met: 1.0}  # Produces O2
        
        assert categorize_reaction(rxn, categories, overrides) == "other_o2_producers"
    
    def test_categorize_non_o2_producer(self):
        """Test that non-O2 producers return None."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "GLYCOLYSIS_RXN"
        rxn.name = "Glycolysis reaction"
        rxn.metabolites = {}  # No O2
        
        assert categorize_reaction(rxn, categories, overrides) is None


class TestAnnotation:
    """Test reaction annotation."""
    
    def test_annotate_reaction_with_category(self):
        """Test annotating a reaction with known category."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "CAT"
        rxn.name = "Catalase"
        rxn.metabolites = {}
        
        ann = annotate_reaction(rxn, categories, overrides)
        
        assert ann is not None
        assert ann.reaction_id == "CAT"
        assert ann.category == "catalases"
        assert ann.estimated_age_ga == 2.8
        assert ann.archean_appropriate == True
    
    def test_annotate_reaction_no_category(self):
        """Test annotating a reaction with no category."""
        categories, overrides = load_category_defaults()
        
        rxn = Mock()
        rxn.id = "UNKNOWN"
        rxn.name = "Unknown"
        rxn.metabolites = {}
        
        ann = annotate_reaction(rxn, categories, overrides)
        assert ann is None
    
    def test_annotate_reaction_with_override(self):
        """Test annotation with reaction-specific override."""
        categories, overrides = load_category_defaults()
        
        # Add a custom override
        overrides["TEST_RXN"] = {
            "category": "catalases",
            "estimated_age_ga": 3.0,  # Override age
            "archean_appropriate": True
        }
        
        rxn = Mock()
        rxn.id = "TEST_RXN"
        rxn.name = "Test"
        rxn.metabolites = {}
        
        ann = annotate_reaction(rxn, categories, overrides)
        
        assert ann.estimated_age_ga == 3.0  # Uses override
        assert ann.category == "catalases"


class TestModelAnnotation:
    """Test full model annotation."""
    
    def test_annotate_model_basic(self):
        """Test annotating a simple model."""
        # Create a minimal test model
        model = cobra.Model("test_model")
        
        # Add some reactions
        rxn1 = cobra.Reaction("CAT")
        rxn1.name = "Catalase"
        model.add_reactions([rxn1])
        
        rxn2 = cobra.Reaction("PSII")
        rxn2.name = "Photosystem II"
        model.add_reactions([rxn2])
        
        # Add O2 metabolite to make reactions relevant
        o2 = cobra.Metabolite("o2_c", name="Oxygen")
        rxn1.add_metabolites({o2: 1.0})
        rxn2.add_metabolites({o2: 1.0})
        
        # Annotate
        database = annotate_model(model, focus_on_o2=True)
        
        assert len(database.reactions) == 2
        assert "CAT" in database.reactions
        assert "PSII" in database.reactions
        
        # Check categories
        assert database.reactions["CAT"].category == "catalases"
        assert database.reactions["PSII"].category == "photosystem_ii"
        
        # Check model metadata
        assert "test_model" in database.models
        meta = database.models["test_model"]
        assert meta.total_reactions == 2
        assert meta.annotated_reactions == 2
    
    def test_annotate_model_o2_filter(self):
        """Test O2 filtering in annotation."""
        model = cobra.Model("test_model")
        
        # Add O2-producing reaction
        rxn1 = cobra.Reaction("O2_PRODUCER")
        o2 = cobra.Metabolite("o2_c")
        rxn1.add_metabolites({o2: 1.0})
        model.add_reactions([rxn1])
        
        # Add non-O2 reaction
        rxn2 = cobra.Reaction("GLYCOLYSIS")
        glucose = cobra.Metabolite("glc_c")
        atp = cobra.Metabolite("atp_c")
        rxn2.add_metabolites({glucose: -1, atp: 1})
        model.add_reactions([rxn2])
        
        # Annotate with O2 focus
        database = annotate_model(model, focus_on_o2=True)
        
        # Should only annotate O2-related reaction
        assert len(database.reactions) <= 1
        if database.reactions:
            assert "O2_PRODUCER" in database.reactions or len(database.reactions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])