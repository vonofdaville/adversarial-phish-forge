# 📋 CHIMERA System Requirements

## Hardware and Software Prerequisites

**Last Updated**: December 2025
**Applies to**: CHIMERA v1.0.0-BLACKBOX

---

## 🖥️ Minimum Hardware Requirements

### Development/Evaluation Environment

| Component | Minimum | Recommended | Purpose |
|-----------|---------|-------------|---------|
| **CPU** | 4 cores | 8+ cores | Parallel processing, AI inference |
| **RAM** | 8 GB | 16 GB | Database operations, AI models |
| **Storage** | 50 GB SSD | 100 GB SSD | Databases, logs, analytics |
| **Network** | 100 Mbps | 1 Gbps | API calls, email delivery |

### Production Environment

| Component | Minimum | Recommended | Purpose |
|-----------|---------|-------------|---------|
| **CPU** | 8 cores | 16+ cores | High-throughput campaign execution |
| **RAM** | 16 GB | 32 GB | Large-scale telemetry processing |
| **Storage** | 200 GB SSD | 500 GB SSD | Long-term analytics retention |
| **Network** | 1 Gbps | 10 Gbps | High-volume email delivery |

---

## 🐧 Operating System Support

### Fully Supported

| OS | Version | Architecture | Notes |
|----|---------|--------------|-------|
| **Ubuntu** | 20.04 LTS+ | x86_64 | Primary development platform |
| **CentOS/RHEL** | 8+ | x86_64 | Enterprise environments |
| **Debian** | 11+ | x86_64 | Alternative Linux distribution |
| **macOS** | 12+ (Monterey) | Intel/Apple Silicon | Development workstations |

### Experimental Support

| OS | Version | Status | Limitations |
|----|---------|--------|-------------|
| **Windows** | 10/11 Pro | Experimental | Docker Desktop required, performance overhead |
| **Windows Server** | 2019+ | Experimental | Enterprise deployments |
| **Fedora** | 35+ | Community | May require additional configuration |

### Unsupported

- **Windows Home editions** (Docker limitations)
- **macOS < 12** (Python/OpenSSL compatibility)
- **32-bit architectures** (memory constraints)
- **ARM-based systems** (experimental Docker support)

---

## 🐳 Docker Requirements

### Required Versions

| Component | Version | Purpose |
|-----------|---------|---------|
| **Docker Engine** | 24.0+ | Container runtime |
| **Docker Compose** | 2.0+ | Multi-container orchestration |
| **Docker Desktop** | 4.0+ | GUI management (optional) |

### Docker Configuration

```bash
# Verify Docker installation
docker --version
docker-compose --version

# Required Docker settings
cat >> ~/.docker/daemon.json << EOF
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# Restart Docker service
sudo systemctl restart docker
```

### Resource Allocation

```yaml
# docker-compose.yml resource limits (recommended)
services:
  orchestrator:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'

  neo4j:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'

  clickhouse:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

---

## 🐍 Python Requirements

### Version Requirements

| Component | Version | Installation |
|-----------|---------|--------------|
| **Python** | 3.11+ | System package manager or pyenv |
| **pip** | 23.0+ | Python package installer |
| **virtualenv** | 20.0+ | Environment isolation |

### Python Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# CentOS/RHEL
sudo yum install python311 python311-pip
# or
sudo dnf install python3.11 python3.11-pip

# macOS (using Homebrew)
brew install python@3.11

# Verify installation
python3.11 --version
pip3 --version
```

### Required Python Packages

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Key dependencies and versions
fastapi==0.104.1          # Web framework
uvicorn==0.24.0          # ASGI server
neo4j==5.18.0            # Graph database
clickhouse-driver==0.2.6 # Analytics database
openai==1.3.7            # AI pretext generation
cryptography==41.0.7     # Security functions
pydantic==2.5.0          # Data validation
```

---

## 🌐 Network Requirements

### Inbound Ports (Production)

| Port | Protocol | Service | Purpose |
|------|----------|---------|---------|
| **22** | TCP | SSH | Administrative access |
| **80** | TCP | HTTP | Redirects to HTTPS |
| **443** | TCP | HTTPS | Web interface/API |
| **587** | TCP | SMTP | Email delivery (TLS) |
| **7474** | TCP | Neo4j | Graph database browser |
| **7687** | TCP | Neo4j | Graph database bolt |
| **8123** | TCP | ClickHouse | Analytics HTTP |
| **9000** | TCP | ClickHouse | Analytics native |

### Outbound Connectivity

| Destination | Port | Purpose | Critical |
|-------------|------|---------|----------|
| **api.openai.com** | 443 | GPT-4 API | Yes |
| **SMTP relays** | 587/465 | Email delivery | Yes |
| **PyPI** | 443 | Python packages | No |
| **NPM registry** | 443 | Node.js packages | No |
| **Docker Hub** | 443 | Container images | Yes |

### Firewall Configuration

```bash
# UFW example (Ubuntu)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 443/tcp
sudo ufw allow 587/tcp

