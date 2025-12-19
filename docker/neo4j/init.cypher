// CHIMERA Identity Graph Schema Initialization
// Neo4j constraints and indexes for identity mapping

// Create constraints for data integrity
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.hashed_email IS UNIQUE;

// Create indexes for performance
CREATE INDEX person_organization_idx IF NOT EXISTS
FOR (p:Person) ON (p.organization);

CREATE INDEX person_role_idx IF NOT EXISTS
FOR (p:Person) ON (p.role);

CREATE INDEX person_department_idx IF NOT EXISTS
FOR (p:Person) ON (p.department);

// Create relationship type constraints (Neo4j 5.0+)
CREATE CONSTRAINT reports_to_relationship IF NOT EXISTS
FOR ()-[r:REPORTS_TO]-() REQUIRE r.created_at IS NOT NULL;

CREATE CONSTRAINT communicates_with_relationship IF NOT EXISTS
FOR ()-[r:COMMUNICATES_WITH]-() REQUIRE r.created_at IS NOT NULL;

// Create sample data for testing (development only)
// NOTE: In production, this would be populated through the API with proper consent

// Sample organization structure for demonstration
CREATE (org1:Organization {
    name: "TechCorp Inc",
    industry: "Technology",
    size: "500-1000",
    created_at: datetime()
});

// Sample executive profiles
CREATE (exec1:Person {
    id: "exec-001",
    role: "CEO",
    department: "Executive",
    organization: "TechCorp Inc",
    industry: "Technology",
    hashed_email: "ceohash",
    hashed_name: "ceoname",
    seniority_level: "Executive",
    communication_style: "Strategic",
    created_at: datetime(),
    consent_verified: true
});

CREATE (exec2:Person {
    id: "exec-002",
    role: "CTO",
    department: "Engineering",
    organization: "TechCorp Inc",
    industry: "Technology",
    hashed_email: "ctohash",
    hashed_name: "ctoname",
    seniority_level: "Executive",
    communication_style: "Technical",
    created_at: datetime(),
    consent_verified: true
});

// Sample manager profiles
CREATE (mgr1:Person {
    id: "mgr-001",
    role: "Engineering Manager",
    department: "Engineering",
    organization: "TechCorp Inc",
    industry: "Technology",
    hashed_email: "engmgrhash",
    hashed_name: "engmgrname",
    seniority_level: "Manager",
    communication_style: "Collaborative",
    created_at: datetime(),
    consent_verified: true
});

CREATE (mgr2:Person {
    id: "mgr-002",
    role: "Product Manager",
    department: "Product",
    organization: "TechCorp Inc",
    industry: "Technology",
    hashed_email: "prodmgrmgrhash",
    hashed_name: "prodmgrname",
    seniority_level: "Manager",
    communication_style: "Customer-focused",
    created_at: datetime(),
    consent_verified: true
});

// Sample individual contributor profiles
CREATE (ic1:Person {
    id: "ic-001",
    role: "Senior Software Engineer",
    department: "Engineering",
    organization: "TechCorp Inc",
    industry: "Technology",
    hashed_email: "srengmgrhash",
    hashed_name: "srengname",
    seniority_level: "Senior",
    communication_style: "Technical",
    created_at: datetime(),
    consent_verified: true
});

CREATE (ic2:Person {
    id: "ic-002",
    role: "Software Engineer",
    department: "Engineering",
    organization: "TechCorp Inc",
    industry: "Technology",
    hashed_email: "engmgrhash",
    hashed_name: "engname",
    seniority_level: "Individual Contributor",
    communication_style: "Collaborative",
    created_at: datetime(),
    consent_verified: true
});

// Create organizational relationships
CREATE (mgr1)-[:REPORTS_TO {
    trust_level: "high",
    interaction_frequency: "weekly",
    created_at: datetime()
}]->(exec2);

CREATE (mgr2)-[:REPORTS_TO {
    trust_level: "high",
    interaction_frequency: "weekly",
    created_at: datetime()
}]->(exec1);

CREATE (ic1)-[:REPORTS_TO {
    trust_level: "high",
    interaction_frequency: "weekly",
    created_at: datetime()
}]->(mgr1);

CREATE (ic2)-[:REPORTS_TO {
    trust_level: "medium",
    interaction_frequency: "monthly",
    created_at: datetime()
}]->(mgr1);

// Create communication relationships
CREATE (exec1)-[:COMMUNICATES_WITH {
    trust_level: "high",
    interaction_frequency: "weekly",
    created_at: datetime()
}]->(exec2);

CREATE (mgr1)-[:COMMUNICATES_WITH {
    trust_level: "high",
    interaction_frequency: "daily",
    created_at: datetime()
}]->(mgr2);

CREATE (ic1)-[:COMMUNICATES_WITH {
    trust_level: "medium",
    interaction_frequency: "weekly",
    created_at: datetime()
}]->(ic2);

// Create sample vendor relationships
CREATE (vendor1:Person {
    id: "vendor-001",
    role: "Account Manager",
    organization: "CloudTech Solutions",
    industry: "Technology Consulting",
    hashed_email: "vendorhash",
    hashed_name: "vendorname",
    seniority_level: "Manager",
    communication_style: "Professional",
    is_vendor: true,
    created_at: datetime(),
    consent_verified: true
});

CREATE (vendor1)-[:VENDOR_RELATIONSHIP {
    trust_level: "medium",
    interaction_frequency: "monthly",
    created_at: datetime()
}]->(exec2);

// Create trust relationships for impersonation analysis
CREATE (mgr1)-[:TRUSTED_BY {
    trust_level: "high",
    interaction_frequency: "daily",
    created_at: datetime()
}]->(ic1);

CREATE (exec1)-[:TRUSTED_BY {
    trust_level: "high",
    interaction_frequency: "weekly",
    created_at: datetime()
}]->(mgr2);

// Add sample project collaboration relationships
CREATE (ic1)-[:COLLABORATES_WITH {
    trust_level: "high",
    interaction_frequency: "daily",
    project_context: "authentication_system",
    created_at: datetime()
}]->(ic2);

// Create indexes for common queries
CREATE INDEX person_reports_to_idx IF NOT EXISTS
FOR ()-[r:REPORTS_TO]-() ON (r.trust_level);

CREATE INDEX person_communicates_idx IF NOT EXISTS
FOR ()-[r:COMMUNICATES_WITH]-() ON (r.interaction_frequency);

CREATE INDEX person_vendor_idx IF NOT EXISTS
FOR ()-[r:VENDOR_RELATIONSHIP]-() ON (r.created_at);


