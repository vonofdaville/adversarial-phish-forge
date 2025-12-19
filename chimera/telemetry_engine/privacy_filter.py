"""
Privacy Filter - Differential Privacy and Data Anonymization

Implements advanced privacy protection for telemetry data:
- Differential privacy with configurable epsilon
- K-anonymity for fingerprinting
- Data minimization and aggregation
- Cryptographic hashing for PII protection

Ensures behavioral analytics without compromising participant privacy.
"""

import hashlib
import hmac
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
import numpy as np

from ..utils.config import config
from ..utils.logger import setup_logging, log_privacy_event

logger = setup_logging(__name__)


class PrivacyFilter:
    """
    Advanced privacy protection for telemetry data.

    Implements multiple privacy-enhancing techniques:
    - Differential privacy for statistical queries
    - K-anonymity for fingerprinting
    - Cryptographic anonymization for PII
    """

    def __init__(self, epsilon: Optional[float] = None, k_anonymity: int = 5):
        self.epsilon = epsilon or config.differential_privacy_epsilon
        self.k_anonymity = k_anonymity
        self.salt = config.fingerprint_hash_salt

        # Pre-computed noise distributions for differential privacy
        self._setup_noise_distributions()

    def _setup_noise_distributions(self):
        """Setup noise distributions for differential privacy."""
        # Laplace distribution for adding noise to counts
        self.laplace_scale = 1.0 / self.epsilon

        # For categorical data, we'll use randomized response
        self.randomized_response_prob = 0.8  # Probability of truthful response

    def anonymize_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize a telemetry event while preserving analytical utility.

        Args:
            event_data: Raw telemetry event

        Returns:
            Anonymized event data
        """
        anonymized = {
            'event_id': self._generate_event_id(event_data),
            'campaign_id': event_data.get('campaign_id', ''),
            'event_type': event_data.get('event_type', 'unknown'),
            'timestamp': event_data.get('timestamp', datetime.utcnow().isoformat()),
            'consent_verified': event_data.get('consent_verified', True),
            'anonymization_level': 'standard'
        }

        # Anonymize fingerprint
        if 'fingerprint' in event_data:
            anonymized['fingerprint_hash'] = self._anonymize_fingerprint(event_data['fingerprint'])

        # Anonymize user agent
        if 'user_agent' in event_data:
            anonymized['user_agent_hash'] = self._hash_user_agent(event_data['user_agent'])

        # Anonymize IP address
        if 'ip_address' in event_data:
            anonymized['ip_hash'] = self._anonymize_ip(event_data['ip_address'])

        # Process geolocation (country-level only, no city/coordinates)
        if 'geolocation' in event_data:
            anonymized['geolocation_country'] = self._process_geolocation(event_data['geolocation'])

        # Extract device/browser metadata (general categories only)
        if 'browser_info' in event_data:
            device_info = self._extract_device_info(event_data['browser_info'])
            anonymized.update(device_info)

        # Process event-specific metadata
        if 'metadata' in event_data:
            anonymized['event_metadata'] = self._anonymize_metadata(event_data['metadata'])

        # Add participant ID if available (should already be anonymized)
        if 'participant_id' in event_data:
            anonymized['participant_id'] = event_data['participant_id']

        log_privacy_event(
            "event_anonymized",
            operation="data_anonymization",
            event_type=event_data.get('event_type'),
            anonymization_technique="differential_privacy"
        )

        return anonymized

    def apply_differential_privacy(self, query_result: List[Tuple],
                                 sensitivity: float = 1.0) -> List[Tuple]:
        """
        Apply differential privacy to query results.

        Args:
            query_result: Raw query results
            sensitivity: Query sensitivity (max difference when one record changes)

        Returns:
            Results with differential privacy noise added
        """
        if not query_result:
            return query_result

        privatized_results = []

        for row in query_result:
            privatized_row = []
            for value in row:
                if isinstance(value, (int, float)):
                    # Add Laplace noise for numeric values
                    noise = np.random.laplace(0, self.laplace_scale * sensitivity)
                    privatized_value = value + noise

                    # Ensure non-negative counts
                    if isinstance(value, int) and privatized_value < 0:
                        privatized_value = 0

                    privatized_row.append(privatized_value)
                else:
                    # For non-numeric data, use randomized response
                    privatized_row.append(self._apply_randomized_response(value))

            privatized_results.append(tuple(privatized_row))

        return privatized_results

    def check_k_anonymity(self, dataset: List[Dict[str, Any]],
                         quasi_identifiers: List[str]) -> Dict[str, Any]:
        """
        Check k-anonymity of a dataset.

        Args:
            dataset: Dataset to check
            quasi_identifiers: Fields that could identify individuals

        Returns:
            K-anonymity analysis results
        """
        if len(dataset) < self.k_anonymity:
            return {
                'k_anonymity_satisfied': False,
                'min_group_size': len(dataset),
                'required_k': self.k_anonymity,
                'recommendation': 'Dataset too small for k-anonymity'
            }

        # Count frequency of quasi-identifier combinations
        frequency_map = {}
        for record in dataset:
            qi_tuple = tuple(record.get(qi, 'unknown') for qi in quasi_identifiers)
            frequency_map[qi_tuple] = frequency_map.get(qi_tuple, 0) + 1

        min_group_size = min(frequency_map.values())
        max_group_size = max(frequency_map.values())

        return {
            'k_anonymity_satisfied': min_group_size >= self.k_anonymity,
            'min_group_size': min_group_size,
            'max_group_size': max_group_size,
            'required_k': self.k_anonymity,
            'unique_combinations': len(frequency_map),
            'groups_below_k': sum(1 for count in frequency_map.values() if count < self.k_anonymity)
        }

    def _generate_event_id(self, event_data: Dict[str, Any]) -> str:
        """Generate a unique event ID."""
        # Create a hash of key event properties
        key_components = [
            event_data.get('campaign_id', ''),
            event_data.get('participant_id', ''),
            event_data.get('event_type', ''),
            str(event_data.get('timestamp', '')),
            str(random.randint(0, 1000000))  # Add randomness to prevent collisions
        ]

        combined = '|'.join(key_components)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _anonymize_fingerprint(self, fingerprint: Dict[str, Any]) -> str:
        """Create anonymized fingerprint hash."""
        # Sort keys for consistent hashing
        sorted_fingerprint = json.dumps(fingerprint, sort_keys=True, default=str)

        # Create HMAC for additional security
        return hmac.new(
            self.salt.encode(),
            sorted_fingerprint.encode(),
            hashlib.sha256
        ).hexdigest()

    def _hash_user_agent(self, user_agent: str) -> str:
        """Hash user agent string."""
        return hashlib.sha256(f"{user_agent}:{self.salt}".encode()).hexdigest()

    def _anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address to subnet level."""
        try:
            # For IPv4, keep only first two octets
            if '.' in ip_address:
                octets = ip_address.split('.')
                if len(octets) >= 2:
                    return f"{octets[0]}.{octets[1]}.0.0"
            # For IPv6, truncate to /32
            elif ':' in ip_address:
                # Keep only first 4 segments
                segments = ip_address.split(':')[:4]
                return ':'.join(segments) + '::'
        except Exception:
            pass

        # Fallback: hash the entire IP
        return hashlib.sha256(f"{ip_address}:{self.salt}".encode()).hexdigest()

    def _process_geolocation(self, geolocation: Dict[str, Any]) -> str:
        """Process geolocation data - country level only."""
        # Only keep country information, discard city/coordinates
        country = geolocation.get('country', geolocation.get('country_code', ''))

        # Validate country code format
        if len(country) == 2 and country.isalpha():
            return country.upper()

        # If no valid country, return empty
        return ''

    def _extract_device_info(self, browser_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract general device/browser categories."""
        device_info = {}

        # Device type (mobile, desktop, tablet)
        user_agent = browser_info.get('user_agent', '').lower()
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            device_info['device_type'] = 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            device_info['device_type'] = 'tablet'
        else:
            device_info['device_type'] = 'desktop'

        # Browser family (general category)
        if 'chrome' in user_agent:
            device_info['browser_family'] = 'chrome'
        elif 'firefox' in user_agent:
            device_info['browser_family'] = 'firefox'
        elif 'safari' in user_agent:
            device_info['browser_family'] = 'safari'
        elif 'edge' in user_agent:
            device_info['browser_family'] = 'edge'
        else:
            device_info['browser_family'] = 'other'

        # OS family (general category)
        if 'windows' in user_agent:
            device_info['os_family'] = 'windows'
        elif 'mac' in user_agent or 'os x' in user_agent:
            device_info['os_family'] = 'macos'
        elif 'linux' in user_agent:
            device_info['os_family'] = 'linux'
        elif 'android' in user_agent:
            device_info['os_family'] = 'android'
        elif 'ios' in user_agent:
            device_info['os_family'] = 'ios'
        else:
            device_info['os_family'] = 'other'

        # Screen resolution (binned to prevent fingerprinting)
        screen_width = browser_info.get('screen_width', 0)
        screen_height = browser_info.get('screen_height', 0)

        if screen_width and screen_height:
            # Bin screen resolutions to reduce uniqueness
            if screen_width <= 1024:
                width_bin = 'small'
            elif screen_width <= 1920:
                width_bin = 'medium'
            else:
                width_bin = 'large'

            if screen_height <= 768:
                height_bin = 'small'
            elif screen_height <= 1080:
                height_bin = 'medium'
            else:
                height_bin = 'large'

            device_info['screen_resolution'] = f"{width_bin}x{height_bin}"
        else:
            device_info['screen_resolution'] = 'unknown'

        # Timezone (keep as-is, commonly shared)
        device_info['timezone'] = browser_info.get('timezone', 'unknown')

        # Language (keep general language family)
        language = browser_info.get('language', 'unknown')
        if language and len(language) >= 2:
            device_info['language'] = language[:2].lower()  # First two chars (e.g., 'en', 'es')
        else:
            device_info['language'] = 'unknown'

        return device_info

    def _anonymize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Anonymize event-specific metadata."""
        # Remove or generalize sensitive metadata
        anonymized = {}

        for key, value in metadata.items():
            # Skip sensitive keys
            if key.lower() in ['password', 'username', 'email', 'name', 'address', 'phone']:
                continue

            # Generalize numeric values
            if isinstance(value, (int, float)):
                # Bin numeric values to reduce precision
                if value < 10:
                    anonymized[key] = '<10'
                elif value < 100:
                    anonymized[key] = '10-99'
                elif value < 1000:
                    anonymized[key] = '100-999'
                else:
                    anonymized[key] = '1000+'
            else:
                # Keep string values but limit length
                if isinstance(value, str) and len(value) > 50:
                    anonymized[key] = value[:47] + '...'
                else:
                    anonymized[key] = value

        return json.dumps(anonymized)

    def _apply_randomized_response(self, value: Any) -> Any:
        """Apply randomized response for categorical data."""
        if random.random() < self.randomized_response_prob:
            return value  # Truthful response
        else:
            # Return a random alternative (simplified - in practice,
            # this would use domain-specific randomization)
            if isinstance(value, str):
                return f"randomized_{hash(str(value)) % 100}"
            else:
                return value

    def get_privacy_metrics(self) -> Dict[str, Any]:
        """Get privacy protection metrics."""
        return {
            'differential_privacy_epsilon': self.epsilon,
            'k_anonymity_requirement': self.k_anonymity,
            'laplace_noise_scale': self.laplace_scale,
            'randomized_response_probability': self.randomized_response_prob,
            'anonymization_techniques': [
                'cryptographic_hashing',
                'ip_address_truncation',
                'geographic_generalization',
                'screen_resolution_binning',
                'metadata_minimization'
            ]
        }

    def estimate_privacy_risk(self, query_result: List[Tuple]) -> Dict[str, Any]:
        """
        Estimate privacy risk of query results.

        Args:
            query_result: Query results to analyze

        Returns:
            Privacy risk assessment
        """
        if not query_result:
            return {'risk_level': 'low', 'concerns': []}

        concerns = []
        risk_score = 0

        # Check for small group sizes (re-identification risk)
        for row in query_result:
            for value in row:
                if isinstance(value, (int, float)) and value > 0 and value < 5:
                    concerns.append(f"Small count detected: {value}")
                    risk_score += 1

        # Check for unique combinations
        unique_rows = len(set(query_result))
        if unique_rows == len(query_result):
            concerns.append("All rows appear unique")
            risk_score += 2

        # Determine risk level
        if risk_score >= 3:
            risk_level = 'high'
        elif risk_score >= 1:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'concerns': concerns,
            'recommendations': self._get_privacy_recommendations(risk_level)
        }

    def _get_privacy_recommendations(self, risk_level: str) -> List[str]:
        """Get privacy protection recommendations."""
        if risk_level == 'high':
            return [
                'Implement additional aggregation before release',
                'Consider query restrictions or access controls',
                'Review data minimization techniques',
                'Consider increasing differential privacy epsilon'
            ]
        elif risk_level == 'medium':
            return [
                'Add more noise to query results',
                'Implement k-anonymity checks',
                'Consider result suppression for small groups'
            ]
        else:
            return [
                'Current privacy protections appear adequate',
                'Continue monitoring for emerging risks'
            ]


