"""
Temporal modeling framework for metabolic models.
Provides tools for annotating, filtering, and generating era-specific metabolic models.
"""

from .schema import (
    Evidence,
    ReactionTemporalAnnotation,
    PathwayTemporalAnnotation,
    ModelTemporalMetadata
)

__version__ = "0.1.0"
__all__ = [
    "Evidence",
    "ReactionTemporalAnnotation", 
    "PathwayTemporalAnnotation",
    "ModelTemporalMetadata"
]