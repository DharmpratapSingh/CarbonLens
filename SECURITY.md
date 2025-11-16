# Security Policy

**Project:** ClimateGPT
**Version:** 0.3.0
**Last Updated:** 2025-11-16

---

## Table of Contents

1. [Supported Versions](#supported-versions)
2. [Reporting a Vulnerability](#reporting-a-vulnerability)
3. [Security Measures](#security-measures)
4. [Known Security Considerations](#known-security-considerations)
5. [Security Best Practices](#security-best-practices)
6. [Dependency Security](#dependency-security)
7. [Disclosure Policy](#disclosure-policy)

---

## Supported Versions

We release security updates for the following versions:

| Version | Supported          | End of Support |
|---------|--------------------|----------------|
| 0.3.x   | ✅ Yes             | Active         |
| 0.2.x   | ⚠️ Security fixes only | 2026-02-16 |
| 0.1.x   | ❌ No              | 2025-03-16     |
| < 0.1   | ❌ No              | Not supported  |

**Recommendation:** Always use the latest version for best security and features.

---

## Reporting a Vulnerability

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security vulnerabilities via one of these methods:

1. **GitHub Security Advisory (Preferred)**
   - Go to: https://github.com/DharmpratapSingh/Team-1B-Fusion/security/advisories
   - Click "Report a vulnerability"
   - Fill out the form with details

2. **Direct Email**
   - Email: [security contact - to be added]
   - Subject: "[SECURITY] Brief description"
   - Include: Detailed description, steps to reproduce, impact assessment

### What to Include

Please provide:
- **Description:** What is the vulnerability?
- **Impact:** What can an attacker do?
- **Reproduction:** Step-by-step instructions
- **Affected Versions:** Which versions are affected?
- **Proposed Fix:** If you have suggestions
- **Disclosure Timeline:** When you plan to publicly disclose (if applicable)

### Response Timeline

- **Initial Response:** Within 48 hours
- **Triage:** Within 7 days
- **Fix Development:** Within 30 days (depending on severity)
- **Public Disclosure:** Coordinated with reporter

### Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | Remote code execution, authentication bypass | 24 hours |
| **High** | SQL injection, XSS, data exposure | 7 days |
| **Medium** | Information disclosure, DoS | 14 days |
| **Low** | Minor information leaks, edge cases | 30 days |

---

## Security Measures

### Current Protections

#### ✅ Input Validation
- **Pydantic schema validation** for all API inputs
- **SQL injection prevention** via parameterized queries
- **Column name sanitization** (whitelist approach)
- **Type checking** for all parameters

#### ✅ Authentication & Authorization
- **API key validation** (username:password format)
- **No hardcoded credentials** (environment variables only)
- **Credential format validation** on startup

#### ✅ Rate Limiting
- **Default:** 100 requests per 60 seconds per IP
- **Configurable** via environment variables
- **Sliding window** algorithm
- **429 responses** with Retry-After headers

#### ✅ CORS Protection
- **Fail-closed** security model
- **Explicit origin whitelist** (no wildcards in production)
- **Configurable** via ALLOWED_ORIGINS
- **Validation** on every request

#### ✅ Error Handling
- **Production mode:** Generic error messages
- **Development mode:** Detailed errors (never in production)
- **No SQL query exposure** in error messages
- **Request ID tracking** for debugging

#### ✅ Code Injection Prevention
- **No eval()** usage (replaced with pandas.eval())
- **No exec()** or compile()
- **No pickle** for data serialization
- **Controlled dynamic imports** only

#### ✅ Dependency Security
- **Automated scanning** (pip-audit, bandit)
- **Dependabot** for security updates
- **License compliance** checking
- **Regular audits** (quarterly)

### Defense in Depth

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Network (CORS, Rate Limiting, HTTPS)  │
├─────────────────────────────────────────────────┤
│ Layer 2: Authentication (API Keys)             │
├─────────────────────────────────────────────────┤
│ Layer 3: Input Validation (Pydantic)           │
├─────────────────────────────────────────────────┤
│ Layer 4: Query Safety (Parameterized Queries)  │
├─────────────────────────────────────────────────┤
│ Layer 5: Error Handling (Sanitized Messages)   │
├─────────────────────────────────────────────────┤
│ Layer 6: Monitoring (Request IDs, Logging)     │
└─────────────────────────────────────────────────┘
```

---

## Known Security Considerations

### Database Access

**Consideration:** DuckDB is single-file, read-only

**Mitigations:**
- ✅ No write access from API
- ✅ File permissions restricted
- ✅ Connection pooling limits concurrent access
- ✅ No user-provided SQL execution

### LLM Integration

**Consideration:** LLM can be prompt-injected

**Mitigations:**
- ✅ Tool calls validated via Pydantic
- ✅ LLM output sanitized before database queries
- ✅ No direct SQL generation from LLM
- ✅ Structured tool responses only

### Environment Variables

**Consideration:** Credentials in environment variables

**Production Recommendation:**
- Use secrets management (Kubernetes Secrets, AWS Secrets Manager)
- Rotate credentials regularly
- Never commit .env files
- Use principle of least privilege

### Rate Limiting

**Consideration:** Per-IP rate limiting can be bypassed

**Mitigations:**
- ✅ IP-based limiting (basic protection)
- ⚠️ Consider adding user-based limits
- ⚠️ Consider adding API key-based limits

### CORS

**Consideration:** Misconfigured CORS can expose API

**Mitigations:**
- ✅ Fail-closed by default
- ✅ No wildcards allowed
- ✅ Explicit origin whitelist
- ✅ Production validation required

---

## Security Best Practices

### For Developers

#### 1. Input Validation

**Always validate user input:**

```python
# Good - Pydantic validation
from models.schemas import QueryEmissionsRequest

req = QueryEmissionsRequest(sector=sector, year=year)

# Bad - No validation
result = query_db(sector, year)  # Unsafe!
```

#### 2. SQL Safety

**Always use parameterized queries:**

```python
# Good
sql = "SELECT * FROM table WHERE year = ?"
result = conn.execute(sql, [2023]).fetchall()

# Bad - SQL injection risk!
sql = f"SELECT * FROM table WHERE year = {year}"
```

#### 3. Error Messages

**Never expose internal details:**

```python
# Good
from utils.error_handling import sanitize_sql_error

try:
    result = execute_query(sql)
except Exception as e:
    return {"error": sanitize_sql_error(e, sql)}

# Bad - Exposes SQL and stack trace!
except Exception as e:
    return {"error": str(e), "sql": sql}
```

#### 4. Secrets

**Never hardcode credentials:**

```python
# Good
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY required")

# Bad - Hardcoded secret!
api_key = "my-secret-key"
```

#### 5. Dependencies

**Keep dependencies updated:**

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade package_name

# Review Dependabot PRs
```

### For Deployment

#### 1. HTTPS Only

```yaml
# In production, enforce HTTPS
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
```

#### 2. Secrets Management

```bash
# Don't use environment variables in production
# Use secrets management instead

# Kubernetes
kubectl create secret generic api-keys \
  --from-literal=OPENAI_API_KEY='username:password'

# AWS
aws secretsmanager create-secret \
  --name climategpt/api-key \
  --secret-string '{"OPENAI_API_KEY":"username:password"}'
```

#### 3. Network Policies

```yaml
# Restrict network access
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: climategpt-policy
spec:
  podSelector:
    matchLabels:
      app: climategpt
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
```

#### 4. Resource Limits

```yaml
# Prevent DoS via resource exhaustion
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

---

## Dependency Security

### Automated Scanning

#### GitHub Actions

We run security scans on every push:

```yaml
# .github/workflows/security-scan.yml
- pip-audit (dependency vulnerabilities)
- bandit (code security issues)
- TruffleHog (secret scanning)
- Trivy (container scanning)
```

#### Dependabot

Automated dependency updates:

```yaml
# .github/dependabot.yml
- Weekly updates for Python packages
- Weekly updates for GitHub Actions
- Auto-create PRs for security patches
```

### Manual Audits

**Quarterly dependency audit:**

```bash
# Run audit script
python audit_dependencies.py

# Check for outdated packages
pip list --outdated

# Review licenses
pip-licenses --format=json
```

### Vulnerability Response

**If vulnerability found:**

1. **Assess Impact:** Does it affect us?
2. **Check Fix:** Is there a patch available?
3. **Update:** Upgrade to fixed version
4. **Test:** Run full test suite
5. **Deploy:** Emergency deployment if critical
6. **Document:** Update changelog

---

## Disclosure Policy

### Coordinated Disclosure

We follow **coordinated disclosure**:

1. **Report received** → Acknowledge within 48 hours
2. **Validate** → Confirm vulnerability within 7 days
3. **Fix** → Develop patch within 30 days
4. **Notify** → Inform reporter when fixed
5. **Coordinate** → Agree on public disclosure date
6. **Disclose** → Publish advisory and release

### Public Disclosure

After fix is released:

- **Security Advisory** on GitHub
- **CVE** if applicable
- **Blog Post** for critical issues
- **Credit** to reporter (if desired)

### Early Disclosure

For critical vulnerabilities (RCE, auth bypass):

- May disclose before fix if actively exploited
- Will coordinate with affected users
- Will provide workarounds if possible

---

## Security Checklist

### Development

- [ ] All inputs validated with Pydantic
- [ ] All database queries parameterized
- [ ] No hardcoded secrets
- [ ] Error messages sanitized
- [ ] Type hints on all functions
- [ ] Security-sensitive code reviewed
- [ ] Tests include security scenarios

### Deployment

- [ ] HTTPS/TLS enabled
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Secrets in vault (not env vars)
- [ ] Logs reviewed regularly
- [ ] Security updates automated
- [ ] Backup and recovery tested

### Monitoring

- [ ] Failed authentication attempts logged
- [ ] Rate limit violations logged
- [ ] Abnormal query patterns detected
- [ ] Error rates monitored
- [ ] Security advisories subscribed
- [ ] Incident response plan ready

---

## Incident Response

### If Security Incident Occurs

1. **Contain:** Isolate affected systems
2. **Assess:** Determine scope and impact
3. **Notify:** Inform affected users
4. **Remediate:** Fix vulnerability
5. **Review:** Post-mortem analysis
6. **Improve:** Update processes

### Emergency Contacts

- **Project Maintainers:** [To be added]
- **Security Team:** [To be added]
- **Hosting Provider:** [Cloud provider support]

---

## Security Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

*(To be populated with contributors)*

---

## Additional Resources

### External Links

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

### Internal Documentation

- `docs/ARCHITECTURE.md` - System architecture
- `docs/DEPLOYMENT.md` - Secure deployment guide
- `CONTRIBUTING.md` - Secure development practices

---

## Questions?

For security-related questions:
- **General:** GitHub Issues (for non-sensitive questions)
- **Sensitive:** Email security team (for sensitive matters)

---

**Thank you for helping keep ClimateGPT secure!** 🔒

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-16
**Next Review:** 2026-02-16
