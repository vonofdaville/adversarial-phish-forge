# Business Email Compromise (BEC) Simulation

This example demonstrates how to use CHIMERA for ethical Business Email Compromise (BEC) training in a controlled, consensual environment.

## Overview

Business Email Compromise is one of the most damaging cyber threats, costing organizations billions annually. This simulation helps finance teams recognize and respond to sophisticated email impersonation attacks.

## Learning Objectives

After completing this simulation, participants will be able to:
- Identify sophisticated email impersonation techniques
- Recognize urgent financial request patterns
- Understand the importance of multi-factor verification
- Practice incident response procedures

## Safety & Ethics

This simulation includes multiple safety mechanisms:
- **Maximum 10 recipients** (Safe Mode restriction)
- **Mandatory consent verification** for all participants
- **72-hour advance notice** requirement
- **Simulation banners** clearly marking all emails as training
- **Kill switch** available for immediate termination

## Prerequisites

1. **CHIMERA Installation** - Follow the main README.md
2. **Participant Consent** - All recipients must provide explicit written consent
3. **Safe Mode Configuration** - Must run in Safe Mode for first deployments
4. **Legal Authorization** - Obtain necessary approvals from legal/compliance teams

## Configuration

### 1. Safe Mode Setup

Create `config/safe_mode.yml`:

```yaml
safe_mode:
  enabled: true

campaign:
  max_recipients: 10
  require_manual_approval: true
  geographic_whitelist: ["US", "CA", "GB"]
  auto_expire_hours: 24
  disable_advanced_tracking: true
  force_simulation_banner: true

consent:
  require_explicit_opt_in: true
  minimum_notice_period: 72  # hours
```

### 2. Campaign Configuration

Create `examples/bec_simulation/campaign_config.yml`:

```yaml
campaign:
  name: "Q4 Financial Review - Urgent Wire Transfer"
  description: "Simulated CFO email requesting immediate wire transfer"
  pretext_template: "cfo_wire_transfer"
  target_audience: "finance_team"
  ethical_justification: "Training finance staff to detect BEC attacks"

simulation:
  sender_impersonation: "CFO"
  urgency_level: "critical"
  financial_amount: "$2,750,000"
  requested_action: "wire_transfer"
  fake_bank_details: true

safety:
  kill_switch_enabled: true
  consent_required: true
  max_campaign_duration: 8  # hours
  monitoring_enabled: true
```

### 3. Target List

Create `examples/bec_simulation/target_list.csv`:

```csv
email,name,department,consent_date,consent_signature
john.doe@company.com,John Doe,Finance,2025-12-19,JD_SIGNATURE_ABC123
jane.smith@company.com,Jane Smith,Accounting,2025-12-19,JS_SIGNATURE_DEF456
bob.wilson@company.com,Bob Wilson,Treasury,2025-12-19,BW_SIGNATURE_GHI789
```

## Execution Steps

### Step 1: Environment Setup

```bash
# Start CHIMERA in Safe Mode
export CHIMERA_SAFE_MODE=true
export CHIMERA_CONFIG=config/safe_mode.yml

# Start infrastructure
docker-compose --profile safe-mode up -d

# Verify consent database
python scripts/init_consent_db.py
```

### Step 2: Consent Verification

```bash
# Load participant consents
python scripts/load_consents.py examples/bec_simulation/target_list.csv

# Verify all consents are active
python scripts/verify_consents.py --campaign bec_simulation_q4
```

### Step 3: Campaign Creation

```bash
# Create the BEC simulation campaign
chimera-cli campaign create \
  --config examples/bec_simulation/campaign_config.yml \
  --targets examples/bec_simulation/target_list.csv \
  --safe-mode \
  --consent-required \
  --manual-approval
```

### Step 4: Content Review & Approval

```bash
# Review generated email content
chimera-cli campaign preview bec_simulation_q4

# Approve campaign (requires manual review)
chimera-cli campaign approve bec_simulation_q4 \
  --reviewer "Security Trainer" \
  --justification "Authorized BEC training exercise"
```

### Step 5: Controlled Execution

```bash
# Send simulation emails
chimera-cli campaign send bec_simulation_q4 \
  --batch-size 3 \
  --delay 300  # 5-minute delays between batches
```

### Step 6: Monitoring & Response

```bash
# Monitor campaign in real-time
chimera-cli campaign monitor bec_simulation_q4

# Check for safety triggers
chimera-cli campaign status bec_simulation_q4

# Emergency stop if needed
chimera-cli emergency kill bec_simulation_q4 \
  --reason "Training completed early"
```

