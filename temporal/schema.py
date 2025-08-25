"""
Schema definitions for temporal annotations of metabolic models.
Uses pydantic for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Literal
from datetime import datetime

class Evidence(BaseModel):
    """Evidence supporting a temporal annotation."""
    citations: List[str] = Field(default_factory=list, description="DOIs, PMIDs, or URLs")
    notes: Optional[str] = Field(None, description="Additional notes about the evidence")
    confidence: Literal["high", "medium", "low", "very_low"] = Field(
        "medium", description="Confidence level in the temporal assignment"
    )

class ReactionTemporalAnnotation(BaseModel):
    """Temporal annotation for a single reaction."""
    reaction_id: str = Field(..., description="BiGG or model-specific reaction ID")
    category: Optional[str] = Field(None, description="Functional category (e.g., photosystem_ii)")
    
    # Age estimates in billions of years ago (Ga)
    estimated_age_ga: Optional[float] = Field(None, description="Best estimate of evolutionary age")
    age_min_ga: Optional[float] = Field(None, description="Minimum age (oldest possible)")
    age_max_ga: Optional[float] = Field(None, description="Maximum age (youngest possible)")
    
    # Era appropriateness flags
    archean_appropriate: Optional[bool] = Field(None, description="Appropriate for Archean (>2.5 Ga)")
    proterozoic_appropriate: Optional[bool] = Field(None, description="Appropriate for Proterozoic (2.5-0.54 Ga)")
    phanerozoic_appropriate: Optional[bool] = Field(None, description="Appropriate for Phanerozoic (<0.54 Ga)")
    
    # Supporting information
    evidence: Evidence = Field(default_factory=Evidence)
    
    # Metadata
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    curator: Optional[str] = Field(None, description="Person or algorithm that created annotation")
    
    @field_validator('age_min_ga')
    @classmethod
    def validate_age_min(cls, v, info):
        """Ensure age_min_ga >= estimated_age_ga (older or equal)."""
        if v is not None and info.data.get('estimated_age_ga') is not None:
            est_age = info.data['estimated_age_ga']
            if v < est_age:
                raise ValueError(f"age_min_ga ({v}) should be >= estimated_age_ga ({est_age})")
        return v
    
    @field_validator('age_max_ga')
    @classmethod
    def validate_age_max(cls, v, info):
        """Ensure age_max_ga <= estimated_age_ga (younger or equal) and <= age_min_ga."""
        if v is not None:
            # Check against estimated age
            if info.data.get('estimated_age_ga') is not None:
                est_age = info.data['estimated_age_ga']
                if v > est_age:
                    raise ValueError(f"age_max_ga ({v}) should be <= estimated_age_ga ({est_age})")
            
            # Check against age_min
            if info.data.get('age_min_ga') is not None:
                age_min = info.data['age_min_ga']
                if v > age_min:
                    raise ValueError(f"age_max_ga ({v}) should be <= age_min_ga ({age_min})")
        return v
    
    def is_appropriate_for_era(self, era_cutoff_ga: float) -> bool:
        """Check if reaction is appropriate for a given era."""
        if self.estimated_age_ga is None:
            return False  # Conservative: unknown age = not appropriate
        return self.estimated_age_ga >= era_cutoff_ga

class PathwayTemporalAnnotation(BaseModel):
    """Temporal annotation for a metabolic pathway or subsystem."""
    pathway_id: str = Field(..., description="Pathway or subsystem identifier")
    pathway_name: Optional[str] = Field(None, description="Human-readable pathway name")
    
    # Age estimates
    estimated_age_ga: Optional[float] = Field(None, description="Best estimate of pathway evolution")
    age_min_ga: Optional[float] = Field(None, description="Minimum age")
    age_max_ga: Optional[float] = Field(None, description="Maximum age")
    
    # Era flags
    archean_appropriate: Optional[bool] = Field(None)
    proterozoic_appropriate: Optional[bool] = Field(None)
    phanerozoic_appropriate: Optional[bool] = Field(None)
    
    # Related reactions
    reaction_ids: List[str] = Field(default_factory=list, description="Reactions in this pathway")
    
    # Evidence
    evidence: Evidence = Field(default_factory=Evidence)
    
    # Metadata
    last_updated: Optional[datetime] = Field(None)
    curator: Optional[str] = Field(None)

class ModelTemporalMetadata(BaseModel):
    """Metadata about temporal annotations for an entire model."""
    model_id: str = Field(..., description="Model identifier (e.g., iJN678)")
    model_name: Optional[str] = Field(None, description="Model name")
    organism: Optional[str] = Field(None, description="Organism name")
    
    # Annotation statistics
    total_reactions: int = Field(0, description="Total reactions in model")
    annotated_reactions: int = Field(0, description="Reactions with temporal annotations")
    archean_appropriate_count: int = Field(0, description="Reactions appropriate for Archean")
    proterozoic_appropriate_count: int = Field(0, description="Reactions appropriate for Proterozoic")
    phanerozoic_appropriate_count: int = Field(0, description="Reactions appropriate for Phanerozoic")
    
    # Coverage metrics
    annotation_coverage: float = Field(0.0, description="Fraction of reactions annotated")
    high_confidence_fraction: float = Field(0.0, description="Fraction with high confidence")
    
    # Metadata
    version: str = Field("0.1.0", description="Annotation version")
    last_updated: Optional[datetime] = Field(None)
    curator: Optional[str] = Field(None)
    
    def calculate_coverage(self, annotations: List[ReactionTemporalAnnotation]):
        """Calculate coverage metrics from annotations."""
        if self.total_reactions > 0:
            self.annotated_reactions = len(annotations)
            self.annotation_coverage = len(annotations) / self.total_reactions
            
            # Count era-appropriate reactions
            self.archean_appropriate_count = sum(
                1 for a in annotations if a.archean_appropriate
            )
            self.proterozoic_appropriate_count = sum(
                1 for a in annotations if a.proterozoic_appropriate
            )
            self.phanerozoic_appropriate_count = sum(
                1 for a in annotations if a.phanerozoic_appropriate
            )
            
            # Calculate confidence metrics
            if annotations:
                high_conf = sum(1 for a in annotations if a.evidence.confidence == "high")
                self.high_confidence_fraction = high_conf / len(annotations)

class TemporalDatabase(BaseModel):
    """Container for a complete temporal annotation database."""
    reactions: Dict[str, ReactionTemporalAnnotation] = Field(
        default_factory=dict, description="Reaction annotations by ID"
    )
    pathways: Dict[str, PathwayTemporalAnnotation] = Field(
        default_factory=dict, description="Pathway annotations by ID"
    )
    models: Dict[str, ModelTemporalMetadata] = Field(
        default_factory=dict, description="Model metadata by ID"
    )
    
    # Database metadata
    version: str = Field("0.1.0", description="Database version")
    last_updated: Optional[datetime] = Field(None)
    description: Optional[str] = Field(None)
    
    def add_reaction(self, annotation: ReactionTemporalAnnotation):
        """Add or update a reaction annotation."""
        self.reactions[annotation.reaction_id] = annotation
        if not self.last_updated or annotation.last_updated > self.last_updated:
            self.last_updated = annotation.last_updated
    
    def get_era_appropriate_reactions(self, era_cutoff_ga: float) -> List[str]:
        """Get all reaction IDs appropriate for a given era."""
        return [
            rxn_id for rxn_id, ann in self.reactions.items()
            if ann.is_appropriate_for_era(era_cutoff_ga)
        ]
    
    def export_to_yaml(self, filepath: str):
        """Export database to YAML format."""
        import yaml
        with open(filepath, 'w') as f:
            yaml.dump(self.dict(), f, default_flow_style=False)
    
    def export_to_json(self, filepath: str):
        """Export database to JSON format."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.dict(), f, indent=2, default=str)