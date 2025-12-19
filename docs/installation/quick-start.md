# 🚀 CHIMERA Quick Start Guide

## Get CHIMERA Running in 10 Minutes

**Target Audience**: Red team operators, security researchers, system administrators

**Prerequisites**: Docker, Python 3.11+, basic command-line knowledge

---

## ⚡ Quick Start Checklist

- [ ] **Step 1**: Clone repository
- [ ] **Step 2**: Configure environment
- [ ] **Step 3**: Deploy infrastructure
- [ ] **Step 4**: Initialize databases
- [ ] **Step 5**: Create first campaign
- [ ] **Step 6**: Monitor results

---

## 1. 📥 Clone and Setup

```bash
# Clone the repository
git clone https://github.com/lucien-vallois/adversarial-phish-forge.git
cd adversarial-phish-forge

# Copy environment template
cp .env.template .env

# Edit .env with your configuration (see configuration section below)
nano .env  # or your preferred editor
```

### Required Environment Variables

```bash
# OpenAI Configuration (Required for AI pretext generation)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ORGANIZATION=your_org_id_here
OPENAI_MODEL=gpt-4-turbo-preview

# Security (Generate strong random keys)
SECRET_KEY=your_super_secret_key_32_chars_minimum
JWT_SECRET_KEY=your_jwt_secret_key_32_chars_minimum
FINGERPRINT_HASH_SALT=your_fingerprint_salt_16_chars_minimum

# Database (PostgreSQL for consent, will be auto-configured)
DATABASE_URL=postgresql://chimera:chimera_password@localhost:5432/chimera

# Optional: Email delivery (use test credentials for evaluation)
SMTP_USER=test@yourdomain.com
SMTP_PASSWORD=your_smtp_password
```

---

## 2. 🐳 Deploy Infrastructure

```bash
# Start all services (Neo4j, ClickHouse, Redis, PostgreSQL, Postfix)
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output should show 6 containers running:
# - postgres, neo4j, clickhouse, redis, postfix, orchestrator (will start after init)
```

### Service Health Checks

```bash
# Check individual service health
curl http://localhost:7474/browser/  # Neo4j Browser (credentials: neo4j/chimera_password)
curl http://localhost:8123/          # ClickHouse HTTP interface
curl http://localhost:6379           # Redis (should refuse connection - normal)
```

---

## 3. 🗄️ Initialize Databases

```bash
# Initialize consent database schema and sample data
python scripts/init_consent_db.py

# Expected output:
# CHIMERA consent database initialization completed successfully
```

### Verify Database Initialization

```bash
# Check PostgreSQL database
docker-compose exec postgres psql -U chimera -d chimera -c "SELECT COUNT(*) FROM consent_registry;"

# Check Neo4j data
docker-compose exec neo4j cypher-shell -u neo4j -p chimera_password "MATCH (n) RETURN count(n);"
```

---

## 4. 🎯 Launch Orchestrator

```bash
# Start the FastAPI orchestrator
docker-compose up orchestrator

# Alternative: Run in background
# docker-compose up -d orchestrator

# Verify orchestrator is running
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "service": "chimera-orchestrator", "version": "1.0.0-BLACKBOX"}
```

---

## 5. 🎯 Create Your First Campaign

### Using the CLI (Recommended)

```bash
# Install CLI (optional)
sudo python scripts/setup_cli.py

# Create a basic campaign
chimera-cli campaign create \
    --name "CHIMERA Evaluation Campaign" \
    --description "First campaign to test system functionality" \
    --type phishing \
    --targets evaluation_targets.csv \
    --approval-required

# Approve the campaign
chimera-cli campaign approve <campaign_id_from_previous_command>

# Monitor campaign progress
chimera-cli campaign monitor --live
```

### Using the API (Alternative)

