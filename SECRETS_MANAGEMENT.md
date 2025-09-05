# ImagePod Secrets Management Guide

This guide explains how to generate, manage, and secure secrets for your ImagePod deployment.

## 🔑 **What are Secrets?**

Secrets are sensitive configuration values used by ImagePod for:
- **JWT Token Signing** - Creating and verifying authentication tokens
- **Password Encryption** - Hashing user passwords and sensitive data
- **Database Access** - PostgreSQL and Redis connection credentials
- **API Authentication** - Worker registration and API access tokens
- **Third-party Services** - Stripe, SMTP, and other service credentials

## 🛠️ **Generating Secrets**

### **Method 1: Using the Secret Generation Script (Recommended)**

```bash
# Generate all secrets automatically
./scripts/generate_secrets.sh
```

This script will:
- ✅ Generate cryptographically secure secrets
- ✅ Create a complete `.env` file
- ✅ Use different methods (Python, OpenSSL, /dev/urandom)
- ✅ Provide security recommendations

### **Method 2: Manual Generation**

#### **Using Python (Recommended)**
```bash
# Generate a 32-byte secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a random password
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(16)))"
```

#### **Using OpenSSL**
```bash
# Generate a base64-encoded secret
openssl rand -base64 32

# Generate a hex-encoded secret
openssl rand -hex 32
```

#### **Using /dev/urandom**
```bash
# Generate a base64-encoded secret
head -c 32 /dev/urandom | base64

# Generate a hex-encoded secret
head -c 32 /dev/urandom | hexdump -e '"%x"'
```

## 📋 **Required Secrets**

### **Core Application Secrets**

| Secret | Purpose | Length | Example |
|--------|---------|--------|---------|
| `SECRET_KEY` | JWT signing, encryption | 32+ bytes | `ilPaVPxmLKNso3N03FNrrgsLdiLBUYbsMrguNlqiWO0` |
| `POSTGRES_PASSWORD` | Database access | 16+ chars | `a7hQ^7fjK9mN2pL8` |
| `REDIS_PASSWORD` | Cache access | 16+ chars | `zUhssj!7mK3nP9qR` |
| `REGISTRATION_TOKEN` | Worker registration | 32+ bytes | `qV_mzCj4Gj9QIuhXh4MU...` |
| `API_KEY` | API authentication | 24+ bytes | `bZQNXGcWDsyUJnXV...` |

### **Optional Service Secrets**

| Secret | Purpose | When to Use |
|--------|---------|-------------|
| `STRIPE_SECRET_KEY` | Payment processing | When using billing features |
| `STRIPE_PUBLISHABLE_KEY` | Payment processing | When using billing features |
| `SMTP_PASSWORD` | Email notifications | When using email features |
| `DOCKER_REGISTRY_PASSWORD` | Private registry access | When using private Docker images |

## 🔒 **Security Best Practices**

### **1. Secret Generation**
- ✅ Use cryptographically secure random generators
- ✅ Generate secrets with sufficient entropy (32+ bytes)
- ✅ Use different secrets for different environments
- ✅ Never use predictable or weak secrets

### **2. Secret Storage**
- ✅ Store secrets in environment variables or `.env` files
- ✅ Never commit secrets to version control
- ✅ Use `.gitignore` to exclude `.env` files
- ✅ Encrypt secrets at rest in production

### **3. Secret Rotation**
- ✅ Regularly rotate secrets in production
- ✅ Have a plan for secret rotation without downtime
- ✅ Monitor for secret exposure
- ✅ Revoke compromised secrets immediately

### **4. Access Control**
- ✅ Limit access to secrets to authorized personnel
- ✅ Use principle of least privilege
- ✅ Audit secret access regularly
- ✅ Use secure communication channels

## 🏗️ **Environment-Specific Secrets**

### **Development Environment**
```bash
# Generate development secrets
./scripts/generate_secrets.sh

# Use weak secrets for development (not recommended for production)
SECRET_KEY=dev-secret-key-not-secure
POSTGRES_PASSWORD=dev123
```