## Email Template Example

The simulation uses ethically designed templates that clearly indicate training status:

```
SUBJECT: URGENT: Q4 Financial Review - Wire Transfer Required

[SIMULATION - TRAINING EXERCISE]
[DO NOT TAKE FINANCIAL ACTION]

Dear Finance Team,

I hope this email finds you well. I'm currently traveling and need your immediate assistance with an urgent Q4 financial matter.

We have received an unexpected acquisition opportunity that requires immediate funding. Please process a wire transfer of $2,750,000 to the following account:

Bank: International Commercial Bank
Account: 123456789
Routing: 021000021
SWIFT: ICBUUS33

This must be completed within the next 2 hours to secure the deal. I've attached the acquisition documents for your reference.

Please confirm completion via reply to this email.

Best regards,
Sarah Johnson
Chief Financial Officer
Company Inc.
Phone: +1 (555) 123-4567

---
[SIMULATION NOTICE]
This is a CHIMERA training exercise to improve your awareness of Business Email Compromise attacks.
No actual financial transactions should be attempted.
If you received this unexpectedly, please contact security@company.com immediately.
```

## Debriefing Process

### Post-Campaign Analysis

```bash
# Generate campaign report
chimera-cli campaign report bec_simulation_q4 \
  --format pdf \
  --include-responses

# Analyze participant responses
chimera-cli analytics responses bec_simulation_q4 \
  --identify-patterns
```

### Training Debrief

1. **Review Results**: Discuss which participants identified the simulation
2. **Lessons Learned**: Cover common BEC indicators missed
3. **Process Improvements**: Update verification procedures
4. **Follow-up Training**: Schedule advanced BEC awareness sessions

## Compliance Checklist

- [ ] **Legal Authorization**: Written approval from legal department
- [ ] **Participant Consent**: All recipients provided explicit consent
- [ ] **Notice Period**: 72-hour advance notice given
- [ ] **Safe Mode**: Campaign executed in Safe Mode
- [ ] **Monitoring**: Real-time monitoring active during execution
- [ ] **Kill Switch**: Emergency termination capability tested
- [ ] **Debrief**: Post-campaign debriefing conducted
- [ ] **Records**: All activities properly documented

## Risk Mitigation

### Technical Safeguards
- Geographic restrictions prevent international execution
- Rate limiting prevents mass distribution
- Consent verification blocks unauthorized recipients
- Kill switch enables immediate termination

### Operational Safeguards
- Manual approval required before sending
- Small batch sizes with delays
- Real-time monitoring throughout execution
- Emergency contact procedures documented

### Legal Safeguards
- Explicit consent required from all participants
- Clear simulation markings on all content
- Comprehensive audit trail maintained
- Incident response procedures documented

## Metrics & Success Criteria

### Success Metrics
- **Detection Rate**: >80% of recipients identify simulation
- **Response Time**: Average <30 minutes to report
- **Process Compliance**: 100% adherence to verification procedures
- **Training Effectiveness**: Improved BEC detection in follow-up assessments

### Quality Assurance
- **Content Review**: All emails reviewed by security experts
- **Technical Validation**: Automated checks for safety mechanisms
- **Participant Feedback**: Survey responses from training participants
- **Process Audit**: Independent review of execution procedures

## Troubleshooting

### Common Issues

#### "Consent verification failed"
```
Solution: Verify participant consent in database
Command: python scripts/check_consent.py --email user@company.com
```

#### "Campaign exceeds Safe Mode limits"
```
Solution: Reduce recipient count or request exception approval
Command: chimera-cli campaign modify bec_simulation_q4 --max-recipients 5
```

#### "Geographic restriction triggered"
```
Solution: Verify recipient locations or expand geographic whitelist
Command: chimera-cli config update geographic_whitelist --add "AU"
```

## Related Resources

- [CHIMERA Safe Mode Guide](../docs/SAFE_MODE.md)
- [Consent Management Documentation](../docs/consent/)
- [Ethical Use Guidelines](../docs/ethics/guidelines.md)
- [FBI BEC Awareness Resources](https://www.fbi.gov/scams-and-safety/common-scams-and-crimes/business-email-compromise)

## Contact & Support

- **Security Team**: security@chimera-project.org
- **Training Support**: training@chimera-project.org
- **Technical Issues**: support@chimera-project.org

---

**This simulation demonstrates responsible cybersecurity training. Always prioritize participant safety and organizational security.**
