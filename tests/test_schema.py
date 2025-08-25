"""Unit tests for temporal schema and validators."""

import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from temporal.schema import (
    Evidence,
    ReactionTemporalAnnotation,
    PathwayTemporalAnnotation,
    ModelTemporalMetadata,
    TemporalDatabase
)


class TestEvidence:
    """Test Evidence model."""
    
    def test_default_evidence(self):
        """Test default evidence creation."""
        evidence = Evidence()
        assert evidence.citations == []
        assert evidence.notes is None
        assert evidence.confidence == "medium"
    
    def test_evidence_with_data(self):
        """Test evidence with full data."""
        evidence = Evidence(
            citations=["DOI:10.1234/test"],
            notes="Test evidence",
            confidence="high"
        )
        assert len(evidence.citations) == 1
        assert evidence.notes == "Test evidence"
        assert evidence.confidence == "high"


class TestReactionTemporalAnnotation:
    """Test ReactionTemporalAnnotation model and validators."""
    
    def test_basic_annotation(self):
        """Test basic annotation creation."""
        ann = ReactionTemporalAnnotation(
            reaction_id="TEST_RXN",
            category="catalases",
            estimated_age_ga=2.8
        )
        assert ann.reaction_id == "TEST_RXN"
        assert ann.category == "catalases"
        assert ann.estimated_age_ga == 2.8
    
    def test_age_range_validation_valid(self):
        """Test valid age ranges (geological ordering)."""
        # Valid: min >= estimated >= max (older to younger)
        ann = ReactionTemporalAnnotation(
            reaction_id="TEST_RXN",
            estimated_age_ga=2.4,
            age_min_ga=2.7,  # Older than estimated
            age_max_ga=2.0   # Younger than estimated
        )
        assert ann.age_min_ga == 2.7
        assert ann.age_max_ga == 2.0
    
    def test_age_range_validation_invalid_min(self):
        """Test invalid age_min (younger than estimated)."""
        with pytest.raises(ValueError, match="age_min_ga.*should be >= estimated_age_ga"):
            ReactionTemporalAnnotation(
                reaction_id="TEST_RXN",
                estimated_age_ga=2.4,
                age_min_ga=2.0  # Invalid: younger than estimated
            )
    
    def test_age_range_validation_invalid_max(self):
        """Test invalid age_max (older than estimated)."""
        with pytest.raises(ValueError, match="age_max_ga.*should be <= estimated_age_ga"):
            ReactionTemporalAnnotation(
                reaction_id="TEST_RXN",
                estimated_age_ga=2.4,
                age_max_ga=2.8  # Invalid: older than estimated
            )
    
    def test_age_range_validation_invalid_range(self):
        """Test invalid age range (max > min)."""
        with pytest.raises(ValueError, match="age_max_ga.*should be <= age_min_ga"):
            ReactionTemporalAnnotation(
                reaction_id="TEST_RXN",
                age_min_ga=2.0,
                age_max_ga=3.0  # Invalid: max older than min
            )
    
    def test_is_appropriate_for_era(self):
        """Test era appropriateness checking."""
        ann = ReactionTemporalAnnotation(
            reaction_id="TEST_RXN",
            estimated_age_ga=2.8
        )
        assert ann.is_appropriate_for_era(2.5) == True  # Archean cutoff
        assert ann.is_appropriate_for_era(3.0) == False  # Too old
    
    def test_is_appropriate_for_era_no_age(self):
        """Test era appropriateness with no age."""
        ann = ReactionTemporalAnnotation(
            reaction_id="TEST_RXN",
            estimated_age_ga=None
        )
        assert ann.is_appropriate_for_era(2.5) == False  # Conservative


class TestTemporalDatabase:
    """Test TemporalDatabase functionality."""
    
    def test_add_reaction(self):
        """Test adding reactions to database."""
        db = TemporalDatabase()
        ann = ReactionTemporalAnnotation(
            reaction_id="TEST_RXN",
            estimated_age_ga=2.8
        )
        db.add_reaction(ann)
        assert "TEST_RXN" in db.reactions
        assert db.reactions["TEST_RXN"].estimated_age_ga == 2.8
    
    def test_get_era_appropriate_reactions(self):
        """Test filtering reactions by era."""
        db = TemporalDatabase()
        
        # Add Archean-appropriate reaction
        ann1 = ReactionTemporalAnnotation(
            reaction_id="ARCHEAN_RXN",
            estimated_age_ga=2.8
        )
        db.add_reaction(ann1)
        
        # Add post-Archean reaction
        ann2 = ReactionTemporalAnnotation(
            reaction_id="MODERN_RXN",
            estimated_age_ga=1.0
        )
        db.add_reaction(ann2)
        
        # Test filtering
        archean_rxns = db.get_era_appropriate_reactions(2.5)
        assert "ARCHEAN_RXN" in archean_rxns
        assert "MODERN_RXN" not in archean_rxns


class TestModelTemporalMetadata:
    """Test ModelTemporalMetadata functionality."""
    
    def test_calculate_coverage(self):
        """Test coverage calculation."""
        meta = ModelTemporalMetadata(
            model_id="TEST_MODEL",
            total_reactions=100
        )
        
        annotations = [
            ReactionTemporalAnnotation(
                reaction_id=f"RXN_{i}",
                estimated_age_ga=2.8,
                archean_appropriate=i < 10,
                evidence=Evidence(confidence="high" if i < 5 else "medium")
            )
            for i in range(20)
        ]
        
        meta.calculate_coverage(annotations)
        
        assert meta.annotated_reactions == 20
        assert meta.annotation_coverage == 0.2
        assert meta.archean_appropriate_count == 10
        assert meta.high_confidence_fraction == 0.25  # 5/20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])