"""
Identity Mapper - Neo4j-based Relationship Graph Management

Creates and manages simulated identity graphs for red team operations:
- Target profile storage with relationship mapping
- Trust path analysis for impersonation vectors
- Privacy-preserving OSINT correlation
- Graph-based pretext personalization

Maintains ethical boundaries while enabling sophisticated social engineering simulation.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from uuid import UUID
import hashlib
from neo4j import GraphDatabase, exceptions
from neo4j.graph import Node, Relationship

from ..utils.config import config
from ..utils.logger import setup_logging, log_audit_event, log_privacy_event

logger = setup_logging(__name__)


class IdentityMapper:
    """
    Neo4j-powered identity relationship mapping.

    Creates privacy-preserving graphs of organizational relationships
    for personalized pretext generation without collecting real PII.
    """

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None,
                 password: Optional[str] = None, database: Optional[str] = None):
        self.uri = uri or config.neo4j_uri
        self.user = user or config.neo4j_user
        self.password = password or config.neo4j_password
        self.database = database or config.neo4j_database

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                database=self.database
            )
            logger.info("Connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    async def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def create_target_profile(self, profile_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a simulated target profile in the graph.

        Args:
            profile_data: Simulated profile data (no real PII)

        Returns:
            Profile ID if created successfully
        """
        try:
            with self.driver.session() as session:
                # Hash sensitive fields for privacy
                hashed_email = self._hash_pii_field(profile_data.get('email', ''))
                hashed_name = self._hash_pii_field(profile_data.get('name', ''))

                # Create profile node with privacy protections
                result = session.run("""
                    CREATE (p:Person {
                        id: $profile_id,
                        role: $role,
                        department: $department,
                        organization: $organization,
                        industry: $industry,
                        hashed_email: $hashed_email,
                        hashed_name: $hashed_name,
                        seniority_level: $seniority_level,
                        communication_style: $communication_style,
                        created_at: datetime(),
                        consent_verified: true
                    })
                    RETURN p.id as profile_id
                """,
                profile_id=str(UUID(profile_data.get('id', UUID()))),
                role=profile_data.get('role', 'Unknown'),
                department=profile_data.get('department', 'Unknown'),
                organization=profile_data.get('organization', 'Unknown'),
                industry=profile_data.get('industry', 'Unknown'),
                hashed_email=hashed_email,
                hashed_name=hashed_name,
                seniority_level=profile_data.get('seniority_level', 'Unknown'),
                communication_style=profile_data.get('communication_style', 'Professional')
                )

                record = result.single()
                if record:
                    profile_id = record["profile_id"]

                    log_audit_event(
                        "profile_created",
                        profile_id=profile_id,
                        role=profile_data.get('role'),
                        organization=profile_data.get('organization')
                    )

                    return profile_id

        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j error creating profile: {e}")
        except Exception as e:
            logger.error(f"Error creating profile: {e}")

        return None

    def create_relationship(self, source_id: str, target_id: str,
                          relationship_type: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a relationship between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            properties: Relationship properties

        Returns:
            True if relationship created successfully
        """
        try:
            with self.driver.session() as session:
                # Validate relationship types to prevent unauthorized connections
                allowed_types = {
                    'REPORTS_TO', 'MANAGES', 'COLLEAGUE', 'VENDOR_RELATIONSHIP',
                    'CLIENT_RELATIONSHIP', 'TRUSTED_BY', 'COMMUNICATES_WITH',
                    'SHARES_PROJECT', 'MENTORS', 'COLLABORATES_WITH'
                }

                if relationship_type.upper() not in allowed_types:
                    logger.warning(f"Rejected unauthorized relationship type: {relationship_type}")
                    return False

                properties = properties or {}
                properties['created_at'] = 'datetime()'
                properties['trust_level'] = properties.get('trust_level', 'medium')
                properties['interaction_frequency'] = properties.get('interaction_frequency', 'occasional')

                result = session.run(f"""
                    MATCH (a), (b)
                    WHERE a.id = $source_id AND b.id = $target_id
                    CREATE (a)-[r:{relationship_type.upper()} {{
                        trust_level: $trust_level,
                        interaction_frequency: $interaction_frequency,
                        created_at: datetime()
                    }}]->(b)
                    RETURN count(r) as created
                """,
                source_id=source_id,
                target_id=target_id,
                trust_level=properties.get('trust_level', 'medium'),
                interaction_frequency=properties.get('interaction_frequency', 'occasional')
                )

                record = result.single()
                if record and record["created"] > 0:
                    log_audit_event(
                        "relationship_created",
                        relationship_type=relationship_type,
                        source_id=source_id,
                        target_id=target_id
                    )
                    return True

        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j error creating relationship: {e}")
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")

        return False

    def find_impersonation_vectors(self, target_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Find potential impersonation vectors for a target.

        Args:
            target_id: Target profile ID
            max_depth: Maximum relationship depth to search

        Returns:
            List of potential impersonators with trust paths
        """
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = (impersonator:Person)-[rels*1..$max_depth]->(target:Person {id: $target_id})
                    WHERE impersonator <> target
                    WITH impersonator, target, path, length(path) as path_length,
                         reduce(trust_score = 0, r in rels |
                           trust_score + CASE r.trust_level
                             WHEN 'high' THEN 3
                             WHEN 'medium' THEN 2
                             WHEN 'low' THEN 1
                             ELSE 0 END
                         ) as total_trust_score
                    RETURN impersonator.id as impersonator_id,
                           impersonator.role as impersonator_role,
                           path_length,
                           total_trust_score,
                           [r in rels | type(r)] as relationship_types
                    ORDER BY total_trust_score DESC, path_length ASC
                    LIMIT 10
                """, target_id=target_id, max_depth=max_depth)

                vectors = []
                for record in result:
                    vectors.append({
                        'impersonator_id': record['impersonator_id'],
                        'impersonator_role': record['impersonator_role'],
                        'trust_distance': record['path_length'],
                        'trust_score': record['total_trust_score'],
                        'relationship_path': record['relationship_types'],
                        'confidence': min(100, record['total_trust_score'] * 20)  # Normalize to percentage
                    })

                log_privacy_event(
                    "impersonation_analysis",
                    operation="vector_discovery",
                    target_id=target_id,
                    vectors_found=len(vectors)
                )

                return vectors

        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j error finding impersonation vectors: {e}")
        except Exception as e:
            logger.error(f"Error finding impersonation vectors: {e}")

        return []

    def get_target_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Get target profile with relationship context.

        Args:
            profile_id: Profile ID to retrieve

        Returns:
            Profile data with relationship insights
        """
        try:
            with self.driver.session() as session:
                # Get basic profile
                profile_result = session.run("""
                    MATCH (p:Person {id: $profile_id})
                    RETURN p
                """, profile_id=profile_id)

                profile_record = profile_result.single()
                if not profile_record:
                    return None

                profile_node = profile_record["p"]

                # Get relationship summary
                relationship_result = session.run("""
                    MATCH (p:Person {id: $profile_id})-[r]-(other:Person)
                    RETURN type(r) as relationship_type,
                           count(other) as count,
                           collect(DISTINCT other.role) as roles
                    ORDER BY count DESC
                """, profile_id=profile_id)

                relationships = []
                for record in relationship_result:
                    relationships.append({
                        'type': record['relationship_type'],
                        'count': record['count'],
                        'connected_roles': record['roles']
                    })

                profile_data = {
                    'id': profile_node['id'],
                    'role': profile_node.get('role'),
                    'department': profile_node.get('department'),
                    'organization': profile_node.get('organization'),
                    'industry': profile_node.get('industry'),
                    'seniority_level': profile_node.get('seniority_level'),
                    'communication_style': profile_node.get('communication_style'),
                    'relationship_summary': relationships,
                    'total_connections': sum(r['count'] for r in relationships)
                }

                return profile_data

        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j error getting profile: {e}")
        except Exception as e:
            logger.error(f"Error getting profile: {e}")

        return None

    def analyze_organizational_structure(self, organization_name: str) -> Dict[str, Any]:
        """
        Analyze organizational structure and hierarchy.

        Args:
            organization_name: Organization to analyze

        Returns:
            Organizational structure analysis
        """
        try:
            with self.driver.session() as session:
                # Find organizational hierarchy
                hierarchy_result = session.run("""
                    MATCH (p:Person {organization: $org})
                    OPTIONAL MATCH (p)-[:REPORTS_TO]->(manager:Person)
                    WITH p, manager
                    ORDER BY p.seniority_level DESC
                    RETURN collect(DISTINCT p.role) as roles,
                           collect(DISTINCT manager.role) as manager_roles,
                           count(DISTINCT p) as total_employees
                """, org=organization_name)

                record = hierarchy_result.single()

                # Analyze communication patterns
                communication_result = session.run("""
                    MATCH (p1:Person {organization: $org})-[r:COMMUNICATES_WITH]-(p2:Person {organization: $org})
                    RETURN count(r) as total_communications,
                           avg(CASE r.interaction_frequency
                               WHEN 'daily' THEN 5
                               WHEN 'weekly' THEN 4
                               WHEN 'monthly' THEN 3
                               WHEN 'occasional' THEN 2
                               ELSE 1 END) as avg_frequency
                """, org=organization_name)

                comm_record = communication_result.single()

                analysis = {
                    'organization': organization_name,
                    'total_profiles': record['total_employees'] if record else 0,
                    'roles': record['roles'] if record else [],
                    'manager_roles': record['manager_roles'] if record else [],
                    'communication_density': comm_record['total_communications'] if comm_record else 0,
                    'avg_interaction_frequency': comm_record['avg_frequency'] if comm_record else 0,
                    'hierarchy_depth': self._calculate_hierarchy_depth(organization_name)
                }

                return analysis

        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j error analyzing organization: {e}")
        except Exception as e:
            logger.error(f"Error analyzing organization: {e}")

        return {}

    def _calculate_hierarchy_depth(self, organization_name: str) -> int:
        """Calculate the depth of organizational hierarchy."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = (p:Person {organization: $org})-[:REPORTS_TO*]->(root:Person)
                    WHERE NOT (root)-[:REPORTS_TO]->()
                    RETURN max(length(path)) as max_depth
                """, org=organization_name)

                record = result.single()
                return record['max_depth'] if record and record['max_depth'] else 1

        except exceptions.Neo4jError:
            return 1

    def _hash_pii_field(self, field_value: str) -> str:
        """Hash PII fields for privacy preservation."""
        if not field_value or field_value == 'Unknown':
            return 'unknown'

        # Create salted hash for privacy
        salted_value = f"{field_value.lower().strip()}:{config.fingerprint_hash_salt}"
        return hashlib.sha256(salted_value.encode()).hexdigest()

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph database statistics."""
        try:
            with self.driver.session() as session:
                # Node counts
                node_result = session.run("""
                    CALL db.labels() YIELD label
                    CALL db.relationshipTypes() YIELD relationshipType
                    RETURN count(*) as node_count,
                           size(collect(DISTINCT label)) as label_count,
                           size(collect(DISTINCT relationshipType)) as relationship_count
                """)

                record = node_result.single()

                # Person-specific stats
                person_result = session.run("""
                    MATCH (p:Person)
                    RETURN count(p) as person_count,
                           collect(DISTINCT p.organization) as organizations,
                           collect(DISTINCT p.role) as roles
                """)

                person_record = person_result.single()

                return {
                    'total_nodes': record['node_count'] if record else 0,
                    'node_labels': record['label_count'] if record else 0,
                    'relationship_types': record['relationship_count'] if record else 0,
                    'person_profiles': person_record['person_count'] if person_record else 0,
                    'organizations': person_record['organizations'] if person_record else [],
                    'roles': person_record['roles'] if person_record else []
                }

        except exceptions.Neo4jError as e:
            logger.error(f"Neo4j error getting statistics: {e}")
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")

        return {}


