# 🔌 CHIMERA API Reference

## RESTful API for Campaign Management and Analytics

**Base URL**: `http://localhost:8000` (default)
**Version**: v1.0.0
**Authentication**: JWT Bearer Token
**Format**: JSON

---

## 📋 API Overview

The CHIMERA API provides comprehensive programmatic access to all platform capabilities, enabling integration with existing red team tools, automation workflows, and custom dashboards.

### Key Features

- **RESTful Design**: Standard HTTP methods and status codes
- **Automatic Documentation**: OpenAPI/Swagger UI at `/docs`
- **Asynchronous Operations**: Background processing for long-running tasks
- **Rate Limiting**: Configurable request limits with burst handling
- **Audit Logging**: Complete API usage tracking

---

## 🔐 Authentication

### JWT Token Authentication

```bash
# Obtain token (implementation dependent)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "redteam", "password": "secure_password"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/campaigns
```

### API Key Authentication (Alternative)

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
     http://localhost:8000/campaigns
```

---

## 📊 Core API Endpoints

### System Health & Status

#### GET `/health`
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "chimera-orchestrator",
  "version": "1.0.0-BLACKBOX",
  "timestamp": "2025-12-19T10:30:00Z"
}
```

#### GET `/system/status`
Comprehensive system status and metrics.

**Response:**
```json
{
  "system": "chimera-orchestrator",
  "version": "1.0.0-BLACKBOX",
  "status": "operational",
  "timestamp": "2025-12-19T10:30:00Z",
  "consent_summary": {
    "total_consents": 150,
    "active_consents": 145,
    "revoked_consents": 3,
    "expired_consents": 2
  },
  "campaign_statistics": {
    "total_campaigns": 25,
    "active_campaigns": 3,
    "total_emails_sent": 1250,
    "total_emails_opened": 387,
    "total_links_clicked": 89
  },
  "kill_switch_status": {
    "total_kill_switches": 2,
    "recent_activations_24h": 0
  }
}
```

---

### Consent Management

#### POST `/consent/register`
Register new participant consent.

**Request:**
```json
{
  "participant_email": "researcher@company.com",
  "participant_role": "Security Analyst",
  "campaign_types_allowed": ["phishing", "vishing"],
  "expiration_days": 365,
  "legal_signoff_officer": "Dr. Jane Smith",
  "created_by": "admin"
}
```

**Response:**
```json
{
  "success": true,
  "participant_id": "550e8400-e29b-41d4-a716-446655440001",
  "consent_hash": "a1b2c3d4...",
  "expiration_date": "2026-12-19T00:00:00Z"
}
```

#### POST `/consent/validate`
Validate participant consent before operations.

**Request:**
```json
{
  "participant_id": "550e8400-e29b-41d4-a716-446655440001",
  "campaign_type": "phishing"
}
```

**Response:**
```json
{
  "valid": true,
  "participant_id": "550e8400-e29b-41d4-a716-446655440001",
  "organization_id": "550e8400-e29b-41d4-a716-446655440002",
  "expiration_date": "2026-12-19T00:00:00Z",
  "campaign_types_allowed": ["phishing", "vishing"],
  "gates": {
    "legal": true,
    "consent": true,
    "operational": true
  }
}
```

#### POST `/consent/revoke`
Revoke participant consent.

**Request:**
```json
{
  "reason": "Participant requested withdrawal",
  "revoked_by": "compliance_officer"
}
```

**Response:**
```json
{
  "success": true,
  "participant_id": "550e8400-e29b-41d4-a716-446655440001",
  "revoked_at": "2025-12-19T10:35:00Z",
  "reason": "Participant requested withdrawal"
}
```

#### GET `/consent/summary`
Get consent database statistics.

**Query Parameters:**
- `organization_id` (optional): Filter by organization

**Response:**
```json
{
  "total_consents": 150,
  "active_consents": 145,
  "revoked_consents": 3,
  "expired_consents": 2,
  "organization_filter": null
}
```

---

### Campaign Management

#### POST `/campaigns`
Create a new campaign.

**Request:**
```json
{
  "name": "Q4 Security Awareness Campaign",
  "description": "Annual phishing awareness training",
  "campaign_type": "phishing",
  "target_participants": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ],
  "ethical_constraints": {
    "no_threats": true,
    "include_opt_out": true,
    "no_personal_data": true,
    "educational_content": true
  },
  "created_by": "red_team_lead"
}
```

