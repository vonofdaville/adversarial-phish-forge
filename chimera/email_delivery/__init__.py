"""
Email Delivery Subsystem - SMTP with DKIM and Tracking

Legitimate email infrastructure featuring:
- Postfix SMTP server
- DKIM signing for authenticity
- Tracking pixel injection
- Bounce handling and reputation management
"""

from .email_sender import EmailSender
from .dkim_signer import DKIMSigner

__all__ = ["EmailSender", "DKIMSigner"]

