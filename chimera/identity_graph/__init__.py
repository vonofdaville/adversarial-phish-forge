"""
Identity Graph - Neo4j-based Relationship Mapping

Manages target profiles and relationships using:
- Neo4j graph database
- Simulated OSINT correlation
- Trust path analysis
- Privacy-preserving data handling
"""

from .identity_mapper import IdentityMapper
from .graph_builder import GraphBuilder

__all__ = ["IdentityMapper", "GraphBuilder"]


