"""
CHIMERA - Cognitive Heuristic Intelligence for Multi-stage Engagement Research & Assessment

Adversarial AI Research Platform for Red Team Operations

WARNING: This framework is designed for AUTHORIZED RED TEAM OPERATIONS ONLY.
Unauthorized deployment may constitute violations of:
- 18 U.S.C. § 1030 (Computer Fraud and Abuse Act)
- 18 U.S.C. § 2701 (Stored Communications Act)
- EU GDPR Articles 5, 9, 32
- CCPA § 1798.100

Version: 1.0.0-BLACKBOX
Author: Lucien Vallois
Date: December 2025
"""

__version__ = "1.0.0-BLACKBOX"
__author__ = "Lucien Vallois"
__description__ = "Adversarial AI Research Platform for Red Team Operations"

# Import core modules for easy access
from . import orchestrator
from . import pretext_engine
from . import identity_graph
from . import telemetry_engine
from . import email_delivery
from . import utils

__all__ = [
    "orchestrator",
    "pretext_engine",
    "identity_graph",
    "telemetry_engine",
    "email_delivery",
    "utils",
]