# Restrict Neo4j/ClickHouse to localhost in production
sudo ufw deny 7474/tcp
sudo ufw deny 8123/tcp
```

---

## 🔐 Security Requirements

### System Hardening

```bash
# Disable root login
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Enable automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades

# Configure fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### SSL/TLS Certificates

```bash
# Let's Encrypt (recommended)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# Self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/chimera.key \
  -out /etc/ssl/certs/chimera.crt
```

---

## 📊 Database Storage Requirements

### PostgreSQL (Consent Database)

| Metric | Development | Production |
|--------|-------------|------------|
| **Storage** | 10 GB | 100 GB+ |
| **Connections** | 10 | 50+ |
| **Retention** | 1 year | 7 years (compliance) |

### Neo4j (Identity Graph)

| Metric | Development | Production |
|--------|-------------|------------|
| **Storage** | 20 GB | 200 GB+ |
| **Nodes** | 10,000 | 1M+ |
| **Relationships** | 50,000 | 10M+ |

### ClickHouse (Telemetry)

| Metric | Development | Production |
|--------|-------------|------------|
| **Storage** | 50 GB | 1 TB+ |
| **Events/Day** | 10,000 | 1M+ |
| **Retention** | 30 days | 2 years |

---

## ⚡ Performance Benchmarks

### Baseline Performance

```
Campaign Creation:     < 5 seconds
Email Delivery:        < 30 seconds
Analytics Query:       < 2 seconds
Graph Traversal:       < 1 second
AI Pretext Generation: < 10 seconds
```

### Scaling Guidelines

| User Load | CPU Cores | RAM | Storage |
|-----------|-----------|-----|---------|
| **10 campaigns/day** | 8 cores | 16 GB | 200 GB |
| **100 campaigns/day** | 16 cores | 32 GB | 500 GB |
| **1000 campaigns/day** | 32 cores | 64 GB | 2 TB |

---

## 🧪 Testing Requirements

### Development Environment

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov black flake8 mypy

# Run test suite
pytest tests/ -v --cov=chimera

# Performance testing
pip install locust
locust -f tests/performance/locustfile.py
```

### Integration Testing

```bash
# Test all services
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# API testing
newman run tests/postman/CHIMERA_API_Tests.postman_collection.json
```

---

## 📋 Pre-Installation Checklist

- [ ] **Hardware meets minimum requirements**
- [ ] **Operating system supported and updated**
- [ ] **Docker and Docker Compose installed**
- [ ] **Python 3.11+ installed and configured**
- [ ] **Network connectivity verified**
- [ ] **Firewall configured appropriately**
- [ ] **SSL certificates obtained**
- [ ] **Backup strategy planned**

---

## 🚨 Known Limitations

### Platform Limitations

1. **Windows Support**: Experimental, performance overhead
2. **ARM Architecture**: Limited Docker image availability
3. **Network Restrictions**: Requires outbound HTTPS access
4. **Resource Intensive**: High memory/CPU requirements for AI features

### Feature Limitations

1. **Email Deliverability**: Depends on SMTP provider reputation
2. **AI Rate Limits**: OpenAI API quotas apply
3. **Geographic Restrictions**: Some services region-locked
4. **Browser Compatibility**: Modern browsers required for tracking

---

## 📞 Support and Compatibility

### Supported Configurations

- ✅ **Single-server deployment**
- ✅ **Docker containerization**
- ✅ **Reverse proxy (nginx/Caddy)**
- ✅ **SSL/TLS termination**
- ✅ **External databases**

### Community Support

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Community support
- **Documentation**: Comprehensive guides
- **Professional Services**: Enterprise support available

---

*"CHIMERA is designed for modern infrastructure. Ensure your environment meets these requirements for optimal performance."*


