"""
CHIMERA Orchestrator - Campaign Lifecycle Management

FastAPI-based orchestrator that manages:
- Campaign creation and execution
- Queue management with Redis
- Integration with all CHIMERA components
- Ethical compliance and consent validation
"""

from .main import app
from .campaign_manager import CampaignManager
from .consent_validator import ConsentValidator
from .kill_switch import KillSwitch

__all__ = ["app", "CampaignManager", "ConsentValidator", "KillSwitch"]

