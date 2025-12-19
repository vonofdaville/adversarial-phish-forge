# Contributing to CHIMERA Framework

Thank you for your interest in contributing to the CHIMERA Framework! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Security Considerations](#security-considerations)
- [Documentation](#documentation)
- [Commit Messages](#commit-messages)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

This project follows a [Code of Conduct](CODE_OF_CONDUCT.md) adapted for security research. By participating, you agree to uphold this code and maintain a respectful environment for all contributors.

## Getting Started

### Prerequisites

- **Python 3.11+** - Required for FastAPI and async operations
- **Docker 24.0+** - For containerized development and testing
- **Git** - Version control
- **Redis** - For caching and rate limiting (optional for basic development)

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lucien-vallois/adversarial-phish-forge.git
   cd adversarial-phish-forge
   ```

2. **Set up Python environment:**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Set up pre-commit hooks:**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Run basic tests:**
   ```bash
   pytest tests/unit/ -v
   ```

## Development Environment

### Directory Structure

```
chimera/
├── core/                    # Core security systems
│   ├── consent.py          # Consent verification
│   ├── kill_switch.py      # Emergency termination
│   └── rate_limiter.py     # Abuse prevention
├── telemetry/              # Data collection and privacy
│   ├── privacy_filter.py   # Credential sanitization
│   └── telemetry_collector.py
├── orchestrator/           # Campaign management
├── pretext_engine/         # AI content generation
├── email_delivery/         # SMTP and DKIM
├── identity_graph/         # OSINT correlation
├── models/                 # Data models
├── utils/                  # Shared utilities
└── cli/                    # Command-line interface
```

### Local Development

1. **Start infrastructure:**
   ```bash
   docker-compose up -d postgres redis neo4j clickhouse
   ```

2. **Initialize databases:**
   ```bash
   python scripts/init_consent_db.py
   python scripts/setup_test_data.py
   ```

3. **Run the application:**
   ```bash
   # Development mode
   uvicorn chimera.orchestrator.main:app --reload --host 0.0.0.0 --port 8000

   # With debugging
   PYTHONPATH=. python -m debugpy --listen 0.0.0.0:5678 -c "import uvicorn; uvicorn.run('chimera.orchestrator.main:app', reload=True)"
   ```

### Testing Environment

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chimera --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/security/      # Security tests

# Run linting
black . --check
isort . --check-only
mypy chimera/
flake8 chimera/
```

## Code Style and Standards

### Python Standards

We follow strict Python coding standards:

- **Formatter:** [Black](https://black.readthedocs.io/) (line length: 100)
- **Import sorting:** [isort](https://pycqa.github.io/isort/)
- **Type hints:** [mypy](https://mypy.readthedocs.io/) strict mode
- **Linting:** [flake8](https://flake8.pycqa.org/) with custom rules
- **Docstrings:** Google style

### Code Quality Requirements

```python
# Good: Type hints, docstrings, comprehensive error handling
def verify_consent(participant_id: UUID, organization_id: Optional[UUID] = None) -> ConsentResult:
    """Verify consent status for a participant.

    Args:
        participant_id: Unique identifier for the participant
        organization_id: Optional organization context

    Returns:
        ConsentResult with verification status

    Raises:
        ConsentException: If consent verification fails
    """
    try:
        # Implementation with proper error handling
        pass
    except Exception as e:
        logger.error(f"Consent verification failed: {e}")
        raise ConsentException(f"Verification failed: {e}")
```

### Security Standards

All code must adhere to security best practices:

- **Input validation:** All inputs validated and sanitized
- **Error handling:** No sensitive information in error messages
- **Logging:** No credentials or PII in logs
- **Async safety:** Thread-safe async operations
- **Resource limits:** Memory and CPU bounds enforced

## Testing

### Test Structure

```
tests/
├── unit/                   # Unit tests (no external dependencies)
├── integration/           # Integration tests (databases, APIs)
├── security/              # Security-specific tests
├── performance/           # Performance benchmarks
└── fixtures/              # Test data and mocks
```

### Testing Standards

- **Coverage:** Minimum 80% code coverage
- **Security tests:** All OWASP Top 10 scenarios covered
- **Consent tests:** 100% coverage of consent logic
- **Async tests:** Proper async testing patterns

### Writing Tests

```python
import pytest
from chimera.core.consent import ConsentVerifier

class TestConsentVerifier:
    @pytest.mark.asyncio
    async def test_valid_consent_approved(self, consent_verifier, valid_participant):
        """Test that valid consent is approved."""
        result = await consent_verifier.check_consent(valid_participant.id)

        assert result.status == ConsentStatus.VALID
        assert result.expiration_date > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_expired_consent_rejected(self, consent_verifier, expired_participant):
        """Test that expired consent is rejected."""
        result = await consent_verifier.check_consent(expired_participant.id)

        assert result.status == ConsentStatus.EXPIRED
        assert result.expiration_date < datetime.utcnow()
```

## Pull Request Process

### Before Submitting

1. **Update documentation** for any changed functionality
2. **Add tests** for new features
3. **Ensure tests pass** locally and in CI
4. **Update CHANGELOG.md** if applicable
5. **Self-review** your code

### PR Template

Use the standard PR template with:

- **Description:** What changes and why
- **Testing:** How tested and test results
- **Security:** Security implications and mitigations
- **Breaking changes:** Any breaking changes
- **Checklist:** All items checked

### Review Process

1. **Automated checks:** CI must pass all tests
2. **Security review:** Required for all PRs
3. **Code review:** At least one maintainer approval
4. **Documentation review:** Technical writers if needed

### Merging

- **Squash merge** preferred for clean history
- **Rebase** for updating from main branch
- **Force push** only to your own branches

## Security Considerations

### Critical Security Rules

1. **Never store credentials** - Even temporarily
2. **Validate all inputs** - No trust in external data
3. **Fail safely** - Deny access when uncertain
4. **Log securely** - No PII or secrets in logs
5. **Handle errors gracefully** - No information leakage

### Security Testing

```bash
# Run security tests
pytest tests/security/ -v

# Security linting
bandit -r chimera/
safety check

# Dependency scanning
pip-audit
```

### Vulnerability Reporting

See [SECURITY.md](SECURITY.md) for vulnerability disclosure procedures.

## Documentation

### Documentation Standards

- **README.md:** High-level overview and quick start
- **API docs:** OpenAPI 3.0 specification
- **Code docs:** Comprehensive docstrings
- **Architecture:** C4 model diagrams
- **Security:** Threat modeling documentation

### Documentation Updates

```bash
# Generate API documentation
python scripts/generate_api_docs.py

# Build documentation site
mkdocs build

# Serve docs locally
mkdocs serve
```

## Commit Messages

### Format

```
type(scope): description

[optional body]

[optional footer]
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes
- **refactor:** Code refactoring
- **test:** Test additions/modifications
- **chore:** Maintenance tasks
- **security:** Security-related changes

### Examples

```
feat(consent): add emergency override mechanism

Implement emergency consent override for critical security incidents.
Adds database schema changes and API endpoints.

BREAKING CHANGE: Requires database migration
```

```
security(auth): prevent token replay attacks

Add token expiration and nonce validation to prevent replay attacks.
Includes database schema changes for token tracking.

Fixes #123
```

## Issue Reporting

### Bug Reports

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml) with:

- Clear reproduction steps
- Expected vs actual behavior
- Environment details
- Security impact assessment

### Feature Requests

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml) with:

- Use case description
- Proposed solution
- Ethical considerations
- Legal compliance check

### Security Issues

**DO NOT file public issues for security vulnerabilities.**

Use the process in [SECURITY.md](SECURITY.md).

## Recognition

Contributors are recognized in:

- **CHANGELOG.md** for all contributions
- **GitHub contributors** list
- **Documentation credits** for major contributions
- **Security acknowledgments** for vulnerability reports

## Getting Help

- **Documentation:** Check docs/ directory first
- **Issues:** Search existing issues before creating new ones
- **Discussions:** Use GitHub Discussions for questions
- **Security:** security@chimera-project.org for security concerns

---

Thank you for contributing to making cybersecurity research safer and more ethical! 🛡️

**Last Updated:** December 2025
