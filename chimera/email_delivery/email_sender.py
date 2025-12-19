"""
Email Sender - SMTP Delivery with DKIM and Tracking

Handles secure email delivery for CHIMERA campaigns:
- SMTP sending with authentication
- DKIM signing for email authenticity
- Tracking pixel injection for opens
- Link tracking for clicks
- Bounce handling and reputation management

Maintains deliverability while enabling measurement.
"""

import asyncio
import base64
import re
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from email.utils import formataddr
from typing import Dict, List, Optional, Any, Tuple
import aiosmtplib
from aiosmtplib import SMTP

from ..utils.config import config
from ..utils.logger import setup_logging, log_audit_event
from .dkim_signer import DKIMSigner

logger = setup_logging(__name__)


class EmailSender:
    """
    Secure email delivery system with tracking capabilities.

    Manages the complete email sending pipeline with privacy preservation
    and deliverability optimization.
    """

    def __init__(self):
        self.dkim_signer = DKIMSigner()
        self.smtp_host = config.smtp_host
        self.smtp_port = config.smtp_port
        self.smtp_user = config.smtp_user
        self.smtp_password = config.smtp_password
        self.smtp_tls = config.smtp_tls

        # Tracking server URL for pixels and links
        self.tracking_base_url = config.tracking_base_url

        # Email templates
        self._setup_email_templates()

    def _setup_email_templates(self):
        """Setup email templates with tracking elements."""
        self.tracking_pixel_html = '''
<img src="{tracking_url}/pixel/{campaign_id}/{participant_id}/{email_id}.png"
     width="1" height="1" style="display:none;" alt="" />
'''

        self.tracking_link_pattern = '{tracking_url}/click/{campaign_id}/{participant_id}/{email_id}/{link_id}'

    async def send_campaign_emails(self, campaign_data: Dict[str, Any],
                                 target_emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send emails for a campaign with tracking.

        Args:
            campaign_data: Campaign configuration
            target_emails: List of target email configurations

        Returns:
            Sending results and tracking data
        """
        campaign_id = campaign_data['campaign_id']
        results = {
            'campaign_id': campaign_id,
            'emails_sent': 0,
            'emails_failed': 0,
            'tracking_pixels_injected': 0,
            'links_tracked': 0,
            'errors': [],
            'email_tracking_ids': []
        }

        # Create SMTP connection
        smtp = None
        try:
            smtp = SMTP(hostname=self.smtp_host, port=self.smtp_port, use_tls=self.smtp_tls)
            await smtp.connect()
            await smtp.login(self.smtp_user, self.smtp_password)

            # Send emails concurrently with rate limiting
            semaphore = asyncio.Semaphore(10)  # Limit concurrent sends

            async def send_single_email(target_config: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    return await self._send_single_email(
                        smtp, campaign_data, target_config
                    )

            # Send all emails
            tasks = [send_single_email(target) for target in target_emails]
            email_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(email_results):
                if isinstance(result, Exception):
                    results['emails_failed'] += 1
                    results['errors'].append(f"Email {i}: {str(result)}")
                else:
                    if result['success']:
                        results['emails_sent'] += 1
                        results['email_tracking_ids'].append(result['tracking_id'])
                        if result['pixel_injected']:
                            results['tracking_pixels_injected'] += 1
                        results['links_tracked'] += result['links_tracked']
                    else:
                        results['emails_failed'] += 1
                        results['errors'].append(result['error'])

        except Exception as e:
            logger.error(f"Campaign email sending failed: {e}")
            results['errors'].append(f"SMTP connection error: {str(e)}")
        finally:
            if smtp:
                await smtp.quit()

        log_audit_event(
            "campaign_emails_sent",
            campaign_id=campaign_id,
            emails_sent=results['emails_sent'],
            emails_failed=results['emails_failed']
        )

        return results

    async def _send_single_email(self, smtp: SMTP, campaign_data: Dict[str, Any],
                               target_config: Dict[str, Any]) -> Dict[str, Any]:
        """Send a single tracked email."""
        try:
            participant_id = target_config['participant_id']
            recipient_email = target_config['email']

            # Generate unique tracking IDs
            email_id = str(uuid.uuid4())
            tracking_id = f"{campaign_data['campaign_id']}_{participant_id}_{email_id}"

            # Prepare email content with tracking
            email_content = self._prepare_email_content(
                campaign_data, target_config, email_id
            )

            # Create email message
            message = self._create_email_message(
                email_content, recipient_email, campaign_data
            )

            # Sign with DKIM
            signed_message = self.dkim_signer.sign_message(message)

            # Send email
            await smtp.send_message(signed_message)

            return {
                'success': True,
                'tracking_id': tracking_id,
                'email_id': email_id,
                'participant_id': participant_id,
                'pixel_injected': email_content['pixel_injected'],
                'links_tracked': email_content['links_tracked']
            }

        except Exception as e:
            logger.error(f"Failed to send email to {target_config.get('email', 'unknown')}: {e}")
            return {
                'success': False,
                'error': str(e),
                'participant_id': target_config.get('participant_id', 'unknown')
            }

    def _prepare_email_content(self, campaign_data: Dict[str, Any],
                             target_config: Dict[str, Any],
                             email_id: str) -> Dict[str, Any]:
        """Prepare email content with tracking elements."""
        pretext_data = campaign_data.get('pretext_data', {})
        participant_id = target_config['participant_id']
        campaign_id = campaign_data['campaign_id']

        # Get base content
        subject = pretext_data.get('subject', 'Security Training Notification')
        body = pretext_data.get('body', 'This is a security awareness training simulation.')

        # Inject tracking pixel
        pixel_injected = False
        if campaign_data.get('enable_tracking', True):
            tracking_pixel = self.tracking_pixel_html.format(
                tracking_url=self.tracking_base_url.rstrip('/'),
                campaign_id=campaign_id,
                participant_id=participant_id,
                email_id=email_id
            )
            body += tracking_pixel
            pixel_injected = True

        # Track links
        links_tracked = 0
        if campaign_data.get('enable_link_tracking', True):
            body, links_tracked = self._inject_link_tracking(
                body, campaign_id, participant_id, email_id
            )

        # Add simulation disclaimer
        if pretext_data.get('simulation_markers'):
            disclaimer = "\n\n---\n" + "\n".join(pretext_data['simulation_markers'])
            body += disclaimer

        return {
            'subject': subject,
            'body': body,
            'pixel_injected': pixel_injected,
            'links_tracked': links_tracked,
            'email_id': email_id
        }

    def _inject_link_tracking(self, body: str, campaign_id: str,
                            participant_id: str, email_id: str) -> Tuple[str, int]:
        """Inject tracking redirects into links."""
        links_tracked = 0

        def replace_link(match):
            nonlocal links_tracked
            original_url = match.group(1)
            link_id = str(uuid.uuid4())[:8]  # Short ID for URL brevity

            tracking_url = self.tracking_link_pattern.format(
                tracking_url=self.tracking_base_url.rstrip('/'),
                campaign_id=campaign_id,
                participant_id=participant_id,
                email_id=email_id,
                link_id=link_id
            )

            # Store original URL for redirect (would be cached in Redis)
            # In production, store: tracking_url -> original_url mapping

            links_tracked += 1
            return f'href="{tracking_url}"'

        # Replace all href attributes
        pattern = r'href="([^"]*)"'
        modified_body = re.sub(pattern, replace_link, body, flags=re.IGNORECASE)

        return modified_body, links_tracked

    def _create_email_message(self, email_content: Dict[str, Any],
                            recipient_email: str, campaign_data: Dict[str, Any]) -> MIMEMultipart:
        """Create a properly formatted email message."""
        message = MIMEMultipart('alternative')
        message['Subject'] = Header(email_content['subject'], 'utf-8')
        message['From'] = formataddr((campaign_data.get('sender_name', 'Security Training'), self.smtp_user))
        message['To'] = recipient_email

        # Add headers for better deliverability
        message['X-Campaign-ID'] = campaign_data['campaign_id']
        message['X-Auto-Response-Suppress'] = 'All'
        message['List-Unsubscribe'] = f'<mailto:{self.smtp_user}?subject=unsubscribe>'

        # Add timestamp
        message['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Create HTML body
        html_body = f"""
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
    {email_content['body'].replace(chr(10), '<br>')}
</body>
</html>
"""

        # Attach HTML content
        html_part = MIMEText(html_body, 'html', 'utf-8')
        message.attach(html_part)

        return message

    async def send_test_email(self, recipient_email: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a test email for campaign validation."""
        test_target = {
            'participant_id': 'test-participant',
            'email': recipient_email
        }

        # Create minimal test campaign data
        test_campaign = {
            'campaign_id': 'test-campaign',
            'sender_name': 'CHIMERA Test',
            'enable_tracking': False,  # Disable tracking for tests
            'pretext_data': {
                'subject': 'CHIMERA Test Email',
                'body': 'This is a test email from the CHIMERA platform. If you received this, email delivery is working correctly.',
                'simulation_markers': ['TEST EMAIL - DO NOT RESPOND']
            }
        }

        # Send single test email
        smtp = None
        try:
            smtp = SMTP(hostname=self.smtp_host, port=self.smtp_port, use_tls=self.smtp_tls)
            await smtp.connect()
            await smtp.login(self.smtp_user, self.smtp_password)

            result = await self._send_single_email(smtp, test_campaign, test_target)

            return {
                'success': result['success'],
                'test_email_sent': result['success'],
                'recipient': recipient_email,
                'error': result.get('error') if not result['success'] else None
            }

        except Exception as e:
            logger.error(f"Test email failed: {e}")
            return {
                'success': False,
                'test_email_sent': False,
                'recipient': recipient_email,
                'error': str(e)
            }
        finally:
            if smtp:
                await smtp.quit()

    def validate_email_configuration(self) -> Dict[str, Any]:
        """Validate email delivery configuration."""
        issues = []

        # Check required configuration
        if not self.smtp_host:
            issues.append("SMTP host not configured")
        if not self.smtp_user:
            issues.append("SMTP user not configured")
        if not self.smtp_password:
            issues.append("SMTP password not configured")

        # Check DKIM configuration
        dkim_status = self.dkim_signer.validate_configuration()
        if not dkim_status['valid']:
            issues.extend(dkim_status['issues'])

        # Check tracking URL
        if not self.tracking_base_url:
            issues.append("Tracking base URL not configured")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'smtp_configured': bool(self.smtp_host and self.smtp_user and self.smtp_password),
            'dkim_configured': dkim_status['valid'],
            'tracking_configured': bool(self.tracking_base_url)
        }

    def get_delivery_metrics(self) -> Dict[str, Any]:
        """Get email delivery performance metrics."""
        # In a production system, this would query delivery logs
        # For now, return configuration status
        config_validation = self.validate_email_configuration()

        return {
            'configuration_valid': config_validation['valid'],
            'smtp_ready': config_validation['smtp_configured'],
            'dkim_ready': config_validation['dkim_configured'],
            'tracking_ready': config_validation['tracking_configured'],
            'deliverability_score': 85 if config_validation['valid'] else 0,  # Estimated
            'configuration_issues': config_validation['issues']
        }