**Response:**
```json
{
  "campaign_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "created",
  "participant_count": 2,
  "requires_approval": true
}
```

#### GET `/campaigns`
List campaigns with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status (created, approved, active, completed, terminated)
- `limit` (optional): Maximum campaigns to return (default: 10)

**Response:**
```json
{
  "campaigns": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "name": "Q4 Security Awareness Campaign",
      "type": "phishing",
      "status": "approved",
      "created_at": "2025-12-19T10:30:00Z",
      "participant_count": 2
    }
  ],
  "total": 1
}
```

#### GET `/campaigns/{campaign_id}`
Get detailed campaign information.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "name": "Q4 Security Awareness Campaign",
  "description": "Annual phishing awareness training",
  "campaign_type": "phishing",
  "status": "active",
  "created_at": "2025-12-19T10:30:00Z",
  "approved_at": "2025-12-19T10:35:00Z",
  "launched_at": "2025-12-19T10:40:00Z",
  "target_participants": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ],
  "metrics": {
    "emails_sent": 2,
    "emails_opened": 1,
    "links_clicked": 0,
    "credentials_submitted": 0,
    "reports_to_security": 0
  },
  "ethical_constraints": {
    "no_threats": true,
    "include_opt_out": true,
    "no_personal_data": true,
    "educational_content": true
  }
}
```

#### POST `/campaigns/{campaign_id}/approve`
Approve a campaign for execution.

**Request:**
```json
{
  "approved_by": "red_team_lead"
}
```

**Response:**
```json
{
  "success": true,
  "campaign_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "approved_and_launching"
}
```

#### POST `/kill-switch`
Activate kill switch for campaign termination.

**Request:**
```json
{
  "campaign_id": "550e8400-e29b-41d4-a716-446655440003",
  "reason": "Geographic violation detected",
  "triggered_by": "system_automatic",
  "affected_participants": 1
}
```

**Response:**
```json
{
  "success": true,
  "campaign_id": "550e8400-e29b-41d4-a716-446655440003",
  "terminated_at": "2025-12-19T10:45:00Z",
  "affected_participants": 1
}
```

---

### Telemetry & Analytics

#### GET `/analytics/campaign/{campaign_id}`
Get campaign analytics and metrics.

**Query Parameters:**
- `hours` (optional): Analysis time window in hours (default: 24)

**Response:**
```json
{
  "campaign_id": "550e8400-e29b-41d4-a716-446655440003",
  "time_window_hours": 24,
  "total_events": 45,
  "unique_visitors": 12,
  "event_breakdown": {
    "email_opened": 15,
    "link_clicked": 3,
    "form_submitted": 1
  },
  "geographic_distribution": ["US", "CA", "GB"],
  "device_distribution": ["desktop", "mobile"],
  "engagement_metrics": {
    "estimated_open_rate": 0.625,
    "estimated_click_rate": 0.125,
    "conversion_funnel": [
      {
        "stage": "Emails Opened",
        "count": 15,
        "conversion_rate": 0.625
      },
      {
        "stage": "Links Clicked",
        "count": 3,
        "conversion_rate": 0.2
      }
    ]
  }
}
```

#### GET `/analytics/anomalies/{campaign_id}`
Get anomaly detection results.

**Response:**
```json
{
  "campaign_id": "550e8400-e29b-41d4-a716-446655440003",
  "anomalies": [
    {
      "type": "rapid_automated_interaction",
      "severity": "high",
      "description": "Suspicious rapid interactions detected",
      "fingerprint_hash": "hash123...",
      "recommendation": "Flag for manual review"
    }
  ],
  "total_anomalies": 1,
  "critical_count": 0,
  "high_count": 1,
  "medium_count": 0
}
```

---

### AI & Pretext Generation

#### POST `/pretext/generate`
Generate AI-powered pretext content.

**Request:**
```json
{
  "campaign_type": "phishing",
  "target_profile": {
    "role": "Senior Engineer",
    "organization": "TechCorp",
    "industry": "Technology"
  },
  "campaign_objective": "credential_harvest",
  "ethical_constraints": {
    "no_threats": true,
    "include_opt_out": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "pretext": {
    "subject": "Urgent: Code Review Required for Q4 Deployment",
    "body": "Dear Senior Engineer,\n\nWe need your immediate input on the Q4 deployment...",
    "call_to_action": "Please review and provide feedback by EOD",
    "opt_out_instructions": "To opt out of these notifications, reply with 'UNSUBSCRIBE'",
    "simulation_markers": ["TRAINING EXERCISE", "DO NOT CLICK LINKS"]
  },
  "metadata": {
    "generated_at": "2025-12-19T10:30:00Z",
    "model": "gpt-4-turbo-preview",
    "ethical_check_passed": true,
    "filter_warnings": []
  }
}
```

---

### Identity Graph Operations

#### POST `/identity/profile`
Create a new identity profile.

**Request:**
```json
{
  "name": "John Doe",
  "email": "john.doe@company.com",
  "role": "Senior Engineer",
  "department": "Engineering",
  "organization": "TechCorp",
  "seniority_level": "Senior",
  "communication_style": "Technical"
}
```

**Response:**
```json
{
  "success": true,
  "profile_id": "550e8400-e29b-41d4-a716-446655440004",
  "relationships_created": 0
}
```

#### GET `/identity/impersonation/{target_id}`
Find impersonation vectors for a target.

**Query Parameters:**
- `max_depth` (optional): Maximum relationship depth (default: 3)

**Response:**
```json
{
  "target_id": "550e8400-e29b-41d4-a716-446655440004",
  "impersonation_vectors": [
    {
      "impersonator_id": "550e8400-e29b-41d4-a716-446655440005",
      "impersonator_role": "Engineering Manager",
      "trust_distance": 1,
      "trust_score": 7,
      "confidence": 70,
      "relationship_path": ["REPORTS_TO"]
    }
  ],
  "total_vectors": 1
}
```

---

## 📊 Rate Limiting

### Default Limits

| Endpoint Category | Requests/Minute | Burst Limit |
|------------------|----------------|-------------|
| Health/Status | 60 | 10 |
| Consent Operations | 30 | 5 |
| Campaign Creation | 10 | 2 |
| Analytics Queries | 60 | 10 |
| AI Generation | 50 | 5 |

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

---

## 🚨 Error Responses

### Standard Error Format

```json
{
  "error": "Detailed error message",
  "error_code": "CAMPAIGN_NOT_FOUND",
  "details": {
    "campaign_id": "550e8400-e29b-41d4-a716-446655440003"
  },
  "timestamp": "2025-12-19T10:30:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CONSENT_REQUIRED` | 403 | Operation requires valid consent |
| `CAMPAIGN_NOT_FOUND` | 404 | Specified campaign does not exist |
| `ETHICS_VIOLATION` | 400 | Content violates ethical constraints |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `KILL_SWITCH_ACTIVE` | 403 | Campaign terminated by kill switch |

---

## 🔒 Security Considerations

### API Security Features

- **JWT Authentication**: Bearer token required for sensitive operations
- **Rate Limiting**: Configurable limits prevent abuse
- **Input Validation**: Pydantic models ensure data integrity
- **Audit Logging**: All API calls are logged with user context
- **CORS Protection**: Restricted cross-origin access

### Best Practices

```bash
# Use HTTPS in production
curl -k https://your-chimera-instance.com/api/v1/campaigns

# Implement retry logic with exponential backoff
# Handle rate limiting gracefully
# Validate SSL certificates
# Use API versioning in requests
```

---

## 📚 Additional Resources

- **OpenAPI Specification**: `/docs` (interactive Swagger UI)
- **Postman Collection**: Available in `/examples/api-testing/`
- **SDKs**: Python and JavaScript SDKs available
- **Webhook Documentation**: Real-time event notifications

---

## 🔄 API Versioning

### Current Version: v1.0.0

- **Base Path**: `/`
- **Version Header**: `Accept: application/vnd.chimera.v1+json`
- **Deprecation Policy**: 12 months notice for breaking changes

### Future Versions

- **v2.0.0** (Q1 2026): Enhanced AI capabilities, GraphQL support
- **v3.0.0** (Q2 2026): Multi-tenant architecture, advanced analytics

---

*"The CHIMERA API provides the programmatic interface to the world's most advanced ethical red team platform."*