```bash
# Create campaign
curl -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CHIMERA Evaluation Campaign",
    "description": "First campaign to test system functionality",
    "campaign_type": "phishing",
    "target_participants": ["test-participant-001"],
    "ethical_constraints": {
      "no_threats": true,
      "include_opt_out": true,
      "educational_content": true
    },
    "created_by": "administrator"
  }'

# Approve campaign (note the campaign_id from response)
curl -X POST http://localhost:8000/campaigns/{campaign_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "administrator"}'
```

### Sample Target File (evaluation_targets.csv)

```csv
participant_id,email
test-participant-001,test@example.com
```

---

## 6. 📊 Monitor and Analyze

### Real-time Monitoring

```bash
# CLI monitoring
chimera-cli campaign monitor --live

# API status check
curl http://localhost:8000/system/status

# Tracking server health
curl http://localhost:8080/health
```

### View Campaign Analytics

```bash
# Get campaign details
chimera-cli campaign list

# View specific campaign
chimera-cli campaign monitor <campaign_id>

# Check telemetry data
curl http://localhost:8123/?query=SELECT%20count()%20FROM%20telemetry_events
```

---

## 7. 🎯 Test Email Delivery

### Send Test Email

```bash
# Test email delivery (requires SMTP configuration)
curl -X POST http://localhost:8000/test/email \
  -H "Content-Type: application/json" \
  -d '{"recipient": "test@example.com"}'
```

### Verify Tracking

```bash
# Check if tracking server receives pixel requests
curl http://localhost:8080/security/status

# Monitor telemetry events
docker-compose exec clickhouse clickhouse-client --query "
  SELECT event_type, count(*) as count
  FROM telemetry_events
  GROUP BY event_type
  ORDER BY count DESC
  LIMIT 10
"
```

---

## 🎉 Success Indicators

### ✅ System is Working If:

1. **All containers running**: `docker-compose ps` shows 6 healthy containers
2. **Health checks pass**: All services return 200 status
3. **Database initialized**: Consent records exist in PostgreSQL
4. **Campaign created**: API returns campaign ID without errors
5. **Emails delivered**: Test emails arrive (if SMTP configured)
6. **Tracking works**: Pixel requests logged in telemetry

### 📈 Expected Performance

- **Campaign creation**: < 5 seconds
- **Email delivery**: < 30 seconds (SMTP dependent)
- **Analytics queries**: < 2 seconds
- **System startup**: < 2 minutes

---

## 🔧 Troubleshooting Quick Fixes

### Common Issues

```bash
# Services not starting
docker-compose logs <service_name>
docker-compose restart <service_name>

# Database connection errors
docker-compose exec postgres psql -U chimera -d chimera -c "SELECT 1;"

# API not responding
curl http://localhost:8000/health
docker-compose logs orchestrator

# OpenAI API errors
# Check OPENAI_API_KEY in .env
# Verify API quota and billing

# Email delivery issues
docker-compose logs postfix
telnet localhost 587  # Test SMTP connection
```

### Reset Everything

```bash
# Nuclear option - reset everything
docker-compose down -v
docker-compose up -d
python scripts/init_consent_db.py
```

---

## 📚 Next Steps

### For Evaluation
- [Create Advanced Campaigns](./examples/basic-campaign.md)
- [Explore Analytics](./user-guide/monitoring.md)
- [Test Ethical Boundaries](./ethics/guidelines.md)

### For Production Deployment
- [Security Hardening](./security/hardening.md)
- [Scalability Tuning](./troubleshooting/performance.md)
- [Backup Procedures](./troubleshooting/backup.md)

### For Development
- [API Documentation](./api/)
- [Extending CHIMERA](./developer/extending.md)
- [Contributing Guide](./contributing/)

---

## 📞 Need Help?

- **Documentation**: [Full Installation Guide](./installation/)
- **Issues**: [GitHub Issues](https://github.com/lucien-vallois/adversarial-phish-forge/issues)
- **Community**: [GitHub Discussions](https://github.com/lucien-vallois/adversarial-phish-forge/discussions)

---

*"CHIMERA provides the tools to understand modern threats without becoming the threat."*


