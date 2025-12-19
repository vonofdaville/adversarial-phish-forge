"""
Pretext Generator - GPT-4 Powered Adaptive Email Generation

Generates sophisticated, context-aware phishing pretexts using:
- OpenAI GPT-4 API with ethical constraints
- Target profile analysis and personalization
- Campaign objective alignment
- Real-time adaptation based on campaign feedback

Maintains strict ethical boundaries and safety filters.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import openai
from openai import OpenAI

from ..utils.config import config
from ..utils.logger import setup_logging, log_audit_event, log_ethics_event
from .ethics_filter import EthicsFilter

logger = setup_logging(__name__)


class PretextGenerator:
    """
    GPT-4 powered pretext generation with ethical safeguards.

    Generates adaptive phishing pretexts that:
    - Personalize based on target profiles
    - Adapt to campaign objectives
    - Maintain ethical boundaries
    - Include opt-out mechanisms
    - Avoid prohibited content
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=config.openai_api_key,
            organization=config.openai_organization
        )
        self.ethics_filter = EthicsFilter()
        self.model = config.openai_model
        self.generation_history: List[Dict[str, Any]] = []

    async def generate_pretext(
        self,
        campaign_type: str,
        target_profile: Dict[str, Any],
        campaign_objective: str,
        ethical_constraints: Dict[str, bool],
        pretext_template: Optional[str] = None,
        adaptation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a pretext using GPT-4 with ethical constraints.

        Args:
            campaign_type: Type of campaign (phishing, vishing, etc.)
            target_profile: Profile data for the target
            campaign_objective: Campaign objective (credential_harvest, awareness, etc.)
            ethical_constraints: Ethical constraints to apply
            pretext_template: Optional template to use as base
            adaptation_data: Previous campaign performance data for adaptation

        Returns:
            Dict containing generated pretext and metadata
        """
        try:
            # Construct system prompt with ethical constraints
            system_prompt = self._build_system_prompt(ethical_constraints)

            # Construct user prompt with target context
            user_prompt = self._build_user_prompt(
                campaign_type,
                target_profile,
                campaign_objective,
                pretext_template,
                adaptation_data
            )

            # Generate pretext with GPT-4
            response = await self._call_gpt4(system_prompt, user_prompt)

            if not response:
                return {
                    "success": False,
                    "reason": "GPT-4 API call failed",
                    "pretext": None
                }

            pretext_content = response.choices[0].message.content.strip()

            # Apply ethical safety filter
            filter_result = self.ethics_filter.validate_pretext(
                pretext_content,
                ethical_constraints
            )

            if not filter_result["approved"]:
                log_ethics_event(
                    "pretext_filter_violation",
                    severity="HIGH",
                    violations=filter_result["violations"],
                    campaign_type=campaign_type
                )

                return {
                    "success": False,
                    "reason": f"Ethics filter violation: {', '.join(filter_result['violations'])}",
                    "pretext": None,
                    "filter_result": filter_result
                }

            # Parse pretext components
            pretext_data = self._parse_pretext_response(pretext_content)

            # Log generation
            log_audit_event(
                "pretext_generated",
                pretext_type=campaign_type,
                campaign_objective=campaign_objective,
                target_profile_hash=self._hash_target_profile(target_profile),
                ethical_constraints=ethical_constraints
            )

            # Store in generation history
            self.generation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "campaign_type": campaign_type,
                "target_profile": target_profile,
                "pretext_data": pretext_data,
                "filter_result": filter_result
            })

            return {
                "success": True,
                "pretext": pretext_data,
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "model": self.model,
                    "ethical_check_passed": True,
                    "filter_warnings": filter_result.get("warnings", [])
                }
            }

        except Exception as e:
            logger.error(f"Pretext generation error: {e}")
            return {
                "success": False,
                "reason": f"Generation error: {str(e)}",
                "pretext": None
            }

    async def adapt_pretext(
        self,
        original_pretext: Dict[str, Any],
        performance_data: Dict[str, Any],
        adaptation_strategy: str
    ) -> Dict[str, Any]:
        """
        Adapt existing pretext based on performance data.

        Args:
            original_pretext: Original pretext data
            performance_data: Campaign performance metrics
            adaptation_strategy: Adaptation strategy to apply

        Returns:
            Adapted pretext data
        """
        try:
            system_prompt = """You are adapting an existing phishing simulation pretext based on campaign performance.
Maintain all ethical constraints and safety measures."""

            user_prompt = f"""
Original pretext:
Subject: {original_pretext.get('subject', '')}
Body: {original_pretext.get('body', '')}

Performance data:
- Open rate: {performance_data.get('open_rate', 0):.1%}
- Click rate: {performance_data.get('click_rate', 0):.1%}
- Report rate: {performance_data.get('report_rate', 0):.1%}
- Success indicators: {performance_data.get('success_indicators', [])}

Adaptation strategy: {adaptation_strategy}

Generate an adapted version that improves effectiveness while maintaining ethical standards.
"""

            response = await self._call_gpt4(system_prompt, user_prompt)

            if response:
                adapted_content = response.choices[0].message.content.strip()
                adapted_data = self._parse_pretext_response(adapted_content)

                # Validate adapted pretext
                filter_result = self.ethics_filter.validate_pretext(
                    adapted_content,
                    original_pretext.get('ethical_constraints', {})
                )

                if filter_result["approved"]:
                    log_audit_event(
                        "pretext_adapted",
                        adaptation_strategy=adaptation_strategy,
                        performance_data=performance_data
                    )

                    return {
                        "success": True,
                        "pretext": adapted_data,
                        "adaptation_metadata": {
                            "strategy": adaptation_strategy,
                            "performance_data": performance_data,
                            "adapted_at": datetime.utcnow().isoformat()
                        }
                    }

            return {
                "success": False,
                "reason": "Adaptation failed or violated ethical constraints",
                "pretext": original_pretext  # Return original if adaptation fails
            }

        except Exception as e:
            logger.error(f"Pretext adaptation error: {e}")
            return {
                "success": False,
                "reason": f"Adaptation error: {str(e)}",
                "pretext": original_pretext
            }

    def _build_system_prompt(self, ethical_constraints: Dict[str, bool]) -> str:
        """Build system prompt with ethical constraints."""
        constraints_text = ""

        if ethical_constraints.get("no_threats", True):
            constraints_text += "- NEVER use threats, urgency, or intimidation\n"

        if ethical_constraints.get("include_opt_out", True):
            constraints_text += "- ALWAYS include clear opt-out/unsubscribe instructions\n"

        if ethical_constraints.get("no_personal_data", True):
            constraints_text += "- NEVER request or reference sensitive personal information\n"

        if ethical_constraints.get("educational_content", True):
            constraints_text += "- Frame as educational security awareness training\n"

        return f"""You are a red team simulation assistant generating phishing pretexts for AUTHORIZED security training.

ETHICAL CONSTRAINTS (MANDATORY):
{constraints_text}
- NO actual harm or exploitation
- NO psychological manipulation
- NO false emergencies or crises
- NO impersonation of authorities without clear context
- ALL content must be clearly marked as simulation/training

LEGAL REQUIREMENTS:
- Include legitimate unsubscribe mechanism
- Respect participant consent and privacy
- Generate content suitable for controlled testing environment

Generate realistic but ethical phishing simulation content."""

    def _build_user_prompt(
        self,
        campaign_type: str,
        target_profile: Dict[str, Any],
        campaign_objective: str,
        pretext_template: Optional[str],
        adaptation_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt with target context."""
        prompt = f"""
CAMPAIGN TYPE: {campaign_type}
OBJECTIVE: {campaign_objective}

TARGET PROFILE:
- Role: {target_profile.get('role', 'Unknown')}
- Organization: {target_profile.get('organization', 'Unknown')}
- Industry: {target_profile.get('industry', 'Unknown')}
- Recent Activity: {target_profile.get('recent_activity', 'None specified')}
- Communication Style: {target_profile.get('communication_style', 'Professional')}

"""

        if pretext_template:
            prompt += f"""
BASE TEMPLATE:
{pretext_template}

"""

        if adaptation_data:
            prompt += f"""
ADAPTATION DATA:
Previous performance suggests: {adaptation_data.get('insights', 'No specific insights')}
Adjust strategy to: {adaptation_data.get('strategy', 'Maintain effectiveness')}

"""

        prompt += """
Generate a complete phishing simulation email with:
1. Subject line (professional and realistic)
2. Email body (contextually appropriate)
3. Call-to-action (clear but not coercive)
4. Opt-out instructions (prominently placed)

Format as JSON:
{
  "subject": "Email subject here",
  "body": "Email body content here",
  "call_to_action": "What you want the recipient to do",
  "opt_out_instructions": "How to opt out",
  "simulation_markers": ["markers indicating this is training"]
}
"""

        return prompt

    async def _call_gpt4(self, system_prompt: str, user_prompt: str) -> Optional[Any]:
        """Call GPT-4 API with error handling and rate limiting."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            return response

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return None
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}")
            return None

    def _parse_pretext_response(self, response_text: str) -> Dict[str, Any]:
        """Parse GPT-4 response into structured pretext data."""
        try:
            # Try to parse as JSON first
            pretext_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: extract components with regex
            pretext_data = self._extract_pretext_components(response_text)

        # Ensure required fields exist
        pretext_data.setdefault("subject", "Security Training Notification")
        pretext_data.setdefault("body", "This is a security awareness training simulation.")
        pretext_data.setdefault("call_to_action", "Please review the attached training materials.")
        pretext_data.setdefault("opt_out_instructions", "To opt out, reply to this email with 'UNSUBSCRIBE'.")
        pretext_data.setdefault("simulation_markers", ["TRAINING SIMULATION", "DO NOT CLICK"])

        return pretext_data

    def _extract_pretext_components(self, text: str) -> Dict[str, Any]:
        """Extract pretext components using regex patterns."""
        components = {}

        # Extract subject
        subject_match = re.search(r'Subject:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if subject_match:
            components["subject"] = subject_match.group(1).strip()

        # Extract body (everything after subject)
        body_match = re.search(r'Body:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
        if body_match:
            components["body"] = body_match.group(1).strip()
        else:
            # Use entire text as body if no clear separation
            components["body"] = text.strip()

        # Extract call to action
        cta_match = re.search(r'Call-to-Action:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if cta_match:
            components["call_to_action"] = cta_match.group(1).strip()

        # Extract opt-out instructions
        opt_out_match = re.search(r'Opt-out:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if opt_out_match:
            components["opt_out_instructions"] = opt_out_match.group(1).strip()

        return components

    def _hash_target_profile(self, profile: Dict[str, Any]) -> str:
        """Create a hash of target profile for privacy-preserving logging."""
        import hashlib

        # Create a normalized string representation
        profile_str = json.dumps(profile, sort_keys=True, default=str)

        # Hash with salt for privacy
        salted = profile_str + config.fingerprint_hash_salt
        return hashlib.sha256(salted.encode()).hexdigest()

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about pretext generation."""
        total_generations = len(self.generation_history)
        successful_generations = sum(1 for g in self.generation_history
                                   if g.get("filter_result", {}).get("approved", False))

        return {
            "total_generations": total_generations,
            "successful_generations": successful_generations,
            "success_rate": successful_generations / max(total_generations, 1),
            "recent_generations": self.generation_history[-10:] if self.generation_history else []
        }


