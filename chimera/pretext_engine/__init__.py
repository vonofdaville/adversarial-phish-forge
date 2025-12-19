"""
Pretext Engine - GPT-4 Powered Adaptive Email Generation

Generates sophisticated, context-aware phishing pretexts using:
- OpenAI GPT-4 API
- Ethical safety filters
- Target profile analysis
- Campaign objective alignment
"""

from .pretext_generator import PretextGenerator
from .ethics_filter import EthicsFilter

__all__ = ["PretextGenerator", "EthicsFilter"]

