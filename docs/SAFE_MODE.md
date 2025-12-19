# Safe Mode Configuration Guide

## Overview

Safe Mode is CHIMERA's most restrictive operating configuration, designed for new users, educational environments, and high-risk scenarios. It implements maximum security controls while maintaining core functionality for learning and safe experimentation.

## When to Use Safe Mode

### Recommended Scenarios
- **First-time setup** and learning
- **Educational environments** (universities, training labs)
- **Development and testing** environments
- **High-compliance organizations** with strict security requirements
- **Proof-of-concept deployments** before production use

### Safe Mode Benefits
- **Zero-risk operation** with maximum restrictions
- **Automatic compliance** with strictest security standards
- **Educational safeguards** to prevent accidental misuse
- **Gradual onboarding** path to full functionality

## Configuration

### Safe Mode Settings

Create a configuration file `config/safe_mode.yml`:

```yaml
# CHIMERA Safe Mode Configuration
# Version: 1.0
# DO NOT MODIFY UNLESS YOU UNDERSTAND THE SECURITY IMPLICATIONS

safe_mode:
  enabled: true

# Campaign Restrictions
campaign:
  max_recipients: 10                    # Maximum recipients per campaign
  require_manual_approval: true         # All campaigns require human approval
  geographic_whitelist:                 # Only allow these countries
    - "US"
    - "CA"
    - "GB"
  auto_expire_hours: 24                 # Campaigns auto-expire after 24 hours
  disable_advanced_tracking: true       # No behavioral tracking
  force_simulation_banner: true         # Show "SIMULATION" banner in emails

# Rate Limiting (Stricter than normal)
rate_limiting:
  per_tenant_emails_per_hour: 10        # Very restrictive
  api_requests_per_hour: 100           # Limited API usage
  tracking_requests_per_minute: 10     # Minimal tracking

# Consent Requirements
consent:
  require_explicit_opt_in: true         # No implied consent
  minimum_notice_period: 72             # 72 hours notice before campaigns
  allow_emergency_override: false       # No emergency overrides
  audit_all_actions: true               # Log everything

# Kill Switch Settings
kill_switch:
  enable_geographic_detection: true     # Block non-whitelisted countries
  enable_time_limits: true              # Enforce campaign time limits
  enable_escalation_detection: true     # Detect forwarded emails
  auto_kill_sensitivity: "high"         # Very sensitive triggers

# Privacy & Security
privacy:
  credential_sanitization: "strict"     # Remove ALL potential credentials
  payload_size_limit: 1024              # 1KB max payload size
  disable_file_attachments: true        # No file attachments
  require_encryption: true              # Force TLS everywhere

# AI & Content Restrictions
pretext_engine:
  disable_ai_generation: false          # Allow AI but with restrictions
  require_human_review: true            # All AI content reviewed
  ethical_filter_sensitivity: "maximum" # Most restrictive filtering
  content_templates_only: true          # Only pre-approved templates

# Monitoring & Alerting
monitoring:
  alert_on_any_violation: true          # Alert on all policy violations
  require_security_review: true         # Security team reviews all campaigns
  log_all_actions: true                 # Comprehensive audit logging
  disable_analytics: false              # Keep basic analytics for learning

# User Interface
ui:
  show_warnings: true                   # Show security warnings prominently
  disable_advanced_features: true       # Hide complex features
  force_tutorial_mode: true             # Guide users through safe practices
  display_compliance_status: true       # Show compliance status dashboard
```

## Safe Mode Operation

### Starting in Safe Mode

```bash
# Set environment variable
export CHIMERA_SAFE_MODE=true

# Or use configuration file
export CHIMERA_CONFIG=config/safe_mode.yml

# Start the application
docker-compose --profile safe-mode up
```

### Safe Mode Indicators

When operating in Safe Mode, you'll see:

1. **UI Banner**: "SAFE MODE - RESTRICTED OPERATION" in red
2. **Campaign Limits**: Maximum 10 recipients per campaign
3. **Approval Required**: All campaigns need manual approval
4. **Geographic Blocking**: Only whitelisted countries allowed
5. **Time Limits**: 24-hour automatic expiration
6. **Simulation Banners**: "SIMULATION - TRAINING EXERCISE" in all emails

### Gradual Relaxation

Safe Mode is designed for gradual progression:

```
Safe Mode (Level 1) → Basic Mode (Level 2) → Advanced Mode (Level 3) → Full Mode (Level 4)
     ↓                        ↓                        ↓                        ↓
  10 recipients           100 recipients           1000 recipients          Unlimited
  Manual approval         Auto-approval            Auto-approval            Auto-approval
  1 country              10 countries              50 countries             Worldwide
  24h expiration          7d expiration            30d expiration           Custom
```

## Safe Mode Features

### Campaign Restrictions

#### Recipient Limits
- **Maximum**: 10 recipients per campaign
- **Purpose**: Prevents mass operations during learning
- **Override**: Requires security team approval

#### Geographic Restrictions
- **Allowed Countries**: US, CA, GB only (configurable)
- **Detection**: IP geolocation on email opens
- **Action**: Immediate campaign termination on violation

#### Time Limits
- **Campaign Duration**: Maximum 24 hours
- **Auto-Expiration**: Campaigns automatically terminate
- **Extension**: Requires manual approval

### Content Restrictions

