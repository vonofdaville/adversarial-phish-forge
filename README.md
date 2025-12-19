# PROJECT CHIMERA
## Cognitive Heuristic Intelligence for Multi-stage Engagement Research & Assessment

**Classification:** Adversarial AI Research - Controlled Disclosure
**Version:** 1.0.0-BLACKBOX
**Author:** Lucien Vallois
**Date:** December 2025
**Codename:** ADVERSARIAL-PHISH-FORGE

---

## SECURITY NOTICE

This framework is designed for **authorized red team operations only**. The techniques documented herein mirror TTPs employed by Advanced Persistent Threat (APT) actors. **Unauthorized deployment constitutes violations of:**

- 18 U.S.C. § 1030 (Computer Fraud and Abuse Act)
- 18 U.S.C. § 2701 (Stored Communications Act)
- EU GDPR Articles 5, 9, 32
- CCPA § 1798.100

---

## Overview

CHIMERA provides red teams with an ethically-bounded, consent-enforced simulation platform that mirrors nation-state social engineering sophistication while maintaining legal and moral guardrails.

**Core Innovation:** The first open-source framework combining adversarial AI (LLM-driven pretext evolution) with identity graph mapping (OSINT correlation) in a privacy-preserving architecture.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │   CHIMERA ORCHESTRATOR          │
                    │   (FastAPI + Redis Queue)       │
                    └───────────┬─────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
        │ PRETEXT AI   │ │ IDENTITY  │ │  TELEMETRY  │
        │ (GPT-4 API)  │ │   GRAPH   │ │   ENGINE    │
        │              │ │ (Neo4j)   │ │ (ClickHouse)│
        └───────┬──────┘ └─────┬─────┘ └──────┬──────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  DELIVERY SUBSYSTEM   │
                    │  (SMTP + JS Tracker)  │
                    └───────────────────────┘
```

## Quickstart

```bash
# Prerequisites
# - Docker 24.0+
# - Python 3.11+
# - OpenAI API key (GPT-4 access)

# 1. Clone repository
git clone https://github.com/lucien-vallois/adversarial-phish-forge.git
cd adversarial-phish-forge

# 2. Configure environment
cp .env.example .env
# Edit .env: Add OPENAI_API_KEY, NEO4J_URI, etc.

# 3. Deploy infrastructure
docker-compose up -d

# 4. Initialize consent database
python scripts/init_consent_db.py

# 5. Create first campaign (requires human approval)
chimera-cli campaign create \
    --name "BEC Simulation Alpha" \
    --target-list targets.csv \
    --approval-required

# 6. Monitor real-time
chimera-cli dashboard --live
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestrator** | Python 3.11 + FastAPI | Campaign lifecycle management |
| **Pretext Engine** | OpenAI GPT-4 API | Adaptive email generation |
| **Identity Graph** | Neo4j (graph DB) | Relationship mapping (mock OSINT) |
| **Telemetry** | ClickHouse | High-velocity event storage |
| **Email Delivery** | Postfix + DKIM | Legitimate infrastructure |
| **Tracking** | Node.js + Express | Behavioral probe (JS-based) |

## Ethical Boundaries

CHIMERA implements a "Three Gates" authorization model:

1. **Legal Clearance** - Written authorization from legal counsel
2. **Participant Consent** - Individual opt-in with revocation rights
3. **Operational Review** - Human approval for all generated content

## Responsible Disclosure

Security vulnerabilities or ethical concerns: security@chimera-project.org

## Legal Disclaimer

THE CHIMERA FRAMEWORK IS PROVIDED FOR AUTHORIZED RED TEAM OPERATIONS ONLY. USERS ASSUME FULL LEGAL RESPONSIBILITY FOR COMPLIANCE WITH APPLICABLE LAWS.

**By using this software, you certify that:**
1. You have obtained written legal authorization
2. All participants have provided informed consent
3. You will comply with all applicable laws and regulations
4. You will not weaponize this technology

---

**The adversary adapts. So must we.**

