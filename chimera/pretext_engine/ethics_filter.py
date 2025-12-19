"""
Ethics Filter - Content Safety and Compliance Validation

Implements multi-layered ethical content filtering:
- Prohibited content detection
- Psychological safety assessment
- Consent boundary validation
- Legal compliance checking

Ensures all generated content meets CHIMERA's ethical standards.
"""

import re
from typing import Dict, List, Any, Set
from ..utils.logger import setup_logging, log_ethics_event

logger = setup_logging(__name__)


class EthicsFilter:
    """
    Multi-layered ethical content filter for CHIMERA pretext generation.

    Implements safety mechanisms to prevent:
    - Harmful or manipulative content
    - Privacy violations
    - Legal boundary crossings
    - Psychological distress
    """

    def __init__(self):
        # Prohibited content patterns
        self.prohibited_patterns = {
            'threats': [
                r'\b(immediately|urgent|emergency|critical|crisis)\b.*\b(action|respond|reply)\b',
                r'\b(account|access|service).*suspend|terminate|lock|disable\b',
                r'\b(legal|law|court|police|authorit)\b.*\b(action|contact|involve)\b',
                r'\b(deadline|time.?sensitive|time.?critical)\b',
                r'\b(consequences|penalties|fees|charges)\b.*\b(if|unless)\b'
            ],
            'manipulation': [
                r'\b(fear|afraid|worried|concerned|anxious)\b',
                r'\b(secret|confidential|private|classified)\b.*\b(share|disclose|reveal)\b',
                r'\b(guarantee|promise|assure)\b.*\b(safe|secure|protect)\b',
                r'\b(exclusive|limited|special|unique)\b.*\b(opportunity|offer|chance)\b'
            ],
            'impersonation': [
                r'\b(government|federal|fbi|cia|irs|sec|treasury|bank|police)\b.*\b(official|authority|agent)\b',
                r'\b(ceo|cto|cfo|president|director|manager)\b.*\b(office|executive|corporate)\b',
                r'\b(hr|human.resources|legal|counsel|compliance)\b.*\b(department|office|team)\b'
            ],
            'privacy_violation': [
                r'\b(password|credential|login|username|account)\b.*\b(verify|confirm|update|reset)\b',
                r'\b(personal|private|confidential|sensitive)\b.*\b(information|data|details)\b',
                r'\b(ssn|social.security|tax.id|birthdate|address|phone)\b',
                r'\b(medical|health|financial|legal)\b.*\b(record|information|data)\b'
            ],
            'psychological_distress': [
                r'\b(cancer|tumor|disease|illness|death|dying|bereavement)\b',
                r'\b(divorce|separation|breakup|affair|cheating)\b',
                r'\b(bankruptcy|foreclosure|eviction|homeless)\b',
                r'\b(accident|injury|hospital|emergency.room)\b'
            ]
        }

        # Required safety elements
        self.required_elements = {
            'opt_out': [
                r'\b(unsubscribe|opt.?out|stop|remove|no.*more)\b',
                r'\b(reply|email|contact)\b.*\b(unsubscribe|opt.?out)\b'
            ],
            'simulation_marker': [
                r'\b(simulation|training|exercise|test|practice)\b',
                r'\b(fake|mock|simulated|pretend|demo)\b',
                r'\b(do.*not|never|avoid)\b.*\b(click|open|respond)\b'
            ],
            'educational_context': [
                r'\b(learn|training|education|awareness|security)\b',
                r'\b(improve|enhance|develop|build)\b.*\b(skill|knowledge|awareness)\b'
            ]
        }

        # Severity levels for violations
        self.violation_severity = {
            'threats': 'CRITICAL',
            'privacy_violation': 'CRITICAL',
            'psychological_distress': 'HIGH',
            'manipulation': 'HIGH',
            'impersonation': 'MEDIUM'
        }

    def validate_pretext(
        self,
        pretext_content: str,
        ethical_constraints: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Validate pretext content against ethical and safety standards.

        Args:
            pretext_content: The pretext content to validate
            ethical_constraints: Ethical constraints to apply

        Returns:
            Dict with validation results and any violations
        """
        violations = []
        warnings = []
        approved = True

        # Convert content to lowercase for pattern matching
        content_lower = pretext_content.lower()

        # Check for prohibited content
        for category, patterns in self.prohibited_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    severity = self.violation_severity.get(category, 'MEDIUM')
                    violations.append({
                        'category': category,
                        'pattern': pattern,
                        'severity': severity,
                        'matched_text': self._extract_matched_text(pattern, pretext_content)
                    })

                    if severity == 'CRITICAL':
                        approved = False

        # Check required safety elements
        missing_elements = []
        for element_type, patterns in self.required_elements.items():
            element_present = any(
                re.search(pattern, content_lower, re.IGNORECASE)
                for pattern in patterns
            )

            if not element_present:
                # Check if this element is required by constraints
                constraint_key = element_type.replace('_', '_')
                if ethical_constraints.get(f'include_{constraint_key}', True):
                    missing_elements.append(element_type)
                    approved = False

        if missing_elements:
            violations.append({
                'category': 'missing_required_elements',
                'severity': 'HIGH',
                'missing_elements': missing_elements
            })

        # Check for overly aggressive language
        aggressive_indicators = [
            r'\b(must|required|mandatory|obligatory)\b',
            r'\b(immediate|instant|now|today|asap)\b',
            r'\b(failure|fail|unable|cannot)\b.*\b(result|cause|lead)\b',
            r'\b(important|critical|vital|essential)\b.*\b(action|step|measure)\b'
        ]

        aggressive_count = sum(
            1 for pattern in aggressive_indicators
            if re.search(pattern, content_lower)
        )

        if aggressive_count > 2:
            warnings.append("Content appears overly aggressive or coercive")
            if ethical_constraints.get('no_threats', True):
                approved = False
                violations.append({
                    'category': 'coercive_language',
                    'severity': 'MEDIUM',
                    'description': 'Excessive use of mandatory or urgent language'
                })

        # Check content length (should not be too short or too long)
        word_count = len(pretext_content.split())
        if word_count < 20:
            warnings.append("Content appears too brief to be realistic")
        elif word_count > 500:
            warnings.append("Content appears excessively long")

        # Check for proper email structure
        if not self._has_proper_email_structure(pretext_content):
            warnings.append("Content lacks proper email structure")

        # Log ethics check
        if violations:
            log_ethics_event(
                "ethics_filter_violation",
                severity=max((v.get('severity', 'LOW') for v in violations),
                           key=lambda x: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].index(x)),
                violation_count=len(violations),
                categories=[v['category'] for v in violations]
            )

        return {
            'approved': approved,
            'violations': violations,
            'warnings': warnings,
            'word_count': word_count,
            'aggressive_indicators': aggressive_count,
            'missing_elements': missing_elements
        }

    def validate_adaptation(
        self,
        original_pretext: str,
        adapted_pretext: str,
        adaptation_strategy: str
    ) -> Dict[str, Any]:
        """
        Validate pretext adaptation against ethical boundaries.

        Args:
            original_pretext: Original pretext content
            adapted_pretext: Adapted pretext content
            adaptation_strategy: Adaptation strategy used

        Returns:
            Validation results for adaptation
        """
        # Validate adapted content
        adapted_validation = self.validate_pretext(adapted_pretext, {})

        # Check if adaptation introduces new violations
        original_validation = self.validate_pretext(original_pretext, {})

        new_violations = []
        for violation in adapted_validation['violations']:
            if not any(
                ov['category'] == violation['category']
                for ov in original_validation['violations']
            ):
                new_violations.append(violation)

        # Assess adaptation risk
        risk_assessment = self._assess_adaptation_risk(
            adaptation_strategy,
            original_validation,
            adapted_validation
        )

        return {
            'adapted_validation': adapted_validation,
            'new_violations': new_violations,
            'risk_assessment': risk_assessment,
            'adaptation_safe': len(new_violations) == 0 and risk_assessment['level'] != 'HIGH'
        }

    def _extract_matched_text(self, pattern: str, content: str, context: int = 50) -> str:
        """Extract matched text with context."""
        try:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start = max(0, match.start() - context)
                end = min(len(content), match.end() + context)
                return f"...{content[start:end]}..."
        except:
            pass
        return "Pattern match found"

    def _has_proper_email_structure(self, content: str) -> bool:
        """Check if content has proper email structure."""
        # Check for greeting
        has_greeting = bool(re.search(r'\b(dear|hi|hello|good\s+(morning|afternoon|evening))\b', content, re.IGNORECASE))

        # Check for closing
        has_closing = bool(re.search(r'\b(best|regards|sincerely|thanks|thank you)\b', content, re.IGNORECASE))

        # Check for signature-like elements
        has_signature = bool(re.search(r'\b(name|title|department|company|organization)\b', content, re.IGNORECASE))

        return has_greeting or has_closing or has_signature

    def _assess_adaptation_risk(
        self,
        adaptation_strategy: str,
        original_validation: Dict[str, Any],
        adapted_validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk level of adaptation."""
        risk_level = 'LOW'
        risk_factors = []

        # High-risk adaptation strategies
        high_risk_strategies = [
            'increase_urgency', 'add_threats', 'personalize_sensitive_data',
            'impersonate_authority', 'create_emergency_scenario'
        ]

        if adaptation_strategy in high_risk_strategies:
            risk_level = 'HIGH'
            risk_factors.append(f"High-risk adaptation strategy: {adaptation_strategy}")

        # Check if adaptation introduces new violations
        if adapted_validation['violations'] and not original_validation['violations']:
            risk_level = max(risk_level, 'MEDIUM')
            risk_factors.append("Adaptation introduces new ethical violations")

        # Check if warnings increased significantly
        if len(adapted_validation.get('warnings', [])) > len(original_validation.get('warnings', [])) + 1:
            risk_level = max(risk_level, 'MEDIUM')
            risk_factors.append("Adaptation significantly increases warning indicators")

        # Assess based on content changes
        original_aggressive = original_validation.get('aggressive_indicators', 0)
        adapted_aggressive = adapted_validation.get('aggressive_indicators', 0)

        if adapted_aggressive > original_aggressive + 1:
            risk_level = max(risk_level, 'MEDIUM')
            risk_factors.append("Adaptation increases coercive language")

        return {
            'level': risk_level,
            'factors': risk_factors,
            'recommendations': self._get_risk_mitigations(risk_level, adaptation_strategy)
        }

    def _get_risk_mitigations(self, risk_level: str, adaptation_strategy: str) -> List[str]:
        """Get risk mitigation recommendations."""
        mitigations = []

        if risk_level == 'HIGH':
            mitigations.extend([
                "Require additional human review",
                "Limit adaptation scope",
                "Consider reverting to original pretext",
                "Document risk assessment"
            ])

        elif risk_level == 'MEDIUM':
            mitigations.extend([
                "Perform additional ethics filter validation",
                "Test adaptation with smaller audience first",
                "Monitor closely for adverse reactions"
            ])

        # Strategy-specific mitigations
        if 'urgency' in adaptation_strategy:
            mitigations.append("Ensure urgency does not cross into threat language")

        if 'personalize' in adaptation_strategy:
            mitigations.append("Verify personalization uses only consented data")

        if 'impersonate' in adaptation_strategy:
            mitigations.append("Ensure impersonation is clearly marked as simulation")

        return mitigations

    def get_filter_stats(self) -> Dict[str, Any]:
        """Get statistics about filter operations."""
        # This would track filter performance over time
        # For now, return basic structure
        return {
            'total_validations': 0,
            'approved_count': 0,
            'rejected_count': 0,
            'violation_categories': {},
            'most_common_violations': []
        }


