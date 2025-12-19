# 🎯 Campaign Management Guide

## Creating and Managing Red Team Campaigns

**Audience**: Red team operators, security trainers
**Difficulty**: Intermediate
**Time Required**: 30-60 minutes

---

## 📋 Campaign Lifecycle Overview

CHIMERA campaigns follow a structured lifecycle designed to maximize effectiveness while maintaining ethical boundaries.

### Campaign Phases

```
1. PLANNING → 2. APPROVAL → 3. EXECUTION → 4. MONITORING → 5. ANALYSIS → 6. DEBRIEF
     ↓             ↓             ↓             ↓             ↓             ↓
  Define      Three Gates    Launch       Real-time     Metrics      Lessons
  objectives   review        campaign     analytics     & insights   learned
```

---

## 1. 📝 Planning Your Campaign

### Define Campaign Objectives

**Choose from predefined campaign types:**

| Type | Description | Typical Duration | Success Metrics |
|------|-------------|------------------|-----------------|
| **Phishing** | Email-based social engineering | 24-72 hours | Open rate, click rate |
| **Vishing** | Voice-based social engineering | 1-2 weeks | Engagement rate, data disclosure |
| **Smishing** | SMS-based social engineering | 12-48 hours | Response rate |
| **Pretexting** | Impersonation scenarios | 3-7 days | Information gathering |

### Target Selection Strategy

#### Consent-Based Targeting
```csv
# participants.csv
participant_id,email,role,department
550e8400-e29b-41d4-a716-446655440001,user1@company.com,Engineer,Development
550e8400-e29b-41d4-a716-446655440002,user2@company.com,Manager,Sales
```

#### Profile-Based Selection
- **High-Value Targets**: Executives, IT staff, finance personnel
- **Representative Sample**: Mix of roles, departments, experience levels
- **Vulnerability Assessment**: Consider organizational culture and training history

### Ethical Constraints Configuration

```json
{
  "ethical_constraints": {
    "no_threats": true,              // Never use threatening language
    "include_opt_out": true,         // Always provide unsubscribe option
    "no_personal_data": true,        // Never request sensitive information
    "educational_content": true,     // Frame as learning opportunity
    "authority_impersonation": false, // Avoid executive impersonation
    "time_pressure": false           // No artificial deadlines
  }
}
```

---

## 2. 🎯 Creating a Campaign

### Using the CLI (Recommended)

```bash
# Create a phishing awareness campaign
chimera-cli campaign create \
    --name "Q4 Phishing Awareness 2025" \
    --description "Annual phishing simulation for employee training" \
    --type phishing \
    --targets participants.csv \
    --approval-required

# Expected output:
# Campaign created successfully
# Campaign ID: 550e8400-e29b-41d4-a716-446655440003
# Status: created
# Participants: 150
# Requires approval: true
```

### Using the API

```bash
# Create campaign via REST API
curl -X POST http://localhost:8000/campaigns \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q4 Phishing Awareness 2025",
    "description": "Annual phishing simulation",
    "campaign_type": "phishing",
    "target_participants": [
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002"
    ],
    "ethical_constraints": {
      "no_threats": true,
      "include_opt_out": true,
      "educational_content": true
    },
    "created_by": "red_team_lead"
  }'
```

### Campaign Configuration Options

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `name` | Campaign identifier | Required | Any string |
| `description` | Detailed purpose | Optional | Any string |
| `campaign_type` | Attack vector | Required | phishing, vishing, smishing |
| `target_participants` | Participant UUIDs | Required | Array of UUIDs |
| `ethical_constraints` | Safety rules | Default set | Boolean flags |
| `pretext_template` | Custom template | Optional | Template string |

---

## 3. ✅ Approval Process

### Three Gates Review

All campaigns require approval through CHIMERA's ethical framework:

#### Gate 1: Legal Review
```bash
# Legal counsel verifies:
# - Written authorization exists
# - Insurance coverage confirmed
# - Geographic restrictions appropriate
# - Compliance with applicable laws
```

#### Gate 2: Consent Validation
```bash
# System automatically verifies:
# - All participants have valid consent
# - Consent covers campaign type
# - Consent hasn't expired
# - No revocation requests
```

#### Gate 3: Operational Approval
```bash
# Red team leadership reviews:
# - Campaign objectives alignment
# - Ethical constraints appropriateness
# - Risk assessment completeness
# - Emergency procedures readiness
```

### Approval Workflow

```bash
# Check campaign status
chimera-cli campaign list --status created

# Approve campaign (requires leadership privileges)
chimera-cli campaign approve 550e8400-e29b-41d4-a716-446655440003 \
    --approved-by "Red Team Director"

# Verify approval
chimera-cli campaign monitor 550e8400-e29b-41d4-a716-446655440003
```

---

## 4. 🚀 Campaign Execution

### Launch Process

```bash
# Campaign launches automatically after approval
# Monitor initial execution
chimera-cli campaign monitor --live

# Expected sequence:
# 1. Pretext generation (AI-powered)
# 2. Email composition with tracking
# 3. DKIM signing and delivery
# 4. Tracking pixel activation
# 5. Real-time telemetry collection
```

