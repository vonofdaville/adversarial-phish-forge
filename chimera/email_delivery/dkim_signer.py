"""
DKIM Signer - Email Authentication and Signing

Implements DKIM (DomainKeys Identified Mail) signing for email authenticity:
- RSA key pair generation and management
- DKIM-Signature header creation
- Email canonicalization (relaxed/simple)
- Integration with SMTP delivery

Ensures email deliverability and prevents spoofing detection.
"""

import base64
import hashlib
import re
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate
from typing import Dict, List, Optional, Any, Tuple
import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa
from cryptography.hazmat.backends import default_backend

from ..utils.config import config
from ..utils.logger import setup_logging

logger = setup_logging(__name__)


class DKIMSigner:
    """
    DKIM email signing implementation.

    Generates and manages DKIM signatures to authenticate email origin
    and improve deliverability.
    """

    def __init__(self, private_key_path: Optional[str] = None,
                 selector: Optional[str] = None, domain: Optional[str] = None):
        self.private_key_path = private_key_path or config.dkim_private_key_path
        self.selector = selector or config.dkim_selector
        self.domain = domain or self._extract_domain_from_email(config.smtp_user)

        self.private_key = None
        self.public_key = None

        # Load or generate keys
        self._load_keys()

    def _extract_domain_from_email(self, email: str) -> str:
        """Extract domain from email address."""
        if '@' in email:
            return email.split('@')[1]
        return 'chimera.local'  # Default fallback

    def _load_keys(self):
        """Load or generate DKIM key pair."""
        try:
            if self.private_key_path:
                # Load existing private key
                with open(self.private_key_path, 'rb') as f:
                    private_key_data = f.read()

                self.private_key = serialization.load_pem_private_key(
                    private_key_data,
                    password=None,
                    backend=default_backend()
                )
            else:
                # Generate new key pair
                logger.info("Generating new DKIM key pair")
                self.private_key = crypto_rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )

                # Save private key (in production, this should be done securely)
                if self.private_key_path:
                    private_key_pem = self.private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    )

                    with open(self.private_key_path, 'wb') as f:
                        f.write(private_key_pem)

            # Derive public key
            self.public_key = self.private_key.public_key()

        except Exception as e:
            logger.error(f"Failed to load/generate DKIM keys: {e}")
            # Generate in-memory keys as fallback
            self.private_key = crypto_rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()

    def sign_message(self, message: EmailMessage) -> EmailMessage:
        """
        Sign an email message with DKIM.

        Args:
            message: Email message to sign

        Returns:
            DKIM-signed email message
        """
        try:
            # Canonicalize message
            canonical_headers, canonical_body = self._canonicalize_message(message)

            # Create DKIM signature
            signature_data = self._create_signature(canonical_headers, canonical_body)

            # Add DKIM-Signature header
            message['DKIM-Signature'] = signature_data

            return message

        except Exception as e:
            logger.error(f"DKIM signing failed: {e}")
            return message  # Return unsigned message

    def _canonicalize_message(self, message: EmailMessage) -> Tuple[str, str]:
        """Canonicalize message headers and body for signing."""
        # Use relaxed canonicalization (most common)
        return self._relaxed_canonicalization(message)

    def _relaxed_canonicalization(self, message: EmailMessage) -> Tuple[str, str]:
        """Implement DKIM relaxed canonicalization."""
        # Headers to sign (standard DKIM headers)
        headers_to_sign = [
            'from', 'to', 'subject', 'date', 'message-id',
            'mime-version', 'content-type'
        ]

        canonical_headers = []

        for header_name in headers_to_sign:
            header_value = message.get(header_name)
            if header_value:
                # Relaxed header canonicalization: lowercase name, collapse whitespace
                canonical_name = header_name.lower()
                canonical_value = self._relaxed_header_value(header_value)
                canonical_headers.append(f"{canonical_name}:{canonical_value}")

        # Body canonicalization: ignore trailing empty lines
        body = message.get_payload()
        if isinstance(body, list):
            # Multipart message
            canonical_body = ""
        else:
            # Simple message
            canonical_body = body or ""

        # Remove trailing whitespace and empty lines
        canonical_body = self._relaxed_body_value(canonical_body)

        return "\r\n".join(canonical_headers), canonical_body

    def _relaxed_header_value(self, value: str) -> str:
        """Apply relaxed canonicalization to header value."""
        # Convert to lowercase (header names already handled)
        # Collapse whitespace sequences to single space
        # Remove leading/trailing whitespace
        return re.sub(r'\s+', ' ', value.strip())

    def _relaxed_body_value(self, body: str) -> str:
        """Apply relaxed canonicalization to body."""
        if not body:
            return ""

        # Remove trailing whitespace from each line
        lines = body.split('\n')
        canonical_lines = []

        for line in lines:
            # Remove trailing whitespace but preserve line
            canonical_lines.append(line.rstrip())

        # Remove trailing empty lines
        while canonical_lines and canonical_lines[-1] == "":
            canonical_lines.pop()

        return '\n'.join(canonical_lines) + '\n'

    def _create_signature(self, canonical_headers: str, canonical_body: str) -> str:
        """Create DKIM signature string."""
        # Calculate body hash
        body_hash = hashlib.sha256(canonical_body.encode('utf-8')).digest()
        body_hash_b64 = base64.b64encode(body_hash).decode('ascii')

        # Create signature data
        signature_data = f"v=1;a=rsa-sha256;c=relaxed/relaxed;d={self.domain};s={self.selector};bh={body_hash_b64};h=from:to:subject:date:message-id:mime-version:content-type;b="

        # Sign the headers
        signature_input = canonical_headers
        signature_bytes = signature_input.encode('utf-8')

        # Create signature
        signature = self.private_key.sign(
            signature_bytes,
            padding=crypto_rsa.PKCS1v15(),
            algorithm=hashlib.sha256()
        )

        signature_b64 = base64.b64encode(signature).decode('ascii')

        return signature_data + signature_b64

    def get_public_key_record(self) -> str:
        """Get DNS TXT record for DKIM public key."""
        try:
            # Get public key in DER format
            public_key_der = self.public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            # Convert to base64 for DNS
            public_key_b64 = base64.b64encode(public_key_der).decode('ascii')

            # Create DNS record
            dns_record = f"v=DKIM1;k=rsa;p={public_key_b64}"

            return dns_record

        except Exception as e:
            logger.error(f"Failed to generate public key DNS record: {e}")
            return ""

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate DKIM configuration."""
        issues = []

        if not self.domain:
            issues.append("DKIM domain not configured")
        elif not self._is_valid_domain(self.domain):
            issues.append(f"Invalid DKIM domain: {self.domain}")

        if not self.selector:
            issues.append("DKIM selector not configured")

        if not self.private_key:
            issues.append("DKIM private key not loaded")

        if not self.public_key:
            issues.append("DKIM public key not available")

        # Check if public key DNS record can be generated
        dns_record = self.get_public_key_record()
        if not dns_record:
            issues.append("Cannot generate DKIM DNS record")

        return {
            'valid': len(issues) == 0,
            'domain': self.domain,
            'selector': self.selector,
            'key_size': self._get_key_size(),
            'dns_record_length': len(dns_record),
            'issues': issues
        }

    def _is_valid_domain(self, domain: str) -> bool:
        """Basic domain validation."""
        # Simple regex for domain validation
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))

    def _get_key_size(self) -> int:
        """Get RSA key size."""
        try:
            if self.public_key:
                return self.public_key.key_size
        except:
            pass
        return 0

    def generate_dns_instructions(self) -> Dict[str, Any]:
        """Generate DNS configuration instructions."""
        dns_record = self.get_public_key_record()

        if not dns_record:
            return {
                'success': False,
                'error': 'Cannot generate DKIM DNS record'
            }

        # Create full DNS record name
        dns_name = f"{self.selector}._domainkey.{self.domain}"

        return {
            'success': True,
            'dns_name': dns_name,
            'record_type': 'TXT',
            'record_value': dns_record,
            'instructions': [
                f"Add the following DNS TXT record to {self.domain}:",
                f"Name: {dns_name}",
                f"Type: TXT",
                f"Value: {dns_record}",
                "",
                "This record allows email receivers to verify DKIM signatures.",
                "DNS propagation may take up to 24 hours."
            ]
        }

    def test_signature(self, test_message: str = None) -> Dict[str, Any]:
        """Test DKIM signature creation."""
        if test_message is None:
            test_message = """From: test@chimera.local
To: recipient@example.com
Subject: DKIM Test

This is a test message for DKIM signing.
"""

        try:
            # Create test email message
            from email.message import EmailMessage
            msg = EmailMessage()
            msg['From'] = 'test@chimera.local'
            msg['To'] = 'recipient@example.com'
            msg['Subject'] = 'DKIM Test'
            msg.set_content('This is a test message for DKIM signing.')

            # Sign message
            signed_msg = self.sign_message(msg)

            # Check if DKIM-Signature header was added
            dkim_header = signed_msg.get('DKIM-Signature')

            return {
                'success': bool(dkim_header),
                'signature_present': bool(dkim_header),
                'signature_length': len(dkim_header) if dkim_header else 0,
                'domain': self.domain,
                'selector': self.selector
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