#### Email Templates
- **Pre-Approved Only**: No custom content allowed
- **Simulation Banners**: Mandatory "SIMULATION" notices
- **Attachment Limits**: No file attachments permitted

#### AI Content Generation
- **Human Review Required**: All AI-generated content reviewed
- **Ethical Filtering**: Maximum sensitivity settings
- **Template Restrictions**: Only educational templates allowed

### Security Features

#### Consent Verification
- **Explicit Opt-In**: No implied consent accepted
- **Notice Period**: 72 hours minimum notice
- **Audit Trail**: All consent actions logged
- **No Overrides**: Emergency overrides disabled

#### Credential Protection
- **Strict Sanitization**: All potential credentials removed
- **Size Limits**: 1KB maximum payload size
- **Pattern Detection**: Advanced credential pattern matching

#### Rate Limiting
- **API Limits**: 100 requests per hour
- **Email Limits**: 10 emails per hour per tenant
- **Tracking Limits**: 10 tracking requests per minute

### Monitoring & Compliance

#### Alert System
- **Violation Alerts**: Immediate alerts on any policy violation
- **Security Review**: All campaigns reviewed by security team
- **Audit Logging**: Comprehensive action logging
- **Compliance Dashboard**: Real-time compliance status

#### Kill Switch Integration
- **Automatic Triggers**: Highly sensitive kill switch settings
- **Geographic Detection**: Blocks non-whitelisted countries
- **Escalation Detection**: Detects email forwarding to HR/legal
- **Time Enforcement**: Strict campaign time limits

## Safe Mode Workflows

### 1. Educational Campaign Creation

```
User Request → Template Selection → Content Review → Security Approval → Limited Send → Monitoring → Auto-Termination
```

### 2. Consent Management

```
Participant → Opt-In Request → 72h Notice → Explicit Consent → Audit Logging → Campaign Access → Auto-Revocation
```

### 3. Violation Handling

```
Violation Detected → Immediate Alert → Campaign Pause → Security Review → Resolution → Resume/Reject
```

## Troubleshooting Safe Mode

### Common Issues

#### "Campaign exceeds recipient limit"
- **Solution**: Reduce recipients to ≤10 or request security approval
- **Prevention**: Plan campaigns with Safe Mode limits in mind

#### "Geographic restriction violation"
- **Solution**: Check recipient locations or request geographic expansion
- **Prevention**: Use geographic tools to verify recipient locations

#### "Content rejected by ethical filter"
- **Solution**: Use pre-approved templates or request content review
- **Prevention**: Familiarize with approved content guidelines

#### "Rate limit exceeded"
- **Solution**: Wait for limit reset or request higher limits
- **Prevention**: Space out operations and monitor usage

### Escalation Process

For Safe Mode restrictions that impede legitimate use:

1. **Document Requirements**: Explain business need and risk mitigation
2. **Security Review**: Submit for security team evaluation
3. **Approval Process**: Wait for formal approval (24-48 hours)
4. **Gradual Relaxation**: Move to higher permission levels incrementally

## Transitioning Out of Safe Mode

### Readiness Assessment

Before transitioning from Safe Mode, ensure:

- [ ] Understanding of CHIMERA security principles
- [ ] Completion of security training modules
- [ ] Successful Safe Mode campaign execution
- [ ] Security team approval for transition
- [ ] Compliance with organizational policies

### Transition Steps

1. **Configuration Update**: Modify `safe_mode.enabled: false`
2. **Gradual Relaxation**: Increase limits incrementally
3. **Training Completion**: Complete advanced user training
4. **Security Approval**: Obtain formal approval for expanded access
5. **Monitoring Period**: Operate under enhanced monitoring for 30 days

### Permission Levels

```
Level 1 (Safe Mode):    10 recipients, 1 country, manual approval
Level 2 (Basic):        100 recipients, 10 countries, auto-approval with review
Level 3 (Advanced):     1000 recipients, 50 countries, auto-approval
Level 4 (Full):         Unlimited, worldwide, full automation
```

## Security Considerations

### Safe Mode Limitations
- **Not a Security Guarantee**: Safe Mode prevents accidental misuse but doesn't replace security expertise
- **Performance Impact**: Additional checks may slow operations
- **User Experience**: Restrictions may impede workflow efficiency
- **False Positives**: Overly restrictive filtering may block legitimate content

### Best Practices
- **Start in Safe Mode**: Always begin with maximum restrictions
- **Gradual Expansion**: Increase permissions as experience grows
- **Regular Audits**: Periodic security reviews of Safe Mode configurations
- **Incident Response**: Use Safe Mode during security incidents

## Support & Resources

### Documentation
- [Main README](../README.md) - Overview and quick start
- [Security Policy](../SECURITY.md) - Security procedures
- [Contributing Guide](../CONTRIBUTING.md) - Development guidelines

### Getting Help
- **Safe Mode Issues**: Create GitHub issue with "safe-mode" label
- **Security Questions**: security@chimera-project.org
- **General Support**: support@chimera-project.org

### Community Resources
- **GitHub Discussions**: Community support and questions
- **Documentation Wiki**: Extended guides and tutorials
- **Training Materials**: Video tutorials and workshops

---

**Safe Mode ensures responsible use of powerful security tools. When in doubt, stay in Safe Mode.**

**Last Updated:** December 2025
**Version:** 1.0