### **Staging Environment**
```bash
# Generate staging secrets
./scripts/generate_secrets.sh

# Use different secrets from production
SECRET_KEY=staging-secret-key-different-from-prod
POSTGRES_PASSWORD=staging-password-different
```

### **Production Environment**
```bash
# Generate production secrets
./scripts/generate_secrets.sh

# Use strong, unique secrets
SECRET_KEY=production-secret-key-very-secure
POSTGRES_PASSWORD=production-password-very-secure
```

## 🔧 **Secret Management Tools**

### **For Development**
- **Local `.env` files** - Simple and effective
- **Docker secrets** - For containerized development
- **Environment variables** - For CI/CD pipelines

### **For Production**
- **HashiCorp Vault** - Enterprise secret management
- **AWS Secrets Manager** - Cloud-native secret management
- **Azure Key Vault** - Microsoft cloud secret management
- **Google Secret Manager** - Google cloud secret management
- **Kubernetes Secrets** - For containerized production

## 📁 **File Structure**

```
imagepod/
├── .env                    # Local development secrets (gitignored)
├── .env.example           # Template for secrets
├── .env.production        # Production secrets (gitignored)
├── .env.staging          # Staging secrets (gitignored)
├── scripts/
│   └── generate_secrets.sh # Secret generation script
└── k8s/
    └── secrets/           # Kubernetes secrets (gitignored)
```

## 🚀 **Deployment Examples**

### **Docker Compose**
```yaml
version: '3.8'
services:
  api:
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    env_file:
      - .env
```

### **Kubernetes**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: imagepod-secrets
type: Opaque
data:
  secret-key: <base64-encoded-secret>
  postgres-password: <base64-encoded-password>
```

### **Systemd Service**
```ini
[Service]
Environment=SECRET_KEY=your-secret-key
Environment=POSTGRES_PASSWORD=your-password
```

## 🔍 **Secret Validation**

### **Check Secret Strength**
```bash
# Check if secret is strong enough
python3 -c "
import secrets
import string

def check_secret_strength(secret):
    if len(secret) < 32:
        return 'Too short'
    if not any(c in string.ascii_letters for c in secret):
        return 'Missing letters'
    if not any(c in string.digits for c in secret):
        return 'Missing digits'
    return 'Strong'

secret = 'your-secret-here'
print(f'Secret strength: {check_secret_strength(secret)}')
"
```

### **Verify Secret Uniqueness**
```bash
# Check if secrets are unique across environments
diff .env .env.production
diff .env .env.staging
```

## 🐛 **Troubleshooting**

### **Common Issues**

#### **1. Weak Secrets**
```bash
# Error: Secret too weak
# Solution: Generate stronger secrets
./scripts/generate_secrets.sh
```

#### **2. Duplicate Secrets**
```bash
# Error: Same secret used in multiple environments
# Solution: Generate unique secrets for each environment
```

#### **3. Secret Exposure**
```bash
# Error: Secret committed to git
# Solution: 
git rm --cached .env
git commit -m "Remove exposed secrets"
./scripts/generate_secrets.sh
```

#### **4. Missing Secrets**
```bash
# Error: Required secret not found
# Solution: Check .env file and add missing secrets
```

## 📚 **Additional Resources**

### **Security Standards**
- [OWASP Secret Management](https://owasp.org/www-project-secrets-management/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/)
- [RFC 4086 - Randomness Requirements](https://tools.ietf.org/html/rfc4086)

### **Tools and Libraries**
- [Python secrets module](https://docs.python.org/3/library/secrets.html)
- [OpenSSL rand](https://www.openssl.org/docs/man1.1.1/man1/rand.html)
- [HashiCorp Vault](https://www.vaultproject.io/)

## 🎉 **Quick Start**

1. **Generate secrets:**
   ```bash
   ./scripts/generate_secrets.sh
   ```

2. **Review configuration:**
   ```bash
   cat .env
   ```

3. **Start ImagePod:**
   ```bash
   docker-compose up -d
   ```

4. **Verify secrets are working:**
   ```bash
   curl http://localhost:8000/health
   ```

Your ImagePod deployment is now secure with properly generated secrets! 🔒