### Execution Monitoring

#### Real-time Metrics
```bash
# Live campaign dashboard
Campaign: Q4 Phishing Awareness 2025
Status: active
Launched: 2025-12-19 10:30:00
Participants: 150

📊 Live Metrics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Emails Sent: 150/150 (100%)
Emails Opened: 45 (30%)
Links Clicked: 12 (8%)
Reports to Security: 3 (2%)
Active Anomalies: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Performance Indicators

| Metric | Good | Concerning | Critical |
|--------|------|------------|----------|
| **Open Rate** | > 25% | 10-25% | < 10% |
| **Click Rate** | > 5% | 2-5% | < 2% |
| **Report Rate** | < 5% | 5-15% | > 15% |
| **Anomaly Rate** | 0 | 1-5 | > 5 |

---

## 5. 👁️ Real-Time Monitoring

### Live Dashboard Features

#### Engagement Tracking
- **Email Opens**: Pixel loading detection
- **Link Clicks**: Redirect tracking with metadata
- **Form Submissions**: Landing page interactions
- **Time to Engagement**: Response time analysis

#### Anomaly Detection
```bash
# Automatic anomaly alerts
⚠️  ANOMALY DETECTED: High-volume automated interaction
   Campaign: 550e8400-e29b-41d4-a716-446655440003
   Severity: High
   Description: 50 rapid interactions from single source
   Recommendation: Investigate potential security scanner
```

#### Geographic Monitoring
```
🌍 Geographic Distribution:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
United States: ████████░░ 80% (120 opens)
Canada:        ███░░░░░░░ 30% (45 opens)
United Kingdom: █░░░░░░░░░ 10% (15 opens)
Other:         ░░░░░░░░░░  5% (8 opens)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Intervention Options

#### Manual Adjustments
```bash
# Pause campaign for investigation
chimera-cli campaign pause 550e8400-e29b-41d4-a716-446655440003

# Resume after resolution
chimera-cli campaign resume 550e8400-e29b-41d4-a716-446655440003
```

#### Adaptive Evolution
```bash
# Allow AI to adapt campaign based on performance
chimera-cli campaign adapt 550e8400-e29b-41d4-a716-446655440003 \
    --strategy increase_personalization \
    --reason "Low engagement detected"
```

---

## 6. 📊 Post-Campaign Analysis

### Comprehensive Analytics

#### Success Metrics Dashboard
```bash
chimera-cli analytics campaign 550e8400-e29b-41d4-a716-446655440003 --hours 168

Campaign Analytics: Q4 Phishing Awareness 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time Window: 168 hours (7 days)
Total Events: 2,450
Unique Visitors: 180
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 Engagement Funnel:
Emails Sent:        ████████████████████ 150 (100%)
Emails Opened:      ███████████████░░░░░ 112 (75%)
Links Clicked:      ████████░░░░░░░░░░░░  45 (30%)
Credentials Submitted: ██░░░░░░░░░░░░░░░░   8 (5%)
Reports to Security: █░░░░░░░░░░░░░░░░░░░   6 (4%)

🎯 Key Performance Indicators:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Open Rate:          74.7% (Industry avg: 25-30%)
Click Rate:         30.0% (Industry avg: 5-10%)
Conversion Rate:     5.3% (Industry avg: 1-3%)
Report Rate:         4.0% (Target: <5%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Behavioral Insights

```bash
# Device and browser analytics
Device Distribution:
Desktop: ████████████████ 65%
Mobile:  ████████░░░░░░░ 35%
Tablet:  █░░░░░░░░░░░░░░ 5%

Browser Distribution:
Chrome:  ████████████████ 70%
Firefox: ██████░░░░░░░░░ 25%
Safari:  ███░░░░░░░░░░░ 12%
Edge:    █░░░░░░░░░░░░░░ 3%

# Time-based patterns
Peak Engagement Hours:
9:00 AM: ████████░░ 40 opens
10:00 AM: ██████████ 50 opens
11:00 AM: ███████░░░ 35 opens
2:00 PM: █████████░░ 45 opens
3:00 PM: ████████░░ 40 opens
```

### Anomaly Investigation

```bash
# Review detected anomalies
chimera-cli analytics anomalies 550e8400-e29b-41d4-a716-446655440003

Anomaly Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Anomalies: 3
Critical: 0  High: 1  Medium: 2  Low: 0

🔴 HIGH SEVERITY:
• Automated scanning detected from IP range 192.168.1.0/24
  150 rapid requests in 30 seconds
  Recommendation: Block IP range, investigate source

🟡 MEDIUM SEVERITY:
• Unusual geographic concentration in single city
  45 interactions from New York City area
  Recommendation: Review targeting distribution

🟡 MEDIUM SEVERITY:
• Elevated report-to-security rate in IT department
  12 reports from 8 IT staff members
  Recommendation: IT staff training effectiveness review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. 🚨 Emergency Response

### Kill Switch Activation

