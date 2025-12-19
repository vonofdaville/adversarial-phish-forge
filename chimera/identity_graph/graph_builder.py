"""
Graph Builder - Automated Identity Graph Construction

Builds simulated organizational graphs for red team training:
- Automated relationship inference from profiles
- Organizational hierarchy construction
- Communication pattern simulation
- Trust relationship modeling

Maintains privacy while enabling realistic social engineering scenarios.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID, uuid4
import random
from dataclasses import dataclass

from .identity_mapper import IdentityMapper
from ..utils.logger import setup_logging, log_audit_event

logger = setup_logging(__name__)


@dataclass
class OrganizationalTemplate:
    """Template for organizational structure generation."""
    name: str
    hierarchy_levels: List[str]
    typical_roles: Dict[str, List[str]]
    communication_patterns: Dict[str, float]  # role -> communication frequency
    vendor_relationships: List[str]


class GraphBuilder:
    """
    Automated construction of identity relationship graphs.

    Builds realistic organizational structures for training scenarios
    while maintaining strict privacy boundaries.
    """

    def __init__(self, identity_mapper: Optional[IdentityMapper] = None):
        self.mapper = identity_mapper or IdentityMapper()

        # Predefined organizational templates
        self.templates = self._load_organizational_templates()

    def _load_organizational_templates(self) -> Dict[str, OrganizationalTemplate]:
        """Load predefined organizational templates."""
        return {
            'tech_startup': OrganizationalTemplate(
                name='Technology Startup',
                hierarchy_levels=['Executive', 'Manager', 'Senior', 'Individual Contributor'],
                typical_roles={
                    'Executive': ['CEO', 'CTO', 'CFO'],
                    'Manager': ['Engineering Manager', 'Product Manager', 'Sales Manager'],
                    'Senior': ['Senior Engineer', 'Senior Designer', 'Senior Analyst'],
                    'Individual Contributor': ['Software Engineer', 'Designer', 'Business Analyst']
                },
                communication_patterns={
                    'CEO': 0.9, 'CTO': 0.8, 'CFO': 0.7,
                    'Engineering Manager': 0.8, 'Product Manager': 0.8,
                    'Senior Engineer': 0.6, 'Senior Designer': 0.6,
                    'Software Engineer': 0.4, 'Designer': 0.4
                },
                vendor_relationships=['Cloud Provider', 'Design Agency', 'Marketing Firm']
            ),
            'enterprise_finance': OrganizationalTemplate(
                name='Enterprise Finance',
                hierarchy_levels=['Executive', 'VP', 'Director', 'Manager', 'Senior', 'Analyst'],
                typical_roles={
                    'Executive': ['CEO', 'CFO', 'COO'],
                    'VP': ['VP Finance', 'VP Operations', 'VP Technology'],
                    'Director': ['Director Finance', 'Director IT', 'Director Compliance'],
                    'Manager': ['Finance Manager', 'IT Manager', 'Compliance Manager'],
                    'Senior': ['Senior Financial Analyst', 'Senior Developer'],
                    'Analyst': ['Financial Analyst', 'Business Analyst', 'Security Analyst']
                },
                communication_patterns={
                    'CEO': 0.95, 'CFO': 0.9, 'COO': 0.85,
                    'VP Finance': 0.85, 'VP Technology': 0.8,
                    'Director Finance': 0.8, 'Director IT': 0.75,
                    'Finance Manager': 0.7, 'IT Manager': 0.7,
                    'Senior Financial Analyst': 0.6,
                    'Financial Analyst': 0.4, 'Security Analyst': 0.5
                },
                vendor_relationships=['Audit Firm', 'Banking Partners', 'IT Consulting', 'Compliance Services']
            ),
            'healthcare_provider': OrganizationalTemplate(
                name='Healthcare Provider',
                hierarchy_levels=['Executive', 'Department Head', 'Manager', 'Senior', 'Staff'],
                typical_roles={
                    'Executive': ['CEO', 'CMO', 'CFO', 'CIO'],
                    'Department Head': ['Chief of Surgery', 'Chief of Medicine', 'Nursing Director'],
                    'Manager': ['Department Manager', 'Clinical Manager', 'IT Manager'],
                    'Senior': ['Senior Nurse', 'Senior Physician Assistant'],
                    'Staff': ['Registered Nurse', 'Physician Assistant', 'Medical Assistant']
                },
                communication_patterns={
                    'CEO': 0.9, 'CMO': 0.85, 'CFO': 0.8, 'CIO': 0.75,
                    'Chief of Surgery': 0.8, 'Chief of Medicine': 0.8,
                    'Nursing Director': 0.75, 'Department Manager': 0.7,
                    'Clinical Manager': 0.65, 'Senior Nurse': 0.6,
                    'Registered Nurse': 0.4, 'Medical Assistant': 0.35
                },
                vendor_relationships=['Medical Equipment', 'Pharmacy Services', 'IT Security', 'Insurance Partners']
            )
        }

    def build_organizational_graph(self, organization_name: str, template_name: str,
                                 employee_count: int = 50) -> Dict[str, Any]:
        """
        Build a complete organizational graph from template.

        Args:
            organization_name: Name of the organization
            template_name: Template to use for structure
            employee_count: Number of employees to generate

        Returns:
            Graph construction results
        """
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = self.templates[template_name]
        logger.info(f"Building organizational graph for {organization_name} using {template_name} template")

        # Generate employee profiles
        profiles = self._generate_employee_profiles(
            organization_name, template, employee_count
        )

        # Create profiles in graph
        created_profiles = []
        for profile in profiles:
            profile_id = self.mapper.create_target_profile(profile)
            if profile_id:
                created_profiles.append(profile_id)
                profile['id'] = profile_id

        # Build hierarchical relationships
        hierarchy_result = self._build_hierarchy(profiles, template)

        # Add communication relationships
        communication_result = self._build_communication_network(profiles, template)

        # Add vendor relationships
        vendor_result = self._build_vendor_relationships(organization_name, profiles, template)

        results = {
            'organization': organization_name,
            'template': template_name,
            'profiles_created': len(created_profiles),
            'hierarchy_relationships': hierarchy_result['relationships_created'],
            'communication_relationships': communication_result['relationships_created'],
            'vendor_relationships': vendor_result['relationships_created'],
            'executive_profiles': [p['id'] for p in profiles if p.get('seniority_level') == 'Executive']
        }

        log_audit_event(
            "organizational_graph_built",
            organization=organization_name,
            template=template_name,
            profiles_created=len(created_profiles)
        )

        return results

    def _generate_employee_profiles(self, organization_name: str,
                                  template: OrganizationalTemplate,
                                  count: int) -> List[Dict[str, Any]]:
        """Generate realistic employee profiles based on template."""
        profiles = []

        # Distribute employees across hierarchy levels
        level_distribution = {
            'Executive': max(1, int(count * 0.05)),      # 5% executives
            'VP': max(0, int(count * 0.08)),             # 8% VPs (if applicable)
            'Director': max(0, int(count * 0.12)),       # 12% directors
            'Manager': max(0, int(count * 0.20)),        # 20% managers
            'Senior': max(0, int(count * 0.25)),         # 25% senior staff
            'Individual Contributor': max(0, int(count * 0.30))  # 30% ICs
        }

        # Adjust for template's actual levels
        valid_levels = [level for level in level_distribution.keys()
                       if level in template.hierarchy_levels]

        generated_count = 0
        for level in valid_levels:
            level_count = level_distribution[level]
            if generated_count + level_count > count:
                level_count = count - generated_count

            for i in range(level_count):
                role = random.choice(template.typical_roles[level])

                # Generate realistic profile data
                profile = {
                    'id': str(uuid4()),
                    'name': f"Employee {generated_count + i + 1}",  # Placeholder - would be anonymized
                    'email': f"employee.{generated_count + i + 1}@{organization_name.lower().replace(' ', '')}.com",
                    'role': role,
                    'department': self._infer_department_from_role(role),
                    'organization': organization_name,
                    'industry': self._infer_industry_from_template(template.name),
                    'seniority_level': level,
                    'communication_style': random.choice(['Formal', 'Collaborative', 'Direct', 'Diplomatic']),
                    'years_experience': random.randint(1, 25),
                    'consent_verified': True
                }

                profiles.append(profile)
                generated_count += 1

                if generated_count >= count:
                    break

            if generated_count >= count:
                break

        return profiles

    def _build_hierarchy(self, profiles: List[Dict[str, Any]],
                        template: OrganizationalTemplate) -> Dict[str, Any]:
        """Build organizational hierarchy relationships."""
        relationships_created = 0

        # Group profiles by seniority level
        level_groups = {}
        for profile in profiles:
            level = profile['seniority_level']
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(profile)

        # Create reporting relationships
        hierarchy_order = template.hierarchy_levels

        for i, level in enumerate(hierarchy_order[:-1]):  # Skip last level (no one reports to them)
            current_level_profiles = level_groups.get(level, [])
            next_level = hierarchy_order[i + 1]
            next_level_profiles = level_groups.get(next_level, [])

            if not next_level_profiles:
                continue

            # Distribute subordinates among managers
            subordinates_per_manager = max(1, len(current_level_profiles) // len(next_level_profiles))

            for j, manager in enumerate(next_level_profiles):
                start_idx = j * subordinates_per_manager
                end_idx = min(start_idx + subordinates_per_manager, len(current_level_profiles))

                for subordinate in current_level_profiles[start_idx:end_idx]:
                    success = self.mapper.create_relationship(
                        subordinate['id'],
                        manager['id'],
                        'REPORTS_TO',
                        {
                            'trust_level': 'high',
                            'interaction_frequency': 'weekly',
                            'organizational_relationship': True
                        }
                    )
                    if success:
                        relationships_created += 1

        return {'relationships_created': relationships_created}

    def _build_communication_network(self, profiles: List[Dict[str, Any]],
                                   template: OrganizationalTemplate) -> Dict[str, Any]:
        """Build communication relationships based on organizational structure."""
        relationships_created = 0

        # Create communication links based on template patterns
        for i, profile1 in enumerate(profiles):
            for j, profile2 in enumerate(profiles[i+1:], i+1):
                # Skip self-relationships
                if profile1['id'] == profile2['id']:
                    continue

                # Calculate communication probability
                comm_freq_1 = template.communication_patterns.get(profile1['role'], 0.5)
                comm_freq_2 = template.communication_patterns.get(profile2['role'], 0.5)
                base_probability = (comm_freq_1 + comm_freq_2) / 2

                # Adjust based on hierarchy proximity
                if abs(template.hierarchy_levels.index(profile1['seniority_level']) -
                       template.hierarchy_levels.index(profile2['seniority_level'])) <= 1:
                    base_probability *= 1.5  # Closer hierarchy = more communication

                # Same department bonus
                if profile1.get('department') == profile2.get('department'):
                    base_probability *= 1.8

                # Create relationship if probability threshold met
                if random.random() < base_probability:
                    frequency = self._calculate_interaction_frequency(base_probability)

                    success = self.mapper.create_relationship(
                        profile1['id'],
                        profile2['id'],
                        'COMMUNICATES_WITH',
                        {
                            'interaction_frequency': frequency,
                            'trust_level': 'medium',
                            'context': 'professional'
                        }
                    )
                    if success:
                        relationships_created += 1

        return {'relationships_created': relationships_created}

    def _build_vendor_relationships(self, organization_name: str,
                                  profiles: List[Dict[str, Any]],
                                  template: OrganizationalTemplate) -> Dict[str, Any]:
        """Build vendor and external relationship network."""
        relationships_created = 0

        # Create vendor organization nodes (simulated)
        vendor_profiles = []
        for vendor_name in template.vendor_relationships:
            vendor_profile = {
                'id': str(uuid4()),
                'name': f"{vendor_name} Contact",
                'email': f"contact@{vendor_name.lower().replace(' ', '')}.com",
                'role': 'Account Manager',
                'organization': vendor_name,
                'industry': 'Consulting',
                'seniority_level': 'Manager',
                'communication_style': 'Professional',
                'is_vendor': True
            }

            vendor_id = self.mapper.create_target_profile(vendor_profile)
            if vendor_id:
                vendor_profiles.append({**vendor_profile, 'id': vendor_id})

        # Connect vendor contacts to relevant internal profiles
        for vendor in vendor_profiles:
            # Find appropriate internal contacts
            relevant_profiles = [
                p for p in profiles
                if self._is_relevant_for_vendor(p['role'], vendor['organization'])
            ]

            if not relevant_profiles:
                # Default to executives if no specific matches
                relevant_profiles = [p for p in profiles if p['seniority_level'] == 'Executive']

            # Connect to 2-3 relevant internal profiles
            for internal_profile in relevant_profiles[:3]:
                success = self.mapper.create_relationship(
                    vendor['id'],
                    internal_profile['id'],
                    'VENDOR_RELATIONSHIP',
                    {
                        'trust_level': 'medium',
                        'interaction_frequency': 'monthly',
                        'business_relationship': True
                    }
                )
                if success:
                    relationships_created += 1

        return {'relationships_created': relationships_created}

    def _infer_department_from_role(self, role: str) -> str:
        """Infer department from role title."""
        role_lower = role.lower()

        if any(word in role_lower for word in ['engineer', 'developer', 'architect', 'tech']):
            return 'Engineering'
        elif any(word in role_lower for word in ['design', 'ux', 'ui']):
            return 'Design'
        elif any(word in role_lower for word in ['finance', 'financial', 'account']):
            return 'Finance'
        elif any(word in role_lower for word in ['sales', 'marketing', 'business']):
            return 'Sales & Marketing'
        elif any(word in role_lower for word in ['hr', 'human', 'people']):
            return 'Human Resources'
        elif any(word in role_lower for word in ['security', 'compliance', 'risk']):
            return 'Security & Compliance'
        elif any(word in role_lower for word in ['nurse', 'medical', 'clinical']):
            return 'Clinical'
        elif any(word in role_lower for word in ['it', 'infrastructure', 'systems']):
            return 'IT'
        else:
            return 'General'

    def _infer_industry_from_template(self, template_name: str) -> str:
        """Infer industry from template name."""
        if 'tech' in template_name.lower():
            return 'Technology'
        elif 'finance' in template_name.lower():
            return 'Financial Services'
        elif 'healthcare' in template_name.lower():
            return 'Healthcare'
        else:
            return 'General Business'

    def _calculate_interaction_frequency(self, probability: float) -> str:
        """Calculate interaction frequency based on probability."""
        if probability > 0.8:
            return 'daily'
        elif probability > 0.6:
            return 'weekly'
        elif probability > 0.4:
            return 'monthly'
        else:
            return 'occasional'

    def _is_relevant_for_vendor(self, role: str, vendor_type: str) -> bool:
        """Determine if a role is relevant for a vendor relationship."""
        role_lower = role.lower()
        vendor_lower = vendor_type.lower()

        if 'it' in vendor_lower or 'tech' in vendor_lower:
            return any(word in role_lower for word in ['it', 'engineer', 'developer', 'architect'])
        elif 'design' in vendor_lower:
            return 'design' in role_lower
        elif 'marketing' in vendor_lower:
            return any(word in role_lower for word in ['marketing', 'sales', 'business'])
        elif 'consulting' in vendor_lower:
            return any(word in role_lower for word in ['manager', 'director', 'executive'])
        elif 'audit' in vendor_lower or 'compliance' in vendor_lower:
            return any(word in role_lower for word in ['finance', 'compliance', 'risk'])
        else:
            return False

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available organizational templates."""
        return [
            {
                'name': name,
                'display_name': template.name,
                'hierarchy_levels': len(template.hierarchy_levels),
                'typical_roles_count': sum(len(roles) for roles in template.typical_roles.values()),
                'vendor_relationships': len(template.vendor_relationships)
            }
            for name, template in self.templates.items()
        ]