#### Automatic Triggers
- **Consent Revocation**: Participant withdrawal
- **Geographic Violation**: Non-consented location access
- **Escalation Detection**: Forwarded to legal/HR
- **Time Boundary**: Campaign exceeds approved duration
- **Anomaly Threshold**: Suspicious behavior patterns

#### Manual Termination
```bash
# Emergency campaign termination
chimera-cli campaign terminate 550e8400-e29b-41d4-a716-446655440003 \
    --reason "Participant safety concern identified" \
    --terminated-by "Red Team Lead"

# Verify termination
chimera-cli campaign monitor 550e8400-e29b-41d4-a716-446655440003

# Expected output:
# Campaign Status: terminated
# Termination Reason: Participant safety concern identified
# Affected Participants: 150
# Incident Report Generated: KS-20251219-143000
```

### Incident Response Protocol

1. **Immediate Actions**
   - Activate kill switch
   - Notify affected participants
   - Preserve all evidence and logs

2. **Investigation (24 hours)**
   - Root cause analysis
   - Impact assessment
   - Ethical compliance review

3. **Remediation**
   - Participant communication
   - Process improvements
   - Training updates

4. **Reporting**
   - Incident documentation
   - Lessons learned session
   - Regulatory notifications (if required)

---

## 8. 📋 Best Practices

### Campaign Planning

#### Target Selection
- **Diverse Representation**: Include all departments and seniority levels
- **Risk Assessment**: Avoid vulnerable individuals or crisis periods
- **Consent Verification**: Double-check all participants have valid consent
- **Geographic Coverage**: Respect international privacy laws

#### Content Strategy
- **Realistic Scenarios**: Base on actual organizational communications
- **Educational Value**: Include learning opportunities in content
- **Cultural Sensitivity**: Consider organizational culture and language
- **Opt-out Clarity**: Make unsubscription process obvious and easy

### Execution Management

#### Monitoring Protocol
- **Continuous Oversight**: Monitor campaigns during business hours
- **Alert Response**: Respond to anomalies within 30 minutes
- **Stakeholder Communication**: Keep leadership informed of progress
- **Documentation**: Record all decisions and interventions

#### Quality Assurance
- **Content Review**: Human review of AI-generated content
- **Technical Validation**: Test email delivery and tracking systems
- **Ethical Compliance**: Verify all constraints are properly applied
- **Backup Systems**: Ensure campaign can be terminated if needed

### Post-Campaign Activities

#### Participant Communication
```bash
# Send debriefing emails
Subject: Thank you for participating in our security training

Dear Team Member,

Thank you for your participation in this month's phishing awareness training.
Here's what we learned:

📊 Campaign Results:
- 75% of emails were opened
- 30% of recipients clicked links
- 4% reported suspicious emails to security

🎯 Key Takeaways:
- Always verify sender identity
- Hover over links before clicking
- Report suspicious emails immediately

Your quick reporting helped improve our security posture!
```

#### Continuous Improvement
- **Lessons Learned**: Document successes and failures
- **Training Updates**: Modify training based on results
- **Process Refinement**: Improve campaign execution procedures
- **Technology Updates**: Incorporate new security features

---

## 📊 Campaign Templates

### Quick Start Templates

#### Basic Phishing Awareness
```json
{
  "name": "Basic Phishing Training",
  "campaign_type": "phishing",
  "ethical_constraints": {
    "no_threats": true,
    "include_opt_out": true,
    "educational_content": true
  },
  "duration_hours": 48
}
```

#### Advanced Social Engineering
```json
{
  "name": "Advanced Social Engineering",
  "campaign_type": "phishing",
  "ethical_constraints": {
    "no_threats": true,
    "include_opt_out": true,
    "educational_content": true,
    "authority_impersonation": false
  },
  "duration_hours": 72,
  "adaptation_enabled": true
}
```

#### Compliance Testing
```json
{
  "name": "Regulatory Compliance Test",
  "campaign_type": "phishing",
  "ethical_constraints": {
    "no_threats": true,
    "include_opt_out": true,
    "educational_content": true,
    "no_personal_data": true
  },
  "duration_hours": 24,
  "reporting_enabled": true
}
```

---

## 🔧 Troubleshooting Common Issues

### Campaign Creation Problems

```bash
# Error: Consent validation failed
# Solution: Check participant consent status
chimera-cli consent validate --participant PARTICIPANT_ID

# Error: Invalid campaign type
# Solution: Use supported campaign types
chimera-cli campaign create --help
```

### Execution Issues

```bash
# Emails not sending
# Check: SMTP configuration and connectivity
docker-compose logs postfix

# Tracking not working
# Check: Tracking server status
curl http://localhost:8080/health

# Anomalies detected
# Check: Review anomaly details
chimera-cli analytics anomalies CAMPAIGN_ID
```

### Performance Problems

```bash
# Slow analytics queries
# Check: ClickHouse performance
docker-compose exec clickhouse clickhouse-client --query "SELECT 1"

# High latency
# Check: Redis connection
docker-compose exec redis redis-cli ping

# Memory issues
# Check: Container resource usage
docker-compose stats
```

---

*"Effective campaign management requires balancing technical sophistication with ethical responsibility."*


